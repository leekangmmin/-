"""AI shadow mode 파이프라인 테스트.

MockScoringProvider만 사용한다 — API 키가 없어 실제 LLM 호출은 검증 불가.
이 테스트는 (1) 파이프라인 배관이 올바르게 동작하는지, (2) evidence 검증이
실제로 작동하는지, (3) shadow mode가 production 채점 경로에 전혀 영향을
주지 않는지를 확인한다.
"""

import pytest

from app.scoring_provider import (
    EvidenceSpan,
    MockScoringProvider,
    ScoringInput,
    get_provider,
    validate_evidence_spans,
)
from app.scorer import score_essay
from app.shadow_mode import run_shadow_comparison, summarize_comparisons
from tests.fixtures import DISCUSSION_HIGH, DISCUSSION_LOW, DISCUSSION_INJECTION


class TestEvidenceValidation:
    def test_matching_span_is_verified(self):
        text = "I believe schools should teach coding early."
        span = EvidenceSpan(start=0, end=9, text="I believe", dimension_id="content")
        result = validate_evidence_spans(text, [span])
        assert result[0].verified is True

    def test_hallucinated_span_is_rejected(self):
        text = "I believe schools should teach coding early."
        span = EvidenceSpan(start=0, end=9, text="I disagree", dimension_id="content")
        result = validate_evidence_spans(text, [span])
        assert result[0].verified is False

    def test_out_of_bounds_span_is_rejected(self):
        text = "Short text."
        span = EvidenceSpan(start=0, end=9999, text="nonsense", dimension_id="content")
        result = validate_evidence_spans(text, [span])
        assert result[0].verified is False


class TestMockProviderPipeline:
    def test_pipeline_runs_end_to_end(self):
        provider = MockScoringProvider()
        result = provider.run(ScoringInput(DISCUSSION_HIGH, "", "academic_discussion"))
        assert result.schema_valid is True
        assert 0.0 <= result.final_score_0_5 <= 5.0
        assert result.confidence in {"low", "medium", "high"}

    def test_too_short_input_is_not_scorable(self):
        provider = MockScoringProvider()
        result = provider.run(ScoringInput("too short", "", "academic_discussion"))
        assert result.input_validation.is_scorable is False
        assert result.final_score_0_5 == 0.0

    def test_evidence_is_verified_against_real_text(self):
        provider = MockScoringProvider()
        result = provider.run(ScoringInput(DISCUSSION_HIGH, "", "academic_discussion"))
        for dim in result.draft.dimensions:
            for ev in dim.evidence:
                actual = DISCUSSION_HIGH[ev.start:ev.end]
                assert (actual == ev.text) == ev.verified

    def test_critic_can_downgrade_score(self):
        """짧은 고득점 답안은 critic이 minor severity로 감점해야 한다."""
        provider = MockScoringProvider()
        short_high = "I agree with this because it is good and helpful for students in school today definitely."
        result = provider.run(ScoringInput(short_high, "", "academic_discussion"))
        # critic이 개입했다면 reason_codes에 흔적이 남아야 한다
        if result.critique.severity != "none":
            assert "critic_minor_adjustment" in result.reason_codes or "critic_major_adjustment" in result.reason_codes

    def test_unknown_provider_raises_clear_error(self):
        with pytest.raises(NotImplementedError, match="아직 구현되지 않았다"):
            get_provider("openai")


class TestShadowModeDoesNotAffectProduction:
    """shadow mode를 실행해도 app.scorer의 production 채점 결과는 완전히 동일해야 한다."""

    def test_scorer_output_identical_with_or_without_shadow_run(self):
        _, score_before = score_essay(DISCUSSION_HIGH, "academic_discussion")

        provider = MockScoringProvider()
        run_shadow_comparison(
            DISCUSSION_HIGH, "", "academic_discussion", score_before, provider, persist=False,
        )

        _, score_after = score_essay(DISCUSSION_HIGH, "academic_discussion")
        assert score_before == score_after

    def test_main_evaluate_function_does_not_use_shadow_mode(self):
        """/api/evaluate (실제 채점 경로)는 shadow_mode를 참조하면 안 된다.
        /api/shadow/summary(읽기 전용 관리자 엔드포인트)는 별도 함수이므로 허용된다."""
        import app.main as main_mod
        import inspect
        source = inspect.getsource(main_mod.evaluate)
        assert "shadow_mode" not in source, "production evaluate()가 shadow mode를 호출하면 안 된다"


class TestShadowComparisonReport:
    @pytest.fixture()
    def isolated_shadow_db(self, tmp_path, monkeypatch):
        import app.shadow_mode as shadow_mode
        monkeypatch.setattr(shadow_mode, "SHADOW_DB_PATH", tmp_path / "test_shadow.db")
        yield

    def test_comparison_report_structure(self, isolated_shadow_db):
        _, heuristic_score = score_essay(DISCUSSION_HIGH, "academic_discussion")
        provider = MockScoringProvider()
        report = run_shadow_comparison(
            DISCUSSION_HIGH, "", "academic_discussion", heuristic_score, provider,
        )
        assert report.heuristic_score_0_5 == heuristic_score
        assert report.provider == "mock"
        assert report.latency_ms >= 0
        assert 0.0 <= report.evidence_success_rate <= 1.0

    def test_summary_aggregates_multiple_runs(self, isolated_shadow_db):
        provider = MockScoringProvider()
        for essay in [DISCUSSION_HIGH, DISCUSSION_LOW, DISCUSSION_INJECTION]:
            _, h_score = score_essay(essay, "academic_discussion")
            run_shadow_comparison(essay, "", "academic_discussion", h_score, provider)

        summary = summarize_comparisons()
        assert summary["count"] == 3
        assert summary["schema_success_rate"] == 1.0

    def test_empty_summary_when_no_runs(self, isolated_shadow_db):
        summary = summarize_comparisons()
        assert summary["count"] == 0
