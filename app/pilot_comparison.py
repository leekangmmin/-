"""전문가·Claude(shadow)·휴리스틱 최초 pilot comparison 구조 (Phase 4, 마스터 스펙 13~14장).

**이 모듈이 계산하는 수치는 파일럿(10~20건) 규모에서는 정확도 결론의 근거가
아니다.** `insufficient_sample=True`와 함께 `pilot_only` 경고를 항상 동반한다.
이 모듈의 결과로 점수 공식이나 캘리브레이션을 즉시 바꾸지 않는다
(`docs/scoring-formula-change-gate.md` 참고).

매칭 방법: 전문가 데이터의 `response_text`를 `app.expert_data.exact_hash()`와
동일한 해시 함수로 해싱해, 같은 텍스트가 이미 앱을 통해 채점된 제출
(`data/submissions.db`)이 있는지 찾는다. 매칭되면 그 제출에 연결된 shadow
비교 결과(`data/shadow_assessments.db`, `historical_submission_id` 기준)도
함께 가져와 3자 비교를 만든다. 전문가 데이터가 앱을 거치지 않은 완전히
새로운 답안이라면(파일럿에서는 흔함) 매칭되지 않는다 — 이 경우 휴리스틱/Claude
점수 없이 전문가 점수만 존재하므로 비교에서 제외된다.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_MIN_SAMPLE_FOR_ANY_CONCLUSION = 30  # 이 미만이면 항상 pilot-only/불충분 경고
_AGREEMENT_TOLERANCE = 0.5


@dataclass
class MatchedTriple:
    """전문가 점수, 휴리스틱 점수, Claude 점수가 모두(또는 일부) 존재하는 한 답안."""

    record_id: str
    task_type: str
    expert_score: float
    heuristic_score: float | None = None
    claude_reconciled_score: float | None = None
    claude_raw_score: float | None = None
    distance_to_rounding_boundary: float | None = None
    pre_round_raw_score: float | None = None


@dataclass
class PilotComparisonReport:
    comparable_count: int
    insufficient_sample: bool
    pilot_only_warning: str
    heuristic_mae: float | None = None
    claude_raw_mae: float | None = None
    claude_reconciled_mae: float | None = None
    heuristic_within_0_5: int | None = None
    claude_within_0_5: int | None = None
    heuristic_overestimate_count: int = 0
    heuristic_underestimate_count: int = 0
    claude_overestimate_count: int = 0
    claude_underestimate_count: int = 0
    by_task_type: dict[str, dict[str, Any]] = field(default_factory=dict)
    notable_cases: dict[str, str | None] = field(default_factory=dict)


def _mae(pairs: list[tuple[float, float]]) -> float | None:
    if not pairs:
        return None
    return round(sum(abs(a - b) for a, b in pairs) / len(pairs), 4)


def build_pilot_comparison(triples: list[MatchedTriple]) -> PilotComparisonReport:
    """휴리스틱/Claude/전문가 점수가 모두 있는 매칭 답안들로 비교 리포트를 만든다.

    호출부(scripts/run_pilot_comparison.py)가 expert_data.db + submissions.db +
    shadow_assessments.db를 조인해 triples를 만들고 이 함수에 넘긴다 — 이 함수
    자체는 저장소에 접근하지 않아 순수 함수로 테스트 가능하다.
    """
    n = len(triples)
    insufficient = n < _MIN_SAMPLE_FOR_ANY_CONCLUSION
    warning = (
        f"pilot-only, insufficient sample (n={n} < {_MIN_SAMPLE_FOR_ANY_CONCLUSION}) — "
        "statistically inconclusive. calibration prohibited, production promotion prohibited."
        if insufficient else
        f"n={n}; still verify against a locked_test split before treating as conclusive."
    )

    heur_pairs = [(t.expert_score, t.heuristic_score) for t in triples if t.heuristic_score is not None]
    claude_raw_pairs = [(t.expert_score, t.claude_raw_score) for t in triples if t.claude_raw_score is not None]
    claude_rec_pairs = [
        (t.expert_score, t.claude_reconciled_score) for t in triples if t.claude_reconciled_score is not None
    ]

    heur_within = sum(1 for e, h in heur_pairs if abs(e - h) <= _AGREEMENT_TOLERANCE) if heur_pairs else None
    claude_within = (
        sum(1 for e, c in claude_rec_pairs if abs(e - c) <= _AGREEMENT_TOLERANCE) if claude_rec_pairs else None
    )

    heur_over = sum(1 for e, h in heur_pairs if h > e)
    heur_under = sum(1 for e, h in heur_pairs if h < e)
    claude_over = sum(1 for e, c in claude_rec_pairs if c > e)
    claude_under = sum(1 for e, c in claude_rec_pairs if c < e)

    by_task: dict[str, dict[str, Any]] = {}
    for t in triples:
        bucket = by_task.setdefault(t.task_type, {"count": 0, "heur_pairs": [], "claude_pairs": []})
        bucket["count"] += 1
        if t.heuristic_score is not None:
            bucket["heur_pairs"].append((t.expert_score, t.heuristic_score))
        if t.claude_reconciled_score is not None:
            bucket["claude_pairs"].append((t.expert_score, t.claude_reconciled_score))
    by_task_summary = {
        task_type: {
            "count": b["count"],
            "heuristic_mae": _mae(b["heur_pairs"]),
            "claude_mae": _mae(b["claude_pairs"]),
        }
        for task_type, b in by_task.items()
    }

    notable: dict[str, str | None] = {
        "claude_closest_to_expert": None,
        "claude_farthest_from_expert": None,
        "heuristic_closest_to_expert": None,
        "heuristic_farthest_from_expert": None,
        "claude_and_heuristic_disagree_in_direction": None,
    }
    claude_diffs = [(t.record_id, abs(t.expert_score - t.claude_reconciled_score))
                     for t in triples if t.claude_reconciled_score is not None]
    if claude_diffs:
        notable["claude_closest_to_expert"] = min(claude_diffs, key=lambda x: x[1])[0]
        notable["claude_farthest_from_expert"] = max(claude_diffs, key=lambda x: x[1])[0]
    heur_diffs = [(t.record_id, abs(t.expert_score - t.heuristic_score))
                   for t in triples if t.heuristic_score is not None]
    if heur_diffs:
        notable["heuristic_closest_to_expert"] = min(heur_diffs, key=lambda x: x[1])[0]
        notable["heuristic_farthest_from_expert"] = max(heur_diffs, key=lambda x: x[1])[0]
    for t in triples:
        if t.heuristic_score is None or t.claude_reconciled_score is None:
            continue
        heur_dir = t.heuristic_score - t.expert_score
        claude_dir = t.claude_reconciled_score - t.expert_score
        if heur_dir * claude_dir < 0:  # 반대 방향(하나는 과대, 하나는 과소)
            notable["claude_and_heuristic_disagree_in_direction"] = t.record_id
            break

    return PilotComparisonReport(
        comparable_count=n,
        insufficient_sample=insufficient,
        pilot_only_warning=warning,
        heuristic_mae=_mae(heur_pairs),
        claude_raw_mae=_mae(claude_raw_pairs),
        claude_reconciled_mae=_mae(claude_rec_pairs),
        heuristic_within_0_5=heur_within,
        claude_within_0_5=claude_within,
        heuristic_overestimate_count=heur_over,
        heuristic_underestimate_count=heur_under,
        claude_overestimate_count=claude_over,
        claude_underestimate_count=claude_under,
        by_task_type=by_task_summary,
        notable_cases=notable,
    )


def boundary_region_analysis(triples: list[MatchedTriple], boundary_threshold: float = 0.1) -> dict[str, Any]:
    """0.5 단위 반올림 경계 근처 답안이 실제로 더 부정확한지 분석한다
    (마스터 스펙 16장, `docs/scoring-formula-change-gate.md`의 게이트 전제 조건).

    `distance_to_rounding_boundary`가 없는 triple은 제외한다(휴리스틱 점수가
    없거나 quantization 메타데이터가 없는 경우). 이 함수는 공식을 바꾸지
    않는다 — 관찰만 한다.
    """
    with_boundary = [
        t for t in triples
        if t.distance_to_rounding_boundary is not None and t.heuristic_score is not None
    ]
    if not with_boundary:
        return {
            "measurable": False,
            "note": "distance_to_rounding_boundary 메타데이터가 있는 매칭 답안 없음 — 측정 불가",
        }

    near = [t for t in with_boundary if t.distance_to_rounding_boundary <= boundary_threshold]
    far = [t for t in with_boundary if t.distance_to_rounding_boundary > boundary_threshold]

    near_mae = _mae([(t.expert_score, t.heuristic_score) for t in near]) if near else None
    far_mae = _mae([(t.expert_score, t.heuristic_score) for t in far]) if far else None

    rounded_up = [t for t in with_boundary if t.pre_round_raw_score is not None and t.heuristic_score > t.pre_round_raw_score]
    rounded_down = [t for t in with_boundary if t.pre_round_raw_score is not None and t.heuristic_score < t.pre_round_raw_score]

    return {
        "measurable": True,
        "boundary_threshold": boundary_threshold,
        "near_boundary_count": len(near),
        "far_from_boundary_count": len(far),
        "near_boundary_heuristic_mae": near_mae,
        "far_from_boundary_heuristic_mae": far_mae,
        "rounded_up_count": len(rounded_up),
        "rounded_down_count": len(rounded_down),
        "sample_too_small_for_conclusion": len(with_boundary) < _MIN_SAMPLE_FOR_ANY_CONCLUSION,
    }


def multi_rater_agreement_summary(rater_score_groups: list[list[float]]) -> dict[str, Any]:
    """복수 채점자 데이터가 있을 때 인간 채점자 간 합의 범위를 계산한다.

    모델 오차를 인간 채점자 간 불일치보다 더 정밀하게 요구하지 않기 위해,
    모델 MAE를 인간 채점자 간 평균 최대 편차와 나란히 봐야 한다
    (마스터 스펙 14장).
    """
    groups = [g for g in rater_score_groups if len(g) >= 2]
    if not groups:
        return {
            "multi_rater_group_count": 0,
            "measurable": False,
            "note": "복수 채점자 데이터 없음 — 구조만 유지, 측정 불가",
        }
    exact_agreement = sum(1 for g in groups if max(g) == min(g))
    within_0_5 = sum(1 for g in groups if max(g) - min(g) <= _AGREEMENT_TOLERANCE)
    max_diffs = [max(g) - min(g) for g in groups]
    return {
        "multi_rater_group_count": len(groups),
        "measurable": True,
        "exact_agreement_rate": round(exact_agreement / len(groups), 4),
        "within_0_5_agreement_rate": round(within_0_5 / len(groups), 4),
        "avg_max_disagreement": round(sum(max_diffs) / len(max_diffs), 4),
        "max_observed_disagreement": round(max(max_diffs), 4),
    }
