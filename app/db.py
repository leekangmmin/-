from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "submissions.db"


def get_conn() -> sqlite3.Connection:
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with get_conn() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                prompt_type TEXT NOT NULL,
                prompt_text TEXT NOT NULL,
                essay_text TEXT NOT NULL,
                result_json TEXT NOT NULL
            )
            """
        )


def save_submission(
    prompt_type: str,
    prompt_text: str,
    essay_text: str,
    evaluation_result: dict[str, Any],
) -> tuple[int, datetime]:
    init_db()
    created_at = datetime.now(UTC)
    with get_conn() as conn:
        cur = conn.execute(
            """
            INSERT INTO submissions (created_at, prompt_type, prompt_text, essay_text, result_json)
            VALUES (?, ?, ?, ?, ?)
            """,
            (
                created_at.isoformat(),
                prompt_type,
                prompt_text,
                essay_text,
                json.dumps(evaluation_result, default=str, ensure_ascii=False),
            ),
        )
        if cur.lastrowid is None:
            raise RuntimeError("Failed to save submission")
        return int(cur.lastrowid), created_at


def list_recent(limit: int = 20) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, created_at, prompt_type, result_json
            FROM submissions
            ORDER BY id DESC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        parsed = json.loads(row["result_json"])
        score_0_5 = float(parsed.get("estimated_score_0_5", 0))
        score_band = float(parsed.get("score_band_1_6", min(6.0, max(1.0, score_0_5 + 1.0))))
        items.append(
            {
                "id": row["id"],
                "created_at": datetime.fromisoformat(row["created_at"]),
                "prompt_type": row["prompt_type"],
                "estimated_score_0_5": score_0_5,
                "score_band_1_6": score_band,
                "estimated_score_30": parsed.get("estimated_score_30", 0),
            }
        )
    return items


def list_all_results(limit: int = 200) -> list[dict[str, Any]]:
    with get_conn() as conn:
        rows = conn.execute(
            """
            SELECT id, result_json
            FROM submissions
            ORDER BY id ASC
            LIMIT ?
            """,
            (limit,),
        ).fetchall()

    items: list[dict[str, Any]] = []
    for row in rows:
        parsed = json.loads(row["result_json"])
        parsed["id"] = row["id"]
        items.append(parsed)
    return items


def get_submission(submission_id: int) -> dict[str, Any] | None:
    with get_conn() as conn:
        row = conn.execute(
            """
            SELECT id, created_at, prompt_type, prompt_text, essay_text, result_json
            FROM submissions
            WHERE id = ?
            """,
            (submission_id,),
        ).fetchone()

    if row is None:
        return None

    return {
        "id": row["id"],
        "created_at": row["created_at"],
        "prompt_type": row["prompt_type"],
        "prompt_text": row["prompt_text"],
        "essay_text": row["essay_text"],
        "result": json.loads(row["result_json"]),
    }
