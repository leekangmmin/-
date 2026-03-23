from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

PromptType = Literal["email", "academic_discussion"]


class EvaluateRequest(BaseModel):
    prompt_type: Optional[PromptType] = Field(
        None, description="Task type: auto-detected if omitted"
    )
    prompt_text: str = Field("", max_length=3000)
    essay_text: str = Field(..., min_length=80, max_length=12000)
    target_score_0_5: float = Field(4.0, ge=0.0, le=5.0)
    exam_mode: bool = False


class PrecheckRequest(BaseModel):
    prompt_type: Optional[PromptType] = None
    prompt_text: str = Field("", max_length=3000)
    essay_text: str = Field(..., min_length=80, max_length=12000)


class ScoreDimension(BaseModel):
    name: str
    score: float
    reason: str


class SentenceEdit(BaseModel):
    original: str
    improved: str
    note: str


class PromptFit(BaseModel):
    score: float
    reason_ko: str
    reason_en: str
    matched_keywords: list[str]
    missing_keywords: list[str]


class ClaimEvidenceTag(BaseModel):
    sentence: str
    tag: Literal["claim", "evidence", "explanation", "other"]
    note: str


class GrammarStats(BaseModel):
    tense: int
    article: int
    preposition: int
    run_on: int
    subject_verb: int
    punctuation: int
    total: int


class RewriteSuggestion(BaseModel):
    minimal: str
    aggressive: str


class SampleComparison(BaseModel):
    matched_points: list[str]
    missing_points: list[str]
    overlap_score: float


class BilingualFeedback(BaseModel):
    summary_ko: str
    summary_en: str


class TemplateCoach(BaseModel):
    opening_templates: list[str]
    body_templates: list[str]
    transition_bank: list[str]
    closing_templates: list[str]


class ScoreHighlight(BaseModel):
    sentence: str
    impact: Literal["positive", "negative", "neutral"]
    reason: str


class WeaknessCard(BaseModel):
    category: str
    wrong_pattern: str
    fix_pattern: str
    tip: str


class PersonalizationAdvice(BaseModel):
    coaching_tone: str
    repeated_issues: list[str]
    next_focus: str


class ParaphraseSuggestion(BaseModel):
    original: str
    improved: str
    reason: str


class ChecklistItem(BaseModel):
    label: str
    status: Literal["good", "warn"]
    score: int


class PreSubmitChecklist(BaseModel):
    total_score: int
    items: list[ChecklistItem]


class GrammarDrill(BaseModel):
    issue: str
    wrong: str
    correct: str
    tip: str


class GrammarCorrection(BaseModel):
    sentence: str
    error_type: str
    focus_text: str
    focus_start: Optional[int] = None
    focus_end: Optional[int] = None
    corrected: str
    explanation: str
    severity: Literal["low", "medium", "high"]


class ScoreSimulatorItem(BaseModel):
    action: str
    expected_delta_0_5: float
    projected_band_1_6: float


class SmartRecommendation(BaseModel):
    title: str
    why: str
    how_to: str
    impact: str
    confidence: Literal["low", "medium", "high"]


class TargetEta(BaseModel):
    estimated_attempts: int
    pace_label: str
    message: str


class SentenceVariety(BaseModel):
    short_ratio: float
    medium_ratio: float
    long_ratio: float
    recommendation: str


class GrammarImpactItem(BaseModel):
    issue: str
    count: int
    estimated_penalty_0_5: float


class BeforeAfterProjection(BaseModel):
    current_score_0_5: float
    projected_score_0_5: float
    current_band_1_6: float
    projected_band_1_6: float
    expected_gain_0_5: float


class TargetBandStrategyItem(BaseModel):
    title: str
    detail: str


class RepetitionTrainingItem(BaseModel):
    word: str
    count: int
    alternatives: list[str]


class ExaminerFeedback(BaseModel):
    mode: Literal["normal", "exam"]
    comments: list[str]


class ScoreBandProfile(BaseModel):
    reading: str
    listening: str
    speaking: str
    writing: str
    total: str


class RiskCheckResponse(BaseModel):
    risk_level: Literal["low", "medium", "high"]
    warnings: list[str]
    ready: bool
    checklist: PreSubmitChecklist


class EvaluationResult(BaseModel):
    estimated_score_0_5: float
    estimated_score_30: int
    score_band_1_6: float
    score_profile: ScoreBandProfile
    ai_mode: Literal["local", "ai"]
    grammar_cap_applied: bool
    grammar_cap_reason: str
    confidence: Literal["low", "medium", "high"]
    confidence_reason: str
    dimensions: list[ScoreDimension]
    prompt_fit: PromptFit
    claim_evidence_map: list[ClaimEvidenceTag]
    grammar_stats: GrammarStats
    target_rewrite: RewriteSuggestion
    sample_comparison: SampleComparison
    bilingual_feedback: BilingualFeedback
    template_coach: TemplateCoach
    score_highlights: list[ScoreHighlight]
    weakness_dictionary: list[WeaknessCard]
    personalization: PersonalizationAdvice
    paraphrase_recommendations: list[ParaphraseSuggestion]
    checklist: PreSubmitChecklist
    grammar_drills: list[GrammarDrill]
    grammar_corrections: list[GrammarCorrection]
    auto_rewrite_essay: str
    revision_diff: list[str]
    grammar_impact: list[GrammarImpactItem]
    before_after_projection: BeforeAfterProjection
    score_simulator: list[ScoreSimulatorItem]
    smart_recommendations: list[SmartRecommendation]
    top_priority_actions: list[SmartRecommendation]
    target_eta: TargetEta
    sentence_variety: SentenceVariety
    target_band_strategy: list[TargetBandStrategyItem]
    repetition_training: list[RepetitionTrainingItem]
    examiner_feedback: ExaminerFeedback
    personal_weakness_ranking: list[str]
    weekly_plan: list[str]
    strengths: list[str]
    weaknesses: list[str]
    action_plan: list[str]
    sentence_edits: list[SentenceEdit]
    upgraded_sample_paragraph: str


class EvaluateResponse(BaseModel):
    submission_id: int
    created_at: datetime
    result: EvaluationResult


class SubmissionHistoryItem(BaseModel):
    id: int
    created_at: datetime
    prompt_type: PromptType
    estimated_score_0_5: float
    score_band_1_6: float
    estimated_score_30: int


class SubmissionHistoryResponse(BaseModel):
    items: list[SubmissionHistoryItem]


class ScoreTrendPoint(BaseModel):
    submission_id: int
    score_0_5: float


class GrammarIssueItem(BaseModel):
    type: str
    count: int


class GrammarTrendPoint(BaseModel):
    submission_id: int
    total_errors: int


class DashboardResponse(BaseModel):
    attempt_count: int
    avg_score_0_5: float
    avg_prompt_fit: float
    score_trend: list[ScoreTrendPoint]
    top_grammar_issues: list[GrammarIssueItem]
    grammar_error_trend: list[GrammarTrendPoint]
    recommended_focus: list[str]
