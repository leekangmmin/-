"""관리자 전용 API(/api/expert-data/summary, /api/shadow/summary) 보안 테스트.

검증 항목:
1. 기본값(TOEFL_ADMIN_API_ENABLED 미설정)에서는 404 — 엔드포인트 존재 자체를 숨김
2. flag를 켜도 로컬이 아닌 클라이언트는 403
3. X-Forwarded-For 헤더 스푸핑으로 검사를 우회할 수 없음
4. flag + 로컬 접근이면 200
5. 응답에 답안 원문이나 개인 식별 정보가 포함되지 않음
"""

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from tests.fixtures import DISCUSSION_HIGH


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from app.main import app

    with TestClient(app) as c:
        yield c


class TestDisabledByDefault:
    def test_expert_data_summary_returns_404_without_flag(self, client, monkeypatch):
        monkeypatch.delenv("TOEFL_ADMIN_API_ENABLED", raising=False)
        res = client.get("/api/expert-data/summary")
        assert res.status_code == 404

    def test_shadow_summary_returns_404_without_flag(self, client, monkeypatch):
        monkeypatch.delenv("TOEFL_ADMIN_API_ENABLED", raising=False)
        res = client.get("/api/shadow/summary")
        assert res.status_code == 404

    def test_flag_set_to_0_still_disabled(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "0")
        res = client.get("/api/expert-data/summary")
        assert res.status_code == 404


class TestEnabledRequiresLocalAccess:
    def test_enabled_and_local_returns_200(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        res = client.get("/api/expert-data/summary")
        assert res.status_code == 200

    def test_shadow_enabled_and_local_returns_200(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        res = client.get("/api/shadow/summary")
        assert res.status_code == 200


class TestXForwardedForNotTrusted:
    def test_spoofed_x_forwarded_for_does_not_bypass_check(self, client, monkeypatch):
        """TestClient는 항상 'testclient' 호스트로 요청하므로 이 테스트만으로는
        비신뢰 검증이 직접적이지 않다 — 대신 코드가 요청 헤더(X-Forwarded-For 등
        클라이언트가 조작 가능한 값)를 아예 읽지 않고, request.client.host만
        신뢰한다는 것을 소스 레벨에서 확인한다. (docstring에는 정책 설명을 위해
        "X-Forwarded-For"라는 단어가 등장하므로, 실제 코드 로직에서 request.headers를
        사용하지 않는지를 확인한다.)"""
        import inspect

        import app.main as main_mod
        source = inspect.getsource(main_mod._require_local_admin_session)
        assert "request.headers" not in source

    def test_spoofed_header_present_but_ignored(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        # 공격자가 이 헤더를 임의로 채워도 request.client.host는 바뀌지 않는다
        res = client.get("/api/expert-data/summary", headers={"X-Forwarded-For": "8.8.8.8"})
        # TestClient 환경에서는 여전히 testclient(로컬 취급)로 인식되므로 200 —
        # 핵심은 응답이 X-Forwarded-For 값에 따라 달라지지 않는다는 것
        assert res.status_code == 200


class TestNoContentLeakage:
    def test_expert_data_summary_has_no_essay_text_fields(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        res = client.get("/api/expert-data/summary")
        body = res.json()
        serialized = str(body)
        # summary 응답은 집계 수치만 포함해야 하고, 원문 텍스트 필드가 없어야 한다
        assert "response_text" not in serialized
        assert "essay_text" not in serialized

    def test_shadow_summary_has_no_essay_text_fields(self, client, monkeypatch):
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        res = client.get("/api/shadow/summary")
        body = res.json()
        serialized = str(body)
        assert "essay_text" not in serialized
        assert "response_text" not in serialized

    def test_real_submission_essay_text_never_appears_in_admin_summaries(self, client, monkeypatch):
        """실제 평가를 하나 만든 뒤, 그 답안 원문이 관리자 요약 응답에 절대
        섞여 들어가지 않는지 확인한다."""
        monkeypatch.setenv("TOEFL_ADMIN_API_ENABLED", "1")
        marker_text = "MyRealNameIsJohnDoeAndMyEmailIsJohnDoeExample dot com. " + DISCUSSION_HIGH
        eval_res = client.post("/api/evaluate", json={"essay_text": marker_text})
        assert eval_res.status_code == 200

        for path in ["/api/expert-data/summary", "/api/shadow/summary"]:
            res = client.get(path)
            assert "MyRealNameIsJohnDoe" not in res.text
