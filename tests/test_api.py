"""API 통합 테스트 — 임시 DB를 사용하며 실제 사용자 데이터를 건드리지 않는다."""

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from tests.fixtures import (
    DISCUSSION_HIGH,
    DISCUSSION_INJECTION,
    DISCUSSION_LOW,
    PROMPT_DISCUSSION_INTERNSHIP,
)


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_health(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    assert res.json()["status"] == "ok"


def test_capabilities_default_to_offline_core_without_required_keys(client):
    res = client.get("/api/capabilities")
    assert res.status_code == 200
    body = res.json()
    assert body["offline_core"] is True
    assert body["api_key_required"] is False
    assert body["cloud_ai"] is False
    assert body["pwa"] is False
    assert body["score_policy"] == "heuristic_score_only"


def test_evaluate_full_flow(client):
    res = client.post(
        "/api/evaluate",
        json={
            "essay_text": DISCUSSION_HIGH,
            "prompt_text": PROMPT_DISCUSSION_INTERNSHIP,
            "target_score_0_5": 4.0,
        },
    )
    assert res.status_code == 200
    body = res.json()
    result = body["result"]
    assert 1.0 <= result["score_band_1_6"] <= 6.0
    assert result["engine"]["scoring_engine_version"]
    assert result["engine"]["rubric_version"]
    assert len(result["dimensions"]) == 6
    # 저장 후 이력 조회 가능
    history = client.get("/api/history").json()
    assert any(item["id"] == body["submission_id"] for item in history["items"])


def test_engine_metadata_is_complete(client):
    """모든 버전 필드가 채워져 있어야 하고, 미적용 항목은 빈 문자열이 아니라
    명시적 값(not-applicable/uncalibrated)이어야 한다."""
    res = client.post("/api/evaluate", json={"essay_text": DISCUSSION_HIGH})
    engine = res.json()["result"]["engine"]

    required_fields = [
        "exam_spec_version", "rubric_version", "scoring_engine_version",
        "grammar_rules_version", "result_schema_version", "prompt_version",
        "provider", "model", "model_identifier", "calibration_version",
    ]
    for field in required_fields:
        assert engine.get(field), f"engine.{field} must not be empty"

    # 현재는 순수 휴리스틱 채점이므로 명시적으로 표시돼야 한다
    assert engine["provider"] == "heuristic"
    assert engine["calibration_version"] == "uncalibrated"
    assert "not-applicable" in engine["model"]


def test_history_marks_current_records_as_non_legacy(client):
    res = client.post("/api/evaluate", json={"essay_text": DISCUSSION_HIGH})
    sid = res.json()["submission_id"]
    history = client.get("/api/history").json()
    item = next(i for i in history["items"] if i["id"] == sid)
    assert item["is_legacy"] is False


def test_evaluate_rejects_short_essay(client):
    res = client.post(
        "/api/evaluate",
        json={"essay_text": "This essay is way too short to be scored properly but longer than eighty characters so validation happens at word count."[:200] + " word " * 0},
    )
    # 80자 이상이지만 60단어 미만 → 400
    assert res.status_code == 400


def test_evaluate_rejects_empty_essay(client):
    res = client.post("/api/evaluate", json={"essay_text": ""})
    assert res.status_code == 422  # pydantic min_length


def test_prompt_injection_does_not_boost_score(client):
    """인젝션 문구가 점수를 끌어올리면 안 된다."""
    res = client.post("/api/evaluate", json={"essay_text": DISCUSSION_INJECTION})
    assert res.status_code == 200
    injected = res.json()["result"]["score_band_1_6"]

    res2 = client.post("/api/evaluate", json={"essay_text": DISCUSSION_HIGH})
    clean_high = res2.json()["result"]["score_band_1_6"]

    assert injected < clean_high
    assert injected <= 3.0  # 저품질 본문 + 인젝션 → 상위 밴드 불가


def test_low_quality_scores_below_high_quality(client):
    low = client.post("/api/evaluate", json={"essay_text": DISCUSSION_LOW}).json()
    high = client.post("/api/evaluate", json={"essay_text": DISCUSSION_HIGH}).json()
    assert low["result"]["score_band_1_6"] < high["result"]["score_band_1_6"]


def test_history_and_submission_persistence(client):
    created = client.post("/api/evaluate", json={"essay_text": DISCUSSION_HIGH}).json()
    sid = created["submission_id"]
    # 같은 세션에서 결과 재조회(PDF 이전 단계인 DB 로드)까지 확인
    from app.db import get_submission

    record = get_submission(sid)
    assert record is not None
    assert record["essay_text"] == DISCUSSION_HIGH
    assert record["result"]["engine"]["scoring_engine_version"]


def test_precheck(client):
    res = client.post(
        "/api/precheck",
        json={"essay_text": DISCUSSION_HIGH, "prompt_text": PROMPT_DISCUSSION_INTERNSHIP},
    )
    assert res.status_code == 200
    body = res.json()
    assert body["risk_level"] in {"low", "medium", "high"}
