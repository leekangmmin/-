"""Phase 6 데이터 안전 테스트 — draft/백업/복원/삭제. 임시 데이터 경로만 사용한다."""

import json
import zipfile

import pytest
from fastapi.testclient import TestClient

import app.db as db_module


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    # backup 모듈은 DB_PATH를 import 시점에 복사해가므로 함께 패치한다
    import app.backup as backup_module
    monkeypatch.setattr(backup_module, "DB_PATH", tmp_path / "test.db")
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
    "graduation rates and long-term career success. Therefore, investing in counseling "
    "programs benefits both individual students and the whole university community."
)


class TestDraft:
    def test_empty_draft_returns_none(self, client):
        assert client.get("/api/draft").json()["draft"] is None

    def test_save_and_load_draft(self, client):
        res = client.put("/api/draft", json={"prompt_text": "P", "essay_text": "E", "task_type": "email"})
        assert res.status_code == 200
        draft = client.get("/api/draft").json()["draft"]
        assert draft["prompt_text"] == "P"
        assert draft["essay_text"] == "E"
        assert draft["task_type"] == "email"
        assert draft["updated_at"]

    def test_save_overwrites_single_row(self, client):
        client.put("/api/draft", json={"essay_text": "first"})
        client.put("/api/draft", json={"essay_text": "second"})
        assert client.get("/api/draft").json()["draft"]["essay_text"] == "second"

    def test_clear_draft(self, client):
        client.put("/api/draft", json={"essay_text": "x"})
        client.delete("/api/draft")
        assert client.get("/api/draft").json()["draft"] is None


class TestHistoryDeletion:
    def test_delete_existing_submission(self, client):
        sub_id = client.post("/api/evaluate", json={"essay_text": ESSAY}).json()["submission_id"]
        res = client.delete(f"/api/history/{sub_id}")
        assert res.status_code == 200
        history = client.get("/api/history").json()["items"]
        assert not any(item["id"] == sub_id for item in history)

    def test_delete_missing_returns_404(self, client):
        assert client.delete("/api/history/999999").status_code == 404


class TestBackup:
    def test_create_backup_and_list(self, client):
        client.post("/api/evaluate", json={"essay_text": ESSAY})
        res = client.post("/api/backup")
        assert res.status_code == 200
        meta = res.json()
        assert meta["record_counts"]["submissions"] == 1
        assert meta["size_bytes"] > 0

        listing = client.get("/api/backup/list").json()
        assert len(listing["backups"]) == 1
        assert listing["backups"][0]["filename"] == meta["filename"]
        assert listing["backups"][0]["readable"] is True

    def test_backup_strips_api_keys(self, client, tmp_path):
        client.post("/api/ai/config", json={"provider": "claude", "enabled": False, "anthropic_api_key": "sk-ant-secret123"})
        meta = client.post("/api/backup").json()

        from app.paths import backups_dir
        backup_zip = backups_dir() / meta["filename"]
        with zipfile.ZipFile(backup_zip) as zf:
            db_bytes = zf.read("submissions.db")
        assert b"sk-ant-secret123" not in db_bytes

    def test_restore_round_trip(self, client):
        sub_id = client.post("/api/evaluate", json={"essay_text": ESSAY}).json()["submission_id"]
        meta = client.post("/api/backup").json()

        # 백업 후 기록을 지우고 복원하면 되살아나야 한다
        client.delete(f"/api/history/{sub_id}")
        assert client.get("/api/history").json()["items"] == []

        res = client.post("/api/backup/restore", json={"filename": meta["filename"]})
        assert res.status_code == 200
        assert res.json()["record_counts"]["submissions"] == 1
        history = client.get("/api/history").json()["items"]
        assert any(item["id"] == sub_id for item in history)

    def test_restore_preserves_current_api_key(self, client):
        meta = client.post("/api/backup").json()  # 키 없는 시점의 백업
        client.post("/api/ai/config", json={"provider": "claude", "enabled": False, "anthropic_api_key": "sk-ant-keepme"})
        client.post("/api/backup/restore", json={"filename": meta["filename"]})
        cfg = client.get("/api/ai/config").json()
        assert cfg["has_anthropic_key"] is True  # 복원해도 이 기기의 키는 유지

    def test_inspect_backup_preview(self, client):
        client.post("/api/evaluate", json={"essay_text": ESSAY})
        meta = client.post("/api/backup").json()
        res = client.post("/api/backup/inspect", json={"filename": meta["filename"]})
        assert res.status_code == 200
        body = res.json()
        assert body["backup"]["record_counts"]["submissions"] == 1
        assert "current_record_counts" in body

    def test_restore_missing_file_returns_400(self, client):
        res = client.post("/api/backup/restore", json={"filename": "no-such-file.zip"})
        assert res.status_code == 400

    def test_restore_corrupted_zip_keeps_current_data(self, client):
        sub_id = client.post("/api/evaluate", json={"essay_text": ESSAY}).json()["submission_id"]
        from app.paths import backups_dir
        bad = backups_dir() / "toefl-writing-backup-corrupt.zip"
        bad.write_bytes(b"this is not a zip file")

        res = client.post("/api/backup/restore", json={"filename": bad.name})
        assert res.status_code in (400, 500)
        # 기존 데이터는 손상되지 않아야 한다
        history = client.get("/api/history").json()["items"]
        assert any(item["id"] == sub_id for item in history)

    def test_restore_path_traversal_blocked(self, client):
        res = client.post("/api/backup/restore", json={"filename": "../../etc/passwd"})
        assert res.status_code == 400


class TestDeleteAll:
    def test_wrong_confirm_phrase_rejected(self, client):
        client.post("/api/evaluate", json={"essay_text": ESSAY})
        res = client.post("/api/data/delete-all", json={"confirm": "삭제"})
        assert res.status_code == 400
        assert client.get("/api/history").json()["items"]  # 데이터 유지

    def test_delete_all_wipes_and_creates_safety_backup(self, client):
        client.post("/api/evaluate", json={"essay_text": ESSAY})
        client.put("/api/draft", json={"essay_text": "work in progress"})
        res = client.post("/api/data/delete-all", json={"confirm": "모두 삭제"})
        assert res.status_code == 200
        body = res.json()
        assert body["deleted_counts"]["submissions"] == 1
        assert body["safety_backup"]

        assert client.get("/api/history").json()["items"] == []
        assert client.get("/api/draft").json()["draft"] is None
        # 삭제 후에도 앱이 정상 작동한다 (새 평가 가능)
        res2 = client.post("/api/evaluate", json={"essay_text": ESSAY})
        assert res2.status_code == 200

    def test_delete_all_recoverable_from_safety_backup(self, client):
        client.post("/api/evaluate", json={"essay_text": ESSAY})
        body = client.post("/api/data/delete-all", json={"confirm": "모두 삭제"}).json()
        res = client.post("/api/backup/restore", json={"filename": body["safety_backup"]})
        assert res.status_code == 200
        assert len(client.get("/api/history").json()["items"]) == 1
