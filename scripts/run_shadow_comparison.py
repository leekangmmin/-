#!/usr/bin/env python3
"""저장된 실제 제출 답안에 대해 shadow AI 비교를 일괄 실행한다.

현재는 MockScoringProvider만 사용 가능하다 (API 키 없음). 실제 LLM provider가
연결되면 --provider openai 등으로 교체할 수 있게 설계했다 (아직 미구현,
app/scoring_provider.get_provider 참고).

사용법:
    .venv/bin/python scripts/run_shadow_comparison.py --limit 20
    .venv/bin/python scripts/run_shadow_comparison.py --summary
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_submission, list_recent
from app.scoring_provider import get_provider
from app.shadow_mode import run_shadow_comparison, summarize_comparisons


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--provider", default="mock", help="현재는 'mock'만 지원 (API 키 없음)")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--summary", action="store_true", help="실행 없이 기존 비교 리포트 요약만 출력")
    args = parser.parse_args()

    if args.summary:
        print(summarize_comparisons())
        return

    provider = get_provider(args.provider)
    summary_rows = list_recent(limit=args.limit)
    print(f"Running shadow comparison for {len(summary_rows)} historical submissions using provider={provider.id}...")

    for summary_row in summary_rows:
        record = get_submission(summary_row["id"])
        if record is None:
            continue
        essay_text = record.get("essay_text", "")
        if not essay_text:
            continue
        heuristic_score = float(record["result"].get("estimated_score_0_5", 0.0))
        task_type = record.get("prompt_type", "academic_discussion")
        report = run_shadow_comparison(
            essay_text, "", task_type, heuristic_score, provider,
            historical_submission_id=record["id"],
        )
        print(f"  #{record['id']}: heuristic={report.heuristic_score_0_5} "
              f"ai_raw={report.ai_raw_score_0_5} ai_reconciled={report.ai_reconciled_score_0_5} "
              f"delta={report.score_delta} evidence={report.evidence_verified}/{report.evidence_total} "
              f"retry={report.retry_count} invalid={report.invalid_assessment} confidence={report.confidence}")

    print("\n=== Summary ===")
    print(summarize_comparisons())


if __name__ == "__main__":
    main()
