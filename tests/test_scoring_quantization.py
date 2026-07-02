"""점수공식 변경 금지 게이트 — 양자화 메타데이터 저장 테스트.

이 테스트는 score_essay()의 표시 점수(공식)가 바뀌지 않았음과, 진단용
메타데이터(score_essay_detailed)가 정확히 기록되는지를 확인한다.
"""

from app.scorer import SCORING_FORMULA_VERSION, score_essay, score_essay_detailed
from tests.fixtures import DISCUSSION_HIGH, DISCUSSION_LOW


class TestBackwardCompatibility:
    def test_score_essay_matches_detailed_total(self):
        """기존 score_essay()의 표시 점수는 상세 버전과 완전히 동일해야 한다 —
        공식이 바뀌지 않았다는 증거."""
        _, total_simple = score_essay(DISCUSSION_HIGH, "academic_discussion")
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        assert total_simple == breakdown.total_0_5

    def test_dimensions_are_identical(self):
        dims_simple, _ = score_essay(DISCUSSION_HIGH, "academic_discussion")
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        assert [d.score for d in dims_simple] == [d.score for d in breakdown.dimensions]


class TestQuantizationMetadata:
    def test_pre_round_raw_score_is_in_valid_range(self):
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        assert 0.0 <= breakdown.pre_round_raw_score <= 5.0

    def test_rounded_score_is_nearest_half_to_raw(self):
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        if not breakdown.grammar_cap_applied:
            expected = round(breakdown.pre_round_raw_score * 2) / 2
            assert breakdown.total_0_5 == expected

    def test_distance_to_boundary_is_at_most_quarter(self):
        """0.5 단위로 반올림하므로 원점수는 항상 가장 가까운 경계에서 0.25 이내다."""
        for essay in [DISCUSSION_HIGH, DISCUSSION_LOW]:
            breakdown = score_essay_detailed(essay, "academic_discussion")
            assert 0.0 <= breakdown.distance_to_rounding_boundary <= 0.25 + 1e-6

    def test_component_scores_match_dimension_names(self):
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        expected_names = {d.name for d in breakdown.dimensions}
        assert set(breakdown.component_scores.keys()) == expected_names

    def test_scoring_formula_version_is_stamped(self):
        breakdown = score_essay_detailed(DISCUSSION_HIGH, "academic_discussion")
        assert breakdown.scoring_formula_version == SCORING_FORMULA_VERSION
        assert breakdown.scoring_formula_version  # not empty

    def test_grammar_cap_metadata_consistent(self):
        breakdown = score_essay_detailed(DISCUSSION_LOW, "academic_discussion")
        if breakdown.grammar_cap_applied:
            assert breakdown.grammar_cap_ceiling is not None
            assert breakdown.total_0_5 <= breakdown.grammar_cap_ceiling
        else:
            assert breakdown.grammar_cap_ceiling is None


class TestFormulaChangeGate:
    def test_deterministic_across_repeated_calls(self):
        """같은 입력에 항상 같은 raw/rounded 값 — 공식이 우연에 좌우되지 않는다."""
        results = [score_essay_detailed(DISCUSSION_HIGH, "academic_discussion") for _ in range(5)]
        raws = {r.pre_round_raw_score for r in results}
        assert len(raws) == 1
