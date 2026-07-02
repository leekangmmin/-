#!/usr/bin/env python3
"""전문가 채점 데이터 import CLI.

사용법:
    .venv/bin/python scripts/import_expert_data.py --preview path/to/data.json
    .venv/bin/python scripts/import_expert_data.py --import path/to/data.json
    .venv/bin/python scripts/import_expert_data.py --history
    .venv/bin/python scripts/import_expert_data.py --rollback <import_id>
    .venv/bin/python scripts/import_expert_data.py --summary

스키마는 app/expert_models.py의 ExpertRatedResponse를 따른다.
JSON 예시: tests/expert_data_fixtures/sample_valid.json (합성 데이터, 형식 참고용)
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import app.expert_data as expert_data


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--preview", metavar="PATH", help="실제 저장 없이 검증만 수행")
    group.add_argument("--import", dest="do_import", metavar="PATH", help="실제로 import 수행")
    group.add_argument("--history", action="store_true", help="import 이력 조회")
    group.add_argument("--rollback", metavar="IMPORT_ID", help="해당 import 전체 취소")
    group.add_argument("--summary", action="store_true", help="dataset split 현황 조회")
    args = parser.parse_args()

    if args.preview:
        result = expert_data.preview_import(args.preview)
        print(f"[PREVIEW] {result.source_path}")
        print(f"  total={result.rows_total} would_import={result.rows_imported} "
              f"duplicate={result.rows_duplicate} invalid={result.rows_invalid}")
        for err in result.errors:
            print(f"  ERROR row {err.row_index} ({err.record_id}): {err.error}")

    elif args.do_import:
        result = expert_data.import_file(args.do_import)
        print(f"[IMPORTED] import_id={result.import_id}")
        print(f"  total={result.rows_total} imported={result.rows_imported} "
              f"duplicate={result.rows_duplicate} invalid={result.rows_invalid}")
        for err in result.errors:
            print(f"  ERROR row {err.row_index} ({err.record_id}): {err.error}")
        if result.rows_invalid:
            print("\n일부 행이 스키마 검증에 실패했습니다. 원본 파일은 수정되지 않았습니다.")

    elif args.history:
        for row in expert_data.list_import_history():
            status = "ROLLED BACK" if row["rolled_back"] else "active"
            print(f"{row['import_id']}  {row['imported_at']}  "
                  f"imported={row['rows_imported']} duplicate={row['rows_duplicate']} "
                  f"invalid={row['rows_invalid']}  [{status}]  {row['source_path']}")

    elif args.rollback:
        deleted = expert_data.rollback_import(args.rollback)
        print(f"Rolled back {args.rollback}: {deleted} rows removed")

    elif args.summary:
        summary = expert_data.dataset_split_summary()
        total = sum(summary.values())
        print(f"Total records: {total}")
        for split, count in summary.items():
            print(f"  {split}: {count}")


if __name__ == "__main__":
    main()
