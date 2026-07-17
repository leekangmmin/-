"""Vocabulary level analysis — Academic Word List (AWL) based."""
from __future__ import annotations

import re

# Academic Word List (AWL) – Coxhead (2000) core subset
ACADEMIC_WORDS: set[str] = {
    "abandon", "abstract", "access", "accompany", "accumulate", "accurate",
    "achieve", "acquire", "adapt", "adequate", "adjacent", "adjust",
    "administer", "adult", "affect", "aggregate", "aid", "alter",
    "alternative", "ambiguous", "amend", "analogy", "analyze", "annual",
    "apparent", "append", "appreciate", "approach", "approximate", "arbitrary",
    "area", "aspect", "assemble", "assess", "assign", "assist", "assume",
    "attach", "attain", "attitude", "attribute", "authority", "automate",
    "available", "aware", "behalf", "benefit", "bias", "bond", "brief",
    "bulk", "capable", "capacity", "category", "cease", "challenge",
    "channel", "circumstance", "cite", "civil", "clarify", "classic",
    "clause", "coherent", "coincide", "collapse", "commit", "complement",
    "complex", "compute", "concept", "conclude", "conduct", "confer",
    "conflict", "consent", "context", "contract", "contribute", "convert",
    "core", "correspond", "criteria", "culture", "cycle", "data", "debate",
    "define", "demonstrate", "derive", "design", "despite", "dimension",
    "discriminate", "displace", "distribute", "diverse", "dominate", "draft",
    "dynamic", "economic", "eliminate", "emerge", "enable", "environment",
    "error", "evaluate", "evidence", "exclude", "exhibit", "expand",
    "expert", "explicit", "exploit", "export", "expose", "extract",
    "facilitate", "factor", "final", "focus", "foundation", "function",
    "fundamental", "generate", "global", "guideline", "hence", "hypothesis",
    "identify", "image", "impact", "implement", "income", "indicate",
    "inevitable", "initial", "integrate", "interpret", "involve", "issue",
    "justify", "label", "layer", "legal", "link", "locate", "logic",
    "maintain", "major", "manipulate", "mechanism", "media", "method",
    "minimize", "modify", "monitor", "motivate", "network", "neutral",
    "normal", "obtain", "obvious", "occur", "outcome", "overview",
    "paradigm", "participate", "perceive", "period", "perspective",
    "phenomenon", "policy", "potential", "principle", "priority", "proceed",
    "proportional", "provision", "publish", "pursue", "rationalize",
    "regulation", "reinforce", "require", "research", "resolve", "restrict",
    "role", "section", "sector", "sequence", "significant", "similar",
    "simulate", "source", "specific", "stability", "strategy", "structure",
    "submit", "subsidy", "sufficient", "sustain", "target", "technique",
    "text", "theory", "transfer", "transform", "transition", "trend",
    "ultimate", "unique", "utilize", "valid", "vary", "version", "volume",
    "analysis", "comment", "community", "complex", "consequence", "convince",
    "coordinate", "create", "debate", "decision", "describe", "develop",
    "discuss", "emphasize", "environment", "establish", "expand", "experience",
    "explain", "explore", "express", "feature", "financial", "formal",
    "impact", "improve", "include", "increase", "indicate", "individual",
    "influence", "inform", "integrate", "interact", "introduce", "involve",
    "justify", "knowledge", "language", "maintain", "manage", "measure",
    "observe", "organize", "outcome", "participate", "pattern", "perform",
    "perspective", "physical", "present", "prevent", "primary", "process",
    "project", "promote", "provide", "publish", "purpose", "respond",
    "result", "review", "significant", "solve", "specific", "structure",
    "suggest", "support", "survey", "sustain", "traditional", "understand",
}

# Backward-compatible alias for older imports.
_AWL = ACADEMIC_WORDS

# Academic collocations and transition phrases
_COLLOCATIONS: list[str] = [
    "in contrast", "on the other hand", "as a result", "in addition",
    "for instance", "for example", "in conclusion", "to summarize",
    "furthermore", "however", "nevertheless", "consequently",
    "specifically", "generally speaking", "in particular",
    "it is important", "this suggests", "it can be argued",
    "studies show", "according to", "in terms of", "with regard to",
    "in order to", "as a consequence", "to illustrate",
    "on the contrary", "in summary", "above all", "in fact",
    "in other words", "that is to say", "as a result of",
    "due to the fact", "it is clear that", "this indicates",
]


def _mattr(tokens: list[str], window: int = 50) -> float:
    if not tokens:
        return 0.0
    if len(tokens) <= window:
        return len(set(tokens)) / len(tokens)
    values = [
        len(set(tokens[start : start + window])) / window
        for start in range(len(tokens) - window + 1)
    ]
    return sum(values) / len(values)


def _base_form(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if token.endswith(suffix) and len(token) - len(suffix) >= 4:
            return token[: -len(suffix)]
    return token


def analyze_vocabulary(text: str) -> dict:
    """Return descriptive vocabulary metrics without mechanical score caps.

    MATTR is used instead of raw type-token ratio so a longer response is not
    automatically labeled less diverse. Academic words and discourse phrases
    are descriptive evidence, not mandatory ingredients.
    """
    tokens = re.findall(r"\b[a-zA-Z]+(?:['-][a-zA-Z]+)*\b", text.lower())
    if not tokens:
        return {
            "total_words": 0,
            "unique_words": 0,
            "academic_word_count": 0,
            "academic_ratio": 0.0,
            "type_token_ratio": 0.0,
            "sophistication_score": 0.0,
            "academic_words_found": [],
            "collocations_found": [],
            "suggestions": ["분석할 영어 답안이 없습니다."],
        }

    normalized = [_base_form(token) for token in tokens]
    academic_tokens = [
        token for token, base in zip(tokens, normalized) if base in ACADEMIC_WORDS
    ]
    academic_ratio = len(academic_tokens) / len(tokens)
    mattr = _mattr(tokens)
    long_content_ratio = sum(len(token.replace("-", "")) >= 7 for token in tokens) / len(tokens)
    sophistication = min(
        1.0,
        academic_ratio * 2.5 + mattr * 0.45 + long_content_ratio * 0.35,
    )
    collocations_found = [
        phrase for phrase in _COLLOCATIONS if phrase in text.lower()
    ]

    suggestions: list[str] = []
    if mattr < 0.55:
        suggestions.append(
            "같은 내용어가 가까운 문장 안에서 반복되는지 확인하고, 의미가 정확할 때만 표현을 바꿔 보세요."
        )
    if academic_ratio < 0.05 and long_content_ratio < 0.12:
        suggestions.append(
            "주제에 맞는 구체적 동사와 명사를 사용하면 표현의 정밀도를 높일 수 있습니다."
        )
    if not suggestions:
        suggestions.append(
            "현재 지표에서는 뚜렷한 어휘 반복 문제가 보이지 않습니다. 어려운 단어 수보다 문맥상 정확성을 우선하세요."
        )

    return {
        "total_words": len(tokens),
        "unique_words": len(set(tokens)),
        "academic_word_count": len(academic_tokens),
        "academic_ratio": round(academic_ratio, 3),
        # API 필드명은 하위 호환을 위해 유지하지만 값은 MATTR이다.
        "type_token_ratio": round(mattr, 3),
        "sophistication_score": round(sophistication, 3),
        "academic_words_found": sorted(set(academic_tokens))[:20],
        "collocations_found": collocations_found[:10],
        "suggestions": suggestions,
    }
