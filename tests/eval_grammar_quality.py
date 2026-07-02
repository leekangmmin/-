"""문법 신호 엔진의 precision/recall/F1 을 카테고리별로 계산한다.

사용법:
    .venv/bin/python -m tests.eval_grammar_quality

"정상 문장 오탐 0건"만으로는 충분하지 않다 — 이 스크립트는 실제 오류를
놓치지 않는지(recall)까지 카테고리별로 측정하고, 현재 엔진이 아예 다루지
않는 언어 현상(공백 카테고리)을 명시적으로 표시한다.
"""

from __future__ import annotations

from collections import defaultdict

from app.grammar import analyze_grammar
from tests.grammar_eval_dataset import DATASET

NOT_IMPLEMENTED_CATEGORIES = {
    "pronoun_reference", "capitalization", "word_form", "collocation",
}


def predict(text: str) -> bool:
    """현재 제품이 실제로 사용자에게 노출하는 신호: 총 오류 카운트 > 0."""
    return analyze_grammar(text).total > 0


def evaluate() -> dict:
    per_category: dict[str, dict[str, int]] = defaultdict(lambda: {"tp": 0, "fp": 0, "tn": 0, "fn": 0})
    overall = {"tp": 0, "fp": 0, "tn": 0, "fn": 0}
    failures: list[dict] = []

    for item in DATASET:
        predicted = predict(item.text)
        actual = item.expects_error

        if predicted and actual:
            bucket = "tp"
        elif predicted and not actual:
            bucket = "fp"
        elif not predicted and not actual:
            bucket = "tn"
        else:
            bucket = "fn"

        per_category[item.category][bucket] += 1
        overall[bucket] += 1

        if bucket in ("fp", "fn"):
            failures.append({
                "id": item.id, "category": item.category, "type": item.item_type,
                "text": item.text, "expected": actual, "predicted": predicted,
                "bucket": bucket, "note": item.note,
            })

    def prf(counts: dict[str, int]) -> dict[str, float]:
        tp, fp, fn = counts["tp"], counts["fp"], counts["fn"]
        precision = tp / (tp + fp) if (tp + fp) else (1.0 if fn == 0 else 0.0)
        recall = tp / (tp + fn) if (tp + fn) else (1.0 if fp == 0 else 0.0)
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
        return {"precision": round(precision, 3), "recall": round(recall, 3), "f1": round(f1, 3)}

    category_report = {}
    for cat, counts in sorted(per_category.items()):
        report = {**counts, **prf(counts)}
        report["not_implemented"] = cat in NOT_IMPLEMENTED_CATEGORIES
        category_report[cat] = report

    return {
        "overall": {**overall, **prf(overall)},
        "categories": category_report,
        "failures": failures,
        "total_items": len(DATASET),
    }


def main() -> None:
    result = evaluate()
    o = result["overall"]
    from tests.grammar_eval_dataset import GRAMMAR_FIXTURE_VERSION

    print(f"=== 문법 엔진 품질 평가 (fixture v{GRAMMAR_FIXTURE_VERSION}, {result['total_items']}개 라벨링 항목) ===")
    print(f"전체: precision={o['precision']} recall={o['recall']} f1={o['f1']} "
          f"(TP={o['tp']} FP={o['fp']} TN={o['tn']} FN={o['fn']})")
    print()
    print(f"{'카테고리':<22}{'precision':>10}{'recall':>10}{'f1':>8}  TP/FP/TN/FN")
    for cat, r in result["categories"].items():
        flag = " [미구현]" if r["not_implemented"] else ""
        print(f"{cat:<22}{r['precision']:>10}{r['recall']:>10}{r['f1']:>8}  "
              f"{r['tp']}/{r['fp']}/{r['tn']}/{r['fn']}{flag}")

    if result["failures"]:
        print(f"\n=== 대표 실패 사례 ({len(result['failures'])}건) ===")
        for f in result["failures"]:
            print(f"[{f['bucket'].upper()}] {f['id']} ({f['category']}): \"{f['text'][:70]}\"")
            print(f"    expected_error={f['expected']} predicted_error={f['predicted']}  note={f['note']}")

    # 구현된 카테고리(not_implemented=False)에서 FP/FN 이 있으면 회귀로 간주해 실패 처리.
    # 미구현 카테고리는 알려진 공백이므로 게이트에서 제외한다.
    implemented_failures = [
        f for f in result["failures"] if f["category"] not in NOT_IMPLEMENTED_CATEGORIES
    ]
    print(f"\n미구현 카테고리 제외 실패: {len(implemented_failures)}건")
    if implemented_failures:
        print("FAIL: 구현된 카테고리에서 오탐/누락 발견")
        raise SystemExit(1)
    print("PASS: 구현된 카테고리 전부 정답")


if __name__ == "__main__":
    main()
