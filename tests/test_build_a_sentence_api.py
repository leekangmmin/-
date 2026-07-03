"""Build a Sentence API 통합 테스트 — 임시 DB를 사용한다."""

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.build_a_sentence_items import BUILD_A_SENTENCE_ITEMS


@pytest.fixture()
def client(tmp_path, monkeypatch):
    monkeypatch.setattr(db_module, "DB_PATH", tmp_path / "test.db")
    from app.main import app

    with TestClient(app) as c:
        yield c


def test_list_items_returns_all_items_without_answers(client):
    res = client.get("/api/build-a-sentence/items")
    assert res.status_code == 200
    data = res.json()
    assert len(data["items"]) == len(BUILD_A_SENTENCE_ITEMS)
    assert "items_version" in data
    for item in data["items"]:
        assert "item_id" in item
        assert "fragment_count" in item
        assert "primary_answer" not in item


def test_get_item_returns_shuffled_fragments_without_answer(client):
    item_id = BUILD_A_SENTENCE_ITEMS[0].item_id
    res = client.get(f"/api/build-a-sentence/items/{item_id}")
    assert res.status_code == 200
    data = res.json()
    assert data["item_id"] == item_id
    assert sorted(data["source_fragments"]) == sorted(BUILD_A_SENTENCE_ITEMS[0].source_fragments)
    assert "primary_answer" not in data
    assert data["is_official"] is False


def test_get_unknown_item_returns_404(client):
    res = client.get("/api/build-a-sentence/items/does-not-exist")
    assert res.status_code == 404


def test_submit_correct_answer(client):
    item = BUILD_A_SENTENCE_ITEMS[0]
    res = client.post(
        f"/api/build-a-sentence/items/{item.item_id}/submit",
        json={"submission_text": item.primary_answer, "time_spent_ms": 4200},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is True
    assert data["match_type"] == "exact"
    assert data["correct_answer"] is None
    assert data["attempt_number"] == 1


def test_submit_incorrect_answer_reveals_correct_answer(client):
    item = BUILD_A_SENTENCE_ITEMS[0]
    res = client.post(
        f"/api/build-a-sentence/items/{item.item_id}/submit",
        json={"submission_text": "completely wrong words here"},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["is_correct"] is False
    assert data["correct_answer"] == item.primary_answer


def test_submit_increments_attempt_number(client):
    item = BUILD_A_SENTENCE_ITEMS[0]
    for expected_attempt in (1, 2, 3):
        res = client.post(
            f"/api/build-a-sentence/items/{item.item_id}/submit",
            json={"submission_text": "wrong"},
        )
        assert res.json()["attempt_number"] == expected_attempt


def test_submit_to_unknown_item_returns_404(client):
    res = client.post(
        "/api/build-a-sentence/items/does-not-exist/submit",
        json={"submission_text": "anything"},
    )
    assert res.status_code == 404


def test_attempts_are_recorded_with_no_official_flag(client):
    item = BUILD_A_SENTENCE_ITEMS[0]
    client.post(
        f"/api/build-a-sentence/items/{item.item_id}/submit",
        json={"submission_text": item.primary_answer},
    )
    attempts = db_module.list_bas_attempts(item_id=item.item_id)
    assert len(attempts) == 1
    assert attempts[0]["is_correct"] is True
    assert attempts[0]["item_id"] == item.item_id
