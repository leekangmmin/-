
from __future__ import annotations

# Python 3.11 이상만 지원
import sys
if sys.version_info < (3, 11):
    print("\n[ERROR] Python 3.11 이상이 필요합니다.\nhttps://www.python.org/downloads/ 에서 최신 버전을 설치하세요.\n")
    sys.exit(1)

import os
import sys
from datetime import datetime, timezone, tzinfo, timedelta
# Python 3.11 이상: datetime.UTC, 이하: 수동 UTC tzinfo
try:
    from datetime import UTC  # type: ignore
except ImportError:
    class UTC(tzinfo):
        def utcoffset(self, dt): return timedelta(0)
        def tzname(self, dt): return "UTC"
        def dst(self, dt): return timedelta(0)
    UTC = UTC()
from pathlib import Path
from typing import Any, Literal, cast

from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

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
from app.build_a_sentence_engine import score_submission as score_bas_submission
from app.build_a_sentence_items import BUILD_A_SENTENCE_ITEMS, BUILD_SENTENCE_ITEMS_VERSION, get_item as get_bas_item
from app.db import get_submission, init_db, list_all_results, list_recent, save_bas_attempt, save_submission
from app.env_loader import load_local_env
from app.feedback import build_feedback
from app.paths import exports_dir, is_frozen, resource_path, user_data_dir
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
    ScoreTrendPoint,
    SubmissionHistoryItem,
    SubmissionHistoryResponse,
    TemplateCoach,
    HighScoreStructureGuide,
    WeaknessCard,
    VocabAnalysisRequest,
    VocabAnalysisResponse,
    WeeklyReportResponse,
    DailySubmissionCount,
    CompareResponse,
    CompareScoreInfo,
    AIConfigRequest,
    AIConfigResponse,
    BackupFileRequest,
    DeleteAllRequest,
    DraftSaveRequest,
    BuildASentenceItemDetail,
    BuildASentenceItemListResponse,
    BuildASentenceItemSummary,
    BuildASentenceSubmitRequest,
    BuildASentenceSubmitResponse,
)
from app.ai_mode import ai_enabled, ai_enhance, ai_runtime_config
from app.operational_grader import OperationalGradeOutcome, grade_operational_task
from app.toefl_2026_grader import TOEFL_2026_GRADER_PROMPT_VERSION, TaskGradeResult
from app.local_ai import get_local_ai_manager
from app.db import get_setting, set_setting
from app.models import EngineInfo
from app.scorer import analyze_essay, grammar_cap_status, score_essay_detailed
from app.high_score_patterns import structure_guide
from app.versions import (
    CALIBRATION_VERSION,
    EXAM_SPEC_VERSION,
    GRAMMAR_RULES_VERSION,
    RESULT_SCHEMA_VERSION,
    RUBRIC_VERSION,
    SCORING_ENGINE_VERSION,
    SCORING_MODEL,
    SCORING_MODEL_IDENTIFIER,
    SCORING_PROMPT_VERSION,
    SCORING_PROVIDER,
)
from app.vocab_analysis import analyze_vocabulary

app = FastAPI(title="TOEFL Writing Evaluator", version="1.0.0")

_LLM_DIMENSION_LABELS = {
    "purposeful_communication": "목적·필수 내용 충족",
    "social_conventions_tone": "상황에 맞는 어조·관습",
    "language_use": "문법·어휘·문장 다양성",
    "organization": "논리적 구성",
    "elaboration_relevance": "관련성·구체적 전개",
    "syntax_vocabulary": "구문·어휘",
    "discourse_conventions": "토론 참여·의견 연결",
    "language_accuracy": "언어 정확성",
}


def _llm_dimensions(grade: TaskGradeResult) -> list[dict[str, Any]]:
    return [
        {
            "name": _LLM_DIMENSION_LABELS.get(key, key),
            "score": float(value.score),
            "reason": value.comment,
        }
        for key, value in grade.dimensions.items()
    ]


def _ai_public_config() -> AIConfigResponse:
    runtime = ai_runtime_config()
    provider_raw = str(runtime.get("provider", "local")).strip().lower() or "local"
    provider = cast(Literal["local", "openai", "claude", "gemini"], provider_raw if provider_raw in {"local", "openai", "claude", "gemini"} else "local")
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

# 로컬 전용 앱 — 로컬 오리진만 허용한다.
# 데스크톱 런처(desktop/launcher.py)는 매 실행마다 동적 loopback 포트를 쓰므로
# 고정 포트를 기본 허용 목록에 넣지 않는다. 웹뷰는 서버와 같은 origin에서
# 페이지를 로드하므로 CORS 자체가 관여하지 않는다 — 이 목록은 브라우저 기반
# 개발/프리뷰(고정 포트 8000)에서 크로스 오리진 호출이 필요한 경우를 위한 것이다.
# TOEFL_EXTRA_ORIGINS 환경변수로 추가 오리진을 등록할 수 있다.
# (운영 배포 시에는 이 값을 설정하지 않는 것이 기본값이며 안전하다.)
_DEFAULT_ORIGINS = [
    "http://127.0.0.1:8000",
    "http://localhost:8000",
]
_extra_origins = [
    o.strip() for o in os.getenv("TOEFL_EXTRA_ORIGINS", "").split(",") if o.strip()
]
app.add_middleware(
    CORSMiddleware,
    allow_origins=_DEFAULT_ORIGINS + _extra_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    from app.data_migration import migrate_legacy_data_if_needed

    migrate_legacy_data_if_needed()
    init_db()


BASE_DIR = Path(__file__).resolve().parent.parent
STATIC_DIR = resource_path("static")
load_local_env(BASE_DIR)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")


@app.get("/")
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/api/health")
def health() -> dict[str, Any]:
    from app.shadow_config import load_shadow_config
    from app.version import APP_VERSION, DB_SCHEMA_VERSION

    return {
        "status": "ok",
        "time": datetime.now(UTC).isoformat(),
        "app_version": APP_VERSION,
        "db_schema_version": DB_SCHEMA_VERSION,
        "offline_core_available": True,
        # shadow 활성 여부만 노출한다 — API 키 존재 여부/모델명 같은 세부 정보는 노출하지 않는다.
        "shadow_enabled": load_shadow_config().enabled,
    }


@app.get("/api/capabilities")
def capabilities() -> dict[str, Any]:
    """Runtime feature flags for desktop, self-hosted web, and future hosted web."""
    raw_mode = os.getenv("TOEFL_APP_MODE", "").strip().lower()
    web_mode = raw_mode == "web" or os.getenv("TOEFL_WEB_MODE", "").strip() == "1"
    mode = "web" if web_mode else ("desktop" if is_frozen() else "desktop_or_web")
    runtime_ai = ai_runtime_config()
    provider = str(runtime_ai.get("provider", "local")).strip().lower()
    cloud_ai_enabled = bool(ai_enabled(runtime_ai) and provider in {"openai", "claude", "gemini"})

    return {
        "mode": mode,
        "offline_core": True,
        "api_key_required": False,
        "local_ai": not web_mode,
        "cloud_ai": cloud_ai_enabled,
        "backup_restore": not web_mode,
        "pdf": True,
        "build_a_sentence": True,
        "draft_autosave": True,
        "history": True,
        "pwa": False,
        "admin_api": False,
        "hosted_ai": False,
        "score_policy": "llm_when_enabled_with_heuristic_fallback",
    }


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
        return {"ok": False, "message": "AI 연결이 비활성화되어 있습니다."}

    provider = str(cfg.get("provider", "local")).strip().lower()
    if provider in {"openai", "claude", "gemini"}:
        sample = (
            "I agree with Mina that clear written instructions help employees. They create a record "
            "that people can review after a meeting, so important details are less likely to be lost. "
            "For example, a project checklist can show deadlines and responsibilities to every team member."
        )
        outcome = grade_operational_task(
            task_type="academic_discussion",
            essay_text=sample,
            prompt_text="Should employees communicate important workplace instructions in writing or by speaking?",
            cfg=cfg,
        )
        if outcome.grade is not None:
            return {"ok": True, "message": f"{provider} 2026 루브릭 채점 연결 테스트 성공"}
        return {"ok": False, "message": outcome.detail}

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
    # 입력 검증은 모든 분석 이전에 수행한다.
    if len(payload.essay_text.split()) < 60:
        raise HTTPException(
            status_code=400,
            detail="Essay is too short. Please write at least 60 words.",
        )

    prompt_type = cast(PromptType, payload.prompt_type or detect_prompt_type(payload.essay_text))
    # 양자화(0.5 단위 반올림) 경계 분석을 위해 상세 버전을 사용한다. 반환되는
    # 표시 점수(total_score) 자체는 score_essay()와 완전히 동일 — 공식은 그대로다.
    scoring_breakdown = score_essay_detailed(payload.essay_text, prompt_type)
    dimensions, total_score = scoring_breakdown.dimensions, scoring_breakdown.total_0_5
    prompt_fit_data = evaluate_prompt_fit(payload.prompt_text, payload.essay_text)
    prompt_fit_evaluated = bool(payload.prompt_text.strip())
    if not prompt_fit_evaluated:
        # 문제가 없는데 "낮은 적합성"으로 해석하지 않는다. 파생 추천은
        # 중립값으로 게이트하고, API/UI에는 evaluated=false를 명시한다.
        prompt_fit_data = {
            "score": 5.0,
            "evaluated": False,
            "reason_ko": "문제 지문이 입력되지 않아 주제 반영도를 측정하지 않았습니다.",
            "reason_en": "Task-response fit was not measured because the prompt was not supplied.",
            "matched_keywords": [],
            "missing_keywords": [],
        }
    runtime_ai = ai_runtime_config()
    operational_grade: OperationalGradeOutcome = grade_operational_task(
        task_type=prompt_type,
        essay_text=payload.essay_text,
        prompt_text=payload.prompt_text,
        cfg=runtime_ai,
    )
    llm_grade = operational_grade.grade

    if llm_grade is not None:
        # 운영 화면 점수의 단일 진실 공급원: 검증을 통과한 2026 루브릭 결과.
        total_score = float(llm_grade.overall_score)
        dimensions = _llm_dimensions(llm_grade)  # type: ignore[assignment]

    # prompt-fit 감점은 파생 계산(피드백/시뮬레이터/프로젝션) 이전에 적용해
    # 표시 점수와 모든 파생 수치가 같은 점수를 기준으로 하도록 한다. LLM 루브릭은
    # 과제 충족도를 자체 평가하므로 휴리스틱 감점을 다시 중복 적용하지 않는다.
    if llm_grade is None and payload.prompt_text.strip():
        if prompt_fit_data["score"] < 2.5:
            total_score = max(0.0, total_score - 1.0)
        elif prompt_fit_data["score"] < 3.0:
            total_score = max(0.0, total_score - 0.5)

    feedback = build_feedback(payload.essay_text, prompt_type, total_score)
    if llm_grade is not None:
        if llm_grade.strengths:
            feedback["strengths"] = llm_grade.strengths
        if llm_grade.priority_fixes:
            feedback["weaknesses"] = llm_grade.priority_fixes
            feedback["action_plan"] = llm_grade.priority_fixes
    claim_map_data = map_claim_evidence(payload.essay_text)
    grammar_stats_data = grammar_error_stats(payload.essay_text, prompt_type)
    target_score_0_5 = min(5.0, max(0.0, payload.target_score_0_5))
    rewrite_data = rewrite_for_target(payload.essay_text, total_score, target_score_0_5)
    sample_data = sample_compare(payload.essay_text, prompt_type)
    historical_rows = list_all_results(limit=200)
    template_data = template_coach(prompt_type)
    structure_guide_data = structure_guide(payload.essay_text, prompt_type)
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
    weakness_ranking_data = personal_weakness_ranking(historical_rows, limit=10)
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

    cap = grammar_cap_status(payload.essay_text, prompt_type)

    ai_mode = "local"
    ai_provider = "none"
    if llm_grade is not None:
        ai_mode = "ai"
        ai_provider = cast(
            Literal["none", "local", "openai", "claude", "gemini"],
            operational_grade.provider,
        )
    elif ai_enabled(runtime_ai) and str(runtime_ai.get("provider", "local")) == "local":
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
            ai_provider = cast(Literal["none", "local", "openai", "claude", "gemini"], str(runtime_ai.get("provider", "local")))
            paraphrase_data = ai_payload.get("paraphrase_recommendations", paraphrase_data) or paraphrase_data
            drills_data = ai_payload.get("grammar_drills", drills_data) or drills_data
            drills_obj = [GrammarDrill(**item) for item in drills_data]
            feedback["upgraded_sample_paragraph"] = ai_payload.get(
                "upgraded_sample_paragraph", feedback["upgraded_sample_paragraph"]
            )

    result = EvaluationResult(
        estimated_score_0_5=total_score,
        estimated_score_30=None,
        score_band_1_6=None,
        engine=EngineInfo(
            exam_spec_version=EXAM_SPEC_VERSION,
            rubric_version=RUBRIC_VERSION,
            scoring_engine_version=SCORING_ENGINE_VERSION,
            grammar_rules_version=GRAMMAR_RULES_VERSION,
            result_schema_version=RESULT_SCHEMA_VERSION,
            prompt_version=(TOEFL_2026_GRADER_PROMPT_VERSION if llm_grade is not None else SCORING_PROMPT_VERSION),
            provider=(operational_grade.provider if llm_grade is not None else SCORING_PROVIDER),
            model=(operational_grade.model if llm_grade is not None else SCORING_MODEL),
            model_identifier=(
                f"{operational_grade.provider}:{operational_grade.model}"
                if llm_grade is not None
                else SCORING_MODEL_IDENTIFIER
            ),
            calibration_version=CALIBRATION_VERSION,
        ),
        score_profile=None,
        score_source=operational_grade.source,
        score_source_detail=operational_grade.detail,
        llm_grade=llm_grade,
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
                prompt_fit_evaluated,
            )
        ),
        template_coach=TemplateCoach(**template_data),
        high_score_structure=HighScoreStructureGuide(**structure_guide_data),
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
        "engine": result.engine.model_dump() if result.engine else None,
        "score_source": result.score_source,
        "score_source_detail": result.score_source_detail,
        "llm_grade": result.llm_grade.model_dump() if result.llm_grade else None,
        # 점수공식 변경 금지 게이트용 진단 데이터 — 사용자에게 노출되지 않는 내부 저장.
        # 전문가 데이터 확보 후 반올림 경계 구간 오차 분석에 사용한다.
        "scoring_quantization": {
            "pre_round_raw_score": scoring_breakdown.pre_round_raw_score,
            "rounded_display_score": scoring_breakdown.total_0_5,
            "distance_to_rounding_boundary": scoring_breakdown.distance_to_rounding_boundary,
            "component_scores": scoring_breakdown.component_scores,
            "scoring_formula_version": scoring_breakdown.scoring_formula_version,
        },
        "score_profile": result.score_profile.model_dump() if result.score_profile else None,
        "ai_mode": result.ai_mode,
        "ai_provider": result.ai_provider,
        "grammar_cap_applied": result.grammar_cap_applied,
        "grammar_cap_reason": result.grammar_cap_reason,
        "confidence": result.confidence,
        "confidence_reason": result.confidence_reason,
        "prompt_fit_score": result.prompt_fit.score,
        "prompt_fit_evaluated": result.prompt_fit.evaluated,
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


@app.delete("/api/history/{submission_id}")
def delete_history_item(submission_id: int) -> dict[str, Any]:
    from app.db import delete_submission

    if not delete_submission(submission_id):
        raise HTTPException(status_code=404, detail="Submission not found")
    return {"deleted": submission_id}


# ── 온보딩 상태 (최초 실행 안내 — 사용자 config에 저장) ─────────────────────
@app.get("/api/onboarding")
def onboarding_status() -> dict[str, Any]:
    return {"done": get_setting("onboarding_done", "0") == "1"}


@app.post("/api/onboarding/complete")
def onboarding_complete() -> dict[str, Any]:
    set_setting("onboarding_done", "1")
    return {"done": True}


@app.post("/api/onboarding/reset")
def onboarding_reset() -> dict[str, Any]:
    set_setting("onboarding_done", "0")
    return {"done": False}


# ── 작성 중 답안 (draft) — 서버측 보존으로 강제 종료 후에도 복구 가능 ────────
@app.get("/api/draft")
def read_draft() -> dict[str, Any]:
    from app.db import get_draft

    draft = get_draft()
    return {"draft": draft}


@app.put("/api/draft")
def write_draft(payload: DraftSaveRequest) -> dict[str, Any]:
    from app.db import save_draft

    updated_at = save_draft(
        prompt_text=payload.prompt_text or "",
        essay_text=payload.essay_text or "",
        task_type=payload.task_type or "",
    )
    return {"saved": True, "updated_at": updated_at}


@app.delete("/api/draft")
def remove_draft() -> dict[str, Any]:
    from app.db import clear_draft

    clear_draft()
    return {"cleared": True}


# ── 백업·복원 (사용자 데이터 안전) ──────────────────────────────────────────
@app.post("/api/backup")
def create_user_backup() -> dict[str, Any]:
    from app.backup import create_backup

    return create_backup()


@app.get("/api/backup/list")
def list_user_backups() -> dict[str, Any]:
    from app.backup import list_backups
    from app.paths import backups_dir

    return {"backups": list_backups(), "backups_dir": str(backups_dir())}


@app.post("/api/backup/inspect")
def inspect_user_backup(payload: BackupFileRequest) -> dict[str, Any]:
    from app.backup import RestoreError, inspect_backup

    try:
        return inspect_backup(payload.filename)
    except RestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/backup/restore")
def restore_user_backup(payload: BackupFileRequest) -> dict[str, Any]:
    from app.backup import RestoreError, restore_backup

    try:
        return restore_backup(payload.filename)
    except RestoreError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.post("/api/data/delete-all")
def delete_all_data(payload: DeleteAllRequest) -> dict[str, Any]:
    """전체 사용자 데이터 삭제 — 위험한 작업이므로 확인 문구를 요구한다."""
    from app.backup import create_backup
    from app.db import delete_all_user_data

    if payload.confirm != "모두 삭제":
        raise HTTPException(status_code=400, detail="확인 문구가 일치하지 않습니다")

    # 삭제 직전 자동 백업 — 실수로 지운 경우 복원 가능
    safety = create_backup()
    deleted = delete_all_user_data()
    return {"deleted_counts": deleted, "safety_backup": safety["filename"]}


@app.get("/api/dashboard", response_model=DashboardResponse)
def dashboard(request: Request, limit: int = 200) -> DashboardResponse:
    host = (request.client.host if request.client else "")
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Dashboard is available only from local app session")
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


def _require_local_session(request: Request) -> None:
    """일반 로컬 기능(예: /api/dashboard)에 쓰는 완화된 검사. CORS와 달리
    실제 접근 제어이지만, 관리자 전용 엔드포인트에는 이것만으로 불충분하므로
    _require_local_admin_session()을 대신 써라."""
    host = (request.client.host if request.client else "")
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Available only from local app session")


def _require_local_admin_session(request: Request) -> None:
    """관리자 전용 엔드포인트(/api/expert-data/*, /api/shadow/*) 접근 제어.

    CORS는 접근 통제가 아니다 — 서버 측에서 다음 두 가지를 모두 요구한다.
    1) 명시적 feature flag(TOEFL_ADMIN_API_ENABLED=1) — 기본값은 비활성화이며,
       운영 배포에서 이 값을 설정하지 않으면 라우트가 아예 존재하지 않는 것처럼
       404를 반환한다 (403이 아니라 404로 응답해 엔드포인트 존재 자체를 숨긴다).
    2) 루프백 인터페이스에서의 접근 — request.client.host는 uvicorn이 실제 TCP
       피어 주소로 채우는 값이며(--proxy-headers 미사용 전제), X-Forwarded-For
       같은 클라이언트 조작 가능 헤더는 절대 신뢰하지 않는다. 이 함수는 그런
       헤더를 읽지 않는다.
    """
    if os.getenv("TOEFL_ADMIN_API_ENABLED", "0").strip() != "1":
        raise HTTPException(status_code=404, detail="Not found")
    host = (request.client.host if request.client else "")
    if host not in {"127.0.0.1", "::1", "localhost", "testclient"}:
        raise HTTPException(status_code=403, detail="Available only from local app session")


# ── Build a Sentence (자체 제작 연습 문제 — API/인터넷 불필요) ──────────────
# 모든 문항은 app/build_a_sentence_items.py의 SYNTHETIC 문항이며 ETS 공식
# 문항이 아니다. 채점은 app/build_a_sentence_engine.py의 결정론적 엔진만
# 사용하며 AI를 호출하지 않는다 (오프라인 코어 기능).
@app.get("/api/build-a-sentence/items", response_model=BuildASentenceItemListResponse)
def list_build_a_sentence_items() -> BuildASentenceItemListResponse:
    return BuildASentenceItemListResponse(
        items_version=BUILD_SENTENCE_ITEMS_VERSION,
        items=[
            BuildASentenceItemSummary(
                item_id=item.item_id,
                fragment_count=len(item.source_fragments),
                difficulty=item.difficulty,
                grammar_tag=item.grammar_tag,
            )
            for item in BUILD_A_SENTENCE_ITEMS
        ],
    )


@app.get("/api/build-a-sentence/items/{item_id}", response_model=BuildASentenceItemDetail)
def get_build_a_sentence_item(item_id: str) -> BuildASentenceItemDetail:
    item = get_bas_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")
    # source_fragments는 셔플해 제공한다 — 순서 자체가 정답 힌트가 되지 않도록 한다.
    import random
    fragments = list(item.source_fragments)
    random.shuffle(fragments)
    return BuildASentenceItemDetail(
        item_id=item.item_id,
        source_fragments=fragments,
        rubric_version=item.rubric_version,
        difficulty=item.difficulty,
        grammar_tag=item.grammar_tag,
        is_official=item.provenance.is_official,
    )


@app.post("/api/build-a-sentence/items/{item_id}/submit", response_model=BuildASentenceSubmitResponse)
def submit_build_a_sentence_answer(item_id: str, payload: BuildASentenceSubmitRequest) -> BuildASentenceSubmitResponse:
    item = get_bas_item(item_id)
    if item is None:
        raise HTTPException(status_code=404, detail="Item not found")

    result = score_bas_submission(item, payload.submission_text)
    attempt_number = save_bas_attempt(
        item_id=item.item_id,
        item_version=BUILD_SENTENCE_ITEMS_VERSION,
        rubric_version=item.rubric_version,
        engine_version=result.engine_version,
        is_correct=result.is_correct,
        match_type=result.match_type,
        time_spent_ms=payload.time_spent_ms,
    )
    return BuildASentenceSubmitResponse(
        item_id=result.item_id,
        match_type=result.match_type,
        is_correct=result.is_correct,
        missing_fragments=result.missing_fragments,
        extra_tokens=result.extra_tokens,
        feedback=result.feedback,
        explanation=item.explanation,
        engine_version=result.engine_version,
        attempt_number=attempt_number,
        correct_answer=None if result.is_correct else item.primary_answer,
    )



# ── Local AI (Phase 8-B) ───────────────────────────────────────────────────
# 기본 분석(Offline Core)은 항상 사용 가능. 로컬 AI는 선택 기능이며 LLM 미설치
# 상태에서도 앱은 정상 작동한다. 답안은 기본적으로 기기 밖으로 나가지 않는다.
@app.get("/api/local-ai/status")
def local_ai_status() -> dict[str, Any]:
    """로컬 AI 상태 조회. 항상 응답하며, LLM 미설치 시 unavailable로 표시된다."""
    manager = get_local_ai_manager()
    return manager.status_summary()


@app.post("/api/local-ai/warmup")
def local_ai_warmup() -> dict[str, Any]:
    """Ollama 모델 웜업. 첫 호출 시 모델 로딩을 미리 수행한다."""
    manager = get_local_ai_manager()
    result = manager.warmup_ollama()
    return result


@app.post("/api/local-ai/test")
def local_ai_test() -> dict[str, Any]:
    """로컬 AI 연결 테스트. RuleLocalAIProvider는 항상 성공, LLM provider는 감지된 경우만."""
    manager = get_local_ai_manager()
    status = manager.status_summary()
    provider = manager.get_selected()

    if provider.id == "rule":
        return {
            "ok": True,
            "message": "기본 분석 엔진이 정상 작동합니다 (규칙 기반, 항상 사용 가능)",
            "provider": provider.id,
            "provider_name": provider.display_name,
            "runs_offline": True,
        }

    availability = provider.is_available()
    if not availability.available:
        return {
            "ok": False,
            "message": f"로컬 AI를 사용할 수 없습니다: {availability.detail}",
            "provider": provider.id,
            "status": availability.status,
        }

    sample_essay = "I think students should use evidence in their writing because it makes arguments stronger. For example, when students include research data, readers trust them more."
    from app.local_ai import LocalAIRequest
    result = provider.analyze_response(LocalAIRequest(essay_text=sample_essay))
    return {
        "ok": result.valid,
        "message": f"{provider.display_name} 연결 테스트 {'성공' if result.valid else '실패'}",
        "provider": provider.id,
        "provider_name": provider.display_name,
        "model_name": result.model_name,
        "runs_offline": result.runs_offline,
        "latency_ms": result.latency_ms,
        "summary": result.summary,
        "performance": result.performance,
    }


@app.post("/api/local-ai/analyze")
def local_ai_analyze(request: Request, payload: dict[str, Any]) -> dict[str, Any]:
    """로컬 AI 분석을 실행한다. 실패해도 Offline Core 채점에 영향을 주지 않는다."""
    _require_local_session(request)

    essay_text = str(payload.get("essay_text", "")).strip()
    if not essay_text or len(essay_text.split()) < 30:
        raise HTTPException(status_code=400, detail="분석할 수 있는 충분한 텍스트가 필요합니다 (최소 30단어)")

    prompt_type = str(payload.get("prompt_type", "academic_discussion"))
    prompt_text = str(payload.get("prompt_text", ""))

    manager = get_local_ai_manager()
    result = manager.analyze(essay_text=essay_text, prompt_type=prompt_type, prompt_text=prompt_text)

    return {
        "valid": result.valid,
        "provider_id": result.provider_id,
        "provider_name": result.provider_name,
        "model_name": result.model_name,
        "runs_offline": result.runs_offline,
        "confidence": result.confidence,
        "latency_ms": result.latency_ms,
        "warnings": result.warnings,
        "summary": result.summary,
        "strengths": [{"text": s.text, "type": s.type, "confidence": s.confidence} for s in result.strengths],
        "priority_issues": [{"text": i.text, "type": i.type, "confidence": i.confidence} for i in result.priority_issues],
        "sentence_suggestions": [
            {"original": s.original, "improved": s.improved, "reason": s.reason, "confidence": s.confidence}
            for s in result.sentence_suggestions
        ],
        "rewrite": result.rewrite,
        "next_practice_goal": result.next_practice_goal,
        "performance": result.performance,
    }

# ── 전문가 데이터 (관리자 전용) ─────────────────────────────────────────────
# 기본 비활성화. TOEFL_ADMIN_API_ENABLED=1 환경변수로만 켤 수 있다.
# 일반 사용자 화면에는 노출하지 않는다. 실제 import는 스크립트/테스트에서 수행하고,
# 이 엔드포인트는 현재 상태를 읽기 전용으로 확인하는 용도다.
# 응답에는 집계 수치만 포함되며 답안 원문·개인정보는 절대 포함하지 않는다
# (tests/test_admin_api_security.py 로 회귀 검증).
@app.get("/api/expert-data/summary")
def expert_data_summary(request: Request) -> dict[str, Any]:
    _require_local_admin_session(request)
    import app.expert_data as expert_data

    return {
        "dataset_split_counts": expert_data.dataset_split_summary(),
        "import_history": expert_data.list_import_history(),
    }


# ── AI shadow mode 비교 리포트 (관리자 전용) ────────────────────────────────
# 프로덕션 채점 경로는 이 데이터를 전혀 사용하지 않는다. 순수 관측용.
# 기본 비활성화. TOEFL_ADMIN_API_ENABLED=1 환경변수로만 켤 수 있다.
@app.get("/api/shadow/summary")
def shadow_summary(request: Request) -> dict[str, Any]:
    _require_local_admin_session(request)
    from app.shadow_mode import summarize_comparisons

    return summarize_comparisons()


@app.get("/api/report/{submission_id}.pdf")
def download_report(submission_id: int) -> FileResponse:
    record = get_submission(submission_id)
    if record is None:
        raise HTTPException(status_code=404, detail="Submission not found")

    from app.pdf_report import build_report

    report_dir = exports_dir() / "reports"
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"submission_{submission_id}.pdf"

    pdf = build_report(record, submission_id)
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

    scores = [float(r.get("estimated_score_0_5", 0.0)) for r in week_rows]

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
        daily[day].append(float(r.get("estimated_score_0_5", 0.0)))

    daily_list = [
        DailySubmissionCount(day=day, count=len(v), avg_score=round(sum(v) / len(v), 2))
        for day, v in sorted(daily.items())
    ]

    avg_s = round(sum(scores) / len(scores), 2)
    best_s = round(max(scores), 2)
    worst_s = round(min(scores), 2)

    if avg_s >= 4.5:
        rec = f"이번 주 평균 과제 점수는 {avg_s}/5입니다. 높은 완성도를 안정적으로 유지하세요."
    elif avg_s >= 4.0:
        rec = f"평균 과제 점수는 {avg_s}/5입니다. {most_common} 오류를 집중 교정하면 5점 요건에 가까워집니다."
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

    s1 = float(res1.get("estimated_score_0_5", 0.0))
    s2 = float(res2.get("estimated_score_0_5", 0.0))
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
            task_score_0_5=s1,
            score_band_1_6=res1.get("score_band_1_6"),
            estimated_score_30=res1.get("estimated_score_30"),
            grammar_total=g1,
            strengths=res1.get("strengths", [])[:3],
            weaknesses=res1.get("weaknesses", [])[:3],
        ),
        submission_2=CompareScoreInfo(
            submission_id=id2,
            created_at=str(r2["created_at"])[:19],
            task_score_0_5=s2,
            score_band_1_6=res2.get("score_band_1_6"),
            estimated_score_30=res2.get("estimated_score_30"),
            grammar_total=g2,
            strengths=res2.get("strengths", [])[:3],
            weaknesses=res2.get("weaknesses", [])[:3],
        ),
        score_delta=round(s2 - s1, 2),
        grammar_delta=g2 - g1,
        improvement_areas=improvements,
    )
