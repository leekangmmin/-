#!/usr/bin/env python3
"""전문가 데이터 + 휴리스틱 점수 + Claude shadow 점수를 매칭해 최초 pilot
comparison을 생성한다 (Phase 4, 마스터 스펙 13~14장).

매칭은 텍스트 정확 해시 기준이다: 전문가가 채점한 답안(response_text)이
이 앱을 통해 이미 채점된 제출(data/submissions.db)과 텍스트가 완전히 같으면
그 제출의 휴리스틱 점수와, 같은 제출에 연결된 shadow(Claude) 결과를 함께 가져와
3자 비교 행을 만든다. 매칭되지 않으면(흔함 — 파일럿 데이터는 보통 앱을 거치지
않은 새 답안) 전문가 점수만 있고 비교에서는 제외된다.

실제 전문가 데이터가 없으면(현재 상태) comparable_count=0으로 보고하고
"실제 데이터 대기"로 표시한다 — 가상 전문가 점수를 만들지 않는다.

사용법:
    .venv/bin/python scripts/run_pilot_comparison.py
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import list_recent, get_submission
from app.expert_data import exact_hash, group_ratings, list_records
from app.pilot_comparison import (
    MatchedTriple,
    boundary_region_analysis,
    build_pilot_comparison,
    multi_rater_agreement_summary,
)
from app.shadow_mode import init_shadow_db, _conn as _shadow_conn  # noqa: PLC2701 — 읽기 전용 조회 목적


def _submission_hash_index() -> dict[str, dict]:
    """data/submissions.db의 모든 제출을 텍스트 해시로 색인한다 (매칭용)."""
    index: dict[str, dict] = {}
    for row in list_recent(limit=100000):
        record = get_submission(row["id"])
        if record is None or not record.get("essay_text"):
            continue
        index[exact_hash(record["essay_text"])] = record
    return index


def _latest_claude_shadow_for_submission(submission_id: int) -> dict | None:
    init_shadow_db()
    with _shadow_conn() as conn:
        row = conn.execute(
            "SELECT * FROM shadow_comparisons WHERE historical_submission_id = ? AND provider = 'claude' "
            "ORDER BY created_at DESC LIMIT 1",
            (submission_id,),
        ).fetchone()
    return dict(row) if row else None


def main() -> None:
    expert_records = list_records(limit=5000)
    print(f"전문가 레코드 수(전체 split 합계): {len(expert_records)}")

    if not expert_records:
        print("\n[전문가 데이터 없음] 실제 전문가 데이터 대기 상태 — 가상 데이터로 비교를 만들지 않는다.")
        report = build_pilot_comparison([])
        print(json.dumps(_report_to_dict(report), indent=2, ensure_ascii=False))
        return

    submission_index = _submission_hash_index()
    triples: list[MatchedTriple] = []
    unmatched = 0
    for rec in expert_records:
        h = exact_hash(rec["response_text"])
        submission = submission_index.get(h)
        if submission is None:
            unmatched += 1
            continue
        heuristic_score = float(submission["result"].get("estimated_score_0_5", 0.0))
        quantization = submission["result"].get("scoring_quantization") or {}
        shadow_row = _latest_claude_shadow_for_submission(submission["id"])
        triples.append(MatchedTriple(
            record_id=rec["record_id"],
            task_type=rec["task_type"],
            expert_score=float(rec["overall_score"]),
            heuristic_score=heuristic_score,
            claude_raw_score=shadow_row["ai_raw_score_0_5"] if shadow_row else None,
            claude_reconciled_score=shadow_row["ai_reconciled_score_0_5"] if shadow_row else None,
            distance_to_rounding_boundary=quantization.get("distance_to_rounding_boundary"),
            pre_round_raw_score=quantization.get("pre_round_raw_score"),
        ))

    print(f"매칭된 비교 가능 답안: {len(triples)} / 미매칭(앱 미채점 원본): {unmatched}")

    report = build_pilot_comparison(triples)
    print(json.dumps(_report_to_dict(report), indent=2, ensure_ascii=False))

    # multi-rater
    group_ids = {rec.get("response_group_id") for rec in expert_records if rec.get("response_group_id")}
    rater_groups = [
        [float(r["overall_score"]) for r in group_ratings(gid)]
        for gid in group_ids
    ]
    print("\n=== 복수 채점자 합의 ===")
    print(json.dumps(multi_rater_agreement_summary(rater_groups), indent=2, ensure_ascii=False))

    print("\n=== 양자화 경계 분석 (공식 변경 금지 게이트 참고용, 공식은 바꾸지 않음) ===")
    print(json.dumps(boundary_region_analysis(triples), indent=2, ensure_ascii=False))


def _report_to_dict(report) -> dict:
    from dataclasses import asdict
    return asdict(report)


if __name__ == "__main__":
    main()
