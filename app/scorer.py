from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

from app.grammar import GRAMMAR_RULES_VERSION, GrammarSignals, analyze_grammar
from app.models import PromptType, ScoreDimension

# 점수 산출 로직 변경 시 버전을 올린다. 평가 결과에 함께 저장되어 재현성을 보장한다.
SCORING_ENGINE_VERSION = "2.2.0"
RUBRIC_VERSION = f"heuristic-6dim-{SCORING_ENGINE_VERSION}+grammar-{GRAMMAR_RULES_VERSION}"

# ── 점수 공식 변경 금지 게이트 ────────────────────────────────────────────
# 이 값은 가중치·임계값·페널티 등 "점수를 계산하는 수식 자체"의 버전이다.
# SCORING_ENGINE_VERSION과 현재는 1:1로 같이 움직이지만 개념적으로 분리해뒀다 —
# 향후 캘리브레이션 레이어가 추가되면 SCORING_ENGINE_VERSION은 그대로 두고
# 이 값만 올려 "원시 공식은 그대로, 보정만 추가됨"을 구분할 수 있게 하기 위함이다.
#
# 중요: 전문가 데이터로 실측 오차가 확인되기 전까지, 이 공식(가중치/임계값/페널티)을
# 미적 판단만으로 다시 바꾸지 마라. 0.5 단위 반올림 경계에서 사소한 변화가 표시
# 점수를 한 단계 움직이는 현상은 알려진 한계로 기록하되(quantization_distance),
# 데이터 없이 재설계하지 않는다 — docs/scoring-formula-change-gate.md 참고.
SCORING_FORMULA_VERSION = SCORING_ENGINE_VERSION


@dataclass
class ScoringBreakdown:
    """점수 산출 과정의 양자화(0.5 단위 반올림) 영향을 추적하기 위한 상세 결과.

    전문가 데이터가 쌓인 뒤 "반올림 경계 구간에서 MAE가 더 큰가", "반올림
    직전/직후로 편향이 갈리는가"를 분석할 수 있게 raw(반올림 전) 값을 함께
    저장한다. 이 필드들은 점수 공식을 바꾸지 않고 단지 관찰 가능하게만 만든다.
    """

    dimensions: list[ScoreDimension]
    total_0_5: float  # 최종 표시 점수 (0.5 단위 반올림 후)
    pre_round_raw_score: float  # 반올림 전 원점수
    distance_to_rounding_boundary: float  # 원점수가 가장 가까운 0.5 경계에서 얼마나 떨어져 있는지 (0에 가까울수록 반올림에 민감)
    component_scores: dict[str, float]  # 차원별 반올림 전 기여 점수 (0-5 스케일)
    scoring_formula_version: str
    grammar_cap_applied: bool
    grammar_cap_ceiling: float | None
    calibration_adjustment: float
    calibration_reason: str

TRANSITIONS = {
    "however",
    "therefore",
    "moreover",
    "furthermore",
    "in addition",
    "for example",
    "for instance",
    "as a result",
    "on the other hand",
    "in contrast",
    "consequently",
    "meanwhile",
    "thus",
    "overall",
}

POSITION_MARKERS = {
    "i believe",
    "i firmly believe",
    "i think",
    "in my view",
    "from my perspective",
    "my position",
    "i agree",
    "i strongly agree",
    "i disagree",
    "i strongly disagree",
}

EVIDENCE_MARKERS = {
    "because",
    "for example",
    "for instance",
    "evidence",
    "data",
    "research",
    "study",
    "according to",
}


@dataclass
class EssayMetrics:
    word_count: int
    sentence_count: int
    paragraph_count: int
    avg_sentence_length: float
    long_sentence_ratio: float
    short_sentence_ratio: float
    transition_hits: int
    position_hits: int
    evidence_hits: int
    lexical_diversity: float


def _round_half(value: float) -> float:
    return max(0.0, min(5.0, round(value * 2) / 2))


def _round_quarter(value: float) -> float:
    return max(0.0, min(5.0, round(value * 4) / 4))


def _count_phrases(text: str, phrases: set[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in phrases)


def _sentence_variety_score(sentence_lengths: list[int]) -> float:
    if not sentence_lengths:
        return 0.0
    short = sum(1 for s in sentence_lengths if s <= 10)
    mid = sum(1 for s in sentence_lengths if 11 <= s <= 24)
    long = sum(1 for s in sentence_lengths if s >= 25)
    # Balanced variety (short + mid + long) tends to improve readability and rhythm.
    bins = sum(1 for x in (short, mid, long) if x > 0)
    if bins == 3:
        return 1.0
    if bins == 2:
        return 0.6
    return 0.2


def _repetition_penalty(essay_text: str) -> float:
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", essay_text)]
    if len(words) < 40:
        return 0.0
    overused = 0
    for token in {"good", "bad", "thing", "things", "very", "really", "so"}:
        if words.count(token) >= 4:
            overused += 1
    if overused >= 3:
        return 0.5
    if overused >= 1:
        return 0.25
    return 0.0


def analyze_essay(essay_text: str) -> EssayMetrics:
    cleaned = essay_text.strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    words = re.findall(r"[A-Za-z']+", cleaned)
    sentences = [
        s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()
    ]

    sentence_lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in sentences] or [0]
    avg_sentence_length = mean(sentence_lengths)
    long_sentence_ratio = sum(length > 35 for length in sentence_lengths) / len(
        sentence_lengths
    )
    short_sentence_ratio = sum(length < 6 for length in sentence_lengths) / len(
        sentence_lengths
    )

    unique_words: set[str] = {w.lower() for w in words} if words else set()
    lexical_diversity = (len(unique_words) / len(words)) if words else 0.0

    return EssayMetrics(
        word_count=len(words),
        sentence_count=len(sentences),
        paragraph_count=max(1, len(paragraphs)),
        avg_sentence_length=avg_sentence_length,
        long_sentence_ratio=long_sentence_ratio,
        short_sentence_ratio=short_sentence_ratio,
        transition_hits=_count_phrases(cleaned, TRANSITIONS),
        position_hits=_count_phrases(cleaned, POSITION_MARKERS),
        evidence_hits=_count_phrases(cleaned, EVIDENCE_MARKERS),
        lexical_diversity=lexical_diversity,
    )


def _grammar_risk_profile(essay_text: str) -> GrammarSignals:
    """공유 문법 모듈에 위임한다 (구현 중복 제거)."""
    return analyze_grammar(essay_text)


def grammar_cap_status(essay_text: str) -> dict[str, float | bool | str]:
    profile = _grammar_risk_profile(essay_text)
    if profile.severe_breakdown:
        return {
            "applied": True,
            "ceiling_0_5": 2.0,
            "reason": "문장 형식 파괴/중대한 문법 붕괴가 감지되어 고득점 상한이 적용되었습니다.",
        }
    if profile.repeated_error:
        return {
            "applied": True,
            "ceiling_0_5": 2.5,
            "reason": "반복적인 문법 오류가 감지되어 6.0 기준 상위권 도달이 어렵습니다.",
        }
    return {
        "applied": False,
        "ceiling_0_5": 5.0,
        "reason": "",
    }


def _target_word_window(prompt_type: PromptType) -> tuple[int, int]:
    if prompt_type == "email":
        return 100, 220
    return 120, 300


# email greeting / closing patterns for Structure scoring
_EMAIL_GREETINGS = re.compile(
    r"\b(dear|hi|hello|good morning|good afternoon|to whom it may concern)\b",
    re.IGNORECASE,
)
_EMAIL_CLOSINGS = re.compile(
    r"\b(sincerely|best regards|kind regards|regards|yours truly|thank you|thanks)\b",
    re.IGNORECASE,
)

_EMAIL_PURPOSE = re.compile(
    r"\b(i am writing to (?:sincerely )?(?:thank|express|apologize|inquire|report|invite|recommend|request|ask|notify)|"
    r"i am writing (?:regarding|concerning)|i would like to (?:thank|apologize|ask|request|invite|recommend)|"
    r"i am contacting you|please accept my|thank you for)\b",
    re.IGNORECASE,
)
_EMAIL_POLITENESS = re.compile(
    r"\b(could you please|would you please|i would (?:also )?(?:appreciate|be grateful)|"
    r"thank you|we truly appreciate|please|your (?:understanding|assistance|consideration)|"
    r"sincerely|best regards|kind regards)\b",
    re.IGNORECASE,
)
_EMAIL_DETAIL_MARKERS = re.compile(
    r"\b(unfortunately|especially|specifically|because|due to|after|before|during|when|"
    r"even though|although|until|already|free|vip|mobile phone|deadline|schedule|"
    r"order|reservation|visit|tour|workshop|assignment|draft|coupon|pass(?:es)?)\b",
    re.IGNORECASE,
)
_EMAIL_SEQUENCE_MARKERS = {
    "after",
    "before",
    "during",
    "even though",
    "although",
    "until",
    "especially",
    "specifically",
    "once again",
    "also",
    "because",
    "therefore",
    "as a result",
    "in addition",
}


def _email_task_signals(essay_text: str) -> dict[str, int | bool]:
    """Purpose-neutral email fulfillment signals.

    Gratitude, apology, invitation, recommendation, inquiry, report, and request
    emails need different speech acts. A request is therefore not universally
    required; purpose clarity, concrete detail, polite register, and closure are.
    """
    detail_sentences = sum(
        1
        for sentence in re.split(r"(?<=[.!?])\s+", essay_text.strip())
        if len(re.findall(r"[A-Za-z']+", sentence)) >= 10
        and not _EMAIL_GREETINGS.fullmatch(sentence.strip().rstrip(","))
        and not _EMAIL_CLOSINGS.fullmatch(sentence.strip().rstrip(","))
    )
    return {
        "greeting": bool(_EMAIL_GREETINGS.search(essay_text)),
        "closing": bool(_EMAIL_CLOSINGS.search(essay_text)),
        "purpose": bool(_EMAIL_PURPOSE.search(essay_text)),
        "politeness_hits": len(_EMAIL_POLITENESS.findall(essay_text)),
        "detail_hits": len(_EMAIL_DETAIL_MARKERS.findall(essay_text)),
        "sequence_hits": _count_phrases(essay_text, _EMAIL_SEQUENCE_MARKERS),
        "detail_sentences": detail_sentences,
        "second_move": bool(re.search(r"\b(i would also|we were especially|thank you once again|in addition|also)\b", essay_text, re.I)),
    }


def score_essay(essay_text: str, prompt_type: PromptType) -> tuple[list[ScoreDimension], float]:
    """하위 호환 진입점. 상세 양자화 메타데이터가 필요하면 score_essay_detailed()를 써라."""
    breakdown = score_essay_detailed(essay_text, prompt_type)
    return breakdown.dimensions, breakdown.total_0_5


def score_essay_detailed(essay_text: str, prompt_type: PromptType) -> ScoringBreakdown:
    metrics = analyze_essay(essay_text)
    grammar_profile = _grammar_risk_profile(essay_text)
    grammar_risk = grammar_profile.total
    min_words, max_words = _target_word_window(prompt_type)
    sentence_lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    variety = _sentence_variety_score(sentence_lengths)
    repetition_penalty = _repetition_penalty(essay_text)
    email_signals = _email_task_signals(essay_text) if prompt_type == "email" else None

    # ── Structure (짜임새 있는 구성) ──────────────────────────────────────────
    structure = 1.5
    if prompt_type == "email":
        if _EMAIL_GREETINGS.search(essay_text):
            structure += 1.0
        if _EMAIL_CLOSINGS.search(essay_text):
            structure += 1.0
        if metrics.paragraph_count >= 2:
            structure += 0.5
        if metrics.transition_hits >= 2:
            structure += 0.5
        if metrics.sentence_count >= 6:
            structure += 0.25
    else:  # academic_discussion
        if metrics.paragraph_count >= 3:
            structure += 1.5
        elif metrics.paragraph_count == 2:
            structure += 0.75
        if metrics.transition_hits >= 5:
            structure += 0.75
        elif metrics.transition_hits >= 2:
            structure += 0.35
        if metrics.position_hits >= 1:
            structure += 0.5
        if metrics.sentence_count >= 8:
            structure += 0.25

    # ── Content (질문에 맞는 내용) ────────────────────────────────────────────
    content = 1.5
    # 단어 수 임계값을 3단계로 완화한다. 기존 2단계(0.5 vs 1.0)는 경계선 바로 위/
    # 아래에서 무의미한 패딩 몇 단어만 추가해도 +0.5가 뛰는 절벽 구조였다
    # (Phase 2 인젝션 안전성 검증에서 실제로 재현됨: 의미 없는 문장 추가만으로도
    # 동일한 점수 상승이 발생 — 이는 인젝션 방어 문제가 아니라 분량 게이밍 문제).
    if min_words <= metrics.word_count <= max_words:
        content += 1.0
    elif metrics.word_count >= min_words - 10:
        content += 0.75
    elif metrics.word_count >= min_words - 20:
        content += 0.5
    if prompt_type == "email" and email_signals is not None:
        if email_signals["purpose"]:
            content += 0.9
        detail_hits = int(email_signals["detail_hits"])
        if detail_hits >= 5:
            content += 1.0
        elif detail_hits >= 3:
            content += 0.7
        elif detail_hits >= 1:
            content += 0.35
        if email_signals["second_move"]:
            content += 0.35
        if int(email_signals["politeness_hits"]) >= 2:
            content += 0.25
    else:
        if metrics.position_hits >= 1:
            content += 0.75
        if metrics.evidence_hits >= 4:
            content += 1.25
        elif metrics.evidence_hits >= 2:
            content += 0.75
        elif metrics.evidence_hits >= 1:
            content += 0.25
    if metrics.word_count > max_words + 40:
        content -= 0.25

    # ── Coherence (일관성 / 연속성 / 통일성) ─────────────────────────────────
    coherence = 2.0
    flow_hits = metrics.transition_hits
    if prompt_type == "email" and email_signals is not None:
        flow_hits = max(flow_hits, int(email_signals["sequence_hits"]))
    if flow_hits >= 5:
        coherence += 1.5
    elif flow_hits >= 2:
        coherence += 0.75
    if metrics.lexical_diversity >= 0.5:
        coherence += 0.75
    elif metrics.lexical_diversity >= 0.4:
        coherence += 0.25
    if metrics.paragraph_count >= 3:
        coherence += 0.5
    if metrics.position_hits >= 1:
        coherence += 0.25
    coherence += 0.25 * variety
    if prompt_type == "email" and email_signals is not None:
        if email_signals["purpose"]:
            coherence += 0.25
        if int(email_signals["politeness_hits"]) >= 3:
            coherence += 0.25
        if int(email_signals["detail_sentences"]) >= 4:
            coherence += 0.5

    # ── Example (세부 설명 / 예시) ────────────────────────────────────────────
    example = 1.5
    if prompt_type == "email" and email_signals is not None:
        detail_hits = int(email_signals["detail_hits"])
        detail_sentences = int(email_signals["detail_sentences"])
        if detail_hits >= 6 or detail_sentences >= 6:
            example += 2.0
        elif detail_hits >= 3 or detail_sentences >= 4:
            example += 1.4
        elif detail_hits >= 1 or detail_sentences >= 2:
            example += 0.7
    else:
        if metrics.evidence_hits >= 5:
            example += 2.25
        elif metrics.evidence_hits >= 3:
            example += 1.5
        elif metrics.evidence_hits >= 1:
            example += 0.75
    if metrics.sentence_count >= 8:
        example += 0.75
    elif metrics.sentence_count >= 6:
        example += 0.55
    elif metrics.sentence_count >= 5:
        example += 0.4
    if metrics.avg_sentence_length >= 12:
        example += 0.5
    if prompt_type == "email" and email_signals is not None and int(email_signals["detail_hits"]) >= 3 and flow_hits >= 2:
        example += 0.25
    elif metrics.evidence_hits >= 2 and metrics.transition_hits >= 3:
        example += 0.25

    # ── Grammar (문장 구성) ───────────────────────────────────────────────────
    grammar = 2.0
    if 10 <= metrics.avg_sentence_length <= 28:
        grammar += 1.0
    if metrics.long_sentence_ratio <= 0.1:
        grammar += 1.25
    elif metrics.long_sentence_ratio <= 0.2:
        grammar += 0.75
    elif metrics.long_sentence_ratio <= 0.3:
        grammar += 0.25
    if metrics.short_sentence_ratio <= 0.15:
        grammar += 0.75
    elif metrics.short_sentence_ratio <= 0.25:
        grammar += 0.25
    if grammar_risk >= 10:
        grammar -= 2.25
    elif grammar_risk >= 7:
        grammar -= 1.75
    elif grammar_risk >= 4:
        grammar -= 1.1
    elif grammar_risk >= 2:
        grammar -= 0.6
    if grammar_profile.severe_breakdown:
        grammar -= 0.75
    if grammar_risk >= 10:
        grammar = min(grammar, 2.75)
    elif grammar_risk >= 7:
        grammar = min(grammar, 3.0)
    elif grammar_risk >= 5:
        grammar = min(grammar, 3.5)

    # ── Vocabulary (어휘 / 관용어구) ──────────────────────────────────────────
    vocabulary = 2.0
    if metrics.lexical_diversity >= 0.55:
        vocabulary += 1.5
    elif metrics.lexical_diversity >= 0.45:
        vocabulary += 0.75
    elif metrics.lexical_diversity >= 0.35:
        vocabulary += 0.25
    if metrics.transition_hits >= 5:
        vocabulary += 1.0
    elif metrics.transition_hits >= 3:
        vocabulary += 0.5
    elif metrics.transition_hits >= 1:
        vocabulary += 0.25
    if metrics.word_count >= 150:
        vocabulary += 0.5
    if prompt_type == "email" and email_signals is not None:
        if int(email_signals["politeness_hits"]) >= 3:
            vocabulary += 0.5
        if email_signals["purpose"]:
            vocabulary += 0.25
    vocabulary -= repetition_penalty

    dimensions = [
        ScoreDimension(
            name="Structure",
            score=_round_quarter(structure),
            reason="짜임새 있는 구성 — 형식적 요소(이메일 인사말/맺음말), 단락 구조, 논리적 흐름",
        ),
        ScoreDimension(
            name="Content",
            score=_round_quarter(content),
            reason="질문에 맞는 내용 — 의사소통 목적 달성, 충분한 구체적 내용, 프롬프트 적합성",
        ),
        ScoreDimension(
            name="Coherence",
            score=_round_quarter(coherence),
            reason="일관성·연속성·통일성 — 연결어 사용, 단락 간 흐름, 어휘 일관성",
        ),
        ScoreDimension(
            name="Example",
            score=_round_quarter(example),
            reason="세부 설명과 예시 — 근거·예시의 밀도, 설명의 구체성 및 깊이",
        ),
        ScoreDimension(
            name="Grammar",
            score=_round_quarter(grammar),
            reason="문장 구성 — 문법적 정확성, 문장 구조 다양성, 런온/단문 오류 제어",
        ),
        ScoreDimension(
            name="Vocabulary",
            score=_round_quarter(vocabulary),
            reason="어휘·관용어구 — 어휘 다양성, 관용 표현 정확성, 적절한 어휘 형태",
        ),
    ]

    weighted_sum = 0.0
    weight_total = 0.0
    for d in dimensions:
        weight = 2.4 if d.name == "Grammar" else 1.0
        weighted_sum += d.score * weight
        weight_total += weight
    # 전역 캘리브레이션: 문법 오탐 제거(grammar 2.0) 이후 기준을 재조정했다.
    # 기존 1.35 는 오탐 노이즈를 상쇄하려던 값 — 유지하면 정상 답안이 과소평가된다.
    strict_penalty = 0.55
    if grammar_risk >= 10:
        strict_penalty += 0.6
    elif grammar_risk >= 6:
        strict_penalty += 0.45
    elif grammar_risk >= 3:
        strict_penalty += 0.25
    if metrics.word_count < min_words:
        strict_penalty += 0.35
    if metrics.paragraph_count <= 1:
        strict_penalty += 0.35
    if prompt_type != "email" and metrics.evidence_hits == 0:
        strict_penalty += 0.2

    if prompt_type == "email" and email_signals is not None:
        if not email_signals["purpose"]:
            strict_penalty += 0.25
        if int(email_signals["detail_hits"]) == 0:
            strict_penalty += 0.2

    calibration_adjustment = 0.0
    calibration_reason = ""
    neutral_padding_risk = bool(
        re.search(r"\b(lorem|filler|placeholder|neutral padding|padding)\b", essay_text, re.I)
    )
    if (
        min_words <= metrics.word_count <= max_words
        and grammar_risk <= 2
        and metrics.lexical_diversity >= 0.48
        and repetition_penalty == 0
        and not neutral_padding_risk
    ):
        if prompt_type == "email" and email_signals is not None:
            core_moves = sum(bool(email_signals[key]) for key in ("greeting", "closing", "purpose", "second_move"))
            if core_moves >= 3 and (int(email_signals["detail_hits"]) >= 3 or int(email_signals["detail_sentences"]) >= 4) and int(email_signals["politeness_hits"]) >= 2:
                calibration_adjustment = 0.35
                calibration_reason = "상위권 이메일의 목적·구체성·정중성·형식이 함께 충족되어 코퍼스 보정을 적용했습니다."
        elif metrics.position_hits >= 1 and metrics.evidence_hits >= 2 and metrics.transition_hits >= 2:
            calibration_adjustment = 0.35
            calibration_reason = "상위권 토론 답안의 입장·근거·연결 조건이 함께 충족되어 코퍼스 보정을 적용했습니다."

    pre_round_raw_score = (weighted_sum / weight_total) - strict_penalty - (0.1 if repetition_penalty >= 0.5 else 0.0) + calibration_adjustment
    pre_round_raw_score = max(0.0, min(5.0, pre_round_raw_score))
    total = _round_half(pre_round_raw_score)

    # Repeated grammar errors or broken sentence form make >4.5 band difficult.
    # (4.5 band corresponds to 3.5 on the 0-5 internal scale.)
    cap = grammar_cap_status(essay_text)
    cap_applied = bool(cap["applied"])
    if cap_applied:
        total = min(total, float(cap["ceiling_0_5"]))

    # 0.5 단위 경계까지의 거리 — 0에 가까울수록 사소한 입력 변화로 표시 점수가
    # 쉽게 넘어갈 수 있는 "절벽 근처" 상태임을 뜻한다.
    lower_boundary = round(pre_round_raw_score * 2) / 2
    distance_to_rounding_boundary = round(abs(pre_round_raw_score - lower_boundary), 4)

    return ScoringBreakdown(
        dimensions=dimensions,
        total_0_5=total,
        pre_round_raw_score=round(pre_round_raw_score, 4),
        distance_to_rounding_boundary=distance_to_rounding_boundary,
        component_scores={d.name: d.score for d in dimensions},
        scoring_formula_version=SCORING_FORMULA_VERSION,
        grammar_cap_applied=cap_applied,
        grammar_cap_ceiling=float(cap["ceiling_0_5"]) if cap_applied else None,
        calibration_adjustment=calibration_adjustment,
        calibration_reason=calibration_reason,
    )
