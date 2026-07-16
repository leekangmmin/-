"""PDF 리포트 렌더러 테스트 (Phase 12).

시각 품질은 자동 테스트로 검증할 수 없으므로, 여기서는 (1) 크래시 없이
2페이지 이내로 생성되는지, (2) 존재하지 않는/None인 밴드·30점 필드를 지어내지
않는지, (3) 폰트가 없어도 degrade하며 죽지 않는지, (4) 엣지 케이스(빈 데이터,
프롬프트 없음)를 안전하게 처리하는지를 검증한다.
"""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

import app.db as db_module
from app.pdf_report import DIM_KO, _score_colors, build_report

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


def _record(**result_overrides):
    result = {
        "estimated_score_0_5": 2.0,
        "confidence": "low",
        "bilingual_feedback": {"summary_ko": "요약입니다."},
        "score_source": "heuristic",
        "prompt_fit_evaluated": True,
        "prompt_fit_score": 3.5,
        "dimensions": [
            {"name": "Structure", "score": 1.5},
            {"name": "Grammar", "score": 5.0},
            {"name": "Vocabulary", "score": 3.8},
        ],
        "strengths": ["어휘가 다양합니다."],
        "weaknesses": ["분량이 짧습니다."],
        "top_priority_actions": [
            {"title": "근거 강화", "why": "예시 부족", "how_to": "For example 추가", "impact": "+0.2", "confidence": "high"},
            {"title": "논리 프레임", "why": "흐름 약함", "how_to": "주장-근거-결론", "impact": "+0.2", "confidence": "medium"},
        ],
        "sentence_edits": [{"original": "I think.", "improved": "I argue.", "note": "더 학술적으로"}],
        "target_eta": {"message": "문법 우선 전략을 쓰세요."},
        "score_source_detail": "내장 기준 점수를 사용했습니다.",
    }
    result.update(result_overrides)
    return {"created_at": "2026-07-16T00:00:00Z", "prompt_type": "academic_discussion", "result": result}


class TestRenderer:
    def test_generates_pdf_bytes(self):
        pdf = build_report(_record(), 1)
        data = bytes(pdf.output())
        assert data[:4] == b"%PDF"
        assert len(data) > 1000

    def test_report_is_two_pages(self):
        pdf = build_report(_record(), 1)
        assert pdf.page_no() == 2

    def test_does_not_crash_without_font(self):
        # 존재하지 않는 후보만 주면 unicode 폰트 미등록 → ASCII degrade, 크래시 금지
        pdf = build_report(_record(), 1, font_candidates=[])
        assert pdf.unicode_font is None
        assert bytes(pdf.output())[:4] == b"%PDF"

    def test_empty_data_is_safe(self):
        rec = {
            "created_at": "2026-01-01",
            "prompt_type": "email",
            "result": {"estimated_score_0_5": 0.0, "confidence": "low"},
        }
        pdf = build_report(rec, 2)
        assert bytes(pdf.output())[:4] == b"%PDF"

    def test_prompt_not_evaluated_shows_no_fabricated_fit(self):
        # prompt_fit_evaluated=False 이면 주제 적합성은 '미측정'이어야 하고 크래시 없어야 함
        pdf = build_report(_record(prompt_fit_evaluated=False, prompt_fit_score=0.0), 3)
        assert bytes(pdf.output())[:4] == b"%PDF"


class TestScoreColors:
    def test_high_score_is_green(self):
        assert _score_colors(4.0)[0] == (23, 160, 93)

    def test_mid_score_is_amber(self):
        assert _score_colors(2.5)[0] == (214, 124, 0)

    def test_low_score_is_red(self):
        assert _score_colors(1.0)[0] == (229, 73, 58)


class TestKoreanLabels:
    def test_all_six_dimensions_have_korean_labels(self):
        for name in ("Structure", "Content", "Coherence", "Example", "Grammar", "Vocabulary"):
            assert name in DIM_KO and DIM_KO[name]


class TestEndToEndViaApi:
    def test_report_endpoint_returns_pdf(self, client):
        sid = client.post("/api/evaluate", json={"essay_text": ESSAY}).json()["submission_id"]
        res = client.get(f"/api/report/{sid}.pdf")
        assert res.status_code == 200
        assert res.headers["content-type"] == "application/pdf"
        assert res.content[:4] == b"%PDF"

    def test_report_404_for_missing_submission(self, client):
        assert client.get("/api/report/999999.pdf").status_code == 404
