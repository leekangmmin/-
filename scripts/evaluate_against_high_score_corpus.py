#!/usr/bin/env python3
"""Local aggregate evaluation; never logs private answers."""

from __future__ import annotations

import argparse
import json
import sys
from collections import defaultdict
from pathlib import Path
from statistics import mean

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.corpus_ingest import ingest_path
from app.high_score_patterns import HIGH_SCORE_MOVES, analyze_high_score_structure
from app.scorer import score_essay


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    args = parser.parse_args()
    if not args.input.exists():
        print("Private corpus not found; skipped safely.")
        return 0
    samples = ingest_path(args.input)
    grouped: dict[str, list[dict]] = defaultdict(list)
    for sample in samples:
        _, score = score_essay(sample.answer_text, sample.task_type)
        structure = analyze_high_score_structure(sample.answer_text, sample.task_type)
        grouped[sample.task_type].append({
            "score": score,
            "false_low": score < 3.0,
            "structure_rate": len(structure.detected_moves) / len(HIGH_SCORE_MOVES[sample.task_type]),
            "template_spam": structure.template_spam_risk,
        })
    report = {"sample_count": len(samples), "scoring_formula_changed": False, "task_types": {}}
    for task_type, rows in sorted(grouped.items()):
        scores = [r["score"] for r in rows]
        report["task_types"][task_type] = {
            "count": len(rows), "average_score": round(mean(scores), 3), "min_score": min(scores), "max_score": max(scores),
            "false_low_rate": round(mean(r["false_low"] for r in rows), 3),
            "structure_detection_rate": round(mean(r["structure_rate"] for r in rows), 3),
            "template_spam_flag_rate": round(mean(r["template_spam"] for r in rows), 3),
        }
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
