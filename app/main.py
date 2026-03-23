from __future__ import annotations

from datetime import UTC, datetime
from pathlib import Path
import textwrap
from typing import Literal, cast

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from fpdf import FPDF

from app.advanced import (
    apply_corrections_to_essay,
    bilingual_summary,
    build_revision_diff,
    build_grammar_drills,
    build_grammar_impact,
    build_before_after_projection,
    build_pre_submit_checklist,
    build_dashboard,
    build_score_simulator,
    build_smart_recommendations,
    build_top_priority_actions,
    build_target_eta,
    build_target_band_strategy,
    build_sentence_variety,
    build_weekly_plan,
    build_repetition_training,
    build_examiner_feedback,
    confidence_reason,
    detect_prompt_type,
    detailed_grammar_corrections,
    evaluate_prompt_fit,
    grammar_error_stats,
    map_claim_evidence,
    personalization_advice,
    paraphrase_recommendations,
    personal_weakness_ranking,
    pre_submit_risk,
    rewrite_for_target,
    sample_compare,
    score_highlights,
    template_coach,
    weakness_dictionary,
)
from app.db import get_submission, init_db, list_all_results, list_recent, save_submission
from app.env_loader import load_local_env
from app.feedback import build_feedback
from app.models import (
    TargetEta,
    SentenceVariety,
    BilingualFeedback,
    ClaimEvidenceTag,
    DashboardResponse,
    EvaluateRequest,
    EvaluateResponse,
    EvaluationResult,
    ExaminerFeedback,
    GrammarImpactItem,
    BeforeAfterProjection,
    GrammarCorrection,
    GrammarDrill,
    GrammarIssueItem,
    GrammarTrendPoint,
    GrammarStats,
    ChecklistItem,
    PersonalizationAdvice,
    ParaphraseSuggestion,
    PreSubmitChecklist,
    PrecheckRequest,
    PromptType,
    PromptFit,
    RewriteSuggestion,
    RiskCheckResponse,
    SampleComparison,
    ScoreHighlight,
    SmartRecommendation,
    TargetBandStrategyItem,
    RepetitionTrainingItem,
    ScoreSimulatorItem,
    ScoreBandProfile,
    ScoreTrendPoint,
    SubmissionHistoryItem,
    SubmissionHistoryResponse,
    TemplateCoach,
    WeaknessCard,
    VocabAnalysisRequest,
    VocabAnalysisResponse,
    WeeklyReportResponse,
    DailySubmissionCount,
    CompareResponse,
    CompareScoreInfo,
    AIConfigRequest,
    AIConfigResponse,
)
from app.ai_mode import ai_enabled, ai_enhance, ai_runtime_config
from app.db import get_setting, set_setting
from app.scorer import analyze_essay, grammar_cap_status, score_essay
from app.vocab_analysis import analyze_vocabulary

app = FastAPI(title="TOEFL Writing Evaluator", version="1.0.0")

TOEFL_BAND_TABLE: dict[float, dict[str, str]] = {
    6.0: {"reading": "29-30", "listening": "28-30", "speaking": "28-30", "writing": "29-30", "total": "114+"},
    5.5: {"reading": "27-28", "listening": "26-27", "speaking": "27", "writing": "27-28", "total": "107+"},
    5.0: {"reading": "24-26", "listening": "22-25", "speaking": "25-26", "writing": "24-26", "total": "95+"},
    4.5: {"reading": "22-23", "listening": "20-21", "speaking": "23-24", "writing": "21-23", "total": "86+"},
    4.0: {"reading": "18-21", "listening": "17-19", "speaking": "20-22", "writing": "17-20", "total": "72+"},
    3.5: {"reading": "12-17", "listening": "13-16", "speaking": "18-19", "writing": "15-16", "total": "58+"},
    3.0: {"reading": "6-11", "listening": "9-12", "speaking": "16-17", "writing": "13-14", "total": "44+"},
    2.5: {"reading": "4-5", "listening": "6-8", "speaking": "13-15", "writing": "11-12", "total": "34+"},
    2.0: {"reading": "3", "listening": "4-5", "speaking": "10-12", "writing": "7-10", "total": "24+"},
    1.5: {"reading": "2", "listening": "2-3", "speaking": "5-9", "writing": "3-6", "total": "12+"},
    1.0: {"reading": "0-1", "listening": "0-1", "speaking": "0-4", "writing": "0-2", "total": "0+"},
}


def _to_band_1_6(score_0_5: float) -> float:
    raw = max(1.0, min(6.0, score_0_5 + 1.0))
    return round(raw * 2.0) / 2.0


def _band_profile(score_band_1_6: float) -> dict[str, str]:
    return TOEFL_BAND_TABLE.get(score_band_1_6, TOEFL_BAND_TABLE[1.0])


def _ai_public_config() -> AIConfigResponse:
    runtime = ai_runtime_config()
    provider_raw = str(runtime.get("provider", "openai")).strip().lower() or "openai"
    provider = cast(Literal["openai", "claude", "gemini"], provider_raw if provider_raw in {"openai", "claude", "gemini"} else "openai")
    enabled = bool(runtime.get("enabled"))
    openai_model = str(runtime.get("openai_model", "gpt-4.1-mini"))
    anthropic_model = str(runtime.get("anthropic_model", "claude-3-5-sonnet-latest"))
    gemini_model = str(runtime.get("gemini_model", "gemini-1.5-pro-latest"))
    return AIConfigResponse(
        provider=provider,
        enabled=enabled,
        openai_model=openai_model,
        anthropic_model=anthropic_model,
        gemini_model=gemini_model,
        has_openai_key=bool(str(runtime.get("openai_api_key", "")).strip()),
        has_anthropic_key=bool(str(runtime.get("anthropic_api_key", "")).strip()),
        has_gemini_key=bool(str(runtime.get("gemini_api_key", "")).strip()),
    )

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = BASE_DIR / "static"
load_local_env(BASE_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok", "time": datetime.now(UTC).isoformat()}


@app.get("/api/ai/config", response_model=AIConfigResponse)
def get_ai_config() -> AIConfigResponse:
    return _ai_public_config()


@app.post("/api/ai/config", response_model=AIConfigResponse)
def save_ai_config(payload: AIConfigRequest) -> AIConfigResponse:
    set_setting("ai_provider", payload.provider)
    set_setting("ai_enabled", "1" if payload.enabled else "0")

    if payload.openai_api_key is not None:
        set_setting("openai_api_key", payload.openai_api_key.strip())
    if payload.anthropic_api_key is not None:
        set_setting("anthropic_api_key", payload.anthropic_api_key.strip())
    if payload.gemini_api_key is not None:
        set_setting("gemini_api_key", payload.gemini_api_key.strip())

    if payload.openai_model is not None:
        set_setting("openai_model", payload.openai_model.strip())
    if payload.anthropic_model is not None:
        set_setting("anthropic_model", payload.anthropic_model.strip())
    if payload.gemini_model is not None:
        set_setting("gemini_model", payload.gemini_model.strip())

    return _ai_public_config()


@app.post("/api/ai/test")
def test_ai_connection() -> dict[str, str | bool]:
    cfg = ai_runtime_config()
    if not ai_enabled(cfg):
        return {"ok": False, "message": "AI 연결이 비활성화되어 있거나 API 키가 없습니다."}

    sample = "Students is often tired and they needs clearer feedback to improve writing quality."
    result = ai_enhance(
        sample,
        "academic_discussion",
        paraphrase_fallback=[],
        grammar_drills_fallback=[],
        sample_paragraph_fallback="",
        cfg=cfg,
    )
    if result:
        return {"ok": True, "message": f"{cfg.get('provider', 'openai')} 연결 테스트 성공"}
    return {"ok": False, "message": f"{cfg.get('provider', 'openai')} 응답을 확인하지 못했습니다."}


@app.post("/api/evaluate", response_model=EvaluateResponse)
def evaluate(payload: EvaluateRequest) -> EvaluateResponse:
    prompt_type = cast(PromptType, payload.prompt_type or detect_prompt_type(payload.essay_text))
    dimensions, total_score = score_essay(payload.essay_text, prompt_type)
    feedback = build_feedback(payload.essay_text, prompt_type, total_score)
    prompt_fit_data = evaluate_prompt_fit(payload.prompt_text, payload.essay_text)
    claim_map_data = map_claim_evidence(payload.essay_text)
    grammar_stats_data = grammar_error_stats(payload.essay_text)
    target_score_0_5 = min(5.0, max(0.0, payload.target_score_0_5))
    rewrite_data = rewrite_for_target(payload.essay_text, total_score, target_score_0_5)
    sample_data = sample_compare(payload.essay_text, prompt_type)
    historical_rows = list_all_results(limit=200)
    template_data = template_coach(prompt_type)
    highlight_data = score_highlights(payload.essay_text)
    weakness_data = weakness_dictionary(payload.essay_text, grammar_stats_data, historical_rows)
    personalization_data = personalization_advice(historical_rows)
    paraphrase_data = paraphrase_recommendations(payload.essay_text, prompt_type)
    checklist_data = build_pre_submit_checklist(prompt_type, payload.prompt_text, payload.essay_text)
    checklist_obj = PreSubmitChecklist(
        total_score=int(checklist_data["total_score"]),
        items=[ChecklistItem(**item) for item in checklist_data["items"]],
    )
    drills_data = build_grammar_drills(grammar_stats_data)
    drills_obj = [GrammarDrill(**item) for item in drills_data]
    grammar_corrections_data = detailed_grammar_corrections(payload.essay_text)
    grammar_corrections_obj = [
        GrammarCorrection(
            sentence=str(item.get("sentence", "")),
            error_type=str(item.get("error_type", "")),
            focus_text=str(item.get("focus_text", "")),
            focus_start=int(item["focus_start"]) if item.get("focus_start") is not None else None,
            focus_end=int(item["focus_end"]) if item.get("focus_end") is not None else None,
            corrected=str(item.get("corrected", "")),
            explanation=str(item.get("explanation", "")),
            severity=cast(Literal["low", "medium", "high"], str(item.get("severity", "medium"))),
        )
        for item in grammar_corrections_data
    ]
    metrics = analyze_essay(payload.essay_text)
    simulator_data = build_score_simulator(total_score, grammar_stats_data, metrics.evidence_hits)
    simulator_obj = [ScoreSimulatorItem(**item) for item in simulator_data]
    weekly_plan_data = build_weekly_plan(feedback["weaknesses"])
    weakness_ranking_data = personal_weakness_ranking(historical_rows, limit=10)
    weekly_plan_data = build_weekly_plan(feedback["weaknesses"], weakness_ranking_data)
    grammar_impact_data = build_grammar_impact(grammar_stats_data)
    projection_data = build_before_after_projection(total_score, grammar_stats_data)
    target_strategy_data = build_target_band_strategy(target_score_0_5, total_score)
    repetition_training_data = build_repetition_training(payload.essay_text)
    examiner_feedback_data = build_examiner_feedback(total_score, grammar_stats_data, float(prompt_fit_data["score"]), payload.exam_mode)
    smart_recommendations_data = build_smart_recommendations(
        payload.essay_text,
        prompt_type,
        grammar_stats_data,
        float(prompt_fit_data["score"]),
        float(total_score),
    )
    top_priority_data = build_top_priority_actions(smart_recommendations_data, top_n=3)
    sentence_variety_data = build_sentence_variety(payload.essay_text)
    eta_data = build_target_eta(historical_rows, total_score, target_score_0_5)
    auto_rewrite = apply_corrections_to_essay(payload.essay_text, grammar_corrections_data)
    revision_diff = build_revision_diff(payload.essay_text, auto_rewrite)

    # Only apply prompt-fit adjustment when a real prompt was provided
    if payload.prompt_text.strip():
        if prompt_fit_data["score"] < 2.5:
            total_score = max(0.0, total_score - 1.0)
        elif prompt_fit_data["score"] < 3.0:
            total_score = max(0.0, total_score - 0.5)

    if len(payload.essay_text.split()) < 60:
        raise HTTPException(
            status_code=400,
            detail="Essay is too short. Please write at least 60 words.",
        )

    estimated_30 = int(round((total_score / 5.0) * 30))
    score_band_1_6 = _to_band_1_6(total_score)
    score_profile = _band_profile(score_band_1_6)
    score_profile_obj = ScoreBandProfile(**score_profile)
    cap = grammar_cap_status(payload.essay_text)

    runtime_ai = ai_runtime_config()
    ai_mode = "local"
    ai_provider = "none"
    if ai_enabled(runtime_ai):
        ai_payload = ai_enhance(
            payload.essay_text,
            prompt_type,
            paraphrase_data,
            drills_data,
            feedback["upgraded_sample_paragraph"],
            cfg=runtime_ai,
        )
        if ai_payload:
            ai_mode = "ai"
            ai_provider = cast(Literal["none", "openai", "claude", "gemini"], str(runtime_ai.get("provider", "openai")))
            paraphrase_data = ai_payload.get("paraphrase_recommendations", paraphrase_data) or paraphrase_data
            drills_data = ai_payload.get("grammar_drills", drills_data) or drills_data
            drills_obj = [GrammarDrill(**item) for item in drills_data]
            feedback["upgraded_sample_paragraph"] = ai_payload.get(
                "upgraded_sample_paragraph", feedback["upgraded_sample_paragraph"]
            )

    result = EvaluationResult(
        estimated_score_0_5=total_score,
        estimated_score_30=estimated_30,
        score_band_1_6=score_band_1_6,
        score_profile=score_profile_obj,
        ai_mode=ai_mode,
        ai_provider=ai_provider,
        grammar_cap_applied=bool(cap["applied"]),
        grammar_cap_reason=str(cap["reason"]),
        confidence=feedback["confidence"],
        confidence_reason=confidence_reason(
            feedback["confidence"],
            prompt_fit_data["score"],
            grammar_stats_data["total"],
            payload.essay_text,
        ),
        dimensions=dimensions,
        prompt_fit=PromptFit(**prompt_fit_data),
        claim_evidence_map=[ClaimEvidenceTag(**item) for item in claim_map_data],
        grammar_stats=GrammarStats(**grammar_stats_data),
        target_rewrite=RewriteSuggestion(**rewrite_data),
        sample_comparison=SampleComparison(**sample_data),
        bilingual_feedback=BilingualFeedback(
            **bilingual_summary(
                total_score,
                prompt_fit_data["score"],
                feedback["weaknesses"],
            )
        ),
        template_coach=TemplateCoach(**template_data),
        score_highlights=[ScoreHighlight(**item) for item in highlight_data],
        weakness_dictionary=[WeaknessCard(**item) for item in weakness_data],
        personalization=PersonalizationAdvice(**personalization_data),
        paraphrase_recommendations=[ParaphraseSuggestion(**item) for item in paraphrase_data],
        checklist=checklist_obj,
        grammar_drills=drills_obj,
        grammar_corrections=grammar_corrections_obj,
        auto_rewrite_essay=auto_rewrite,
        revision_diff=revision_diff,
        grammar_impact=[
            GrammarImpactItem(
                issue=str(item.get("issue", "")),
                count=int(item.get("count", 0)),
                estimated_penalty_0_5=float(item.get("estimated_penalty_0_5", 0.0)),
            )
            for item in grammar_impact_data
        ],
        before_after_projection=BeforeAfterProjection(**projection_data),
        score_simulator=simulator_obj,
        smart_recommendations=[
            SmartRecommendation(
                title=str(item.get("title", "")),
                why=str(item.get("why", "")),
                how_to=str(item.get("how_to", "")),
                impact=str(item.get("impact", "")),
                confidence=cast(Literal["low", "medium", "high"], str(item.get("confidence", "medium"))),
            )
            for item in smart_recommendations_data
        ],
        top_priority_actions=[
            SmartRecommendation(
                title=str(item.get("title", "")),
                why=str(item.get("why", "")),
                how_to=str(item.get("how_to", "")),
                impact=str(item.get("impact", "")),
                confidence=cast(Literal["low", "medium", "high"], str(item.get("confidence", "medium"))),
            )
            for item in top_priority_data
        ],
        target_eta=TargetEta(**eta_data),
        sentence_variety=SentenceVariety(**sentence_variety_data),
        target_band_strategy=[TargetBandStrategyItem(**item) for item in target_strategy_data],
        repetition_training=[
            RepetitionTrainingItem(
                word=str(item.get("word", "")),
                count=int(item.get("count", 0)),
                alternatives=[str(x) for x in item.get("alternatives", [])],
            )
            for item in repetition_training_data
        ],
        examiner_feedback=ExaminerFeedback(**examiner_feedback_data),
        personal_weakness_ranking=weakness_ranking_data,
        weekly_plan=weekly_plan_data,
        strengths=feedback["strengths"],
        weaknesses=feedback["weaknesses"],
        action_plan=feedback["action_plan"],
        sentence_edits=feedback["sentence_edits"],
        upgraded_sample_paragraph=feedback["upgraded_sample_paragraph"],
    )

    record = {
        "estimated_score_0_5": result.estimated_score_0_5,
        "estimated_score_30": result.estimated_score_30,
        "score_band_1_6": result.score_band_1_6,
        "score_profile": result.score_profile.model_dump(),
        "ai_mode": result.ai_mode,
        "ai_provider": result.ai_provider,
        "grammar_cap_applied": result.grammar_cap_applied,
        "grammar_cap_reason": result.grammar_cap_reason,
        "confidence": result.confidence,
        "confidence_reason": result.confidence_reason,
        "prompt_fit_score": result.prompt_fit.score,
        "strengths": result.strengths,
        "weaknesses": result.weaknesses,
        "action_plan": result.action_plan,
        "sentence_edits": [edit.model_dump() for edit in result.sentence_edits],
        "target_rewrite": result.target_rewrite.model_dump(),
        "upgraded_sample_paragraph": result.upgraded_sample_paragraph,
        "grammar_stats": result.grammar_stats.model_dump(),
        "sample_comparison": result.sample_comparison.model_dump(),
        "dimensions": [d.model_dump() for d in result.dimensions],
        "personalization": result.personalization.model_dump(),
        "paraphrase_recommendations": [item.model_dump() for item in result.paraphrase_recommendations],
        "checklist": result.checklist.model_dump(),
        "grammar_drills": [item.model_dump() for item in result.grammar_drills],
        "grammar_corrections": [item.model_dump() for item in result.grammar_corrections],
        "auto_rewrite_essay": result.auto_rewrite_essay,
        "revision_diff": result.revision_diff,
        "grammar_impact": [item.model_dump() for item in result.grammar_impact],
        "before_after_projection": result.before_after_projection.model_dump(),
        "score_simulator": [item.model_dump() for item in result.score_simulator],
        "smart_recommendations": [item.model_dump() for item in result.smart_recommendations],
        "top_priority_actions": [item.model_dump() for item in result.top_priority_actions],
        "target_eta": result.target_eta.model_dump(),
        "sentence_variety": result.sentence_variety.model_dump(),
        "target_band_strategy": [item.model_dump() for item in result.target_band_strategy],
        "repetition_training": [item.model_dump() for item in result.repetition_training],
        "examiner_feedback": result.examiner_feedback.model_dump(),
        "personal_weakness_ranking": result.personal_weakness_ranking,
        "weekly_plan": result.weekly_plan,
        "weakness_dictionary": [card.model_dump() for card in result.weakness_dictionary],
    }

    submission_id, created_at = save_submission(
        prompt_type=prompt_type,
        prompt_text=payload.prompt_text,
        essay_text=payload.essay_text,
        evaluation_result=record,
    )

    return EvaluateResponse(
        submission_id=submission_id,
        created_at=created_at,
        result=result,
    )


@app.post("/api/precheck", response_model=RiskCheckResponse)
def precheck(payload: PrecheckRequest) -> RiskCheckResponse:
    prompt_type = cast(PromptType, payload.prompt_type or detect_prompt_type(payload.essay_text))
    risk = pre_submit_risk(
        prompt_type,
        payload.prompt_text,
        payload.essay_text,
    )
    checklist_data = build_pre_submit_checklist(
        prompt_type,
        payload.prompt_text,
        payload.essay_text,
    )
    risk["checklist"] = PreSubmitChecklist(
        total_score=int(checklist_data["total_score"]),
        items=[ChecklistItem(**item) for item in checklist_data["items"]],
    )
    return RiskCheckResponse(**risk)


@app.get("/api/history", response_model=SubmissionHistoryResponse)
def history(limit: int = 20) -> SubmissionHistoryResponse:
    rows = list_recent(limit=max(1, min(limit, 100)))
    items = [SubmissionHistoryItem(**row) for row in rows]
    return SubmissionHistoryResponse(items=items)


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(limit: int = 200) -> DashboardResponse:
    rows = list_all_results(limit=max(1, min(limit, 1000)))
    payload = build_dashboard(rows)
    return DashboardResponse(
        attempt_count=payload["attempt_count"],
        avg_score_0_5=payload["avg_score_0_5"],
        avg_prompt_fit=payload["avg_prompt_fit"],
        score_trend=[ScoreTrendPoint(**item) for item in payload["score_trend"]],
        top_grammar_issues=[
            GrammarIssueItem(**item) for item in payload["top_grammar_issues"]
        ],
        grammar_error_trend=[
            GrammarTrendPoint(**item) for item in payload["grammar_error_trend"]
        ],
        recommended_focus=payload["recommended_focus"],
    )


@app.get("/api/report/{submission_id}.pdf")
def download_report(submission_id: int) -> FileResponse:
    record = get_submission(submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    result = record["result"]
    report_dir = BASE_DIR / "data" / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"submission_{submission_id}.pdf"

    class BrandedPDF(FPDF):
        def footer(self) -> None:
            self.set_y(-11)
            self.set_draw_color(214, 223, 233)
            self.line(self.l_margin, self.get_y(), self.w - self.r_margin, self.get_y())

            self.set_font("Helvetica", "I", 7)
            self.set_text_color(93, 109, 126)
            self.set_xy(self.l_margin, self.get_y() + 1.4)
            self.cell(0, 3.6, "LKM TOEFL LAB", align="L")
            self.set_xy(self.l_margin, self.get_y())
            self.cell(0, 3.6, f"Page {self.page_no()}/{{nb}}", align="R")
            self.set_text_color(0, 0, 0)

    pdf = BrandedPDF()
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=14)

    unicode_font_enabled = False
    report_font_name = "Helvetica"
    unicode_candidates = [
        Path("/System/Library/Fonts/Supplemental/Arial Unicode.ttf"),
        Path("/System/Library/Fonts/AppleSDGothicNeo.ttc"),
        Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
    ]
    for unicode_font_path in unicode_candidates:
        if not unicode_font_path.exists():
            continue
        try:
            pdf.add_font("ReportUnicode", fname=str(unicode_font_path))
            report_font_name = "ReportUnicode"
            unicode_font_enabled = True
            break
        except Exception:
            continue

    def set_report_font(style: Literal["", "B", "I", "U"] = "", size: int = 12) -> None:
        if unicode_font_enabled:
            pdf.set_font(report_font_name, size=size)
            return
        pdf.set_font("Helvetica", style=style, size=size)

    pdf.add_page()
    set_report_font(size=12)

    def safe(text: str) -> str:
        if unicode_font_enabled:
            return text
        return text.encode("ascii", errors="ignore").decode("ascii")

    def chart_title(text: str) -> None:
        set_report_font("B", 12)
        pdf.cell(0, 8, safe(text), new_x="LMARGIN", new_y="NEXT")
        set_report_font(size=11)

    def draw_cover_header(submission_id: int, created_at: str, score_text: str) -> None:
        left = pdf.l_margin
        width = pdf.w - pdf.l_margin - pdf.r_margin

        # Header band
        y = pdf.get_y()
        pdf.set_fill_color(18, 86, 136)
        pdf.rect(left, y, width, 18, "F")
        pdf.set_text_color(255, 255, 255)
        pdf.set_xy(left + 4, y + 4.2)
        set_report_font("B", 16)
        pdf.cell(0, 6, "TOEFL Writing Assessment Report")

        set_report_font(size=10)
        pdf.set_xy(left + 4, y + 11.2)
        pdf.cell(0, 5, safe(f"Submission #{submission_id}  |  {created_at}  |  For Educational Use"))

        # Brand chip
        chip_w = 42
        chip_h = 6
        chip_x = left + width - chip_w - 3
        chip_y = y + 2.3
        pdf.set_fill_color(10, 63, 106)
        pdf.rect(chip_x, chip_y, chip_w, chip_h, "F")
        set_report_font("B", 7)
        pdf.set_text_color(235, 243, 251)
        pdf.set_xy(chip_x + 1.7, chip_y + 1.5)
        pdf.cell(chip_w - 3.4, 3, "LKM TOEFL LAB", align="C")

        # Score spotlight card
        card_y = y + 22
        card_h = 18
        pdf.set_fill_color(234, 245, 253)
        pdf.set_draw_color(18, 86, 136)
        pdf.rect(left, card_y, width, card_h, "DF")
        pdf.set_text_color(18, 86, 136)
        set_report_font("B", 11)
        pdf.set_xy(left + 4, card_y + 4)
        pdf.cell(0, 5, "Estimated TOEFL Writing Band (1-6)")
        set_report_font("B", 22)
        pdf.set_xy(left + 4, card_y + 8.2)
        pdf.cell(0, 8, score_text)

        pdf.set_text_color(0, 0, 0)
        pdf.set_y(card_y + card_h + 5)

    def draw_cover_kpis(confidence: str, eta_attempts: str, eta_pace: str) -> None:
        left = pdf.l_margin
        total_w = pdf.w - pdf.l_margin - pdf.r_margin
        gap = 3.0
        box_w = (total_w - gap * 2) / 3.0
        y = pdf.get_y()

        kpis = [
            ("CONFIDENCE", confidence),
            ("TARGET ETA", eta_attempts),
            ("PACE", eta_pace),
        ]

        for idx, (label, value) in enumerate(kpis):
            x = left + idx * (box_w + gap)
            pdf.set_fill_color(246, 248, 251)
            pdf.set_draw_color(208, 216, 226)
            pdf.rect(x, y, box_w, 14, "DF")
            set_report_font("B", 8)
            pdf.set_text_color(86, 101, 115)
            pdf.set_xy(x + 2.5, y + 2.2)
            pdf.cell(box_w - 5, 3.6, label)
            set_report_font("B", 12)
            pdf.set_text_color(32, 42, 52)
            pdf.set_xy(x + 2.5, y + 6.6)
            pdf.cell(box_w - 5, 5.2, safe(value))

        pdf.set_text_color(0, 0, 0)
        pdf.set_y(y + 16.5)

    def draw_dimension_chart(dimensions: list[dict]) -> None:
        if not dimensions:
            return
        chart_title("Dimension Scores")
        left = pdf.l_margin
        total_w = pdf.w - pdf.l_margin - pdf.r_margin
        label_w = 45
        value_w = 20
        bar_w = max(40.0, total_w - label_w - value_w - 8)
        y = pdf.get_y() + 1

        pdf.set_draw_color(210, 215, 225)
        pdf.line(left, y - 1, left + total_w, y - 1)

        for dim in dimensions[:6]:
            score = float(dim.get("score", 0.0))
            # Internal dimension score is 0-5; display as user-facing 1-6 band.
            display_score = max(1.0, min(6.0, score + 1.0))
            pdf.set_xy(left, y)
            pdf.cell(label_w, 6, safe(str(dim.get("name", ""))))

            track_x = left + label_w + 2
            pdf.set_fill_color(227, 232, 240)
            pdf.rect(track_x, y + 1.2, bar_w, 3.8, "F")

            fill_w = bar_w * max(0.0, min(5.0, score)) / 5.0
            pdf.set_fill_color(0, 131, 143)
            pdf.rect(track_x, y + 1.2, fill_w, 3.8, "F")

            pdf.set_xy(track_x + bar_w + 3, y)
            pdf.cell(value_w, 6, f"{display_score:.1f}/6")
            y += 7

        pdf.set_y(y + 2)

    def draw_grammar_chart(stats: dict) -> None:
        keys = ["tense", "article", "preposition", "run_on", "subject_verb", "punctuation"]
        rows = [(k, int(stats.get(k, 0))) for k in keys]
        max_val = max([v for _, v in rows] + [1])
        chart_title("Grammar Issue Distribution")
        left = pdf.l_margin
        total_w = pdf.w - pdf.l_margin - pdf.r_margin
        label_w = 45
        value_w = 16
        bar_w = max(40.0, total_w - label_w - value_w - 8)
        y = pdf.get_y() + 1

        legend_x = left + total_w - 72
        pdf.set_xy(legend_x, y - 8)
        pdf.set_fill_color(217, 95, 2)
        pdf.rect(legend_x, y - 5.6, 5, 3.8, "F")
        pdf.set_xy(legend_x + 7, y - 7)
        pdf.cell(30, 6, "error count")

        # Risk zones (green: 0-1, amber: 2-3, red: 4+)
        pdf.set_fill_color(220, 252, 231)
        pdf.rect(left + label_w + 2, y - 4, bar_w * (1 / max_val), 2.4, "F")
        pdf.set_fill_color(254, 243, 199)
        pdf.rect(left + label_w + 2 + bar_w * (1 / max_val), y - 4, bar_w * (2 / max_val), 2.4, "F")
        pdf.set_fill_color(254, 226, 226)
        red_start = left + label_w + 2 + bar_w * (3 / max_val)
        pdf.rect(red_start, y - 4, (left + label_w + 2 + bar_w) - red_start, 2.4, "F")
        pdf.set_xy(left + label_w + 2, y - 8)
        pdf.cell(bar_w, 3, "risk zone: low / medium / high")

        # axis labels
        set_report_font(size=8)
        for tick in [0, max(1, max_val // 2), max_val]:
            tx = left + label_w + 2 + (bar_w * tick / max_val)
            pdf.set_xy(tx - 3, y - 2)
            pdf.cell(8, 4, str(tick))
        pdf.set_xy(left + label_w + 2 + bar_w + 4, y - 2)
        pdf.cell(10, 4, "count")
        set_report_font(size=11)

        for label, value in rows:
            pdf.set_xy(left, y)
            pdf.cell(label_w, 6, safe(label))

            track_x = left + label_w + 2
            pdf.set_fill_color(241, 245, 249)
            pdf.rect(track_x, y + 1.2, bar_w, 3.8, "F")

            fill_w = bar_w * (value / max_val)
            pdf.set_fill_color(217, 95, 2)
            pdf.rect(track_x, y + 1.2, fill_w, 3.8, "F")

            pdf.set_xy(track_x + bar_w + 3, y)
            pdf.cell(value_w, 6, str(value))
            y += 7

        pdf.set_y(y + 3)

    def draw_recent_trend_chart(submission_id: int) -> None:
        rows = list_recent(limit=8)
        if len(rows) < 2:
            return
        points = [float(r.get("estimated_score_0_5", 0)) + 1.0 for r in rows]
        chart_title("Recent Score Trend")

        left = pdf.l_margin
        top = pdf.get_y() + 2
        width = pdf.w - pdf.l_margin - pdf.r_margin
        height = 26
        pdf.set_draw_color(205, 212, 224)
        pdf.rect(left, top, width, height)

        # Score risk zones based on 1-6 band: low(<4), medium(4-5), high(>=5)
        zone_low_y = top + height - ((4.0 - 1.0) / 5.0) * height
        zone_mid_y = top + height - ((5.0 - 1.0) / 5.0) * height
        pdf.set_fill_color(254, 226, 226)
        pdf.rect(left, zone_low_y, width, top + height - zone_low_y, "F")
        pdf.set_fill_color(254, 243, 199)
        pdf.rect(left, zone_mid_y, width, zone_low_y - zone_mid_y, "F")
        pdf.set_fill_color(220, 252, 231)
        pdf.rect(left, top, width, zone_mid_y - top, "F")

        # legend for risk zones
        lx = left + width - 54
        ly = top + 2
        set_report_font(size=8)
        pdf.set_fill_color(220, 252, 231)
        pdf.rect(lx, ly, 3.8, 2.5, "F")
        pdf.set_xy(lx + 5, ly - 1)
        pdf.cell(14, 4, "high")
        pdf.set_fill_color(254, 243, 199)
        pdf.rect(lx + 18, ly, 3.8, 2.5, "F")
        pdf.set_xy(lx + 23, ly - 1)
        pdf.cell(16, 4, "mid")
        pdf.set_fill_color(254, 226, 226)
        pdf.rect(lx + 33, ly, 3.8, 2.5, "F")
        pdf.set_xy(lx + 38, ly - 1)
        pdf.cell(14, 4, "low")

        # y-axis labels (1 to 6)
        set_report_font(size=8)
        for tick in [1, 3, 5, 6]:
            ty = top + height - ((tick - 1) / 5.0) * height
            pdf.set_draw_color(232, 236, 243)
            pdf.line(left, ty, left + width, ty)
            pdf.set_xy(left - 8, ty - 2)
            pdf.cell(7, 4, str(tick))
        set_report_font(size=11)

        min_v = min(points)
        max_v = max(points)
        span = max(0.5, max_v - min_v)
        xs = [left + (width * i / max(1, len(points) - 1)) for i in range(len(points))]
        ys = [top + height - (((p - min_v) / span) * (height - 3)) - 1.5 for p in points]

        pdf.set_draw_color(0, 122, 128)
        for i in range(1, len(points)):
            pdf.line(xs[i - 1], ys[i - 1], xs[i], ys[i])
        pdf.set_fill_color(0, 122, 128)
        for i in range(len(points)):
            pdf.ellipse(xs[i] - 0.9, ys[i] - 0.9, 1.8, 1.8, "F")

        pdf.set_xy(left, top + height + 1)
        pdf.cell(width, 6, f"Latest submission: #{submission_id} | trend window: {len(points)}")
        pdf.set_xy(left, top + height + 5)
        set_report_font(size=8)
        pdf.cell(width, 4, "x-axis: attempt order (old -> recent), y-axis: band(1-6)")
        set_report_font(size=11)
        pdf.set_y(top + height + 8)

    lines = [
        "TOEFL Writing Assessment Report",
        f"Submission ID: {submission_id}",
        f"Created At: {record['created_at']}",
        f"Prompt Type: {record['prompt_type']}",
        f"Analysis Mode: {result.get('ai_mode', 'local')}",
        "",
        f"TOEFL SCORE (MAX 6.0): {result.get('score_band_1_6', 'n/a')}",
        f"Confidence: {result.get('confidence', 'n/a')}",
        safe(str(result.get('confidence_reason', ''))),
        "",
        "Task Response Fit",
        f"Score: {_to_band_1_6(float(result.get('prompt_fit_score', 0.0))):.1f}/6.0",
        "",
        "Dimensions",
    ]

    for dim in result.get("dimensions", []):
        line = f"- {dim.get('name', '')}: {_to_band_1_6(float(dim.get('score', 0.0))):.1f}/6.0"
        lines.append(safe(line))

    profile = result.get("score_profile", {})
    lines.extend([
        "",
        "TOEFL Band Profile Ranges",
        safe(f"Reading: {profile.get('reading', 'n/a')}"),
        safe(f"Listening: {profile.get('listening', 'n/a')}"),
        safe(f"Speaking: {profile.get('speaking', 'n/a')}"),
        safe(f"Writing: {profile.get('writing', 'n/a')}"),
        safe(f"Total: {profile.get('total', 'n/a')}"),
    ])

    lines.extend([
        "",
        "Essay Preview",
        safe(record["essay_text"])[:1400],
    ])

    strengths = result.get("strengths", [])
    weaknesses = result.get("weaknesses", [])
    action_plan = result.get("action_plan", [])
    sentence_edits = result.get("sentence_edits", [])
    target_rewrite = result.get("target_rewrite", {})
    upgraded_sample = result.get("upgraded_sample_paragraph", "")
    paraphrases = result.get("paraphrase_recommendations", [])
    checklist = result.get("checklist", {})
    drills = result.get("grammar_drills", [])
    grammar_corrections = result.get("grammar_corrections", [])
    simulator = result.get("score_simulator", [])
    smart_recommendations = result.get("smart_recommendations", [])
    top_priority_actions = result.get("top_priority_actions", [])
    target_eta = result.get("target_eta", {})
    sentence_variety = result.get("sentence_variety", {})
    revision_diff = result.get("revision_diff", [])
    auto_rewrite_essay = result.get("auto_rewrite_essay", "")
    grammar_impact = result.get("grammar_impact", [])
    before_after_projection = result.get("before_after_projection", {})
    target_band_strategy = result.get("target_band_strategy", [])
    repetition_training = result.get("repetition_training", [])
    examiner_feedback = result.get("examiner_feedback", {})
    weakness_ranking = result.get("personal_weakness_ranking", [])
    weekly_plan = result.get("weekly_plan", [])
    bilingual_feedback = result.get("bilingual_feedback", {})

    # Cover page (executive summary)
    score_text = str(result.get("score_band_1_6", "n/a"))
    draw_cover_header(submission_id, str(record["created_at"]), score_text)
    draw_cover_kpis(
        str(result.get("confidence", "n/a")),
        f"{target_eta.get('estimated_attempts', 'n/a')} attempts",
        str(target_eta.get("pace_label", "n/a")),
    )

    if target_eta.get("message"):
        pdf.set_fill_color(253, 248, 232)
        pdf.set_draw_color(234, 198, 113)
        info_y = pdf.get_y()
        info_h = 10
        pdf.rect(pdf.l_margin, info_y, pdf.w - pdf.l_margin - pdf.r_margin, info_h, "DF")
        pdf.set_xy(pdf.l_margin + 3, info_y + 2.4)
        set_report_font(size=10)
        pdf.cell(0, 5, safe(str(target_eta.get("message", ""))))
        pdf.set_y(info_y + info_h + 4)

    summary_y = pdf.get_y()
    summary_h = 24
    pdf.set_fill_color(246, 249, 253)
    pdf.set_draw_color(194, 208, 224)
    pdf.rect(pdf.l_margin, summary_y, pdf.w - pdf.l_margin - pdf.r_margin, summary_h, "DF")
    pdf.set_xy(pdf.l_margin + 3, summary_y + 2)
    set_report_font("B", 11)
    pdf.cell(0, 4, "EXECUTIVE SUMMARY")
    pdf.set_xy(pdf.l_margin + 3, summary_y + 7)
    set_report_font(size=10)
    summary_text = str(bilingual_feedback.get("summary_en", "")).strip()
    if not summary_text:
        summary_text = "Thank you for your submission. This report provides a respectful, detailed review of your current writing level and practical next steps for improvement."
    pdf.multi_cell(0, 4.8, safe(summary_text))
    pdf.set_y(summary_y + summary_h + 4)

    pdf.set_fill_color(239, 244, 250)
    pdf.set_draw_color(205, 214, 226)
    sec_y = pdf.get_y()
    sec_h = 8
    pdf.rect(pdf.l_margin, sec_y, pdf.w - pdf.l_margin - pdf.r_margin, sec_h, "DF")
    pdf.set_xy(pdf.l_margin + 3, sec_y + 2)
    set_report_font("B", 11)
    pdf.cell(0, 4, "RECOMMENDED PRIORITY ACTIONS")
    pdf.set_y(sec_y + sec_h + 3)

    set_report_font(size=11)
    for item in top_priority_actions[:3]:
        block_y = pdf.get_y()
        block_h = 12
        pdf.set_fill_color(250, 252, 255)
        pdf.set_draw_color(220, 228, 238)
        pdf.rect(pdf.l_margin, block_y, pdf.w - pdf.l_margin - pdf.r_margin, block_h, "DF")
        pdf.set_xy(pdf.l_margin + 3, block_y + 2)
        set_report_font("B", 10)
        pdf.cell(0, 4, safe(str(item.get("title", ""))))
        pdf.set_xy(pdf.l_margin + 3, block_y + 6.2)
        set_report_font(size=9)
        pdf.cell(0, 4, safe(f"Impact {item.get('impact', '')}  |  Confidence {item.get('confidence', 'medium')}"))
        pdf.set_y(block_y + block_h + 2)

    pdf.set_fill_color(239, 244, 250)
    pdf.set_draw_color(205, 214, 226)
    sec2_y = pdf.get_y()
    pdf.rect(pdf.l_margin, sec2_y, pdf.w - pdf.l_margin - pdf.r_margin, sec_h, "DF")
    pdf.set_xy(pdf.l_margin + 3, sec2_y + 2)
    set_report_font("B", 11)
    pdf.cell(0, 4, "SENTENCE VARIETY OVERVIEW")
    pdf.set_y(sec2_y + sec_h + 3)

    set_report_font(size=11)
    pdf.cell(0, 7, safe(f"Short: {sentence_variety.get('short_ratio', 0)} | Medium: {sentence_variety.get('medium_ratio', 0)} | Long: {sentence_variety.get('long_ratio', 0)}"), new_x="LMARGIN", new_y="NEXT")
    pdf.multi_cell(0, 6, safe(str(sentence_variety.get("recommendation", ""))))

    pdf.add_page()
    set_report_font(size=12)

    draw_dimension_chart(result.get("dimensions", []))
    draw_grammar_chart(result.get("grammar_stats", {}))
    draw_recent_trend_chart(submission_id)

    # Page 1 ends with compact visual summary.
    lines.extend(["", "Quick Visual Summary"])
    lines.append(safe(f"Top Weakness Ranking: {', '.join(weakness_ranking[:3]) if weakness_ranking else 'n/a'}"))
    if before_after_projection:
        lines.append(
            safe(
                "Before/After Projection: "
                f"{before_after_projection.get('current_band_1_6', 'n/a')}/6.0 -> "
                f"{before_after_projection.get('projected_band_1_6', 'n/a')}/6.0 "
                f"(gain {before_after_projection.get('expected_gain_0_5', 0)})"
            )
        )
    if target_eta:
        lines.append(
            safe(
                f"Target ETA: {target_eta.get('estimated_attempts', 'n/a')} attempts | {target_eta.get('pace_label', 'n/a')}"
            )
        )

    lines.extend(["", "Strengths"])
    for item in strengths[:5]:
        lines.append(safe(f"- {item}"))

    lines.extend(["", "Weaknesses"])
    for item in weaknesses[:5]:
        lines.append(safe(f"- {item}"))

    lines.extend(["", "Action Plan"])
    for idx, item in enumerate(action_plan[:5], start=1):
        lines.append(safe(f"{idx}. {item}"))

    lines.extend(["", "Sentence Edits"])
    for item in sentence_edits[:5]:
        original = safe(str(item.get("original", "")))
        improved = safe(str(item.get("improved", "")))
        note = safe(str(item.get("note", "")))
        lines.append(f"- Original: {original}")
        lines.append(f"  Improved: {improved}")
        lines.append(f"  Note: {note}")

    lines.extend(["", "Revision Diff (before -> after)"])
    for d in revision_diff[:20]:
        lines.append(safe(d))
    if auto_rewrite_essay:
        lines.extend(["", "Auto Rewrite Essay"])
        lines.append(safe(auto_rewrite_essay)[:1200])

    lines.extend([
        "",
        "Target Rewrite (High-score Variants)",
        safe(f"Minimal: {target_rewrite.get('minimal', '')}"),
        safe(f"Aggressive: {target_rewrite.get('aggressive', '')}"),
    ])

    lines.extend([
        "",
        "Upgraded Sample Paragraph",
        safe(str(upgraded_sample)),
    ])

    lines.extend(["", "High-score Paraphrasing Suggestions"])
    for item in paraphrases[:8]:
        lines.append(safe(f"- {item.get('original', '')} -> {item.get('improved', '')}"))
        lines.append(safe(f"  Why: {item.get('reason', '')}"))

    lines.extend(["", "Pre-submit Checklist"])
    lines.append(safe(f"Total: {checklist.get('total_score', 'n/a')} / 100"))
    for item in checklist.get("items", [])[:6]:
        lines.append(safe(f"- {item.get('label', '')}: {item.get('score', '')} ({item.get('status', '')})"))

    lines.extend(["", "Grammar Drills"])
    for item in drills[:6]:
        lines.append(safe(f"- [{item.get('issue', '')}] {item.get('wrong', '')} -> {item.get('correct', '')}"))
        lines.append(safe(f"  Tip: {item.get('tip', '')}"))

    lines.extend(["", "Detailed Grammar Corrections"])
    for item in grammar_corrections[:10]:
        lines.append(
            safe(
                f"- [{item.get('severity', 'medium')}] {item.get('error_type', '')}: {item.get('sentence', '')}"
            )
        )
        lines.append(safe(f"  Fix: {item.get('corrected', '')}"))
        lines.append(safe(f"  Why: {item.get('explanation', '')}"))

    lines.extend(["", "Grammar Penalty Impact"])
    for item in grammar_impact[:6]:
        lines.append(
            safe(
                f"- {item.get('issue', '')}: count {item.get('count', 0)}, est penalty {item.get('estimated_penalty_0_5', 0)}"
            )
        )

    lines.extend(["", "Score Simulator"])
    for item in simulator[:4]:
        lines.append(
            safe(
                f"- {item.get('action', '')}: +{item.get('expected_delta_0_5', 0)} (projected band {item.get('projected_band_1_6', 'n/a')})"
            )
        )

    lines.extend(["", "Smart Recommendations"])
    for item in smart_recommendations[:8]:
        lines.append(safe(f"- {item.get('title', '')} ({item.get('impact', '')}, {item.get('confidence', 'medium')})"))
        lines.append(safe(f"  Why: {item.get('why', '')}"))
        lines.append(safe(f"  How: {item.get('how_to', '')}"))

    lines.extend(["", "Target Band Strategy"])
    for item in target_band_strategy[:6]:
        lines.append(safe(f"- {item.get('title', '')}"))
        lines.append(safe(f"  {item.get('detail', '')}"))

    lines.extend(["", "Repetition Training"])
    for item in repetition_training[:6]:
        lines.append(
            safe(
                f"- {item.get('word', '')} ({item.get('count', 0)}x) -> {', '.join(item.get('alternatives', []))}"
            )
        )

    lines.extend(["", "Examiner Mode Comments"])
    for line in examiner_feedback.get("comments", [])[:5]:
        lines.append(safe(f"- {line}"))

    lines.extend(["", "Weekly Plan"])
    for day in weekly_plan[:7]:
        lines.append(safe(f"- {day}"))

    lines.extend([
        "",
        "Closing Note",
        "Thank you for your effort. Please use this report as a structured guide, and revise step by step with patience and consistency.",
    ])

    section_titles = {
        "Quick Visual Summary",
        "Strengths",
        "Weaknesses",
        "Action Plan",
        "Sentence Edits",
        "Revision Diff (before -> after)",
        "Auto Rewrite Essay",
        "Target Rewrite (High-score Variants)",
        "Upgraded Sample Paragraph",
        "High-score Paraphrasing Suggestions",
        "Pre-submit Checklist",
        "Grammar Drills",
        "Detailed Grammar Corrections",
        "Grammar Penalty Impact",
        "Score Simulator",
        "Smart Recommendations",
        "Target Band Strategy",
        "Repetition Training",
        "Examiner Mode Comments",
        "Weekly Plan",
        "Closing Note",
    }

    def ensure_space(height: float) -> None:
        if pdf.get_y() + height > pdf.h - 18:
            pdf.add_page()
            # subtle page header for branded continuity
            header_y = pdf.get_y()
            pdf.set_fill_color(242, 246, 252)
            pdf.set_draw_color(208, 216, 226)
            pdf.rect(pdf.l_margin, header_y, pdf.w - pdf.l_margin - pdf.r_margin, 7, "DF")
            pdf.set_xy(pdf.l_margin + 2.5, header_y + 1.8)
            set_report_font("B", 9)
            pdf.set_text_color(66, 83, 99)
            pdf.cell(0, 4, "TOEFL WRITING COACHING REPORT")
            pdf.set_xy(pdf.w - pdf.r_margin - 40, header_y + 1.8)
            set_report_font("B", 8)
            pdf.set_text_color(80, 98, 117)
            pdf.cell(40, 4, "LKM TOEFL LAB", align="R")
            pdf.set_text_color(0, 0, 0)
            pdf.set_y(header_y + 9.5)

    def draw_section_bar(title: str) -> None:
        ensure_space(10)
        y = pdf.get_y()
        pdf.set_fill_color(231, 240, 249)
        pdf.set_draw_color(176, 197, 220)
        pdf.rect(pdf.l_margin, y, pdf.w - pdf.l_margin - pdf.r_margin, 7.4, "DF")
        pdf.set_xy(pdf.l_margin + 2.8, y + 1.8)
        set_report_font("B", 10)
        pdf.set_text_color(35, 74, 112)
        pdf.cell(0, 4, safe(title.upper()))
        pdf.set_text_color(0, 0, 0)
        pdf.set_y(y + 9)

    def draw_bullet_card(text: str) -> None:
        wrapped = textwrap.wrap(text, width=88, break_long_words=True)
        h = max(6.0, 3.8 * len(wrapped) + 2.2)
        ensure_space(h + 1.5)
        y = pdf.get_y()
        pdf.set_fill_color(249, 251, 254)
        pdf.set_draw_color(224, 232, 241)
        pdf.rect(pdf.l_margin, y, pdf.w - pdf.l_margin - pdf.r_margin, h, "DF")

        # left accent line
        pdf.set_fill_color(56, 115, 171)
        pdf.rect(pdf.l_margin, y, 1.6, h, "F")

        pdf.set_xy(pdf.l_margin + 3.2, y + 1.5)
        set_report_font(size=9)
        for idx, chunk in enumerate(wrapped):
            prefix = "• " if idx == 0 else "  "
            pdf.cell(0, 3.6, safe(prefix + chunk), new_x="LMARGIN", new_y="NEXT")
            pdf.set_x(pdf.l_margin + 3.2)
        pdf.set_y(y + h + 1.2)

    for idx, line in enumerate(lines):
        if idx == 0:
            continue

        if line == "Strengths":
            pdf.add_page()
            set_report_font(size=12)

        if not line:
            ensure_space(3.5)
            pdf.cell(0, 3.5, " ", new_x="LMARGIN", new_y="NEXT")
            continue

        if line in section_titles:
            draw_section_bar(line)
            continue

        if line.startswith("- "):
            draw_bullet_card(line[2:])
            continue

        wrapped = textwrap.wrap(line, width=95, break_long_words=True)
        ensure_space(max(6.0, 4.3 * len(wrapped)))
        set_report_font(size=10)
        for chunk in wrapped:
            pdf.cell(0, 4.6, safe(chunk), new_x="LMARGIN", new_y="NEXT")

    pdf.output(str(report_path))
    return FileResponse(
        report_path,
        media_type="application/pdf",
        filename=f"submission_{submission_id}.pdf",
    )


# ── Vocabulary Analysis ─────────────────────────────────────────────────────

@app.post("/api/vocab-analysis", response_model=VocabAnalysisResponse)
def vocab_analysis(payload: VocabAnalysisRequest) -> VocabAnalysisResponse:
    result = analyze_vocabulary(payload.essay_text)
    return VocabAnalysisResponse(**result)


# ── Weekly Report ───────────────────────────────────────────────────────────

@app.get("/api/weekly-report", response_model=WeeklyReportResponse)
def weekly_report() -> WeeklyReportResponse:
    from collections import defaultdict
    from datetime import timedelta

    rows = list_all_results(limit=500)
    cutoff = (datetime.now(UTC) - timedelta(days=7)).isoformat()

    week_rows = [r for r in rows if str(r.get("created_at", "")) >= cutoff]

    if not week_rows:
        return WeeklyReportResponse(
            week_attempts=0,
            week_avg_score=0.0,
            week_best_score=0.0,
            week_worst_score=0.0,
            most_common_error="n/a",
            recommendation="이번 주 제출 기록이 없습니다. 꾸준히 연습하세요!",
            daily_submissions=[],
        )

    scores = [float(r.get("score_band_1_6", 1.0)) for r in week_rows]

    error_counts: dict[str, int] = {}
    for r in week_rows:
        gs = r.get("grammar_stats", {})
        for k in ["tense", "article", "preposition", "run_on", "subject_verb", "punctuation"]:
            error_counts[k] = error_counts.get(k, 0) + int(gs.get(k, 0))
    most_common = max(error_counts, key=lambda k: error_counts[k]) if error_counts else "n/a"

    daily: dict[str, list[float]] = defaultdict(list)
    for r in week_rows:
        created = str(r.get("created_at", ""))
        day = created[:10] if len(created) >= 10 else "unknown"
        daily[day].append(float(r.get("score_band_1_6", 1.0)))

    daily_list = [
        DailySubmissionCount(day=day, count=len(v), avg_score=round(sum(v) / len(v), 2))
        for day, v in sorted(daily.items())
    ]

    avg_s = round(sum(scores) / len(scores), 2)
    best_s = round(max(scores), 2)
    worst_s = round(min(scores), 2)

    if avg_s >= 5.0:
        rec = f"이번 주 평균 {avg_s}점으로 훌륭합니다! 꾸준히 유지하면 6.0 달성이 가능합니다."
    elif avg_s >= 4.0:
        rec = f"평균 {avg_s}점입니다. {most_common} 오류를 집중 교정하면 5.5~6.0 구간 진입이 가능합니다."
    else:
        rec = f"평균 {avg_s}점입니다. {most_common} 교정을 우선 연습하고 매일 1회 이상 제출해보세요."

    return WeeklyReportResponse(
        week_attempts=len(week_rows),
        week_avg_score=avg_s,
        week_best_score=best_s,
        week_worst_score=worst_s,
        most_common_error=most_common,
        recommendation=rec,
        daily_submissions=daily_list,
    )


# ── Submission Compare ──────────────────────────────────────────────────────

@app.get("/api/compare/{id1}/{id2}", response_model=CompareResponse)
def compare_submissions(id1: int, id2: int) -> CompareResponse:
    r1 = get_submission(id1)
    r2 = get_submission(id2)
    if r1 is None:
        raise HTTPException(status_code=404, detail=f"Submission {id1} not found")
    if r2 is None:
        raise HTTPException(status_code=404, detail=f"Submission {id2} not found")

    res1 = r1["result"]
    res2 = r2["result"]

    s1 = float(res1.get("score_band_1_6", 1.0))
    s2 = float(res2.get("score_band_1_6", 1.0))
    g1 = int(res1.get("grammar_stats", {}).get("total", 0))
    g2 = int(res2.get("grammar_stats", {}).get("total", 0))

    improvements: list[str] = []
    if s2 > s1:
        improvements.append(f"점수 향상: {s1} → {s2} (+{round(s2 - s1, 1)}점)")
    elif s2 < s1:
        improvements.append(f"점수 하락: {s1} → {s2} ({round(s2 - s1, 1)}점)")
    else:
        improvements.append("점수 동일")
    if g2 < g1:
        improvements.append(f"문법 오류 감소: {g1} → {g2} ({g1 - g2}개 감소)")
    elif g2 > g1:
        improvements.append(f"문법 오류 증가: {g1} → {g2} (+{g2 - g1}개)")

    return CompareResponse(
        submission_1=CompareScoreInfo(
            submission_id=id1,
            created_at=str(r1["created_at"])[:19],
            score_band_1_6=s1,
            estimated_score_30=int(res1.get("estimated_score_30", 0)),
            grammar_total=g1,
            strengths=res1.get("strengths", [])[:3],
            weaknesses=res1.get("weaknesses", [])[:3],
        ),
        submission_2=CompareScoreInfo(
            submission_id=id2,
            created_at=str(r2["created_at"])[:19],
            score_band_1_6=s2,
            estimated_score_30=int(res2.get("estimated_score_30", 0)),
            grammar_total=g2,
            strengths=res2.get("strengths", [])[:3],
            weaknesses=res2.get("weaknesses", [])[:3],
        ),
        score_delta=round(s2 - s1, 2),
        grammar_delta=g2 - g1,
        improvement_areas=improvements,
    )
