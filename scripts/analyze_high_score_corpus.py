#!/usr/bin/env python3
"""Analyze a private corpus without printing or exporting answer text."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.corpus_ingest import ingest_path, safe_aggregate, write_safe_summary


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--out", type=Path)
    parser.add_argument("--safe-summary", action="store_true")
    args = parser.parse_args()
    if not args.input.exists():
        print("Private corpus not found; skipped safely.")
        return 0
    samples = ingest_path(args.input)
    report = safe_aggregate(samples)
    if args.out:
        if not args.safe_summary:
            print("Refusing file output without --safe-summary; only aggregate reports may be written.", file=sys.stderr)
            return 2
        write_safe_summary(samples, args.out)
    print(json.dumps(report, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
