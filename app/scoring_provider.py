"""AI 채점 provider 추상화 + shadow mode 파이프라인.

**중요**: 이 모듈의 결과는 현재 어떤 경우에도 사용자에게 표시되는 점수
(`/api/evaluate`의 `estimated_score_0_5`)에 영향을 주지 않는다. 결정론적
휴리스틱 엔진(app/scorer.py)이 여전히 유일한 production 채점 경로다.

Shadow mode 목적: AI provider가 휴리스틱과 얼마나 다르게 채점하는지, evidence를
환각하지는 않는지, 구조적으로 안정적인지 측정해 향후 실제 채점 반영 여부를
데이터로 판단하기 위함이다 (프로덕션 반영 전 단계).

파이프라인 단계 (마스터 스펙 15장 최소 단계 중 shadow 검증에 필요한 핵심만 구현):
  1. 입력 유효성 검사
  2. 문제 요구사항 추출 (task_type별)
  3. 답안 분석 (주장/근거/구조, 점수 없이)
  4. 차원별 독립 점수 (dimension scoring)
  5. evidence span 추출 + 원문 대조 검증
  6. 독립 critic (draft 점수의 문제 지적)
  7. 최종 점수 reconciliation (명시적 규칙: critic이 문제 제기한 차원만 조정)
  8. confidence 산출

실제 LLM(OpenAI/Claude/Gemini) 경로는 API 키가 없어 이 세션에서 네트워크
호출이 검증되지 않았다 — 구조만 구현했고, MockScoringProvider로 파이프라인
메커니즘(스키마, evidence 검증, 비교 리포트)만 검증했다.
"""

from __future__ import annotations

import json
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

SHADOW_PROMPT_VERSION = "shadow-v1"


# ── 데이터 모델 ──────────────────────────────────────────────────────────

@dataclass
class InputValidation:
    is_scorable: bool
    reason_codes: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)


@dataclass
class RequirementItem:
    requirement: str
    status: Literal["met", "partially_met", "missing"]
    evidence_text: str = ""


@dataclass
class InputAnalysis:
    requirements: list[RequirementItem] = field(default_factory=list)
    main_claims: list[str] = field(default_factory=list)
    off_topic_risk: bool = False
    template_risk: bool = False


@dataclass
class EvidenceSpan:
    start: int
    end: int
    text: str
    dimension_id: str = ""
    explanation: str = ""
    verified: bool = False  # response_text[start:end] == text 검증 결과


@dataclass
class DimensionAssessment:
    dimension_id: str
    score: float
    max_score: float
    explanation: str
    evidence: list[EvidenceSpan] = field(default_factory=list)


@dataclass
class DimensionScoreResult:
    dimensions: list[DimensionAssessment] = field(default_factory=list)
    overall_draft_score: float = 0.0


@dataclass
class AssessmentCritique:
    """draft 평가에 대한 독립 검토. 새 점수를 무조건 만들지 않고 문제만 지적한다."""

    flagged_dimension_ids: list[str] = field(default_factory=list)
    issues: list[str] = field(default_factory=list)
    severity: Literal["none", "minor", "major"] = "none"


@dataclass
class FeedbackResult:
    summary: str = ""
    priority_issues: list[str] = field(default_factory=list)


@dataclass
class ShadowScoreResult:
    input_validation: InputValidation
    analysis: InputAnalysis
    draft: DimensionScoreResult
    critique: AssessmentCritique
    final_score_0_5: float
    confidence: Literal["low", "medium", "high"]
    feedback: FeedbackResult
    schema_valid: bool
    evidence_total: int  # score_dimensions가 최초에 제시한 evidence 총수 (재시도 포함 마지막 시도 기준)
    evidence_verified: int
    reason_codes: list[str] = field(default_factory=list)
    retry_count: int = 0
    invalid_assessment: bool = False


# evidence 검증 실패 시 재시도를 유발하는 기준 (하나라도 실패하면 재시도)
_EVIDENCE_RETRY_TRIGGER_RATE = 1.0
# 재시도를 다 써도 이 비율 미만이면 assessment 전체를 invalid로 표시하고,
# 검증 실패한 evidence는 결과에서 제거한다 (UI/comparison report에 노출 금지).
_EVIDENCE_INVALID_THRESHOLD = 0.5


# ── evidence 검증 (provider와 무관한 순수 함수 — 반드시 코드에서 검증) ──────

def validate_evidence_spans(response_text: str, spans: list[EvidenceSpan]) -> list[EvidenceSpan]:
    """response_text.slice(start, end) === text 를 코드에서 강제 검증한다.

    일치하지 않는 evidence는 verified=False로 표시되며, 호출부는 verified=False인
    evidence를 사용자에게 노출하면 안 된다.
    """
    validated: list[EvidenceSpan] = []
    for span in spans:
        actual = response_text[span.start:span.end] if 0 <= span.start < span.end <= len(response_text) else None
        verified = actual == span.text
        validated.append(EvidenceSpan(
            start=span.start, end=span.end, text=span.text,
            dimension_id=span.dimension_id, explanation=span.explanation,
            verified=verified,
        ))
    return validated


# ── Provider 추상화 ──────────────────────────────────────────────────────

@dataclass
class ScoringInput:
    essay_text: str
    prompt_text: str
    task_type: str


class ScoringProvider(ABC):
    """실제 채점에 쓰이지 않는 shadow-mode 전용 provider 인터페이스.

    메서드 경계는 마스터 스펙 13장을 따른다: 분석/차원점수/비판/피드백을
    분리해 한 번의 호출로 모든 것을 뭉뚱그리지 않는다.
    """

    id: str

    def __init__(self) -> None:
        # 실제 provider(예: ClaudeScoringProvider)가 API 호출마다 누적하는 토큰 사용량.
        # MockScoringProvider처럼 네트워크를 쓰지 않는 provider는 0으로 유지된다 —
        # 실제로 사용하지 않은 토큰/비용을 지어내지 않기 위해서다.
        self.last_usage: dict[str, int] = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

    @abstractmethod
    def analyze_input(self, scoring_input: ScoringInput) -> tuple[InputValidation, InputAnalysis]:
        ...

    @abstractmethod
    def score_dimensions(self, scoring_input: ScoringInput, analysis: InputAnalysis) -> DimensionScoreResult:
        ...

    @abstractmethod
    def critique_assessment(self, scoring_input: ScoringInput, draft: DimensionScoreResult) -> AssessmentCritique:
        ...

    @abstractmethod
    def generate_feedback(self, scoring_input: ScoringInput, final_score: float) -> FeedbackResult:
        ...

    max_evidence_retries: int = 1

    def run(self, scoring_input: ScoringInput) -> ShadowScoreResult:
        """전체 파이프라인을 순서대로 실행하고 evidence를 코드에서 검증한다.

        evidence 검증 실패 시 최대 max_evidence_retries번 score_dimensions를
        재호출한다. 재시도 후에도 검증 성공률이 낮으면 assessment 전체를
        invalid로 표시하고, 검증 실패한 evidence는 결과에서 제거해 UI나
        비교 리포트에 절대 노출하지 않는다.
        """
        # 매 실행마다 토큰 사용량을 초기화한다 (subclass가 __init__에서 super()를
        # 호출하지 않아도 항상 유효한 값을 갖도록 방어적으로 재설정).
        self.last_usage = {"input_tokens": 0, "output_tokens": 0, "calls": 0}

        validation, analysis = self.analyze_input(scoring_input)

        reason_codes: list[str] = list(validation.reason_codes)
        if not validation.is_scorable:
            return ShadowScoreResult(
                input_validation=validation, analysis=analysis,
                draft=DimensionScoreResult(), critique=AssessmentCritique(),
                final_score_0_5=0.0, confidence="low",
                feedback=FeedbackResult(summary="입력이 채점 불가로 판정됨"),
                schema_valid=True, evidence_total=0, evidence_verified=0,
                reason_codes=reason_codes,
            )

        draft = self.score_dimensions(scoring_input, analysis)
        evidence_total, evidence_verified = self._validate_and_filter_evidence(scoring_input, draft)

        retry_count = 0
        while (
            evidence_total > 0
            and (evidence_verified / evidence_total) < _EVIDENCE_RETRY_TRIGGER_RATE
            and retry_count < self.max_evidence_retries
        ):
            retry_count += 1
            reason_codes.append(f"evidence_retry_{retry_count}")
            draft = self.score_dimensions(scoring_input, analysis)
            evidence_total, evidence_verified = self._validate_and_filter_evidence(scoring_input, draft)

        invalid_assessment = False
        if evidence_total > 0 and (evidence_verified / evidence_total) < _EVIDENCE_INVALID_THRESHOLD:
            invalid_assessment = True
            reason_codes.append("invalid_assessment_low_evidence_confidence")
        elif evidence_total and evidence_verified < evidence_total:
            reason_codes.append("evidence_hallucination_detected")

        critique = self.critique_assessment(scoring_input, draft)

        # ── 점수 조정: 명시적 규칙, "알아서 결정" 블랙박스 금지 ──────────
        final_score = draft.overall_draft_score
        if critique.severity == "major":
            final_score = max(0.0, final_score - 0.5)
            reason_codes.append("critic_major_adjustment")
        elif critique.severity == "minor":
            final_score = max(0.0, final_score - 0.2)
            reason_codes.append("critic_minor_adjustment")
        final_score = round(max(0.0, min(5.0, final_score)) * 4) / 4

        # ── confidence: evidence 검증율 + critic severity 조합 ───────────
        evidence_rate = (evidence_verified / evidence_total) if evidence_total else 1.0
        if invalid_assessment or evidence_rate < 0.8 or critique.severity == "major":
            confidence: Literal["low", "medium", "high"] = "low"
        elif evidence_rate < 1.0 or critique.severity == "minor":
            confidence = "medium"
        else:
            confidence = "high"

        feedback = self.generate_feedback(scoring_input, final_score)

        return ShadowScoreResult(
            input_validation=validation, analysis=analysis, draft=draft,
            critique=critique, final_score_0_5=final_score, confidence=confidence,
            feedback=feedback, schema_valid=True,
            evidence_total=evidence_total, evidence_verified=evidence_verified,
            reason_codes=reason_codes, retry_count=retry_count,
            invalid_assessment=invalid_assessment,
        )

    @staticmethod
    def _validate_and_filter_evidence(
        scoring_input: ScoringInput, draft: DimensionScoreResult,
    ) -> tuple[int, int]:
        """evidence를 코드에서 강제 검증하고, 검증 실패한 evidence는 draft에서 제거한다
        (UI/비교 리포트에 절대 노출하지 않기 위함). (검증 전 총수, 검증 통과 수)를 반환한다."""
        total = 0
        verified = 0
        for dim in draft.dimensions:
            checked = validate_evidence_spans(scoring_input.essay_text, dim.evidence)
            total += len(checked)
            verified += sum(1 for e in checked if e.verified)
            dim.evidence = [e for e in checked if e.verified]
        return total, verified


# ── Mock provider: 네트워크 없이 파이프라인 자체를 검증하기 위함 ───────────

class MockScoringProvider(ScoringProvider):
    """실제 LLM을 호출하지 않는다. 텍스트 통계만으로 그럴듯한 구조화된 결과를
    만들어 shadow 파이프라인의 배관(스키마, evidence 검증, reconciliation,
    confidence 계산)이 올바르게 동작하는지 테스트하기 위한 provider다.

    이 provider의 점수는 채점 품질의 증거가 아니다 — 배관 검증용이다.
    """

    id = "mock"

    def analyze_input(self, scoring_input: ScoringInput) -> tuple[InputValidation, InputAnalysis]:
        text = scoring_input.essay_text.strip()
        word_count = len(text.split())
        if word_count < 10:
            return InputValidation(is_scorable=False, reason_codes=["too_short"]), InputAnalysis()
        return (
            InputValidation(is_scorable=True),
            InputAnalysis(main_claims=[text[:60]], off_topic_risk=False, template_risk=False),
        )

    def score_dimensions(self, scoring_input: ScoringInput, analysis: InputAnalysis) -> DimensionScoreResult:
        text = scoring_input.essay_text
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]
        first_sentence = sentences[0] if sentences else ""
        start = text.find(first_sentence) if first_sentence else -1

        evidence = []
        if start >= 0 and first_sentence:
            evidence = [EvidenceSpan(
                start=start, end=start + len(first_sentence), text=first_sentence,
                dimension_id="content", explanation="mock: 첫 문장을 근거로 사용",
            )]

        word_count = len(text.split())
        base = min(5.0, 1.5 + word_count / 60.0)
        dims = [
            DimensionAssessment("structure", round(base, 2), 5.0, "mock structure score", list(evidence)),
            DimensionAssessment("content", round(base, 2), 5.0, "mock content score", list(evidence)),
        ]
        overall = sum(d.score for d in dims) / len(dims)
        return DimensionScoreResult(dimensions=dims, overall_draft_score=overall)

    def critique_assessment(self, scoring_input: ScoringInput, draft: DimensionScoreResult) -> AssessmentCritique:
        if draft.overall_draft_score >= 4.5 and len(scoring_input.essay_text.split()) < 80:
            return AssessmentCritique(
                flagged_dimension_ids=["content"],
                issues=["짧은 답안인데 점수가 과도하게 높음"],
                severity="minor",
            )
        return AssessmentCritique(severity="none")

    def generate_feedback(self, scoring_input: ScoringInput, final_score: float) -> FeedbackResult:
        return FeedbackResult(
            summary=f"mock feedback for score {final_score}",
            priority_issues=["mock priority issue"],
        )


def get_provider(name: str) -> ScoringProvider:
    """이름으로 직접 provider를 얻는다 (설정/가용성 확인 없이). 테스트/CLI용.

    프로덕션 경로에서 shadow provider를 얻을 때는 get_shadow_provider()를 써서
    TOEFL_SHADOW_ENABLED/API 키 존재 여부를 함께 확인하라.
    """
    if name == "mock":
        return MockScoringProvider()
    if name == "claude":
        from app.claude_provider import ClaudeScoringProvider
        from app.shadow_config import load_shadow_config

        return ClaudeScoringProvider(load_shadow_config())
    raise NotImplementedError(
        f"provider '{name}'는 아직 구현되지 않았다. 현재 'mock'과 'claude'만 지원한다. "
        "OpenAI/Gemini shadow provider가 필요하면 app/claude_provider.py를 참고해 동일한 "
        "패턴(4단계 호출 + evidence 검증)으로 구현하라."
    )


def get_shadow_provider() -> tuple[ScoringProvider | None, Any]:
    """설정을 확인하고 사용 가능하면 (provider, availability)를, 아니면 (None, availability)를 반환한다.

    이 함수는 절대 예외를 던지지 않는다 — API 키가 없거나 shadow mode가 꺼져 있어도
    앱이 정상 기동해야 한다.
    """
    from app.shadow_config import ProviderAvailability, load_shadow_config

    cfg = load_shadow_config()
    if not cfg.enabled:
        return None, ProviderAvailability(available=False, reason_code="shadow_disabled")

    if cfg.provider == "mock":
        return MockScoringProvider(), ProviderAvailability(available=True, reason_code="ok")

    if cfg.provider == "claude":
        if not cfg.anthropic_api_key:
            return None, ProviderAvailability(
                available=False, reason_code="missing_api_key",
                detail="ANTHROPIC_API_KEY not set",
            )
        from app.claude_provider import ClaudeScoringProvider

        return ClaudeScoringProvider(cfg), ProviderAvailability(available=True, reason_code="ok")

    return None, ProviderAvailability(
        available=False, reason_code="unknown_provider", detail=cfg.provider,
    )
