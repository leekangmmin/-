"""Hosted web 모드 안전장치 테스트 — TOEFL_WEB_MODE 환경변수, admin API 항상
비활성, 요청 크기 제한. 실제 사용자 데이터 경로는 건드리지 않는다."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.db as db_module

ESSAY = (
    "Universities should invest more resources in mental health support for students "
    "because academic pressure has increased significantly in recent years. Many students "
    "struggle silently with anxiety and stress, and without adequate counseling services "
    "their academic performance and overall wellbeing suffer considerably over time. "
    "Providing accessible mental health resources on campus would help students manage "
    "these challenges early, before they escalate into more serious problems that affect "
    "graduation rates and long-term career success for everyone involved in education."
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from app.main import app

    with TestClient(app) as c:
        yield c


class TestWebModeEnvVar:
    def test_toefl_web_mode_1_switches_capabilities_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        body = client.get("/api/capabilities").json()
        assert body["mode"] == "web"

    def test_toefl_app_mode_web_switches_capabilities_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_APP_MODE", "web")
        body = client.get("/api/capabilities").json()
        assert body["mode"] == "web"

    def test_web_mode_hides_desktop_only_features(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        body = client.get("/api/capabilities").json()
        # 공유 hosted 서버에서는 로컬 파일 백업/복원과 로컬 AI 프로세스 관리를
        # 노출하지 않는다 — 다른 방문자의 데이터를 건드릴 여지를 만들지 않기 위함.
        assert body["local_ai"] is False
        assert body["backup_restore"] is False

    def test_web_mode_keeps_offline_core_available(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        body = client.get("/api/capabilities").json()
        assert body["offline_core"] is True
        assert body["api_key_required"] is False
        assert body["build_a_sentence"] is True
        assert body["pdf"] is True

    def test_web_mode_does_not_enable_cloud_ai_by_default(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        body = client.get("/api/capabilities").json()
        assert body["cloud_ai"] is False
        assert body["hosted_ai"] is False

    def test_no_web_mode_env_defaults_to_desktop_or_web(self, client, monkeypatch):
        monkeypatch.delenv("TOEFL_WEB_MODE", raising=False)
        monkeypatch.delenv("TOEFL_APP_MODE", raising=False)
        body = client.get("/api/capabilities").json()
        assert body["mode"] == "desktop_or_web"


class TestAdminApiAlwaysDisabledRegardlessOfMode:
    """web 모드 여부와 무관하게 admin API는 명시적 플래그 없이는 항상 404."""

    def test_expert_data_summary_404_in_web_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        monkeypatch.delenv("TOEFL_ADMIN_API_ENABLED", raising=False)
        res = client.get("/api/expert-data/summary")
        assert res.status_code == 404

    def test_shadow_summary_404_in_web_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        monkeypatch.delenv("TOEFL_ADMIN_API_ENABLED", raising=False)
        res = client.get("/api/shadow/summary")
        assert res.status_code == 404

    def test_capabilities_reports_admin_api_false_in_web_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        body = client.get("/api/capabilities").json()
        assert body["admin_api"] is False


class TestRequestSizeLimits:
    """공개 데모 남용 방지 — 답안/프롬프트 길이 상한이 실제로 거부되는지 확인."""

    def test_oversized_essay_rejected(self, client):
        huge_essay = "word " * 3000  # 15000자 이상, max_length=12000 초과
        res = client.post("/api/evaluate", json={"essay_text": huge_essay})
        assert res.status_code == 422

    def test_oversized_prompt_rejected(self, client):
        huge_prompt = "prompt " * 1000  # max_length=3000 초과
        res = client.post("/api/evaluate", json={"essay_text": ESSAY, "prompt_text": huge_prompt})
        assert res.status_code == 422

    def test_essay_within_limits_accepted(self, client):
        res = client.post("/api/evaluate", json={"essay_text": ESSAY})
        assert res.status_code == 200


class TestHostedModeEvaluationWorks:
    """web 모드에서도 오프라인 코어 채점·기록·PDF가 정상 동작해야 한다."""

    def test_evaluate_and_pdf_work_in_web_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        res = client.post("/api/evaluate", json={"essay_text": ESSAY})
        assert res.status_code == 200
        submission_id = res.json()["submission_id"]

        pdf_res = client.get(f"/api/report/{submission_id}.pdf")
        assert pdf_res.status_code == 200
        assert pdf_res.headers["content-type"] == "application/pdf"

    def test_build_a_sentence_works_in_web_mode(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_WEB_MODE", "1")
        res = client.get("/api/build-a-sentence/items")
        assert res.status_code == 200
        assert len(res.json()["items"]) > 0
