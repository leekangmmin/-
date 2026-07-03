"""전문가 채점 데이터 import·저장·중복탐지·데이터셋 분리.

지원: JSON import, CSV import, import preview(dry-run), schema validation,
중복 탐지(정확 해시 + 정규화 해시), 원본 파일 보존, 여러 채점자 지원,
adjudication 표시, dataset split(development/calibration/validation/locked_test),
prompt 단위 group split(같은 문제의 답안이 여러 세트에 흩어지지 않게), import rollback.

이 모듈은 실제 전문가 데이터를 하드코딩하지 않는다. 데이터가 없는 상태에서는
빈 테이블로 남아 있으며, 화면/코드 어디에서도 가짜 데이터를 실제 데이터처럼
표시하지 않는다.
"""

from __future__ import annotations

import csv
import hashlib
import json
import re
import sqlite3
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pydantic import ValidationError

from app.expert_models import ExpertRatedResponse, ImportResult, ImportRowError
from app.paths import databases_dir

EXPERT_DB_PATH = databases_dir() / "expert_data.db"

# 같은 prompt_id의 답안들이 development/calibration/validation/locked_test에
# 무작위로 흩어지지 않도록, prompt_id 해시로 결정론적 split을 배정한다.
_SPLIT_BUCKETS: list[tuple[str, int]] = [
    ("development", 40),
    ("calibration", 25),
    ("validation", 20),
    ("locked_test", 15),
]


def _conn() -> sqlite3.Connection:
    EXPERT_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(EXPERT_DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_expert_db() -> None:
    with _conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expert_responses (
                record_id TEXT PRIMARY KEY,
                response_group_id TEXT NOT NULL,
                prompt_id TEXT NOT NULL,
                task_type TEXT NOT NULL,
                exact_hash TEXT NOT NULL,
                normalized_hash TEXT NOT NULL,
                dataset_split TEXT,
                payload_json TEXT NOT NULL,
                import_id TEXT NOT NULL,
                imported_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_prompt ON expert_responses(prompt_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_group ON expert_responses(response_group_id)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_exact_hash ON expert_responses(exact_hash)"
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_expert_import ON expert_responses(import_id)"
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS expert_import_log (
                import_id TEXT PRIMARY KEY,
                source_path TEXT NOT NULL,
                imported_at TEXT NOT NULL,
                rows_total INTEGER NOT NULL,
                rows_imported INTEGER NOT NULL,
                rows_duplicate INTEGER NOT NULL,
                rows_invalid INTEGER NOT NULL,
                dry_run INTEGER NOT NULL,
                rolled_back INTEGER NOT NULL DEFAULT 0
            )
            """
        )


def _normalize_text(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def exact_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def normalized_hash(text: str) -> str:
    return hashlib.sha256(_normalize_text(text).encode("utf-8")).hexdigest()


def _default_split_for_prompt(prompt_id: str) -> str:
    """prompt_id를 해시해 결정론적으로 split을 배정한다 (같은 prompt는 항상 같은 split)."""
    digest = int(hashlib.sha256(prompt_id.encode("utf-8")).hexdigest(), 16)
    bucket = digest % 100
    cumulative = 0
    for split_name, weight in _SPLIT_BUCKETS:
        cumulative += weight
        if bucket < cumulative:
            return split_name
    return "development"


def _parse_records(raw_rows: list[dict[str, Any]]) -> tuple[list[ExpertRatedResponse], list[ImportRowError]]:
    parsed: list[ExpertRatedResponse] = []
    errors: list[ImportRowError] = []
    for idx, row in enumerate(raw_rows):
        try:
            item = ExpertRatedResponse(**row)
            if not item.response_group_id:
                item.response_group_id = item.record_id
            parsed.append(item)
        except ValidationError as exc:
            errors.append(ImportRowError(
                row_index=idx,
                record_id=str(row.get("record_id", "")) or None,
                error=str(exc.errors()[0]["msg"]) if exc.errors() else str(exc),
            ))
        except Exception as exc:  # noqa: BLE001
            errors.append(ImportRowError(row_index=idx, record_id=None, error=str(exc)))
    return parsed, errors


def _load_json_rows(path: Path) -> list[dict[str, Any]]:
    data = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(data, dict):
        data = data.get("records", data.get("items", [data]))
    if not isinstance(data, list):
        raise ValueError("JSON 최상위는 배열이거나 'records'/'items' 키를 가진 객체여야 합니다.")
    return data


_CSV_LIST_FIELDS = {"strengths", "weaknesses"}
_CSV_JSON_FIELDS = {
    "dimension_scores", "evidence_spans", "corrections", "rater",
    "adjudication", "provenance",
}


def _load_csv_rows(path: Path) -> list[dict[str, Any]]:
    """CSV는 평면 구조를 기본으로 하되, 중첩 필드(rater/provenance 등)는
    해당 셀에 JSON 문자열을 넣는 방식을 지원한다."""
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for raw in reader:
            row: dict[str, Any] = {}
            for key, value in raw.items():
                if value is None or value == "":
                    continue
                if key in _CSV_JSON_FIELDS:
                    try:
                        row[key] = json.loads(value)
                    except json.JSONDecodeError as exc:
                        raise ValueError(f"CSV 필드 '{key}'는 유효한 JSON 문자열이어야 합니다: {exc}") from exc
                elif key in _CSV_LIST_FIELDS:
                    row[key] = [s.strip() for s in value.split("|") if s.strip()]
                elif key == "overall_score":
                    row[key] = float(value)
                else:
                    row[key] = value
            rows.append(row)
    return rows


def _import(
    raw_rows: list[dict[str, Any]],
    source_path: str,
    dry_run: bool,
) -> ImportResult:
    init_expert_db()
    import_id = str(uuid.uuid4())
    imported_at = datetime.now(UTC)

    parsed, errors = _parse_records(raw_rows)

    with _conn() as conn:
        # 중복 판정은 (텍스트 해시, 채점자) 조합으로 한다. 같은 답안을 여러 채점자가
        # 평가하는 것은 정상적인 multi-rater 케이스이므로 중복이 아니다 — 같은
        # 채점자가 같은 텍스트를 다시 제출한 경우만 중복으로 본다.
        existing_pairs = {
            (r["exact_hash"], json.loads(r["payload_json"])["rater"]["rater_id"])
            for r in conn.execute("SELECT exact_hash, payload_json FROM expert_responses")
        }
        existing_norm_pairs = {
            (r["normalized_hash"], json.loads(r["payload_json"])["rater"]["rater_id"])
            for r in conn.execute("SELECT normalized_hash, payload_json FROM expert_responses")
        }

        seen_in_batch: set[tuple[str, str]] = set()
        rows_imported = 0
        rows_duplicate = 0

        for item in parsed:
            eh = exact_hash(item.response_text)
            nh = normalized_hash(item.response_text)
            rater_id = item.rater.rater_id
            key = (eh, rater_id)
            norm_key = (nh, rater_id)

            if key in existing_pairs or key in seen_in_batch or norm_key in existing_norm_pairs:
                rows_duplicate += 1
                continue

            split = item.dataset_split or _default_split_for_prompt(item.prompt_id)

            if not dry_run:
                conn.execute(
                    """
                    INSERT INTO expert_responses
                    (record_id, response_group_id, prompt_id, task_type, exact_hash,
                     normalized_hash, dataset_split, payload_json, import_id, imported_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        item.record_id, item.response_group_id, item.prompt_id, item.task_type,
                        eh, nh, split, item.model_dump_json(), import_id, imported_at.isoformat(),
                    ),
                )
            seen_in_batch.add(key)
            rows_imported += 1

        if not dry_run:
            conn.execute(
                """
                INSERT INTO expert_import_log
                (import_id, source_path, imported_at, rows_total, rows_imported,
                 rows_duplicate, rows_invalid, dry_run, rolled_back)
                VALUES (?, ?, ?, ?, ?, ?, ?, 0, 0)
                """,
                (
                    import_id, source_path, imported_at.isoformat(), len(raw_rows),
                    rows_imported, rows_duplicate, len(errors),
                ),
            )

    return ImportResult(
        import_id=import_id,
        source_path=source_path,
        imported_at=imported_at,
        rows_total=len(raw_rows),
        rows_imported=rows_imported,
        rows_duplicate=rows_duplicate,
        rows_invalid=len(errors),
        errors=errors,
        dry_run=dry_run,
    )


def preview_import(path: str | Path) -> ImportResult:
    """실제로 저장하지 않고 검증 결과만 반환한다 (dry-run)."""
    path = Path(path)
    rows = _load_json_rows(path) if path.suffix.lower() == ".json" else _load_csv_rows(path)
    return _import(rows, str(path), dry_run=True)


def import_file(path: str | Path) -> ImportResult:
    path = Path(path)
    rows = _load_json_rows(path) if path.suffix.lower() == ".json" else _load_csv_rows(path)
    return _import(rows, str(path), dry_run=False)


def rollback_import(import_id: str) -> int:
    """해당 import로 들어온 레코드를 전부 삭제한다. 삭제된 행 수를 반환한다."""
    init_expert_db()
    with _conn() as conn:
        cur = conn.execute("DELETE FROM expert_responses WHERE import_id = ?", (import_id,))
        conn.execute(
            "UPDATE expert_import_log SET rolled_back = 1 WHERE import_id = ?", (import_id,)
        )
        return cur.rowcount


def list_import_history() -> list[dict[str, Any]]:
    init_expert_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT * FROM expert_import_log ORDER BY imported_at DESC"
        ).fetchall()
    return [dict(r) for r in rows]


def list_records(dataset_split: str | None = None, limit: int = 500) -> list[dict[str, Any]]:
    init_expert_db()
    with _conn() as conn:
        if dataset_split:
            rows = conn.execute(
                "SELECT payload_json FROM expert_responses WHERE dataset_split = ? LIMIT ?",
                (dataset_split, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                "SELECT payload_json FROM expert_responses LIMIT ?", (limit,)
            ).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]


def group_ratings(response_group_id: str) -> list[dict[str, Any]]:
    """같은 답안(response_group_id)에 대한 모든 채점자의 평가를 반환한다.

    각 평가를 개별 보존하며, 여기서 평균만 계산해 원본을 버리지 않는다.
    """
    init_expert_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT payload_json FROM expert_responses WHERE response_group_id = ?",
            (response_group_id,),
        ).fetchall()
    return [json.loads(r["payload_json"]) for r in rows]


def compute_rater_disagreement(response_group_id: str, threshold: float = 1.0) -> dict[str, Any]:
    """채점자 간 점수 차이를 계산하고, 임계값을 넘으면 adjudication 필요로 표시한다.

    threshold는 score_scale에 따라 의미가 달라지므로, 여러 척도가 섞인 그룹에는
    사용하지 말 것(호출부에서 동일 rubric_version/score_scale인지 먼저 확인해야 한다).
    """
    ratings = group_ratings(response_group_id)
    scores = [float(r["overall_score"]) for r in ratings]
    if len(scores) < 2:
        return {
            "response_group_id": response_group_id,
            "rater_count": len(scores),
            "scores": scores,
            "max_disagreement": 0.0,
            "adjudication_required": False,
        }
    max_disagreement = max(scores) - min(scores)
    return {
        "response_group_id": response_group_id,
        "rater_count": len(scores),
        "scores": scores,
        "max_disagreement": round(max_disagreement, 3),
        "adjudication_required": max_disagreement > threshold,
    }


def dataset_split_summary() -> dict[str, int]:
    init_expert_db()
    with _conn() as conn:
        rows = conn.execute(
            "SELECT dataset_split, COUNT(*) as cnt FROM expert_responses GROUP BY dataset_split"
        ).fetchall()
    return {r["dataset_split"] or "unassigned": r["cnt"] for r in rows}
