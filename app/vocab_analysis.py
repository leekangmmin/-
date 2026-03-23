"""Vocabulary level analysis — Academic Word List (AWL) based."""
from __future__ import annotations

import re

# Academic Word List (AWL) – Coxhead (2000) core subset
_AWL: set[str] = {
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


def analyze_vocabulary(text: str) -> dict:
    """Return vocabulary richness metrics for the given essay text."""
    tokens = re.findall(r"\b[a-zA-Z]{3,}\b", text.lower())
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
            "suggestions": [],
        }

    unique = set(tokens)
    academic_found = sorted(w for w in unique if w in _AWL)
    text_lower = text.lower()
    collocations_found = [c for c in _COLLOCATIONS if c in text_lower]

    academic_ratio = len(academic_found) / max(len(unique), 1)
    ttr = len(unique) / max(len(tokens), 1)
    sophistication = round((academic_ratio * 0.6 + ttr * 0.4) * 100, 1)

    suggestions: list[str] = []
    if academic_ratio < 0.15:
        suggestions.append(
            "학술 어휘 비율이 낮습니다. analyze, significant, demonstrate, contrast 등 학술 단어를 더 활용하세요."
        )
    if ttr < 0.50:
        suggestions.append(
            "반복 단어가 많습니다. 유의어 사전(thesaurus)을 활용해 어휘 다양성을 높이세요."
        )
    if len(collocations_found) < 3:
        suggestions.append(
            "학술 연결어 사용이 부족합니다. furthermore, consequently, in contrast, as a result 등을 문장 흐름에 맞게 추가하세요."
        )
    if len(tokens) < 200:
        suggestions.append(
            "답안 분량이 짧습니다. 통합형 250단어+, 토론형 150단어+ 작성을 목표로 하세요."
        )

    return {
        "total_words": len(tokens),
        "unique_words": len(unique),
        "academic_word_count": len(academic_found),
        "academic_ratio": round(academic_ratio, 3),
        "type_token_ratio": round(ttr, 3),
        "sophistication_score": sophistication,
        "academic_words_found": academic_found[:20],
        "collocations_found": collocations_found[:10],
        "suggestions": suggestions,
    }
