from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

from app.models import PromptType, ScoreDimension

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
    "i think",
    "in my view",
    "from my perspective",
    "my position",
    "i agree",
    "i disagree",
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


def _grammar_risk_count(essay_text: str) -> int:
    lowered = essay_text.lower()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]

    run_on = sum(len(re.findall(r"[A-Za-z']+", s)) > 32 for s in sentences)
    comma_splice = sum(bool(re.search(r",\s+(i|we|they|he|she|it)\s+\w+", s.lower())) for s in sentences)
    article = len(re.findall(r"\b(a|an)\s+[aeiou]\w+", lowered))
    article += len(re.findall(r"\b(an)\s+[^aeiou\W]\w+", lowered))
    article += len(re.findall(r"\b(a|an)\s+(information|advice|research|evidence)\b", lowered))
    preposition = len(re.findall(r"\bdiscuss about\b|\bmention about\b", lowered))
    preposition += len(re.findall(r"\bin nowadays\b|\bmarried with\b|\bdepend of\b|\binterested on\b", lowered))
    tense = len(re.findall(r"\byesterday\b.*\b(is|are)\b", lowered))
    tense += len(re.findall(r"\b(last year|last week|in \d{4})\b[^.?!]{0,40}\b(is|are|has)\b", lowered))
    tense += len(re.findall(r"\b(i|we|they)\s+was\b|\b(he|she|it)\s+were\b", lowered))
    subject_verb = len(re.findall(r"\b(people|students|they)\s+is\b", lowered))
    subject_verb += len(re.findall(r"\b(he|she|it)\s+(go|have|do)\b", lowered))
    subject_verb += len(re.findall(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lowered))
    subject_verb += len(re.findall(r"\bone of\s+the\s+\w+\s+are\b", lowered))
    subject_verb += len(re.findall(r"\b(people|children)\s+has\b", lowered))
    punctuation = sum(1 for s in sentences if not re.search(r"[.!?]$", s))
    punctuation += len(re.findall(r"\s,{2,}|\.{2,}(?!\.)", essay_text))
    punctuation += len(re.findall(r"[a-zA-Z][.!?][A-Za-z]", essay_text))
    style = len(re.findall(r"\b(could|should|would)\s+of\b", lowered))
    style += len(re.findall(r"\bmore\s+better\b|\bmore\s+worse\b", lowered))
    fragment_like = 0
    for s in sentences:
        tokens = re.findall(r"[A-Za-z']+", s)
        if len(tokens) < 5:
            continue
        has_verb = any(
            re.fullmatch(r"(is|are|was|were|be|been|being|have|has|had|do|does|did|can|could|should|would|will|might|may|must)", t.lower())
            or t.lower().endswith(("ed", "ing", "s"))
            for t in tokens
        )
        if not has_verb:
            fragment_like += 1

    return run_on + comma_splice + article + preposition + tense + subject_verb + punctuation + fragment_like + style


def _grammar_risk_profile(essay_text: str) -> dict[str, int | bool]:
    lowered = essay_text.lower()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]

    run_on = sum(len(re.findall(r"[A-Za-z']+", s)) > 32 for s in sentences)
    comma_splice = sum(bool(re.search(r",\s+(i|we|they|he|she|it)\s+\w+", s.lower())) for s in sentences)
    article = len(re.findall(r"\b(a|an)\s+[aeiou]\w+", lowered))
    article += len(re.findall(r"\b(an)\s+[^aeiou\W]\w+", lowered))
    article += len(re.findall(r"\b(a|an)\s+(information|advice|research|evidence)\b", lowered))
    preposition = len(re.findall(r"\bdiscuss about\b|\bmention about\b", lowered))
    preposition += len(re.findall(r"\bin nowadays\b|\bmarried with\b|\bdepend of\b|\binterested on\b", lowered))
    tense = len(re.findall(r"\byesterday\b.*\b(is|are)\b", lowered))
    tense += len(re.findall(r"\b(last year|last week|in \d{4})\b[^.?!]{0,40}\b(is|are|has)\b", lowered))
    tense += len(re.findall(r"\b(i|we|they)\s+was\b|\b(he|she|it)\s+were\b", lowered))
    subject_verb = len(re.findall(r"\b(people|students|they)\s+is\b", lowered))
    subject_verb += len(re.findall(r"\b(he|she|it)\s+(go|have|do)\b", lowered))
    subject_verb += len(re.findall(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lowered))
    subject_verb += len(re.findall(r"\bone of\s+the\s+\w+\s+are\b", lowered))
    subject_verb += len(re.findall(r"\b(people|children)\s+has\b", lowered))
    punctuation = sum(1 for s in sentences if not re.search(r"[.!?]$", s))
    punctuation += len(re.findall(r"\s,{2,}|\.{2,}(?!\.)", essay_text))
    punctuation += len(re.findall(r"[a-zA-Z][.!?][A-Za-z]", essay_text))
    style = len(re.findall(r"\b(could|should|would)\s+of\b", lowered))
    style += len(re.findall(r"\bmore\s+better\b|\bmore\s+worse\b", lowered))
    fragment_like = 0
    for s in sentences:
        tokens = re.findall(r"[A-Za-z']+", s)
        if len(tokens) < 5:
            continue
        has_verb = any(
            re.fullmatch(r"(is|are|was|were|be|been|being|have|has|had|do|does|did|can|could|should|would|will|might|may|must)", t.lower())
            or t.lower().endswith(("ed", "ing", "s"))
            for t in tokens
        )
        if not has_verb:
            fragment_like += 1

    total = run_on + comma_splice + article + preposition + tense + subject_verb + punctuation + fragment_like + style
    repeated_error = total >= 6 or max(run_on + comma_splice, article, preposition, tense, subject_verb, punctuation, fragment_like) >= 3
    severe_breakdown = (run_on + comma_splice) >= 3 or fragment_like >= 2 or punctuation >= 3 or total >= 10
    return {
        "total": total,
        "repeated_error": repeated_error,
        "severe_breakdown": severe_breakdown,
    }


def grammar_cap_status(essay_text: str) -> dict[str, float | bool | str]:
    profile = _grammar_risk_profile(essay_text)
    if bool(profile["severe_breakdown"]):
        return {
            "applied": True,
            "ceiling_0_5": 3.0,
            "reason": "문장 형식 파괴/중대한 문법 붕괴가 감지되어 고득점 상한이 적용되었습니다.",
        }
    if bool(profile["repeated_error"]):
        return {
            "applied": True,
            "ceiling_0_5": 3.5,
            "reason": "반복적인 문법 오류가 감지되어 4.5+ 달성이 어렵습니다.",
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


def score_essay(essay_text: str, prompt_type: PromptType) -> tuple[list[ScoreDimension], float]:
    metrics = analyze_essay(essay_text)
    grammar_profile = _grammar_risk_profile(essay_text)
    grammar_risk = int(grammar_profile["total"])
    min_words, max_words = _target_word_window(prompt_type)
    sentence_lengths = [len(re.findall(r"[A-Za-z']+", s)) for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    variety = _sentence_variety_score(sentence_lengths)
    repetition_penalty = _repetition_penalty(essay_text)

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
    if min_words <= metrics.word_count <= max_words:
        content += 1.0
    elif metrics.word_count >= min_words - 20:
        content += 0.5
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
    if metrics.transition_hits >= 5:
        coherence += 1.5
    elif metrics.transition_hits >= 2:
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

    # ── Example (세부 설명 / 예시) ────────────────────────────────────────────
    example = 1.5
    if metrics.evidence_hits >= 5:
        example += 2.25
    elif metrics.evidence_hits >= 3:
        example += 1.5
    elif metrics.evidence_hits >= 1:
        example += 0.75
    if metrics.sentence_count >= 8:
        example += 0.75
    elif metrics.sentence_count >= 5:
        example += 0.4
    if metrics.avg_sentence_length >= 12:
        example += 0.5
    if metrics.evidence_hits >= 2 and metrics.transition_hits >= 3:
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
    if grammar_risk >= 8:
        grammar -= 1.75
    elif grammar_risk >= 5:
        grammar -= 1.25
    elif grammar_risk >= 3:
        grammar -= 0.75
    if bool(grammar_profile.get("severe_breakdown")):
        grammar -= 0.5

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
    # Be intentionally conservative: default tendency is about -0.5 on 0-5 scale.
    strict_penalty = 0.5
    if grammar_risk >= 10:
        strict_penalty += 0.25
    elif grammar_risk >= 6:
        strict_penalty += 0.15
    if metrics.word_count < min_words:
        strict_penalty += 0.1

    total = _round_half((weighted_sum / weight_total) - strict_penalty - (0.1 if repetition_penalty >= 0.5 else 0.0))

    # Repeated grammar errors or broken sentence form make >4.5 band difficult.
    # (4.5 band corresponds to 3.5 on the 0-5 internal scale.)
    cap = grammar_cap_status(essay_text)
    if bool(cap["applied"]):
        total = min(total, float(cap["ceiling_0_5"]))

    return dimensions, total
