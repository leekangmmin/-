"""app/pilot_comparison.py의 계산 로직 테스트.

여기서 쓰는 점수는 전부 계산 로직 검증을 위한 합성(synthetic) 값이다 —
실제 전문가/Claude 채점 결과가 아니다. 실제 데이터가 없을 때(현재 상태)
0건으로 정직하게 보고하는지가 가장 중요한 케이스다.
"""

from __future__ import annotations

from app.pilot_comparison import (
    MatchedTriple,
    boundary_region_analysis,
    build_pilot_comparison,
    multi_rater_agreement_summary,
)


class TestEmptyInput:
    def test_no_triples_reports_zero_and_insufficient(self):
        report = build_pilot_comparison([])
        assert report.comparable_count == 0
        assert report.insufficient_sample is True
        assert "insufficient sample" in report.pilot_only_warning
        assert report.heuristic_mae is None
        assert report.claude_reconciled_mae is None


class TestMaeAndAgreement:
    def test_mae_computed_correctly(self):
        triples = [
            MatchedTriple("r1", "academic_discussion", expert_score=4.0, heuristic_score=3.5, claude_reconciled_score=4.0),
            MatchedTriple("r2", "academic_discussion", expert_score=3.0, heuristic_score=3.5, claude_reconciled_score=2.5),
        ]
        report = build_pilot_comparison(triples)
        assert report.comparable_count == 2
        assert report.heuristic_mae == 0.5  # |4-3.5| + |3-3.5| = 1.0 / 2
        assert report.claude_reconciled_mae == 0.25  # (|4-4| + |3-2.5|) / 2 = 0.5 / 2

    def test_small_sample_always_flagged_insufficient(self):
        triples = [MatchedTriple(f"r{i}", "email", expert_score=4.0, heuristic_score=4.0) for i in range(10)]
        report = build_pilot_comparison(triples)
        assert report.insufficient_sample is True  # 10 < 30

    def test_within_0_5_agreement_counted(self):
        triples = [
            MatchedTriple("r1", "email", expert_score=4.0, claude_reconciled_score=4.4),  # within 0.5
            MatchedTriple("r2", "email", expert_score=4.0, claude_reconciled_score=5.0),  # not within
        ]
        report = build_pilot_comparison(triples)
        assert report.claude_within_0_5 == 1

    def test_over_and_under_estimate_counted_separately(self):
        triples = [
            MatchedTriple("r1", "email", expert_score=3.0, heuristic_score=4.0),  # over
            MatchedTriple("r2", "email", expert_score=4.0, heuristic_score=3.0),  # under
        ]
        report = build_pilot_comparison(triples)
        assert report.heuristic_overestimate_count == 1
        assert report.heuristic_underestimate_count == 1


class TestByTaskTypeBreakdown:
    def test_grouped_by_task_type(self):
        triples = [
            MatchedTriple("r1", "email", expert_score=4.0, heuristic_score=4.0),
            MatchedTriple("r2", "academic_discussion", expert_score=3.0, heuristic_score=2.0),
        ]
        report = build_pilot_comparison(triples)
        assert set(report.by_task_type.keys()) == {"email", "academic_discussion"}
        assert report.by_task_type["academic_discussion"]["heuristic_mae"] == 1.0


class TestNotableCases:
    def test_disagreement_in_direction_detected(self):
        triples = [
            MatchedTriple("r1", "email", expert_score=3.0, heuristic_score=4.0, claude_reconciled_score=2.0),
        ]
        report = build_pilot_comparison(triples)
        assert report.notable_cases["claude_and_heuristic_disagree_in_direction"] == "r1"

    def test_closest_and_farthest_identified(self):
        triples = [
            MatchedTriple("close", "email", expert_score=4.0, claude_reconciled_score=4.1),
            MatchedTriple("far", "email", expert_score=4.0, claude_reconciled_score=1.0),
        ]
        report = build_pilot_comparison(triples)
        assert report.notable_cases["claude_closest_to_expert"] == "close"
        assert report.notable_cases["claude_farthest_from_expert"] == "far"


class TestMultiRaterAgreement:
    def test_no_groups_reports_unmeasurable(self):
        result = multi_rater_agreement_summary([])
        assert result["measurable"] is False
        assert result["multi_rater_group_count"] == 0

    def test_single_rater_groups_excluded(self):
        result = multi_rater_agreement_summary([[4.0]])
        assert result["measurable"] is False

    def test_agreement_rates_computed(self):
        result = multi_rater_agreement_summary([[4.0, 4.0], [3.0, 4.5]])
        assert result["measurable"] is True
        assert result["multi_rater_group_count"] == 2
        assert result["exact_agreement_rate"] == 0.5
        assert result["max_observed_disagreement"] == 1.5


class TestBoundaryRegionAnalysis:
    def test_no_boundary_metadata_reports_unmeasurable(self):
        triples = [MatchedTriple("r1", "email", expert_score=4.0, heuristic_score=4.0)]
        result = boundary_region_analysis(triples)
        assert result["measurable"] is False

    def test_near_and_far_split_correctly(self):
        triples = [
            MatchedTriple("near1", "email", expert_score=4.0, heuristic_score=4.0,
                          distance_to_rounding_boundary=0.05),
            MatchedTriple("far1", "email", expert_score=3.0, heuristic_score=4.0,
                          distance_to_rounding_boundary=0.4),
        ]
        result = boundary_region_analysis(triples, boundary_threshold=0.1)
        assert result["measurable"] is True
        assert result["near_boundary_count"] == 1
        assert result["far_from_boundary_count"] == 1
        assert result["near_boundary_heuristic_mae"] == 0.0
        assert result["far_from_boundary_heuristic_mae"] == 1.0

    def test_small_sample_flagged(self):
        triples = [MatchedTriple("r1", "email", expert_score=4.0, heuristic_score=4.0,
                                 distance_to_rounding_boundary=0.05)]
        result = boundary_region_analysis(triples)
        assert result["sample_too_small_for_conclusion"] is True
