"""집중형 PDF 리포트 렌더러 (Phase 12).

기존 리포트는 20여 개 섹션을 6페이지에 쏟아내 "무엇을 먼저 봐야 하는지"가
불분명했다. 이 모듈은 우선순위가 분명한 2페이지 시각 리포트를 만든다.

- 1페이지 "한눈에": 도넛 점수 게이지 + 한 줄 총평 + **지금 가장 먼저 할 일**
  (가장 크게) + 영역별 점수 막대 + 잘한 점/보완할 점
- 2페이지 "개선 가이드": 우선순위 액션 카드 + 문장 다듬기 예시 +
  목표 리라이팅 + 연습 페이스 + 면책 고지

색상은 앱 UI(static/styles.css)의 토큰 계열을 따른다. 한글은 unicode 폰트가
있을 때만 렌더링되며, 없으면 ASCII로 degrade한다(main.py가 폰트를 주입).
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Sequence

from fpdf import FPDF

# PDF 한글 렌더링용 unicode 폰트 후보 (macOS / Linux·Docker 표준 경로).
# 하나라도 존재하면 등록해서 한글을 렌더링하고, 없으면 ASCII로 degrade한다.
UNICODE_FONT_CANDIDATES = [
    Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
    Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
    Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    Path("/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/truetype/noto/NotoSansCJK-Regular.ttc"),
    Path("/usr/share/fonts/noto-cjk/NotoSansCJK-Regular.ttc"),
    # Windows — 맑은 고딕(대부분의 Windows에 기본 설치)
    Path("C:/Windows/Fonts/malgun.ttf"),
    Path("C:/Windows/Fonts/gulim.ttc"),
]

# ── 색상 팔레트 (앱 UI 계열) ──────────────────────────────────────────────
PRIMARY = (49, 130, 246)        # #3182f6
PRIMARY_DARK = (27, 100, 218)   # #1b64da
PRIMARY_SOFT = (232, 243, 255)
INK = (25, 31, 40)              # #191f28
INK_SUB = (78, 89, 104)         # #4e5968
INK_MUTED = (139, 149, 161)     # #8b95a1
BORDER = (229, 232, 235)
BG_SOFT = (246, 248, 250)
WHITE = (255, 255, 255)
GREEN = (23, 160, 93)
GREEN_SOFT = (230, 246, 238)
AMBER = (214, 124, 0)
AMBER_SOFT = (255, 243, 224)
RED = (229, 73, 58)
RED_SOFT = (253, 236, 234)

# 영역 영문명 → 한글 라벨
DIM_KO = {
    "Structure": "구성",
    "Content": "내용",
    "Coherence": "일관성",
    "Example": "근거·예시",
    "Grammar": "문법",
    "Vocabulary": "어휘",
}


def _score_colors(score: float) -> tuple[tuple[int, int, int], tuple[int, int, int]]:
    """점수(0-5)에 따른 (진한색, 연한 배경색)."""
    if score >= 3.5:
        return GREEN, GREEN_SOFT
    if score >= 2.0:
        return AMBER, AMBER_SOFT
    return RED, RED_SOFT


class ReportPDF(FPDF):
    """브랜드 푸터가 있는 A4 리포트."""

    unicode_font: str | None = None

    def footer(self) -> None:
        self.set_y(-12)
        self.set_draw_color(*BORDER)
        self.set_line_width(0.2)
        self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())
        self._font("", 7.5)
        self.set_text_color(*INK_MUTED)
        self.set_xy(self.l_margin, self.get_y() + 1.5)
        self.cell(0, 4, self._safe("토플 라이팅 채점기 · 연습용 리포트"), align="L")
        self.set_xy(self.l_margin, self.get_y())
        self.cell(0, 4, f"{self.page_no()} / {{nb}}", align="R")
        self.set_text_color(*INK)

    # ── 폰트/텍스트 헬퍼 ──────────────────────────────────────────────
    def _font(self, style: str = "", size: float = 11) -> None:
        if self.unicode_font:
            # unicode(.ttc) 폰트는 단일 스타일만 등록했으므로 style은 무시하고
            # 크기만 조절한다(볼드 효과는 크기·색으로 대체).
            self.set_font(self.unicode_font, size=size)
        else:
            self.set_font("Helvetica", style=style, size=size)

    def _safe(self, text: str) -> str:
        if self.unicode_font:
            return text
        return text.encode("ascii", errors="ignore").decode("ascii")

    @property
    def content_w(self) -> float:
        return self.w - self.l_margin - self.r_margin


def _draw_header(pdf: ReportPDF, submission_id: int, created_at: str, prompt_type: str) -> None:
    left, w = pdf.l_margin, pdf.content_w
    y = pdf.get_y()
    h = 22
    pdf.set_fill_color(*PRIMARY_DARK)
    pdf.rect(left, y, w, h, "F")

    pdf.set_text_color(*WHITE)
    pdf._font("B", 17)
    pdf.set_xy(left + 6, y + 4.5)
    pdf.cell(0, 7, pdf._safe("라이팅 채점 리포트"))

    type_ko = "이메일" if prompt_type == "email" else "학술 토론"
    pdf._font("", 9.5)
    pdf.set_xy(left + 6, y + 13)
    pdf.cell(0, 5, pdf._safe(f"#{submission_id}  ·  {type_ko}  ·  {created_at[:10]}  ·  연습용"))

    pdf.set_text_color(*INK)
    pdf.set_y(y + h + 6)


def _draw_gauge(pdf: ReportPDF, cx: float, cy: float, r: float, score: float, max_score: float = 5.0) -> None:
    """도넛 점수 게이지: 회색 트랙 + 점수 비율만큼 색상 아크 + 중앙 큰 숫자."""
    dark, _ = _score_colors(score)
    frac = max(0.0, min(1.0, score / max_score))

    pdf.set_line_width(5.2)
    # 트랙
    pdf.set_draw_color(*BORDER)
    pdf.arc(cx, cy, r, 0, 360, style="D")
    # 진행 아크 (12시에서 시계방향)
    if frac > 0.001:
        pdf.set_draw_color(*dark)
        start = 90.0
        end = 90.0 - 360.0 * frac
        pdf.arc(cx, cy, r, end, start, style="D")
    pdf.set_line_width(0.2)

    # 중앙 숫자
    pdf.set_text_color(*dark)
    pdf._font("B", 26)
    num = f"{score:.1f}"
    pdf.set_xy(cx - r, cy - 6.5)
    pdf.cell(2 * r, 9, num, align="C")
    pdf.set_text_color(*INK_MUTED)
    pdf._font("", 8)
    pdf.set_xy(cx - r, cy + 3)
    pdf.cell(2 * r, 4, f"/ {max_score:.0f}", align="C")
    pdf.set_text_color(*INK)


def _stat_chip(pdf: ReportPDF, x: float, y: float, w: float, h: float, label: str, value: str) -> None:
    pdf.set_fill_color(*BG_SOFT)
    pdf.set_draw_color(*BORDER)
    pdf.rect(x, y, w, h, "DF")
    pdf.set_text_color(*INK_MUTED)
    pdf._font("", 7.5)
    pdf.set_xy(x + 2.6, y + 2)
    pdf.cell(w - 5, 3.4, pdf._safe(label))
    pdf.set_text_color(*INK)
    pdf._font("B", 12)
    pdf.set_xy(x + 2.6, y + 6.2)
    pdf.cell(w - 5, 5, pdf._safe(value))
    pdf.set_text_color(*INK)


def _draw_hero(
    pdf: ReportPDF,
    score: float,
    confidence: str,
    summary: str,
    prompt_fit_score: float | None,
    score_source: str,
) -> None:
    left, w = pdf.l_margin, pdf.content_w
    y = pdf.get_y()
    h = 42
    # 카드 배경
    pdf.set_fill_color(*WHITE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(left, y, w, h, "DF")

    # 게이지 (왼쪽)
    gauge_cx = left + 24
    gauge_cy = y + 17
    _draw_gauge(pdf, gauge_cx, gauge_cy, 15, score)
    pdf.set_text_color(*INK_MUTED)
    pdf._font("", 7.5)
    pdf.set_xy(left + 6, y + h - 6)
    pdf.cell(36, 4, pdf._safe("예상 과제 점수"), align="C")
    pdf.set_text_color(*INK)

    # 오른쪽: 한 줄 총평 + 스탯 칩
    rx = left + 50
    rw = w - 54
    pdf._font("", 9.5)
    pdf.set_text_color(*INK_SUB)
    pdf.set_xy(rx, y + 4)
    pdf.multi_cell(rw, 4.6, pdf._safe(summary), align="L")

    chip_y = y + h - 15
    chip_gap = 3
    chip_w = (rw - 2 * chip_gap) / 3
    conf_ko = {"high": "높음", "medium": "보통", "low": "낮음"}.get(confidence, confidence)
    fit_val = f"{prompt_fit_score:.1f} / 5" if prompt_fit_score is not None else "미측정"
    source_ko = {
        "llm": "AI 루브릭",
        "heuristic": "내장 기준",
        "heuristic_fallback": "내장 기준",
        "legacy": "내장 기준",
    }.get(score_source, "내장 기준")
    _stat_chip(pdf, rx, chip_y, chip_w, 12, "신뢰도", conf_ko)
    _stat_chip(pdf, rx + chip_w + chip_gap, chip_y, chip_w, 12, "주제 적합성", fit_val)
    _stat_chip(pdf, rx + 2 * (chip_w + chip_gap), chip_y, chip_w, 12, "채점 방식", source_ko)

    pdf.set_y(y + h + 6)


def _section_title(pdf: ReportPDF, text: str, accent: tuple[int, int, int] = PRIMARY) -> None:
    left = pdf.l_margin
    y = pdf.get_y()
    pdf.set_fill_color(*accent)
    pdf.rect(left, y + 0.5, 3, 5, "F")
    pdf.set_text_color(*INK)
    pdf._font("B", 12)
    pdf.set_xy(left + 5, y)
    pdf.cell(0, 6, pdf._safe(text))
    pdf.set_y(y + 8.5)


def _draw_top_action(pdf: ReportPDF, action: dict) -> None:
    """'지금 가장 먼저 할 일' — 리포트에서 가장 강조되는 요소."""
    if not action:
        return
    left, w = pdf.l_margin, pdf.content_w
    _section_title(pdf, "지금 가장 먼저 할 일", PRIMARY)

    title = str(action.get("title", ""))
    how = str(action.get("how_to", ""))
    impact = str(action.get("impact", ""))

    y = pdf.get_y()
    # 높이 계산: 제목 1줄 + how_to 래핑
    pdf._font("", 9.5)
    how_lines = pdf.multi_cell(w - 40, 4.6, pdf._safe(how), align="L", dry_run=True, output="LINES")
    h = 12 + max(1, len(how_lines)) * 4.6 + 4

    pdf.set_fill_color(*PRIMARY_SOFT)
    pdf.set_draw_color(*PRIMARY)
    pdf.rect(left, y, w, h, "DF")
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(left, y, 3, h, "F")

    # 제목
    pdf.set_text_color(*PRIMARY_DARK)
    pdf._font("B", 13)
    pdf.set_xy(left + 7, y + 3.5)
    pdf.cell(w - 45, 6, pdf._safe(title))

    # impact 배지 (우상단)
    if impact:
        badge_w = 26
        pdf.set_fill_color(*PRIMARY)
        pdf.rect(left + w - badge_w - 4, y + 3.5, badge_w, 6.5, "F")
        pdf.set_text_color(*WHITE)
        pdf._font("B", 8.5)
        pdf.set_xy(left + w - badge_w - 4, y + 5)
        pdf.cell(badge_w, 3.5, pdf._safe(f"기대 {impact}"), align="C")

    # how_to
    pdf.set_text_color(*INK_SUB)
    pdf._font("", 9.5)
    pdf.set_xy(left + 7, y + 11)
    pdf.multi_cell(w - 14, 4.6, pdf._safe(how), align="L")

    pdf.set_text_color(*INK)
    pdf.set_y(y + h + 6)


def _draw_dimension_bars(pdf: ReportPDF, dimensions: Sequence[dict]) -> None:
    if not dimensions:
        return
    _section_title(pdf, "영역별 점수", PRIMARY)
    left, w = pdf.l_margin, pdf.content_w
    label_w = 26
    value_w = 16
    bar_w = w - label_w - value_w
    row_h = 8.4
    y = pdf.get_y()

    for dim in list(dimensions)[:6]:
        name = str(dim.get("name", ""))
        score = max(0.0, min(5.0, float(dim.get("score", 0.0))))
        dark, soft = _score_colors(score)
        ko = DIM_KO.get(name, name)

        # 라벨
        pdf.set_text_color(*INK)
        pdf._font("", 9.5)
        pdf.set_xy(left, y + 1)
        pdf.cell(label_w, 5, pdf._safe(ko))

        # 트랙 + 채움
        track_x = left + label_w
        pdf.set_fill_color(*BG_SOFT)
        pdf.rect(track_x, y + 1.4, bar_w, 4, "F")
        pdf.set_fill_color(*dark)
        pdf.rect(track_x, y + 1.4, bar_w * score / 5.0, 4, "F")

        # 점수
        pdf.set_text_color(*dark)
        pdf._font("B", 9.5)
        pdf.set_xy(track_x + bar_w + 2, y + 1)
        pdf.cell(value_w - 2, 5, f"{score:.1f}", align="R")
        y += row_h

    pdf.set_text_color(*INK)
    pdf.set_y(y + 3)


def _draw_two_columns(pdf: ReportPDF, strengths: Sequence[str], weaknesses: Sequence[str]) -> None:
    left, w = pdf.l_margin, pdf.content_w
    gap = 6
    col_w = (w - gap) / 2
    y = pdf.get_y()

    def col(x: float, title: str, items: Sequence[str], accent: tuple[int, int, int], soft: tuple[int, int, int]) -> float:
        picked = [str(i) for i in items[:3] if str(i).strip()]
        pdf._font("", 8.8)
        # 높이 계산
        total_lines = 0
        wrapped_all = []
        for it in picked:
            lines = pdf.multi_cell(col_w - 8, 4.2, pdf._safe(it), dry_run=True, output="LINES")
            wrapped_all.append(lines)
            total_lines += max(1, len(lines))
        body_h = total_lines * 4.2 + len(picked) * 2.5
        h = 9 + max(body_h, 6)

        pdf.set_fill_color(*soft)
        pdf.set_draw_color(*accent)
        pdf.rect(x, y, col_w, h, "DF")
        pdf.set_text_color(*accent)
        pdf._font("B", 10)
        pdf.set_xy(x + 4, y + 2.6)
        pdf.cell(col_w - 8, 5, pdf._safe(title))

        cy = y + 9
        pdf.set_text_color(*INK_SUB)
        pdf._font("", 8.8)
        for it in picked:
            pdf.set_xy(x + 4, cy)
            pdf.multi_cell(col_w - 8, 4.2, pdf._safe("· " + it), align="L")
            cy = pdf.get_y() + 1.4
        return h

    h1 = col(left, "잘한 점", strengths, GREEN, GREEN_SOFT)
    h2 = col(left + col_w + gap, "보완할 점", weaknesses, AMBER, AMBER_SOFT)
    pdf.set_text_color(*INK)
    pdf.set_y(y + max(h1, h2) + 5)


def _draw_action_card(pdf: ReportPDF, idx: int, action: dict) -> None:
    left, w = pdf.l_margin, pdf.content_w
    title = str(action.get("title", ""))
    why = str(action.get("why", ""))
    how = str(action.get("how_to", ""))
    conf = str(action.get("confidence", "medium"))

    pdf._font("", 8.8)
    why_lines = pdf.multi_cell(w - 12, 4.2, pdf._safe("왜? " + why), dry_run=True, output="LINES")
    how_lines = pdf.multi_cell(w - 12, 4.2, pdf._safe("어떻게? " + how), dry_run=True, output="LINES")
    h = 9 + (len(why_lines) + len(how_lines)) * 4.2 + 3

    if pdf.get_y() + h > pdf.h - 20:
        pdf.add_page()

    y = pdf.get_y()
    pdf.set_fill_color(*WHITE)
    pdf.set_draw_color(*BORDER)
    pdf.rect(left, y, w, h, "DF")
    pdf.set_fill_color(*PRIMARY)
    pdf.rect(left, y, 3, h, "F")

    # 번호 + 제목
    pdf.set_text_color(*PRIMARY_DARK)
    pdf._font("B", 10.5)
    pdf.set_xy(left + 6, y + 2.6)
    pdf.cell(0, 5, pdf._safe(f"{idx}. {title}"))

    pdf.set_text_color(*INK_SUB)
    pdf._font("", 8.8)
    pdf.set_xy(left + 6, y + 8.5)
    pdf.multi_cell(w - 12, 4.2, pdf._safe("왜?  " + why), align="L")
    pdf.set_x(left + 6)
    pdf.multi_cell(w - 12, 4.2, pdf._safe("어떻게?  " + how), align="L")

    pdf.set_text_color(*INK)
    pdf.set_y(y + h + 3)


def _draw_sentence_edit(pdf: ReportPDF, edit: dict) -> None:
    left, w = pdf.l_margin, pdf.content_w
    original = str(edit.get("original", ""))
    improved = str(edit.get("improved", ""))
    note = str(edit.get("note", ""))

    pdf._font("", 8.8)
    o_lines = pdf.multi_cell(w - 14, 4.2, original, dry_run=True, output="LINES")
    i_lines = pdf.multi_cell(w - 14, 4.2, improved, dry_run=True, output="LINES")
    n_lines = pdf.multi_cell(w - 14, 4.0, pdf._safe(note), dry_run=True, output="LINES") if note else []
    h = 4 + len(o_lines) * 4.2 + 3 + len(i_lines) * 4.2 + (len(n_lines) * 4.0 + 2 if note else 0) + 4

    if pdf.get_y() + h > pdf.h - 20:
        pdf.add_page()

    y = pdf.get_y()
    pdf.set_fill_color(*BG_SOFT)
    pdf.set_draw_color(*BORDER)
    pdf.rect(left, y, w, h, "DF")

    cy = y + 2.5
    # before
    pdf.set_text_color(*RED)
    pdf._font("B", 8)
    pdf.set_xy(left + 4, cy)
    pdf.cell(14, 4, pdf._safe("수정 전"))
    pdf.set_text_color(*INK_SUB)
    pdf._font("", 8.8)
    pdf.set_xy(left + 18, cy)
    pdf.multi_cell(w - 22, 4.2, original, align="L")
    cy = pdf.get_y() + 1.5
    # after
    pdf.set_text_color(*GREEN)
    pdf._font("B", 8)
    pdf.set_xy(left + 4, cy)
    pdf.cell(14, 4, pdf._safe("수정 후"))
    pdf.set_text_color(*INK)
    pdf._font("", 8.8)
    pdf.set_xy(left + 18, cy)
    pdf.multi_cell(w - 22, 4.2, improved, align="L")
    if note:
        cy = pdf.get_y() + 1
        pdf.set_text_color(*INK_MUTED)
        pdf._font("", 8)
        pdf.set_xy(left + 18, cy)
        pdf.multi_cell(w - 22, 4.0, pdf._safe("→ " + note), align="L")

    pdf.set_text_color(*INK)
    pdf.set_y(y + h + 3)


def _draw_disclaimer(pdf: ReportPDF, score_source_detail: str) -> None:
    left, w = pdf.l_margin, pdf.content_w
    if pdf.get_y() + 22 > pdf.h - 16:
        pdf.add_page()
    y = pdf.get_y() + 2
    pdf.set_fill_color(*BG_SOFT)
    pdf.set_draw_color(*BORDER)
    pdf._font("", 8)
    text = (
        "이 점수는 공개 기준을 참고한 연습용 추정치이며 ETS 공식 점수가 아닙니다. "
        "실제 시험 점수와 다를 수 있습니다."
    )
    if score_source_detail:
        text += " " + score_source_detail
    lines = pdf.multi_cell(w - 8, 4, pdf._safe(text), dry_run=True, output="LINES")
    h = len(lines) * 4 + 5
    pdf.rect(left, y, w, h, "DF")
    pdf.set_text_color(*INK_MUTED)
    pdf.set_xy(left + 4, y + 2.5)
    pdf.multi_cell(w - 8, 4, pdf._safe(text), align="L")
    pdf.set_text_color(*INK)


def _register_unicode_font(pdf: ReportPDF, candidates: Sequence[Path] | None = None) -> None:
    """존재하는 첫 unicode 폰트를 등록하고 pdf.unicode_font를 설정한다.
    등록에 실패하면 unicode_font=None으로 남아 ASCII degrade된다."""
    for path in (candidates if candidates is not None else UNICODE_FONT_CANDIDATES):
        if not path.exists():
            continue
        try:
            pdf.add_font("ReportUni", fname=str(path))
            pdf.unicode_font = "ReportUni"
            return
        except Exception:
            continue


def build_report(
    record: dict[str, Any],
    submission_id: int,
    font_candidates: Sequence[Path] | None = None,
) -> ReportPDF:
    """리포트 PDF 객체를 만들어 반환한다(호출부에서 output). 한글 폰트를
    자동 등록하며, 사용 가능한 폰트가 없으면 한글이 ASCII로 degrade된다."""
    result = record["result"]

    pdf = ReportPDF(format="A4")
    _register_unicode_font(pdf, font_candidates)
    pdf.set_auto_page_break(auto=True, margin=16)
    pdf.set_margins(14, 14, 14)
    pdf.alias_nb_pages()
    pdf.add_page()

    score = float(result.get("estimated_score_0_5", 0.0) or 0.0)
    confidence = str(result.get("confidence", "-"))
    bilingual = result.get("bilingual_feedback", {}) or {}
    summary = str(bilingual.get("summary_ko", "")).strip() or "제출한 답안을 분석했습니다. 아래 우선순위부터 개선해 보세요."
    prompt_fit_score = (
        float(result.get("prompt_fit_score", 0.0))
        if result.get("prompt_fit_evaluated")
        else None
    )
    score_source = str(result.get("score_source", "heuristic"))

    # ── 1페이지 ─────────────────────────────────────────────────────
    _draw_header(pdf, submission_id, str(record["created_at"]), str(record.get("prompt_type", "")))
    _draw_hero(pdf, score, confidence, summary, prompt_fit_score, score_source)

    actions = result.get("top_priority_actions", []) or []
    if actions:
        _draw_top_action(pdf, actions[0])

    _draw_dimension_bars(pdf, result.get("dimensions", []))
    _draw_two_columns(pdf, result.get("strengths", []), result.get("weaknesses", []))

    # ── 2페이지 ─────────────────────────────────────────────────────
    pdf.add_page()
    if len(actions) > 1:
        _section_title(pdf, "개선 우선순위", PRIMARY)
        for i, action in enumerate(actions[1:4], start=2):
            _draw_action_card(pdf, i, action)

    sentence_edits = result.get("sentence_edits", []) or []
    if sentence_edits:
        _section_title(pdf, "문장 다듬기 예시", GREEN)
        for edit in sentence_edits[:3]:
            _draw_sentence_edit(pdf, edit)

    target_eta = result.get("target_eta", {}) or {}
    eta_msg = str(target_eta.get("message", "")).strip()
    if eta_msg:
        _section_title(pdf, "연습 페이스", AMBER)
        left, w = pdf.l_margin, pdf.content_w
        y = pdf.get_y()
        pdf._font("", 9)
        lines = pdf.multi_cell(w - 8, 4.4, pdf._safe(eta_msg), dry_run=True, output="LINES")
        h = len(lines) * 4.4 + 5
        pdf.set_fill_color(*AMBER_SOFT)
        pdf.set_draw_color(*AMBER)
        pdf.rect(left, y, w, h, "DF")
        pdf.set_text_color(*INK_SUB)
        pdf.set_xy(left + 4, y + 2.5)
        pdf.multi_cell(w - 8, 4.4, pdf._safe(eta_msg), align="L")
        pdf.set_text_color(*INK)
        pdf.set_y(y + h + 5)

    _draw_disclaimer(pdf, str(result.get("score_source_detail", "")))
    return pdf
