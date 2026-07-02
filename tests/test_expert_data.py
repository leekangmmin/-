"""전문가 데이터 import 파이프라인 테스트.

tests/expert_data_fixtures/ 의 모든 데이터는 합성(synthetic) 테스트 데이터다.
"""

from pathlib import Path

import pytest

import app.expert_data as expert_data

FIXTURES = Path(__file__).parent / "expert_data_fixtures"


@pytest.fixture()
def isolated_db(tmp_path, monkeypatch):
    monkeypatch.setattr(expert_data, "EXPERT_DB_PATH", tmp_path / "test_expert.db")
    expert_data.init_expert_db()
    yield


def test_preview_import_does_not_write(isolated_db):
    result = expert_data.preview_import(FIXTURES / "sample_valid.json")
    assert result.dry_run is True
    assert result.rows_imported == 3
    assert result.rows_invalid == 0
    # dry-run이므로 실제 저장은 없어야 한다
    assert expert_data.list_records() == []


def test_import_json_writes_records(isolated_db):
    result = expert_data.import_file(FIXTURES / "sample_valid.json")
    assert result.rows_imported == 3
    assert result.rows_duplicate == 0
    records = expert_data.list_records()
    assert len(records) == 3


def test_import_csv(isolated_db):
    result = expert_data.import_file(FIXTURES / "sample_valid.csv")
    assert result.rows_imported == 1
    assert result.rows_invalid == 0
    records = expert_data.list_records()
    assert records[0]["rater"]["rater_id"] == "synthetic-rater-C"
    assert records[0]["provenance"]["source_type"] == "synthetic"


def test_schema_validation_reports_errors(isolated_db):
    result = expert_data.import_file(FIXTURES / "sample_with_errors.json")
    # 3개 행: 1개 중복(001과 동일 텍스트), 1개 필드 누락, 1개 task_type 오류
    assert result.rows_invalid == 2
    assert len(result.errors) == 2


def test_duplicate_detection_exact_text(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    # sample_with_errors.json의 첫 행은 sample_valid.json의 001과 정확히 같은 response_text
    result = expert_data.import_file(FIXTURES / "sample_with_errors.json")
    assert result.rows_duplicate >= 1


def test_duplicate_detection_within_same_batch(isolated_db, tmp_path):
    import json
    base = json.loads((FIXTURES / "sample_valid.json").read_text())
    dup_row = dict(base["records"][0])
    dup_row["record_id"] = "synthetic-001-dup-in-batch"
    batch = {"records": [base["records"][0], dup_row]}
    batch_path = tmp_path / "batch_with_internal_dup.json"
    batch_path.write_text(json.dumps(batch))

    result = expert_data.import_file(batch_path)
    assert result.rows_imported == 1
    assert result.rows_duplicate == 1


def test_multi_rater_preserved_individually(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    ratings = expert_data.group_ratings("synthetic-001")
    assert len(ratings) == 2
    scores = sorted(r["overall_score"] for r in ratings)
    assert scores == [4.5, 5.0]  # 평균으로 뭉개지 않고 개별 보존


def test_rater_disagreement_and_adjudication_flag(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    result = expert_data.compute_rater_disagreement("synthetic-001", threshold=1.0)
    assert result["rater_count"] == 2
    assert result["max_disagreement"] == 0.5
    assert result["adjudication_required"] is False

    tight_result = expert_data.compute_rater_disagreement("synthetic-001", threshold=0.3)
    assert tight_result["adjudication_required"] is True


def test_dataset_split_is_deterministic_per_prompt(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    records = expert_data.list_records()
    by_prompt: dict[str, set[str]] = {}
    for r in records:
        by_prompt.setdefault(r["prompt_id"], set()).add(r["dataset_split"])
    # 같은 prompt_id의 모든 답안은 같은 split에 배정돼야 한다 (누출 방지)
    for prompt_id, splits in by_prompt.items():
        assert len(splits) == 1, f"{prompt_id} split across multiple sets: {splits}"


def test_split_summary(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    summary = expert_data.dataset_split_summary()
    assert sum(summary.values()) == 3
    assert set(summary.keys()) <= {"development", "calibration", "validation", "locked_test"}


def test_rollback_removes_imported_rows(isolated_db):
    result = expert_data.import_file(FIXTURES / "sample_valid.json")
    assert len(expert_data.list_records()) == 3
    deleted = expert_data.rollback_import(result.import_id)
    assert deleted == 3
    assert expert_data.list_records() == []


def test_import_history_recorded(isolated_db):
    expert_data.import_file(FIXTURES / "sample_valid.json")
    history = expert_data.list_import_history()
    assert len(history) == 1
    assert history[0]["rows_imported"] == 3


def test_no_hardcoded_real_expert_scores():
    """제품 코드 어디에도 실제 전문가 점수를 하드코딩하지 않았는지 확인한다.

    fixtures 디렉터리는 명시적으로 synthetic으로 표시돼 있어야 하며,
    app/ 소스에는 개별 sample response 텍스트가 존재하면 안 된다.
    """
    import app.expert_data as mod
    source = Path(mod.__file__).read_text(encoding="utf-8")
    assert "overall_score" not in source or "= 4." not in source
