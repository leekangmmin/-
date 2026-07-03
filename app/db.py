from __future__ import annotations

import json
import sqlite3
from datetime import UTC, datetime
from typing import Any

from app.paths import databases_dir

DB_PATH = databases_dir() / "submissions.db"


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
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS app_settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS drafts (
                id INTEGER PRIMARY KEY CHECK (id = 1),
                prompt_text TEXT NOT NULL DEFAULT '',
                essay_text TEXT NOT NULL DEFAULT '',
                task_type TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL
            )
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS bas_attempts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                created_at TEXT NOT NULL,
                item_id TEXT NOT NULL,
                item_version TEXT NOT NULL,
                rubric_version TEXT NOT NULL,
                engine_version TEXT NOT NULL,
                is_correct INTEGER NOT NULL,
                match_type TEXT NOT NULL,
                time_spent_ms INTEGER,
                attempt_number INTEGER NOT NULL
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
                "is_legacy": parsed.get("engine") is None,
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


def save_draft(prompt_text: str, essay_text: str, task_type: str = "") -> str:
    """작성 중 답안을 단일 행(id=1)으로 upsert한다. updated_at(ISO)을 반환한다."""
    init_db()
    updated_at = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO drafts (id, prompt_text, essay_text, task_type, updated_at)
            VALUES (1, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                prompt_text=excluded.prompt_text,
                essay_text=excluded.essay_text,
                task_type=excluded.task_type,
                updated_at=excluded.updated_at
            """,
            (prompt_text, essay_text, task_type, updated_at),
        )
    return updated_at


def get_draft() -> dict[str, Any] | None:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT prompt_text, essay_text, task_type, updated_at FROM drafts WHERE id = 1"
        ).fetchone()
    if row is None:
        return None
    return dict(row)


def clear_draft() -> None:
    init_db()
    with get_conn() as conn:
        conn.execute("DELETE FROM drafts WHERE id = 1")


def delete_submission(submission_id: int) -> bool:
    """기록 1건을 삭제한다. 존재하지 않으면 False를 반환한다."""
    init_db()
    with get_conn() as conn:
        cur = conn.execute("DELETE FROM submissions WHERE id = ?", (submission_id,))
        return cur.rowcount > 0


def count_user_records() -> dict[str, int]:
    """백업 메타데이터/삭제 확인용 사용자 데이터 레코드 수."""
    init_db()
    with get_conn() as conn:
        return {
            "submissions": int(conn.execute("SELECT COUNT(*) AS c FROM submissions").fetchone()["c"]),
            "bas_attempts": int(conn.execute("SELECT COUNT(*) AS c FROM bas_attempts").fetchone()["c"]),
            "drafts": int(conn.execute("SELECT COUNT(*) AS c FROM drafts").fetchone()["c"]),
            "app_settings": int(conn.execute("SELECT COUNT(*) AS c FROM app_settings").fetchone()["c"]),
        }


def delete_all_user_data() -> dict[str, int]:
    """모든 사용자 데이터(제출 기록/BAS 기록/draft/설정)를 삭제하고
    삭제 전 레코드 수를 반환한다. 테이블 구조는 유지한다(DB 재생성 불필요)."""
    counts = count_user_records()
    with get_conn() as conn:
        conn.execute("DELETE FROM submissions")
        conn.execute("DELETE FROM bas_attempts")
        conn.execute("DELETE FROM drafts")
        conn.execute("DELETE FROM app_settings")
    return counts


def save_bas_attempt(
    item_id: str,
    item_version: str,
    rubric_version: str,
    engine_version: str,
    is_correct: bool,
    match_type: str,
    time_spent_ms: int | None,
) -> int:
    init_db()
    created_at = datetime.now(UTC).isoformat()
    with get_conn() as conn:
        attempt_number = 1 + int(
            conn.execute(
                "SELECT COUNT(*) AS c FROM bas_attempts WHERE item_id = ?",
                (item_id,),
            ).fetchone()["c"]
        )
        cur = conn.execute(
            """
            INSERT INTO bas_attempts
                (created_at, item_id, item_version, rubric_version, engine_version,
                 is_correct, match_type, time_spent_ms, attempt_number)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                created_at, item_id, item_version, rubric_version, engine_version,
                int(is_correct), match_type, time_spent_ms, attempt_number,
            ),
        )
        if cur.lastrowid is None:
            raise RuntimeError("Failed to save build-a-sentence attempt")
        return attempt_number


def list_bas_attempts(item_id: str | None = None, limit: int = 200) -> list[dict[str, Any]]:
    with get_conn() as conn:
        if item_id:
            rows = conn.execute(
                """
                SELECT id, created_at, item_id, item_version, rubric_version, engine_version,
                       is_correct, match_type, time_spent_ms, attempt_number
                FROM bas_attempts WHERE item_id = ? ORDER BY id DESC LIMIT ?
                """,
                (item_id, limit),
            ).fetchall()
        else:
            rows = conn.execute(
                """
                SELECT id, created_at, item_id, item_version, rubric_version, engine_version,
                       is_correct, match_type, time_spent_ms, attempt_number
                FROM bas_attempts ORDER BY id DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
    return [dict(row) | {"is_correct": bool(row["is_correct"])} for row in rows]


def set_setting(key: str, value: str) -> None:
    init_db()
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO app_settings (key, value)
            VALUES (?, ?)
            ON CONFLICT(key) DO UPDATE SET value=excluded.value
            """,
            (key, value),
        )


def get_setting(key: str, default: str = "") -> str:
    init_db()
    with get_conn() as conn:
        row = conn.execute(
            "SELECT value FROM app_settings WHERE key = ?",
            (key,),
        ).fetchone()
    if row is None:
        return default
    return str(row["value"])
