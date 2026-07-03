"""구버전(v0.5.0, drafts 테이블 없음) 사용자 DB → 신버전 앱 업데이트 보존 테스트.

Phase 6에서 submissions.db에 drafts 테이블이 추가됐다. 실제 업데이트
시나리오(구버전 앱이 만든 DB를 신버전 앱이 여는 상황)를 fixture DB로
재현한다 — 기존 기록/설정/BAS 기록이 보존되고, 새 테이블이 생성되며,
기존 기능이 계속 동작해야 한다.

패키징 앱 수준의 동일 시나리오는 scripts/update_migration_test.py로 검증한다.
"""

import json
import sqlite3

import pytest
from fastapi.testclient import TestClient

import app.db as db_module


def _build_v050_fixture_db(path):
    """Phase 5(v0.5.0) 스키마 그대로의 DB를 만든다 — drafts 테이블 없음."""
    conn = sqlite3.connect(path)
    conn.executescript(
        """
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL,
            prompt_type TEXT NOT NULL,
            prompt_text TEXT NOT NULL,
            essay_text TEXT NOT NULL,
            result_json TEXT NOT NULL
        );
        CREATE TABLE app_settings (
            key TEXT PRIMARY KEY,
            value TEXT NOT NULL
        );
        CREATE TABLE bas_attempts (
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
        );
        """
    )
    result = {"estimated_score_0_5": 3.5, "score_band_1_6": 4.5, "estimated_score_30": 24, "engine": None}
    for i in (1, 2):
        conn.execute(
            "INSERT INTO submissions (created_at, prompt_type, prompt_text, essay_text, result_json) "
            "VALUES (?, ?, ?, ?, ?)",
            (f"2026-06-0{i}T00:00:00+00:00", "academic_discussion", "old prompt", f"old essay {i}",
             json.dumps(result)),
        )
    conn.execute(
        "INSERT INTO bas_attempts (created_at, item_id, item_version, rubric_version, engine_version, "
        "is_correct, match_type, time_spent_ms, attempt_number) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
        ("2026-06-01T00:00:00+00:00", "bas-001", "1.0.0", "bas-rubric-1.0.0", "build-a-sentence-1.0.0",
         1, "exact", 5000, 1),
    )
    conn.execute("INSERT INTO app_settings (key, value) VALUES ('ai_provider', 'local')")
    conn.commit()
    conn.close()


@pytest.fixture()
def upgraded_client(tmp_path, monkeypatch):
    """v0.5.0 fixture DB가 이미 존재하는 상태에서 신버전 앱을 기동한다."""
    db_path = tmp_path / "submissions.db"
    _build_v050_fixture_db(db_path)
    monkeypatch.setattr(db_module, "DB_PATH", db_path)
    import app.backup as backup_module
    monkeypatch.setattr(backup_module, "DB_PATH", db_path)
    monkeypatch.setenv("TOEFL_DATA_DIR", str(tmp_path / "data"))
    from app.main import app

    with TestClient(app) as c:
        yield c


ESSAY = (
    "Universities should invest more resources in mental health support for students "
    "because academic pressure has increased significantly in recent years. Many students "
    "struggle silently with anxiety and stress, and without adequate counseling services "
    "their academic performance and overall wellbeing suffer considerably over time. "
    "Providing accessible mental health resources on campus would help students manage "
    "these challenges early, before they escalate into more serious problems that affect "
    "graduation rates and long-term career success for everyone involved in education."
)


def test_legacy_records_preserved_with_ids(upgraded_client):
    items = upgraded_client.get("/api/history").json()["items"]
    assert len(items) == 2
    assert {item["id"] for item in items} == {1, 2}
    # engine 정보가 없는 구버전 기록은 legacy로 표시된다
    assert all(item["is_legacy"] for item in items)


def test_new_drafts_table_created_without_touching_old_data(upgraded_client):
    # 신버전 기능(draft)이 구버전 DB 위에서 정상 동작
    res = upgraded_client.put("/api/draft", json={"essay_text": "new draft on old db"})
    assert res.status_code == 200
    assert upgraded_client.get("/api/draft").json()["draft"]["essay_text"] == "new draft on old db"
    # 기존 기록 수 불변
    assert len(upgraded_client.get("/api/history").json()["items"]) == 2


def test_settings_and_bas_attempts_preserved(upgraded_client):
    from app.db import get_setting, list_bas_attempts

    assert get_setting("ai_provider") == "local"
    attempts = list_bas_attempts(item_id="bas-001")
    assert len(attempts) == 1
    assert attempts[0]["is_correct"] is True


def test_new_evaluation_coexists_with_legacy(upgraded_client):
    res = upgraded_client.post("/api/evaluate", json={"essay_text": ESSAY})
    assert res.status_code == 200
    new_id = res.json()["submission_id"]
    assert new_id == 3  # AUTOINCREMENT 이어짐 — ID 충돌 없음

    items = upgraded_client.get("/api/history").json()["items"]
    assert len(items) == 3
    new_item = next(i for i in items if i["id"] == new_id)
    assert not new_item["is_legacy"]


def test_backup_of_upgraded_db_includes_legacy_records(upgraded_client):
    meta = upgraded_client.post("/api/backup").json()
    assert meta["record_counts"]["submissions"] == 2
    assert meta["record_counts"]["bas_attempts"] == 1
