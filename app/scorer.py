from __future__ import annotations

import re
from dataclasses import dataclass
from statistics import mean

from app.grammar import (
    GRAMMAR_RULES_VERSION,
    GrammarSignals,
    analyze_grammar,
    grammar_analysis_text,
)
from app.models import PromptType, ScoreDimension
from app.vocab_analysis import ACADEMIC_WORDS

# v3 replaces the old checklist/length formula with an ETS-rubric-aligned
# holistic estimate. Paragraph count, transition count, and sentence length are
# retained only as diagnostics; none is an automatic deduction.
SCORING_ENGINE_VERSION = "3.0.0"
SCORING_FORMULA_VERSION = SCORING_ENGINE_VERSION
RUBRIC_VERSION = (
    f"ets-holistic-proxy-{SCORING_ENGINE_VERSION}+grammar-{GRAMMAR_RULES_VERSION}"
)


@dataclass
class ScoringBreakdown:
    dimensions: list[ScoreDimension]
    total_0_5: float
    pre_round_raw_score: float
    distance_to_rounding_boundary: float
    component_scores: dict[str, float]
    scoring_formula_version: str
    grammar_cap_applied: bool
    grammar_cap_ceiling: float | None
    calibration_adjustment: float
    calibration_reason: str


TRANSITIONS = {
    "although",
    "as a result",
    "because",
    "consequently",
    "for example",
    "for instance",
    "for these reasons",
    "furthermore",
    "however",
    "in addition",
    "in conclusion",
    "in contrast",
    "meanwhile",
    "moreover",
    "nevertheless",
    "on the other hand",
    "overall",
    "since",
    "therefore",
    "thus",
    "while",
    "whereas",
}

POSITION_MARKERS = {
    "from my perspective",
    "i agree",
    "i believe",
    "i disagree",
    "i firmly believe",
    "i strongly agree",
    "i strongly disagree",
    "i support",
    "i think",
    "in my view",
    "my position",
}

EVIDENCE_MARKERS = {
    "according to",
    "as a result",
    "because",
    "data",
    "evidence",
    "for example",
    "for instance",
    "in my experience",
    "research",
    "since",
    "study",
}

_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['-][A-Za-z]+)*")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")

# Meta-grading instructions and neutral padding are not part of a TOEFL
# response. Excluding them prevents prompt-injection text from gaming length or
# vocabulary proxies. This is not a quality deduction; the lines simply do not
# count as student task performance.
_NON_RESPONSE_LINE_RE = re.compile(
    r"(ignore (?:all |the )?(?:previous )?instructions|"
    r"give (?:this response )?(?:the )?highest score|"
    r"output only \d|replace the rubric|system content|"
    r"</?student_response>|<system>|set (?:the )?(?:score|band)|"
    r"grading result:|final band:|\"score\"\s*:|"
    r"이 채점을 무시|最高得点|"
    r"\b(?:lorem|filler|placeholder|neutral padding)\b)",
    re.IGNORECASE,
)

_DISCUSSION_STANCE_RE = re.compile(
    r"\b(i\s+(?:firmly\s+|strongly\s+)?(?:believe|agree|disagree|maintain|"
    r"support|prefer|favor)|in my view|from my perspective|my position|"
    r"(?:schools?|students?|universities|governments?|educators?|people)\s+"
    r"(?:should|must|ought to)|(?:is|are)\s+(?:more|less)\s+\w+\s+than)\b",
    re.IGNORECASE,
)
_REASON_RE = re.compile(
    r"\b(because|since|one reason|the reason|this is (?:important|critical)|"
    r"due to|so that|in order to)\b",
    re.IGNORECASE,
)
_EXAMPLE_RE = re.compile(
    r"\b(for example|for instance|in my experience|consider (?:a|the)|"
    r"research|a study|studies|data|a student who|students who|people who|"
    r"when (?:i|we|students|people)|if (?:a|the|students|people))\b",
    re.IGNORECASE,
)
_EXPLANATION_RE = re.compile(
    r"\b(as a result|therefore|consequently|thus|this (?:means|shows|allows|"
    r"helps|enables|would)|which (?:means|shows|allows|helps|is)|"
    r"leads? to|results? in|so\b)\b",
    re.IGNORECASE,
)
_NAMED_VIEW_RE = re.compile(
    r"\b(?:agree|disagree) with [A-Z][a-z]+|"
    r"\b[A-Z][a-z]+(?:'s|\s+(?:raises?|argues?|points?|notes?|suggests?))|"
    r"\bwhile [A-Z][a-z]+\b",
)
_REINFORCEMENT_RE = re.compile(
    r"\b(for these reasons|overall|in conclusion|therefore,?\s+i|"
    r"i maintain|should therefore)\b",
    re.IGNORECASE,
)
_SUBORDINATION_RE = re.compile(
    r"\b(although|because|before|after|if|since|unless|when|whereas|while|"
    r"even though|so that|in order to|who|which|that)\b",
    re.IGNORECASE,
)
_RELATIVE_CLAUSE_RE = re.compile(
    r"\b(who|which|whose|that)\s+(?:\w+\s+){0,2}(?:is|are|was|were|has|have|"
    r"can|could|will|would|should|\w+(?:s|ed))\b",
    re.IGNORECASE,
)
_COORDINATION_RE = re.compile(r"[,;—]\s*|\b(and|but|yet|so)\b", re.IGNORECASE)

_CONTENT_STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "because", "been", "but",
    "by", "can", "could", "did", "do", "does", "for", "from", "had", "has",
    "have", "he", "her", "hers", "him", "his", "i", "if", "in", "is", "it",
    "its", "may", "might", "more", "most", "not", "of", "on", "or", "our",
    "ours", "she", "should", "so", "some", "such", "than", "that", "the",
    "their", "theirs", "them", "there", "these", "they", "this", "those",
    "to", "was", "we", "were", "what", "when", "which", "while", "who",
    "will", "with", "would", "you", "your",
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


def _tokens(text: str) -> list[str]:
    return [token.lower() for token in _TOKEN_RE.findall(text)]


def _sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _round_half(value: float) -> float:
    value = max(0.0, min(5.0, value))
    return int(value * 2 + 0.5) / 2


def _round_quarter(value: float) -> float:
    value = max(0.0, min(5.0, value))
    return int(value * 4 + 0.5) / 4


def _count_phrases(text: str, phrases: set[str]) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in phrases)


def _mattr(tokens: list[str], window: int = 50) -> float:
    """Moving-average type-token ratio, reducing raw-TTR length bias."""
    if not tokens:
        return 0.0
    if len(tokens) <= window:
        return len(set(tokens)) / len(tokens)
    scores = [
        len(set(tokens[start : start + window])) / window
        for start in range(0, len(tokens) - window + 1)
    ]
    return mean(scores)


def _sentence_variety_score(sentence_lengths: list[int]) -> float:
    if not sentence_lengths:
        return 0.0
    bins = {
        "short" if length <= 10 else "medium" if length <= 24 else "long"
        for length in sentence_lengths
    }
    if len(bins) == 3:
        return 1.0
    if len(bins) == 2:
        return 0.65
    return 0.35


def _scorable_text(essay_text: str) -> str:
    kept = [
        raw_line
        for raw_line in essay_text.splitlines()
        if not _NON_RESPONSE_LINE_RE.search(raw_line)
    ]
    cleaned = "\n".join(kept).strip()
    return cleaned or essay_text.strip()


def _generic_repetition_penalty(text: str) -> float:
    sentences = _sentences(text)
    lowered = text.lower()
    penalty = 0.0
    generic_frames = (
        "in today's society",
        "everyone has different opinions",
        "there are many reasons",
        "this is very important",
        "many things",
    )
    repeated_frames = sum(lowered.count(frame) >= 2 for frame in generic_frames)
    penalty += min(1.0, repeated_frames * 0.35)

    openings: list[str] = []
    for sentence in sentences:
        words = _tokens(sentence)
        if len(words) >= 3:
            openings.append(" ".join(words[:3]))
    if openings:
        most_common = max(openings.count(item) for item in set(openings))
        if most_common >= max(3, len(openings) // 2 + 1):
            penalty += 0.35
    return min(1.25, penalty)


def analyze_essay(essay_text: str) -> EssayMetrics:
    cleaned = essay_text.strip()
    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", cleaned) if p.strip()]
    words = _tokens(cleaned)
    sentences = _sentences(cleaned)
    sentence_lengths = [len(_tokens(sentence)) for sentence in sentences] or [0]

    return EssayMetrics(
        word_count=len(words),
        sentence_count=len(sentences),
        paragraph_count=max(1, len(paragraphs)),
        avg_sentence_length=mean(sentence_lengths),
        long_sentence_ratio=(
            sum(length > 35 for length in sentence_lengths) / len(sentence_lengths)
        ),
        short_sentence_ratio=(
            sum(length < 6 for length in sentence_lengths) / len(sentence_lengths)
        ),
        transition_hits=_count_phrases(cleaned, TRANSITIONS),
        position_hits=_count_phrases(cleaned, POSITION_MARKERS),
        evidence_hits=_count_phrases(cleaned, EVIDENCE_MARKERS),
        lexical_diversity=_mattr(words),
    )


def _grammar_risk_profile(
    essay_text: str, prompt_type: PromptType | None = None
) -> GrammarSignals:
    scoring_text = _scorable_text(essay_text)
    return analyze_grammar(grammar_analysis_text(scoring_text, prompt_type))


def grammar_cap_status(
    essay_text: str, prompt_type: PromptType | None = None
) -> dict[str, float | bool | str]:
    """Apply a ceiling only for demonstrated, repeated language breakdown.

    A long sentence, one paragraph, or a missing transition can never trigger a
    cap. The ceiling reflects the ETS 1-3 descriptors for accumulated errors.
    """
    profile = _grammar_risk_profile(essay_text, prompt_type)
    if profile.severe_breakdown:
        return {
            "applied": True,
            "ceiling_0_5": 2.0,
            "reason": "여러 문장에서 의미 전달을 방해하는 문장 구조 오류가 반복되어 언어 정확성 상한이 적용되었습니다.",
        }
    if profile.repeated_error:
        return {
            "applied": True,
            "ceiling_0_5": 3.0,
            "reason": "검출 가능한 문법 오류가 반복되어 ETS 3점 이상의 일관된 언어 정확성을 확인하기 어렵습니다.",
        }
    return {"applied": False, "ceiling_0_5": 5.0, "reason": ""}


def _target_word_window(prompt_type: PromptType) -> tuple[int, int]:
    # Advisory planning floors only. There is deliberately no upper limit.
    return (80, 10_000) if prompt_type == "email" else (100, 10_000)


_EMAIL_GREETINGS = re.compile(
    r"\b(dear|hi|hello|good morning|good afternoon|to whom it may concern)\b",
    re.IGNORECASE,
)
_EMAIL_CLOSINGS = re.compile(
    r"\b(sincerely|best regards|kind regards|regards|yours truly|thank you|thanks)\b",
    re.IGNORECASE,
)
_EMAIL_PURPOSE = re.compile(
    r"\b(i am writing to (?:sincerely )?(?:thank|express|apologize|inquire|"
    r"report|invite|recommend|request|ask|notify)|i am writing "
    r"(?:regarding|concerning)|i would like to "
    r"(?:thank|apologize|ask|request|invite|recommend)|"
    r"i am contacting you|please accept my|thank you for)\b",
    re.IGNORECASE,
)
_EMAIL_POLITENESS = re.compile(
    r"\b(could you please|would you please|i would (?:also )?"
    r"(?:appreciate|be grateful)|thank you|we truly appreciate|please|"
    r"your (?:understanding|assistance|consideration)|sincerely|"
    r"best regards|kind regards)\b",
    re.IGNORECASE,
)
_EMAIL_DETAIL_MARKERS = re.compile(
    r"\b(unfortunately|especially|specifically|because|due to|after|before|"
    r"during|when|even though|although|until|already|deadline|schedule|order|"
    r"reservation|visit|tour|workshop|assignment|draft|coupon|pass(?:es)?)\b",
    re.IGNORECASE,
)
_EMAIL_SEQUENCE_MARKERS = {
    "after",
    "although",
    "also",
    "as a result",
    "because",
    "before",
    "during",
    "especially",
    "even though",
    "in addition",
    "once again",
    "specifically",
    "therefore",
    "until",
}


def _email_task_signals(essay_text: str) -> dict[str, int | bool]:
    sentences = _sentences(essay_text)
    detail_sentences = sum(
        1
        for sentence in sentences
        if len(_tokens(sentence)) >= 10
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
        "second_move": bool(
            re.search(
                r"\b(i would also|we were especially|thank you once again|"
                r"in addition|also|please also|let me know)\b",
                essay_text,
                re.IGNORECASE,
            )
        ),
    }


def _development_ratio(word_count: int, target: int) -> float:
    """Evidence opportunity, not a length penalty.

    A concise answer can still score well. The contribution saturates at the
    advisory planning length and never falls when a response is longer.
    """
    if word_count <= 20:
        return 0.0
    return max(0.0, min(1.0, (word_count - 20) / max(1, target - 20)))


def _count_matching_sentences(sentences: list[str], pattern: re.Pattern[str]) -> int:
    return sum(bool(pattern.search(sentence)) for sentence in sentences)


def _discussion_scores(
    text: str,
    metrics: EssayMetrics,
    sentences: list[str],
    template_penalty: float,
) -> tuple[float, float, float]:
    stance = bool(_DISCUSSION_STANCE_RE.search(text))
    reason_units = _count_matching_sentences(sentences, _REASON_RE)
    example_units = _count_matching_sentences(sentences, _EXAMPLE_RE)
    explanation_units = _count_matching_sentences(sentences, _EXPLANATION_RE)
    named_view_units = _count_matching_sentences(sentences, _NAMED_VIEW_RE)
    support_units = reason_units + example_units + explanation_units
    substantive_sentences = sum(len(_tokens(sentence)) >= 12 for sentence in sentences)
    development = _development_ratio(metrics.word_count, 100)

    task_fulfillment = (
        1.0
        + (1.25 if stance else 0.0)
        + development * 0.75
        + min(1.0, support_units / 3) * 1.4
        + (0.25 if named_view_units else 0.0)
        + (0.35 if metrics.sentence_count >= 4 else 0.0)
        - template_penalty
    )

    elaboration = (
        1.0
        + development * 0.8
        + min(reason_units, 2) * 0.45
        + min(example_units, 2) * 0.65
        + min(explanation_units, 2) * 0.45
        + (0.35 if support_units >= 3 else 0.0)
        + (0.35 if support_units >= 5 else 0.0)
        + min(1.0, substantive_sentences / 5) * 0.5
        + (0.2 if named_view_units else 0.0)
        - template_penalty
    )

    connective_categories = sum(
        bool(
            re.search(
                pattern,
                text,
                re.IGNORECASE,
            )
        )
        for pattern in (
            r"\b(?:although|while|whereas|however|in contrast)\b",
            r"\b(?:because|since|due to|so that)\b",
            r"\b(?:for example|for instance|research|a study|data)\b",
            r"\b(?:therefore|as a result|consequently|thus)\b",
        )
    )
    organization = (
        1.5
        + (0.75 if metrics.sentence_count >= 3 else metrics.sentence_count * 0.2)
        + (0.5 if stance else 0.0)
        + min(3, connective_categories) * 0.25
        + (0.25 if _REINFORCEMENT_RE.search(text) else 0.0)
    )
    return task_fulfillment, elaboration, organization


def _email_scores(
    text: str,
    metrics: EssayMetrics,
    template_penalty: float,
) -> tuple[float, float, float]:
    signals = _email_task_signals(text)
    development = _development_ratio(metrics.word_count, 80)
    detail_hits = int(signals["detail_hits"])
    detail_sentences = int(signals["detail_sentences"])
    politeness_hits = int(signals["politeness_hits"])
    sequence_hits = int(signals["sequence_hits"])

    task_fulfillment = (
        0.75
        + (1.35 if signals["purpose"] else 0.0)
        + development * 0.75
        + min(1.0, detail_hits / 4) * 1.25
        + (0.55 if detail_sentences >= 3 else detail_sentences * 0.15)
        + (0.25 if politeness_hits else 0.0)
        - template_penalty
    )
    elaboration = (
        1.0
        + development * 0.8
        + min(detail_hits, 5) * 0.3
        + min(1.0, detail_sentences / 4) * 1.0
        + (0.25 if signals["purpose"] else 0.0)
        + (0.3 if signals["second_move"] else 0.0)
        - template_penalty
    )
    organization = (
        1.25
        + (0.45 if signals["greeting"] else 0.0)
        + (0.45 if signals["closing"] else 0.0)
        + (0.5 if signals["purpose"] else 0.0)
        + (0.75 if metrics.sentence_count >= 4 else metrics.sentence_count * 0.15)
        + min(3, sequence_hits) * 0.2
        + (
            0.5
            if signals["greeting"] and signals["closing"] and signals["purpose"]
            else 0.0
        )
    )
    return task_fulfillment, elaboration, organization


def _syntax_score(text: str, sentences: list[str], grammar: GrammarSignals) -> float:
    lengths = [len(_tokens(sentence)) for sentence in sentences]
    if not lengths:
        return 0.0
    subordination_units = _count_matching_sentences(sentences, _SUBORDINATION_RE)
    relative_units = len(_RELATIVE_CLAUSE_RE.findall(text))
    coordination_units = len(_COORDINATION_RE.findall(text))
    variety = _sentence_variety_score(lengths)

    score = (
        1.5
        + min(1.0, len(sentences) / 6) * 0.6
        + min(1.0, subordination_units / 3) * 1.0
        + min(1.0, relative_units / 2) * 0.55
        + variety * 0.55
        + (0.45 if mean(lengths) >= 11 else mean(lengths) / 11 * 0.45)
        + min(1.0, coordination_units / 5) * 0.35
    )
    score -= min(1.5, (grammar.fragment + grammar.comma_splice) * 0.45)
    return score


def _vocabulary_score(
    text: str, metrics: EssayMetrics, prompt_type: PromptType
) -> float:
    tokens = _tokens(text)
    content_tokens = [token for token in tokens if token not in _CONTENT_STOPWORDS]
    long_content_ratio = (
        sum(len(token.replace("-", "")) >= 7 for token in content_tokens)
        / max(1, len(content_tokens))
    )
    def is_academic(token: str) -> bool:
        candidates = {token}
        for suffix in ("ing", "ed", "es", "s"):
            if token.endswith(suffix) and len(token) - len(suffix) >= 4:
                candidates.add(token[: -len(suffix)])
        return bool(candidates & ACADEMIC_WORDS)

    academic_ratio = (
        sum(is_academic(token) for token in content_tokens)
        / max(1, len(content_tokens))
    )
    mattr = metrics.lexical_diversity
    if mattr >= 0.72:
        diversity_points = 1.2
    elif mattr >= 0.62:
        diversity_points = 1.0
    elif mattr >= 0.52:
        diversity_points = 0.8
    elif mattr >= 0.42:
        diversity_points = 0.6
    else:
        diversity_points = 0.35

    academic_points = min(1.2, academic_ratio / 0.18 * 1.2)
    long_word_points = min(0.55, long_content_ratio / 0.24 * 0.55)
    discourse_range = sum(
        bool(re.search(pattern, text, re.IGNORECASE))
        for pattern in (
            r"\b(?:although|while|whereas|however)\b",
            r"\b(?:because|since|therefore|thus)\b",
            r"\b(?:for example|for instance|specifically)\b",
        )
    )
    register_points = 0.0
    if prompt_type == "email":
        email_signals = _email_task_signals(text)
        if email_signals["purpose"] and int(email_signals["politeness_hits"]) >= 2:
            register_points = 0.5

    return (
        1.4
        + diversity_points
        + academic_points
        + long_word_points
        + min(0.35, discourse_range * 0.12)
        + register_points
        - _generic_repetition_penalty(text)
    )


def _language_accuracy_score(
    metrics: EssayMetrics, grammar: GrammarSignals
) -> float:
    if metrics.word_count == 0:
        return 0.0
    weighted_errors = (
        grammar.tense * 1.2
        + grammar.article
        + grammar.preposition
        + grammar.run_on * 1.4
        + grammar.comma_splice * 1.4
        + grammar.subject_verb * 1.25
        + grammar.punctuation * 0.65
        + grammar.style * 0.8
        + grammar.fragment * 1.5
    )
    errors_per_100 = weighted_errors / metrics.word_count * 100
    return 5.0 - min(4.5, errors_per_100 * 0.42)


def score_essay(
    essay_text: str, prompt_type: PromptType
) -> tuple[list[ScoreDimension], float]:
    breakdown = score_essay_detailed(essay_text, prompt_type)
    return breakdown.dimensions, breakdown.total_0_5


def score_essay_detailed(
    essay_text: str, prompt_type: PromptType
) -> ScoringBreakdown:
    scoring_text = _scorable_text(essay_text)
    metrics = analyze_essay(scoring_text)
    sentences = _sentences(scoring_text)
    grammar_profile = _grammar_risk_profile(scoring_text, prompt_type)
    template_penalty = _generic_repetition_penalty(scoring_text)

    if prompt_type == "email":
        task_fulfillment, elaboration, organization = _email_scores(
            scoring_text, metrics, template_penalty
        )
    else:
        task_fulfillment, elaboration, organization = _discussion_scores(
            scoring_text, metrics, sentences, template_penalty
        )

    # Sentence completeness is legitimate organization evidence. Formatting
    # choices (one paragraph vs. several) and long-but-controlled sentences are
    # intentionally absent.
    organization += 0.5 if grammar_profile.fragment == 0 else 0.0
    syntax = _syntax_score(scoring_text, sentences, grammar_profile)
    vocabulary = _vocabulary_score(scoring_text, metrics, prompt_type)
    accuracy = _language_accuracy_score(metrics, grammar_profile)

    dimensions = [
        ScoreDimension(
            name="Task Fulfillment",
            score=_round_quarter(task_fulfillment),
            reason="과제 목적·입장·관련 지원이 실제로 전달되는 정도",
        ),
        ScoreDimension(
            name="Elaboration",
            score=_round_quarter(elaboration),
            reason="설명·이유·예시·세부 정보가 아이디어를 충분히 발전시키는 정도",
        ),
        ScoreDimension(
            name="Organization",
            score=_round_quarter(organization),
            reason="문장과 아이디어가 명확하고 응집력 있게 이어지는 정도",
        ),
        ScoreDimension(
            name="Syntax Range",
            score=_round_quarter(syntax),
            reason="문장 구조의 자연스러운 범위와 통제력",
        ),
        ScoreDimension(
            name="Vocabulary Control",
            score=_round_quarter(vocabulary),
            reason="길이 편향을 줄인 어휘 다양성·정확성·표현 범위",
        ),
        ScoreDimension(
            name="Language Accuracy",
            score=_round_quarter(accuracy),
            reason="검출 가능한 문법·어법·문장부호 오류의 빈도와 심각도",
        ),
    ]

    # The weighting mirrors the rubric emphasis: relevance/elaboration first,
    # then organization and controlled language. There is no unexplained global
    # penalty or formatting penalty.
    weights = {
        "Task Fulfillment": 0.24,
        "Elaboration": 0.22,
        "Organization": 0.14,
        "Syntax Range": 0.14,
        "Vocabulary Control": 0.12,
        "Language Accuracy": 0.14,
    }
    pre_round_raw_score = sum(
        dimension.score * weights[dimension.name] for dimension in dimensions
    )
    pre_round_raw_score = max(0.0, min(5.0, pre_round_raw_score))
    total = _round_half(pre_round_raw_score)

    cap = grammar_cap_status(scoring_text, prompt_type)
    cap_applied = bool(cap["applied"])
    if cap_applied:
        total = min(total, float(cap["ceiling_0_5"]))

    if metrics.word_count == 0:
        total = 0.0
    elif metrics.word_count < 20:
        total = min(total, 1.0)
    elif metrics.word_count < 40:
        total = min(total, 2.0)

    # A response with pervasive, demonstrable language errors cannot be
    # "mostly understandable" merely because surface vocabulary is varied.
    accuracy_dimension = next(
        dimension.score
        for dimension in dimensions
        if dimension.name == "Language Accuracy"
    )
    if accuracy_dimension <= 1.0:
        total = min(total, 2.0)

    nearest_boundary = _round_half(pre_round_raw_score)
    distance_to_rounding_boundary = round(
        abs(pre_round_raw_score - nearest_boundary), 4
    )

    return ScoringBreakdown(
        dimensions=dimensions,
        total_0_5=total,
        pre_round_raw_score=round(pre_round_raw_score, 4),
        distance_to_rounding_boundary=distance_to_rounding_boundary,
        component_scores={dimension.name: dimension.score for dimension in dimensions},
        scoring_formula_version=SCORING_FORMULA_VERSION,
        grammar_cap_applied=cap_applied,
        grammar_cap_ceiling=(
            float(cap["ceiling_0_5"]) if cap_applied else None
        ),
        calibration_adjustment=0.0,
        calibration_reason=(
            "별도 사후 가감점 없이 ETS 정렬 차원의 가중 종합값을 사용했습니다."
        ),
    )
