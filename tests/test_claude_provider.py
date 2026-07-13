"""실제 Claude provider 테스트.

API 키가 없으므로 실제 Anthropic 서버에 호출하지 않는다. 대신 httpx.MockTransport로
HTTP 계층을 가짜로 만들어 (1) 요청 페이로드 구조, (2) JSON 파싱, (3) 재시도/타임아웃
처리, (4) 인증 실패 처리, (5) 로그에 답안 원문이 노출되지 않는지를 검증한다.

이것은 "내 코드가 응답을 올바르게 처리하는가"의 테스트이지, "Claude가 좋은 점수를
주는가"의 테스트가 아니다 — 후자는 실제 API 키 없이는 검증 불가하다.
"""

from __future__ import annotations

import json
import logging

import httpx
import pytest

from app.claude_provider import (
    ClaudeScoringProvider,
    ProviderCallError,
    _content_fingerprint,
    call_claude,
)
from app.scoring_provider import ScoringInput, get_shadow_provider
from app.shadow_config import ShadowConfig, load_shadow_config

SAMPLE_ESSAY = "I believe schools should teach coding because it builds logical thinking skills for every student."


def _claude_message_response(json_body: dict) -> dict:
    return {
        "content": [{"type": "text", "text": json.dumps(json_body)}],
        "id": "msg_test",
        "model": "claude-3-5-sonnet-latest",
    }


def _mock_transport(handler):
    return httpx.MockTransport(handler)


@pytest.fixture()
def cfg() -> ShadowConfig:
    return ShadowConfig(
        enabled=True, provider="claude", anthropic_api_key="test-key-not-real",
        model="claude-3-5-sonnet-latest", timeout_seconds=5.0, max_retries=2,
    )


class TestCallClaude:
    def test_missing_api_key_raises_before_any_call(self):
        bad_cfg = ShadowConfig(
            enabled=True, provider="claude", anthropic_api_key="",
            model="x", timeout_seconds=5.0, max_retries=1,
        )
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(bad_cfg, "system", {"a": 1}, stage="test")
        assert exc_info.value.reason_code == "missing_api_key"

    def test_successful_call_returns_parsed_json(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            assert body["model"] == cfg.model
            assert "system" in body
            return httpx.Response(200, json=_claude_message_response({"ok": True, "value": 42}))

        client = httpx.Client(transport=_mock_transport(handler))
        result = call_claude(cfg, "system prompt", {"key": "value"}, stage="test", client=client, sleep_fn=lambda s: None)
        assert result == {"ok": True, "value": 42}

    def test_request_wraps_student_response_as_data_not_instruction(self, cfg):
        captured = {}

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            captured["system"] = body["system"]
            captured["user_content"] = json.loads(body["messages"][0]["content"])
            return httpx.Response(200, json=_claude_message_response({"ok": True}))

        client = httpx.Client(transport=_mock_transport(handler))
        call_claude(cfg, "sys with untrusted data notice", {"student_response": SAMPLE_ESSAY},
                    stage="analyze_input", client=client, sleep_fn=lambda s: None)

        assert "student_response" in captured["user_content"]
        assert captured["user_content"]["student_response"] == SAMPLE_ESSAY

    def test_401_raises_auth_failed_without_exhausting_retries(self, cfg):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(401, json={"error": "unauthorized"})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code == "auth_failed"
        assert call_count["n"] == 1  # 인증 실패는 재시도하지 않음

    def test_timeout_retries_then_fails_with_reason_code(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            raise httpx.TimeoutException("simulated timeout")

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code == "timeout"

    def test_retry_then_succeed(self, cfg):
        attempts = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 2:
                return httpx.Response(500, json={"error": "server error"})
            return httpx.Response(200, json=_claude_message_response({"recovered": True}))

        client = httpx.Client(transport=_mock_transport(handler))
        result = call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert result == {"recovered": True}
        assert attempts["n"] == 2

    def test_invalid_json_response_fails_with_reason_code(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"content": [{"type": "text", "text": "not json at all !!"}]})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code in {"call_failed_after_retries", "timeout"}

    def test_truncated_json_response_fails_with_reason_code(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json={"content": [{"type": "text", "text": '{"dimensions": [{"dimension_id":'}]})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code in {"call_failed_after_retries", "timeout"}

    def test_429_retries_with_backoff_then_succeeds(self, cfg):
        attempts = {"n": 0}
        sleeps: list[float] = []

        def handler(request: httpx.Request) -> httpx.Response:
            attempts["n"] += 1
            if attempts["n"] < 2:
                return httpx.Response(429, json={"error": "rate_limited"})
            return httpx.Response(200, json=_claude_message_response({"ok": True}))

        client = httpx.Client(transport=_mock_transport(handler))
        result = call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=sleeps.append)
        assert result == {"ok": True}
        assert attempts["n"] == 2
        assert sleeps  # 429는 백오프 후 재시도한다

    def test_429_exhausted_retries_fails_with_reason_code(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(429, json={"error": "rate_limited"})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code == "call_failed_after_retries"

    def test_500_exhausted_retries_fails_with_reason_code(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(500, json={"error": "server_error"})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code == "call_failed_after_retries"

    def test_403_raises_auth_failed_without_exhausting_retries(self, cfg):
        call_count = {"n": 0}

        def handler(request: httpx.Request) -> httpx.Response:
            call_count["n"] += 1
            return httpx.Response(403, json={"error": "forbidden"})

        client = httpx.Client(transport=_mock_transport(handler))
        with pytest.raises(ProviderCallError) as exc_info:
            call_claude(cfg, "system", {}, stage="test", client=client, sleep_fn=lambda s: None)
        assert exc_info.value.reason_code == "auth_failed"
        assert call_count["n"] == 1


class TestNoContentInLogs:
    def test_essay_text_not_in_log_records(self, cfg, caplog):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({"ok": True}))

        client = httpx.Client(transport=_mock_transport(handler))
        with caplog.at_level(logging.INFO, logger="toefl.shadow.claude"):
            call_claude(cfg, "system", {"student_response": SAMPLE_ESSAY}, stage="analyze_input",
                        client=client, sleep_fn=lambda s: None)

        for record in caplog.records:
            assert SAMPLE_ESSAY not in record.getMessage()

    def test_fingerprint_does_not_contain_raw_text(self):
        fp = _content_fingerprint(SAMPLE_ESSAY)
        assert SAMPLE_ESSAY not in fp
        assert "len=" in fp and "sha256=" in fp


class TestClaudeProviderPipeline:
    def test_analyze_input_parses_response_into_dataclasses(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "is_scorable": True,
                "reason_codes": [],
                "warnings": [],
                "requirements": [{"requirement": "state a position", "status": "met", "evidence_text": "I believe"}],
                "main_claims": ["schools should teach coding"],
                "off_topic_risk": False,
                "template_risk": False,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        validation, analysis = provider.analyze_input(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"))
        assert validation.is_scorable is True
        assert analysis.requirements[0].status == "met"

    def test_score_dimensions_validates_evidence_against_real_text(self, cfg):
        first_sentence_end = SAMPLE_ESSAY.index(".") + 1

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "dimensions": [{
                    "dimension_id": "elaboration_relevance", "score": 4.0, "max_score": 5.0,
                    "explanation": "clear claim",
                    "evidence": [
                        {"start": 0, "end": first_sentence_end, "text": SAMPLE_ESSAY[:first_sentence_end], "explanation": "thesis"},
                        {"start": 0, "end": 5, "text": "WRONG TEXT", "explanation": "hallucinated"},
                    ],
                }],
                "overall_draft_score": 4.0,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis, validate_evidence_spans

        draft = provider.score_dimensions(
            ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"),
            InputAnalysis(),
        )
        validated = validate_evidence_spans(SAMPLE_ESSAY, draft.dimensions[0].evidence)
        assert validated[0].verified is True
        assert validated[1].verified is False  # 환각 evidence는 코드에서 걸러짐

    def test_full_pipeline_end_to_end_with_mocked_transport(self, cfg):
        responses = {
            "analyze_input": {
                "is_scorable": True, "reason_codes": [], "warnings": [],
                "requirements": [], "main_claims": [], "off_topic_risk": False, "template_risk": False,
            },
            "score_dimensions": {
                "dimensions": [{"dimension_id": "elaboration_relevance", "score": 3.5, "max_score": 5.0, "explanation": "ok", "evidence": []}],
                "overall_draft_score": 3.5,
            },
            "critique_assessment": {"flagged_dimension_ids": [], "issues": [], "severity": "none"},
            "generate_feedback": {"summary": "good job", "priority_issues": []},
        }
        call_log = []

        def handler(request: httpx.Request) -> httpx.Response:
            body = json.loads(request.content)
            user_content = json.loads(body["messages"][0]["content"])
            # stage를 구분할 근거가 없으므로 순서로 유추 (테스트 내부 목적)
            stage = list(responses.keys())[len(call_log)]
            call_log.append(stage)
            return httpx.Response(200, json=_claude_message_response(responses[stage]))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        result = provider.run(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"))

        assert call_log == ["analyze_input", "score_dimensions", "critique_assessment", "generate_feedback"]
        assert result.schema_valid is True
        assert 0.0 <= result.final_score_0_5 <= 5.0


class TestScoreDimensionsSchemaValidation:
    """score_dimensions 응답이 스키마를 어길 때 실패 유형이 구분되는지 검증한다
    (마스터 스펙 6장: schema_validation_failed / score_out_of_range / unsupported_task_type)."""

    def test_missing_dimensions_field_raises_schema_validation_failed(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({"overall_draft_score": 3.0}))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        with pytest.raises(ProviderCallError) as exc_info:
            provider.score_dimensions(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"), InputAnalysis())
        assert exc_info.value.reason_code == "schema_validation_failed"

    def test_unknown_dimension_id_raises_schema_validation_failed(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "dimensions": [{"dimension_id": "made_up_dimension", "score": 3.0, "max_score": 5.0,
                                 "explanation": "x", "evidence": []}],
                "overall_draft_score": 3.0,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        with pytest.raises(ProviderCallError) as exc_info:
            provider.score_dimensions(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"), InputAnalysis())
        assert exc_info.value.reason_code == "schema_validation_failed"

    def test_score_above_max_raises_score_out_of_range(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "dimensions": [{"dimension_id": "elaboration_relevance", "score": 9.9, "max_score": 5.0,
                                 "explanation": "x", "evidence": []}],
                "overall_draft_score": 9.9,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        with pytest.raises(ProviderCallError) as exc_info:
            provider.score_dimensions(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"), InputAnalysis())
        assert exc_info.value.reason_code == "score_out_of_range"

    def test_negative_score_raises_score_out_of_range(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "dimensions": [{"dimension_id": "elaboration_relevance", "score": -1.0, "max_score": 5.0,
                                 "explanation": "x", "evidence": []}],
                "overall_draft_score": 0.0,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        with pytest.raises(ProviderCallError) as exc_info:
            provider.score_dimensions(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"), InputAnalysis())
        assert exc_info.value.reason_code == "score_out_of_range"

    def test_malformed_evidence_offsets_raise_schema_validation_failed(self, cfg):
        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(200, json=_claude_message_response({
                "dimensions": [{"dimension_id": "elaboration_relevance", "score": 3.0, "max_score": 5.0,
                                 "explanation": "x",
                                 "evidence": [{"start": "not-an-int", "end": 5, "text": "x", "explanation": "y"}]}],
                "overall_draft_score": 3.0,
            }))

        client = httpx.Client(transport=_mock_transport(handler))
        provider = ClaudeScoringProvider(cfg, client=client)
        from app.scoring_provider import InputAnalysis

        with pytest.raises(ProviderCallError) as exc_info:
            provider.score_dimensions(ScoringInput(SAMPLE_ESSAY, "", "academic_discussion"), InputAnalysis())
        assert exc_info.value.reason_code == "schema_validation_failed"


class TestShadowConfigAndAvailability:
    def test_disabled_by_default(self, monkeypatch):
        monkeypatch.delenv("TOEFL_SHADOW_ENABLED", raising=False)
        cfg = load_shadow_config()
        assert cfg.enabled is False

    def test_enabled_via_env(self, monkeypatch):
        monkeypatch.setenv("TOEFL_SHADOW_ENABLED", "1")
        cfg = load_shadow_config()
        assert cfg.enabled is True

    def test_get_shadow_provider_disabled(self, monkeypatch):
        monkeypatch.delenv("TOEFL_SHADOW_ENABLED", raising=False)
        provider, availability = get_shadow_provider()
        assert provider is None
        assert availability.reason_code == "shadow_disabled"

    def test_get_shadow_provider_missing_key(self, monkeypatch):
        monkeypatch.setenv("TOEFL_SHADOW_ENABLED", "1")
        monkeypatch.setenv("TOEFL_SHADOW_PROVIDER", "claude")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        provider, availability = get_shadow_provider()
        assert provider is None
        assert availability.reason_code == "missing_api_key"

    def test_get_shadow_provider_claude_available_with_key(self, monkeypatch):
        monkeypatch.setenv("TOEFL_SHADOW_ENABLED", "1")
        monkeypatch.setenv("TOEFL_SHADOW_PROVIDER", "claude")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "fake-key-for-test")
        provider, availability = get_shadow_provider()
        assert provider is not None
        assert provider.id == "claude"
        assert availability.available is True

    def test_get_shadow_provider_unknown_provider(self, monkeypatch):
        monkeypatch.setenv("TOEFL_SHADOW_ENABLED", "1")
        monkeypatch.setenv("TOEFL_SHADOW_PROVIDER", "not_a_real_provider")
        provider, availability = get_shadow_provider()
        assert provider is None
        assert availability.reason_code == "unknown_provider"

    def test_app_does_not_crash_without_api_key(self, monkeypatch):
        """앱 기동 시 API 키가 없어도 예외가 나지 않아야 한다."""
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        monkeypatch.delenv("TOEFL_SHADOW_ENABLED", raising=False)
        provider, availability = get_shadow_provider()
        assert provider is None
        assert isinstance(availability.reason_code, str)
