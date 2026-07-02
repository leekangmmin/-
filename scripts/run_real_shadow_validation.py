#!/usr/bin/env python3
"""실제 Claude provider로 shadow validation을 실행한다 (Phase 4).

**비용을 발생시킨다.** 다음 조건을 모두 만족해야 실제 네트워크 호출을 수행한다:
1. `ANTHROPIC_API_KEY` 환경변수 존재
2. `TOEFL_SHADOW_ENABLED=1`
3. `TOEFL_SHADOW_PROVIDER=claude`
4. CLI 플래그 `--i-understand-this-costs-money`
5. `--limit`으로 최대 실행 건수 명시
6. `--max-estimated-cost-usd`로 예산 상한 명시

조건 중 하나라도 빠지면 dry-run만 수행하고 종료한다 (실제 호출 없음).
결과는 프로덕션 DB(`data/submissions.db`)가 아니라 shadow DB
(`data/shadow_assessments.db`)에만 저장된다 — `app/shadow_mode.run_shadow_comparison`이
이미 이 격리를 보장한다.

사용법:
    # dry-run (API 키 유무와 무관하게 항상 안전) — 실제 호출 없음
    .venv/bin/python scripts/run_real_shadow_validation.py --limit 5 --dry-run

    # 실제 호출 (비용 발생, 명시적 동의 필요)
    .venv/bin/python scripts/run_real_shadow_validation.py \\
        --limit 5 --max-estimated-cost-usd 1.00 --i-understand-this-costs-money
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.db import get_submission, list_recent
from app.scoring_provider import ScoringInput, get_shadow_provider
from app.shadow_mode import (
    SHADOW_DB_PATH,
    already_processed_submission_ids,
    run_shadow_comparison,
    summarize_comparisons,
)
from app.shadow_config import load_shadow_config

# 4단계(analyze_input/score_dimensions/critique_assessment/generate_feedback) 호출당
# 대략적인 토큰 상한 추정치. 실제 사용량과 다를 수 있다 — 사전 예산 계산용일 뿐이다.
_ESTIMATED_CALLS_PER_ESSAY = 4
_ESTIMATED_INPUT_TOKENS_PER_CALL = 900
_ESTIMATED_OUTPUT_TOKENS_PER_CALL = 500
_CONSECUTIVE_FAILURE_STOP_THRESHOLD = 3


def _estimate_run_cost(model: str, essay_count: int) -> float | None:
    from app.claude_provider import estimate_cost_usd

    total_input = essay_count * _ESTIMATED_CALLS_PER_ESSAY * _ESTIMATED_INPUT_TOKENS_PER_CALL
    total_output = essay_count * _ESTIMATED_CALLS_PER_ESSAY * _ESTIMATED_OUTPUT_TOKENS_PER_CALL
    return estimate_cost_usd(model, total_input, total_output)


def _select_targets(limit: int) -> list[dict]:
    """최근 제출 답안 중 실행 대상을 고른다. 답안 원문은 콘솔에 절대 출력하지 않는다."""
    targets = []
    for row in list_recent(limit=limit * 3):  # skip 대상 감안해 여유 있게 조회
        record = get_submission(row["id"])
        if record is None:
            continue
        if not record.get("essay_text"):
            continue
        targets.append(record)
        if len(targets) >= limit:
            break
    return targets


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--limit", type=int, required=True, help="최대 실행 건수")
    parser.add_argument("--max-estimated-cost-usd", type=float, default=None,
                         help="예상 비용 상한(USD). 실제 호출 시 필수.")
    parser.add_argument("--i-understand-this-costs-money", action="store_true",
                         help="실제 API 호출에 동의함을 명시하는 플래그. 없으면 dry-run만 수행.")
    parser.add_argument("--dry-run", action="store_true", help="강제로 dry-run만 수행 (실제 호출 없음)")
    parser.add_argument("--force", action="store_true",
                         help="이미 같은 provider/model로 처리된 답안도 다시 실행 (기본은 중복 스킵)")
    args = parser.parse_args()

    cfg = load_shadow_config()
    provider, availability = get_shadow_provider()

    live_call_requested = (
        not args.dry_run
        and args.i_understand_this_costs_money
        and args.max_estimated_cost_usd is not None
    )

    print("=== Real Claude Shadow Validation (Phase 4) ===")
    print(f"provider(config)     : {cfg.provider}")
    print(f"model                : {cfg.model}")
    print(f"shadow enabled       : {cfg.enabled}")
    print(f"api key present      : {bool(cfg.anthropic_api_key)}")
    print(f"provider availability: {availability.reason_code} (available={availability.available})")
    print(f"timeout(s)           : {cfg.timeout_seconds}")
    print(f"max retries          : {cfg.max_retries}")
    print(f"target essay count   : {args.limit}")
    print(f"estimated calls      : {args.limit * _ESTIMATED_CALLS_PER_ESSAY} "
          f"({_ESTIMATED_CALLS_PER_ESSAY} stage calls x {args.limit} essays)")
    est_cost = _estimate_run_cost(cfg.model, args.limit)
    print(f"estimated max cost   : {'$%.4f' % est_cost if est_cost is not None else 'unknown model — cannot estimate'}")
    print(f"result storage       : {SHADOW_DB_PATH} (production DB is NOT touched)")
    print("production score path: unaffected (this script never calls app.scorer or writes to data/submissions.db)")
    print("raw essay logging    : never printed to console or logs (length/hash fingerprint only)")

    if not live_call_requested:
        reasons = []
        if args.dry_run:
            reasons.append("--dry-run specified")
        if not args.i_understand_this_costs_money:
            reasons.append("missing --i-understand-this-costs-money")
        if args.max_estimated_cost_usd is None:
            reasons.append("missing --max-estimated-cost-usd")
        print(f"\n[DRY RUN ONLY] 실제 API 호출을 수행하지 않는다. 이유: {', '.join(reasons)}")
        if not availability.available:
            print(f"[DRY RUN] 참고: 현재 설정으로는 실제 호출도 불가능함 (reason_code={availability.reason_code})")
        targets = _select_targets(args.limit)
        print(f"[DRY RUN] 실행 대상 후보: {len(targets)}건 (원문 미노출, ID만 표시)")
        for t in targets:
            print(f"  candidate submission_id={t['id']} task_type={t.get('prompt_type', 'unknown')}")
        return 0

    if not availability.available or provider is None:
        print(f"\n[ABORT] 실제 호출 조건은 충족했지만 provider를 사용할 수 없다: "
              f"reason_code={availability.reason_code} detail={availability.detail}")
        return 1

    if provider.id != "claude":
        print(f"\n[ABORT] TOEFL_SHADOW_PROVIDER가 'claude'가 아니다 (현재: {provider.id}). "
              "실제 유료 검증은 claude provider에서만 지원한다.")
        return 1

    max_cost = args.max_estimated_cost_usd
    if est_cost is not None and est_cost > max_cost:
        print(f"\n[ABORT] 예상 비용(${est_cost:.4f})이 예산 상한(${max_cost:.4f})을 초과한다. "
              "--limit을 줄이거나 --max-estimated-cost-usd를 높여라.")
        return 1

    processed_ids = set() if args.force else already_processed_submission_ids(provider.id, cfg.model)
    targets = [t for t in _select_targets(args.limit) if args.force or t["id"] not in processed_ids]
    if not targets:
        print("\n[INFO] 실행할 새 대상이 없다 (이미 전부 처리됐거나 원문이 없는 제출뿐).")
        return 0

    print(f"\n[LIVE] {len(targets)}건 실제 Claude 호출을 시작한다 (예산 상한 ${max_cost:.4f}).")

    running_cost = 0.0
    consecutive_failures = 0
    results = []
    interrupted = False
    try:
        for record in targets:
            essay_text = record["essay_text"]
            task_type = record.get("prompt_type", "academic_discussion")
            heuristic_score = float(record["result"].get("estimated_score_0_5", 0.0))

            report = run_shadow_comparison(
                essay_text, "", task_type, heuristic_score, provider,
                historical_submission_id=record["id"],
            )
            results.append(report)

            cost_this_call = report.estimated_cost_usd or 0.0
            running_cost += cost_this_call
            failed = report.failure_reason is not None or report.invalid_assessment
            consecutive_failures = consecutive_failures + 1 if failed else 0

            print(f"  submission_id={record['id']} status={'FAIL' if failed else 'ok'} "
                  f"heuristic={report.heuristic_score_0_5} ai_reconciled={report.ai_reconciled_score_0_5} "
                  f"evidence={report.evidence_verified}/{report.evidence_total} "
                  f"schema_valid={report.schema_valid} cost=${cost_this_call:.4f} "
                  f"running_cost=${running_cost:.4f} failure_reason={report.failure_reason}")

            if running_cost >= max_cost:
                print(f"\n[STOP] 누적 예상 비용(${running_cost:.4f})이 예산 상한(${max_cost:.4f})에 도달해 중단한다.")
                break
            if consecutive_failures >= _CONSECUTIVE_FAILURE_STOP_THRESHOLD:
                print(f"\n[STOP] 연속 실패 {consecutive_failures}건으로 중단한다 (임계값 {_CONSECUTIVE_FAILURE_STOP_THRESHOLD}).")
                break
    except KeyboardInterrupt:
        interrupted = True
        print(f"\n[INTERRUPTED] Ctrl+C — 지금까지 완료된 {len(results)}건은 이미 shadow DB에 저장됐다. 안전하게 종료한다.")

    print(f"\n=== 실행 결과 ({'중단됨' if interrupted else '완료'}) ===")
    print(f"처리 건수: {len(results)} / 대상 {len(targets)}")
    print(f"누적 예상 비용: ${running_cost:.4f}")
    print(f"저장 위치: {SHADOW_DB_PATH}")
    print("\n=== Shadow DB 누적 요약 ===")
    print(summarize_comparisons())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
