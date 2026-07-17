from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.corpus_ingest import ingest_path, safe_aggregate, write_safe_summary
from app.corpus_schema import HighScoreSample
from app.high_score_patterns import analyze_high_score_structure, structure_guide


ACADEMIC = """I strongly believe community projects benefit students because they develop practical skills.

I agree with Mina's point about cooperation. For example, students can organize a neighborhood event.
As a result, they learn to solve real problems and communicate with residents.

For these reasons, schools should support this approach."""

EMAIL = """Dear Program Coordinator,

I am writing regarding the workshop. Unfortunately, a schedule conflict prevents me from attending.
Could you please move my registration? I would also appreciate it if you could confirm the new date.
Thank you for your assistance.

Best regards,
Student"""


def test_schema_rejects_redistribution_for_unknown_source():
    with pytest.raises(ValueError):
        HighScoreSample(sample_id="sample-123", task_type="email", answer_text=EMAIL, content_hash="a" * 64, can_redistribute=True)


def test_ingest_txt_and_deduplicate(tmp_path: Path):
    (tmp_path / "answers.txt").write_text(ACADEMIC + "\n===\n" + ACADEMIC, encoding="utf-8")
    samples = ingest_path(tmp_path)
    assert len(samples) == 1
    assert samples[0].task_type == "academic_discussion"


def test_ingest_csv_and_redact_pii(tmp_path: Path):
    path = tmp_path / "answers.csv"
    path.write_text('task_type,answer_text\nemail,"' + EMAIL.replace('Student', 'student@example.com') + '"\n', encoding="utf-8")
    samples = ingest_path(path)
    assert len(samples) == 1
    assert "student@example.com" not in samples[0].answer_text


def test_move_detection_for_both_tasks():
    academic = analyze_high_score_structure(ACADEMIC, "academic_discussion")
    email = analyze_high_score_structure(EMAIL, "email")
    assert {"stance", "reason", "specific_example", "explanation", "other_view"} <= set(academic.detected_moves)
    assert {"greeting", "purpose", "situation_detail", "polite_request", "second_action", "closing"} <= set(email.detected_moves)


def test_safe_summary_contains_no_raw_text(tmp_path: Path):
    source = tmp_path / "one.md"
    source.write_text(ACADEMIC, encoding="utf-8")
    samples = ingest_path(source)
    out = tmp_path / "report.json"
    write_safe_summary(samples, out)
    payload = out.read_text(encoding="utf-8")
    assert ACADEMIC not in payload
    assert "answer_text" not in payload
    assert json.loads(payload)["sample_count"] == 1


def test_structure_guide_is_korean_friendly_and_quote_free():
    guide = structure_guide(ACADEMIC, "academic_discussion")
    assert "명확한 입장" in guide["detected"]
    assert ACADEMIC not in json.dumps(guide, ensure_ascii=False)


def test_ui_contains_high_score_structure_section():
    root = Path(__file__).resolve().parents[1]
    html = (root / "static" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "static" / "app.js").read_text(encoding="utf-8")
    assert "고득점 구조 체크" in html
    assert "high_score_structure" in javascript


def test_github_pages_webapp_is_relative_and_private():
    root = Path(__file__).resolve().parents[1]
    html = (root / "web" / "index.html").read_text(encoding="utf-8")
    javascript = (root / "web" / "app.js").read_text(encoding="utf-8")
    assert 'href="/static/' not in html
    assert 'src="/static/' not in html
    assert "fetch(" not in javascript
    assert "서버 전송 없음" in html
    assert "service-worker.js" in javascript
    assert "Task Fulfillment" in javascript
    assert "return {dims,taskScore" in javascript
    assert "if (paragraphs <= 1)" not in javascript
    assert "ss.every(s=>words(s).length<=36)" not in javascript
    assert "/ 5.0 예상 과제 점수" in html
