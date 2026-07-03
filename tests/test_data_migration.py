"""app/data_migration.py — 레거시 data/ → 사용자 데이터 경로 안전 이관 테스트.

원본 삭제 금지, 실패 시 부분 완료 마커 미기록, record count 검증 등
마스터 스펙 10장의 안전 원칙을 실제로 지키는지 검증한다.
"""

from __future__ import annotations

import sqlite3

import pytest

import app.data_migration as migration_module


def _make_sqlite_db(path, rows: list[tuple]) -> None:
    conn = sqlite3.connect(path)
    conn.execute("CREATE TABLE submissions (id INTEGER PRIMARY KEY, essay_text TEXT)")
    conn.executemany("INSERT INTO submissions (essay_text) VALUES (?)", rows)
    conn.commit()
    conn.close()


@pytest.fixture()
def env(tmp_path, monkeypatch):
    legacy_dir = tmp_path / "legacy_data"
    legacy_dir.mkdir()
    user_dir = tmp_path / "user_data"
    monkeypatch.setenv("TOEFL_DATA_DIR", str(user_dir))
    monkeypatch.setattr(migration_module, "legacy_project_data_dir", lambda: legacy_dir)
    return {"legacy_dir": legacy_dir, "user_dir": user_dir}


class TestNoLegacyData:
    def test_no_legacy_dir_marks_complete_without_error(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOEFL_DATA_DIR", str(tmp_path / "user_data"))
        monkeypatch.setattr(migration_module, "legacy_project_data_dir", lambda: tmp_path / "nonexistent")
        report = migration_module.migrate_legacy_data_if_needed()
        assert report.performed is True
        assert report.results == []

    def test_second_call_is_noop(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TOEFL_DATA_DIR", str(tmp_path / "user_data"))
        monkeypatch.setattr(migration_module, "legacy_project_data_dir", lambda: tmp_path / "nonexistent")
        migration_module.migrate_legacy_data_if_needed()
        report2 = migration_module.migrate_legacy_data_if_needed()
        assert report2.already_completed is True
        assert report2.performed is False


class TestSuccessfulMigration:
    def test_db_copied_with_matching_record_count(self, env):
        _make_sqlite_db(env["legacy_dir"] / "submissions.db", [("essay one",), ("essay two",)])
        report = migration_module.migrate_legacy_data_if_needed()

        assert report.performed is True
        result = next(r for r in report.results if r.filename == "submissions.db")
        assert result.succeeded is True
        assert result.source_row_count == 2
        assert result.dest_row_count == 2

        dest_db = env["user_dir"] / "databases" / "submissions.db"
        assert dest_db.exists()

    def test_original_not_deleted(self, env):
        original = env["legacy_dir"] / "submissions.db"
        _make_sqlite_db(original, [("keep me",)])
        migration_module.migrate_legacy_data_if_needed()
        assert original.exists()  # 원본은 절대 삭제하지 않는다

    def test_completion_marker_written_after_success(self, env):
        _make_sqlite_db(env["legacy_dir"] / "submissions.db", [("x",)])
        migration_module.migrate_legacy_data_if_needed()
        marker = env["user_dir"] / "migrations" / migration_module.MIGRATION_MARKER_NAME
        assert marker.exists()

    def test_backup_created_before_migration(self, env):
        _make_sqlite_db(env["legacy_dir"] / "submissions.db", [("x",)])
        report = migration_module.migrate_legacy_data_if_needed()
        assert report.backup_dir is not None
        from pathlib import Path
        assert (Path(report.backup_dir) / "submissions.db").exists()


class TestDestinationAlreadyExists:
    def test_does_not_overwrite_existing_destination(self, env):
        _make_sqlite_db(env["legacy_dir"] / "submissions.db", [("legacy row",)])
        dest_dir = env["user_dir"] / "databases"
        dest_dir.mkdir(parents=True)
        _make_sqlite_db(dest_dir / "submissions.db", [("already here",), ("do not touch",)])

        report = migration_module.migrate_legacy_data_if_needed()
        result = next(r for r in report.results if r.filename == "submissions.db")
        assert result.succeeded is False
        assert result.error == "destination_already_exists_not_overwritten"

        conn = sqlite3.connect(dest_dir / "submissions.db")
        rows = conn.execute("SELECT essay_text FROM submissions").fetchall()
        assert len(rows) == 2  # 기존 데이터가 그대로 유지됨


class TestPartialFailureDoesNotMarkComplete:
    def test_no_marker_when_a_db_fails(self, env):
        _make_sqlite_db(env["legacy_dir"] / "submissions.db", [("ok",)])
        # 손상된 shadow DB — 읽기 실패를 유도
        (env["legacy_dir"] / "shadow_assessments.db").write_bytes(b"not a valid sqlite file")

        report = migration_module.migrate_legacy_data_if_needed()
        shadow_result = next(r for r in report.results if r.filename == "shadow_assessments.db")
        assert shadow_result.succeeded is False

        marker = env["user_dir"] / "migrations" / migration_module.MIGRATION_MARKER_NAME
        assert not marker.exists()  # 부분 실패 상태로 완료 마커를 남기지 않는다

    def test_retry_possible_after_partial_failure(self, env):
        (env["legacy_dir"] / "shadow_assessments.db").write_bytes(b"corrupt")
        migration_module.migrate_legacy_data_if_needed()

        # 손상 파일을 정상 DB로 교체 후 재시도하면 이번엔 성공해야 한다
        (env["legacy_dir"] / "shadow_assessments.db").unlink()
        _make_sqlite_db(env["legacy_dir"] / "shadow_assessments.db", [("recovered",)])

        report2 = migration_module.migrate_legacy_data_if_needed()
        assert report2.already_completed is False  # 마커가 없었으므로 재시도됨
        result = next(r for r in report2.results if r.filename == "shadow_assessments.db")
        assert result.succeeded is True
