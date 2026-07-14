"""Production score bridge tests; all provider traffic is mocked."""

from __future__ import annotations

import json

import httpx

from app.operational_grader import grade_operational_task
from app.toefl_2026_grader import ACADEMIC_DISCUSSION_DIMENSIONS

ESSAY = " ".join(f"word{i}" for i in range(100))


def _valid_grade() -> dict:
    return {
        "task_type": "academic_discussion",
        "word_count": 100,
        "in_target_range": True,
        "overall_score": 4,
        "band_label": "Strong task response",
        "required_points": {"covered": ["answer the question"], "missed": []},
        "dimensions": {
            key: {"score": 4, "comment": "Clear and effective."}
            for key in ACADEMIC_DISCUSSION_DIMENSIONS
        },
        "caps_triggered": [],
        "template_flag": {"detected": False, "evidence": []},
        "error_patterns": [],
        "meaning_impeding_error_count": 0,
        "strengths": ["Clear position"],
        "priority_fixes": ["Add one more concrete detail"],
        "one_line_verdict": "A strong response.",
    }


def _cfg(provider: str = "openai") -> dict:
    return {
        "provider": provider,
        "enabled": True,
        "openai_api_key": "test-openai-key",
        "openai_model": "gpt-test",
        "anthropic_api_key": "test-anthropic-key",
        "anthropic_model": "claude-test",
        "gemini_api_key": "test-gemini-key",
        "gemini_model": "gemini-test",
    }


def test_openai_structured_grade_becomes_operational_score():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "output": [
                    {
                        "type": "message",
                        "content": [
                            {"type": "output_text", "text": json.dumps(_valid_grade())}
                        ],
                    }
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    outcome = grade_operational_task(
        task_type="academic_discussion",
        essay_text=ESSAY,
        prompt_text="Which approach is more useful?",
        cfg=_cfg(),
        client=client,
    )

    assert outcome.source == "llm"
    assert outcome.grade is not None
    assert outcome.grade.overall_score == 4
    assert seen["store"] is False
    assert seen["text"]["format"]["type"] == "json_schema"
    assert seen["text"]["format"]["strict"] is True
    assert ESSAY not in seen["instructions"]
    assert ESSAY in seen["input"]


def test_invalid_provider_output_falls_back_without_breaking_evaluation():
    def handler(_: httpx.Request) -> httpx.Response:
        return httpx.Response(
            200,
            json={"output": [{"content": [{"type": "output_text", "text": "{}"}]}]},
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    outcome = grade_operational_task(
        task_type="academic_discussion",
        essay_text=ESSAY,
        prompt_text="A practice question",
        cfg=_cfg(),
        client=client,
    )
    assert outcome.grade is None
    assert outcome.source == "heuristic_fallback"
    assert "내장 기준" in outcome.detail


def test_gemini_uses_json_schema_and_validated_result():
    seen: dict = {}

    def handler(request: httpx.Request) -> httpx.Response:
        seen.update(json.loads(request.content))
        return httpx.Response(
            200,
            json={
                "candidates": [
                    {"content": {"parts": [{"text": json.dumps(_valid_grade())}]}}
                ]
            },
        )

    client = httpx.Client(transport=httpx.MockTransport(handler))
    outcome = grade_operational_task(
        task_type="academic_discussion",
        essay_text=ESSAY,
        prompt_text="A practice question",
        cfg=_cfg("gemini"),
        client=client,
    )
    assert outcome.source == "llm"
    assert outcome.grade is not None
    assert seen["generationConfig"]["responseMimeType"] == "application/json"
    assert seen["generationConfig"]["responseJsonSchema"]["additionalProperties"] is False


def test_disabled_cloud_ai_uses_deterministic_score_without_network():
    cfg = _cfg()
    cfg["enabled"] = False
    outcome = grade_operational_task(
        task_type="academic_discussion",
        essay_text=ESSAY,
        prompt_text="A practice question",
        cfg=cfg,
    )
    assert outcome.grade is None
    assert outcome.source == "heuristic"
    assert outcome.provider == "local"
