"""evidence 검증 실패 시 재시도/무효화 로직 테스트.

MockScoringProvider가 아니라 호출 횟수별로 다른 evidence를 반환하도록 만든
테스트 전용 provider를 사용해 재시도 경로를 정확히 통제한다.
"""

from __future__ import annotations

from app.scoring_provider import (
    AssessmentCritique,
    DimensionAssessment,
    DimensionScoreResult,
    EvidenceSpan,
    FeedbackResult,
    InputAnalysis,
    InputValidation,
    ScoringInput,
    ScoringProvider,
)

ESSAY = "I believe schools should teach coding because it builds logical thinking skills for students today."
REAL_SENTENCE = "I believe schools should teach coding because it builds logical thinking skills for students today."


class _AlwaysHallucinatingProvider(ScoringProvider):
    """모든 시도에서 존재하지 않는 evidence를 반환한다 — invalid_assessment로 귀결돼야 한다."""

    id = "test-hallucinating"
    max_evidence_retries = 1

    def __init__(self):
        self.score_dimensions_calls = 0

    def analyze_input(self, scoring_input):
        return InputValidation(is_scorable=True), InputAnalysis()

    def score_dimensions(self, scoring_input, analysis):
        self.score_dimensions_calls += 1
        bad_evidence = EvidenceSpan(start=0, end=10, text="NONEXISTENT TEXT NOT IN ESSAY", dimension_id="content")
        return DimensionScoreResult(
            dimensions=[DimensionAssessment("content", 4.0, 5.0, "explanation", [bad_evidence])],
            overall_draft_score=4.0,
        )

    def critique_assessment(self, scoring_input, draft):
        return AssessmentCritique(severity="none")

    def generate_feedback(self, scoring_input, final_score):
        return FeedbackResult(summary="ok")


class _RecoversOnRetryProvider(ScoringProvider):
    """첫 호출은 환각 evidence, 재시도 시에는 올바른 evidence를 반환한다."""

    id = "test-recovers"
    max_evidence_retries = 1

    def __init__(self):
        self.score_dimensions_calls = 0

    def analyze_input(self, scoring_input):
        return InputValidation(is_scorable=True), InputAnalysis()

    def score_dimensions(self, scoring_input, analysis):
        self.score_dimensions_calls += 1
        if self.score_dimensions_calls == 1:
            evidence = [EvidenceSpan(start=0, end=10, text="WRONG", dimension_id="content")]
        else:
            real = scoring_input.essay_text[:9]
            evidence = [EvidenceSpan(start=0, end=9, text=real, dimension_id="content")]
        return DimensionScoreResult(
            dimensions=[DimensionAssessment("content", 4.0, 5.0, "explanation", evidence)],
            overall_draft_score=4.0,
        )

    def critique_assessment(self, scoring_input, draft):
        return AssessmentCritique(severity="none")

    def generate_feedback(self, scoring_input, final_score):
        return FeedbackResult(summary="ok")


class _AlwaysCorrectProvider(ScoringProvider):
    id = "test-correct"

    def __init__(self):
        self.score_dimensions_calls = 0

    def analyze_input(self, scoring_input):
        return InputValidation(is_scorable=True), InputAnalysis()

    def score_dimensions(self, scoring_input, analysis):
        self.score_dimensions_calls += 1
        real = scoring_input.essay_text[:9]
        evidence = [EvidenceSpan(start=0, end=9, text=real, dimension_id="content")]
        return DimensionScoreResult(
            dimensions=[DimensionAssessment("content", 4.0, 5.0, "explanation", evidence)],
            overall_draft_score=4.0,
        )

    def critique_assessment(self, scoring_input, draft):
        return AssessmentCritique(severity="none")

    def generate_feedback(self, scoring_input, final_score):
        return FeedbackResult(summary="ok")


class TestEvidenceRetryAndInvalidation:
    def test_always_hallucinating_triggers_retry_then_invalid(self):
        provider = _AlwaysHallucinatingProvider()
        result = provider.run(ScoringInput(ESSAY, "", "academic_discussion"))

        assert provider.score_dimensions_calls == 2  # 최초 1회 + 재시도 1회
        assert result.retry_count == 1
        assert result.invalid_assessment is True
        assert "invalid_assessment_low_evidence_confidence" in result.reason_codes
        assert result.confidence == "low"

    def test_hallucinated_evidence_never_exposed_in_result(self):
        provider = _AlwaysHallucinatingProvider()
        result = provider.run(ScoringInput(ESSAY, "", "academic_discussion"))
        # 검증 실패한 evidence는 draft에서 제거돼야 한다 — UI/비교 리포트에 노출 금지
        for dim in result.draft.dimensions:
            assert all(e.verified for e in dim.evidence)
            assert len(dim.evidence) == 0  # 유일한 evidence가 가짜였으므로 전부 제거됨

    def test_recovers_on_retry_is_not_marked_invalid(self):
        provider = _RecoversOnRetryProvider()
        result = provider.run(ScoringInput(ESSAY, "", "academic_discussion"))

        assert provider.score_dimensions_calls == 2
        assert result.retry_count == 1
        assert result.invalid_assessment is False
        assert result.evidence_verified == result.evidence_total == 1

    def test_correct_evidence_does_not_trigger_retry(self):
        provider = _AlwaysCorrectProvider()
        result = provider.run(ScoringInput(ESSAY, "", "academic_discussion"))

        assert provider.score_dimensions_calls == 1  # 재시도 없음
        assert result.retry_count == 0
        assert result.invalid_assessment is False
        assert result.confidence == "high"

    def test_retry_is_bounded_by_max_evidence_retries(self):
        provider = _AlwaysHallucinatingProvider()
        provider.max_evidence_retries = 3
        provider.run(ScoringInput(ESSAY, "", "academic_discussion"))
        assert provider.score_dimensions_calls == 4  # 최초 1회 + 재시도 3회, 무한루프 아님
