from __future__ import annotations

import difflib
import re
from collections import Counter
from typing import Any, Literal

from app.grammar import analyze_grammar, find_comma_splices, grammar_analysis_text, split_sentences, starts_with_vowel_sound
from app.scorer import analyze_essay

STOPWORDS = {
    "the",
    "a",
    "an",
    "and",
    "or",
    "to",
    "for",
    "of",
    "in",
    "on",
    "at",
    "with",
    "is",
    "are",
    "was",
    "were",
    "be",
    "been",
    "being",
    "that",
    "this",
    "these",
    "those",
    "it",
    "its",
    "as",
    "by",
    "from",
    "can",
    "could",
    "should",
    "would",
    "will",
    "may",
    "might",
    "do",
    "does",
    "did",
    "what",
    "which",
    "who",
    "when",
    "where",
    "why",
    "how",
}

CLAIM_MARKERS = {"i think", "i believe", "i agree", "i disagree", "my view", "i argue"}
EVIDENCE_MARKERS = {"for example", "for instance", "because", "according to", "research", "data"}
EXPLANATION_MARKERS = {"therefore", "this means", "as a result", "so", "thus"}
TEMPLATE_SPAM_MARKERS = {
    "in today's society",
    "nowadays many people",
    "there are many reasons",
    "this essay will discuss",
    "everyone has different opinions",
    "i want discuss about this topic",
    "in conclusion, i think this is very important",
}

_EMAIL_OPEN_RE = re.compile(
    r"^\s*(dear\b|hi\b|hello\b|good morning\b|good afternoon\b|to whom it may concern)",
    re.IGNORECASE | re.MULTILINE,
)
_EMAIL_CLOSE_RE = re.compile(
    r"\b(sincerely|best regards|kind regards|yours truly|best,|regards,|thank you,)\s*[\n\r]",
    re.IGNORECASE,
)
_EMAIL_INTENT_RE = re.compile(
    r"\b(i am writing to|i would like to (request|inform|ask|apply|invite|notify)|i am contacting|please find|please let me know)\b",
    re.IGNORECASE,
)


def detect_prompt_type(essay_text: str) -> str:
    """Auto-detect Task 2 (email) or Task 3 (academic_discussion) from essay content."""
    text = essay_text.strip()
    score = 0
    if _EMAIL_OPEN_RE.search(text):
        score += 2
    if _EMAIL_CLOSE_RE.search(text):
        score += 2
    if _EMAIL_INTENT_RE.search(text):
        score += 1
    return "email" if score >= 2 else "academic_discussion"


def _tokens(text: str) -> list[str]:
    return [w.lower() for w in re.findall(r"[A-Za-z']+", text)]


def _keywords(text: str, top_n: int = 8) -> list[str]:
    words = [w for w in _tokens(text) if len(w) >= 4 and w not in STOPWORDS]
    counts = Counter(words)
    return [w for w, _ in counts.most_common(top_n)]


def _stem_token(token: str) -> str:
    if len(token) > 5 and token.endswith("ies"):
        return token[:-3] + "y"
    if len(token) > 5 and token.endswith(("ing", "ers")):
        return token[:-3]
    if len(token) > 4 and token.endswith(("ed", "es")):
        return token[:-2]
    if len(token) > 4 and token.endswith("s"):
        return token[:-1]
    return token


def _has_any(text: str, patterns: tuple[str, ...]) -> bool:
    return any(re.search(pattern, text, flags=re.IGNORECASE) for pattern in patterns)


def _prompt_requirements(prompt_text: str) -> list[tuple[str, tuple[str, ...]]]:
    lower = prompt_text.lower()
    requirements: list[tuple[str, tuple[str, ...]]] = []

    if "email" in lower or "write to" in lower or "professor" in lower:
        requirements.append(("recipient/tone", (r"\b(dear|hello|hi|professor|teacher)\b",)))
        requirements.append(("clear request or purpose", (r"\b(request|ask|would like|i am writing|please|could you)\b",)))
    if "reason" in lower or "explain why" in lower:
        requirements.append(("reason", (r"\b(because|since|due to|as a result|reason)\b",)))
    if "progress" in lower:
        requirements.append(("progress", (r"\b(progress|draft|outline|finished|completed|revised|citations?)\b",)))
    if "deadline" in lower or "new deadline" in lower or "extension" in lower:
        requirements.append(("proposed deadline", (r"\b(submit by|turn .* in by|by friday|by monday|by tuesday|by wednesday|by thursday|tomorrow|next week|new deadline)\b",)))

    if "do you think" in lower or "agree" in lower or "disagree" in lower or "position" in lower:
        requirements.append(("clear position", (r"\b(i believe|i think|i agree|i disagree|in my view|my position|i support)\b",)))
    if "reason" in lower or "reasons" in lower or "why" in lower:
        requirements.append(("reasoning", (r"\b(because|therefore|so|this means|as a result|one reason|another reason)\b",)))
    if "example" in lower or "specific" in lower:
        requirements.append(("specific example", (r"\b(for example|for instance|when i|in my experience|research|study|data)\b",)))
    if "classmate" in lower or "students said" in lower or "discussion" in lower:
        requirements.append(("discussion engagement", (r"\b(as .* said|responding to|classmate|student|discussion|build on)\b",)))

    return requirements


def _requirement_match(prompt_text: str, essay_text: str) -> tuple[list[str], list[str]]:
    requirements = _prompt_requirements(prompt_text)
    if not requirements:
        return [], []
    met: list[str] = []
    missing: list[str] = []
    for label, patterns in requirements:
        if _has_any(essay_text, patterns):
            met.append(label)
        else:
            missing.append(label)
    return met, missing


def _template_spam_penalty(essay_text: str) -> tuple[float, list[str]]:
    lowered = essay_text.lower()
    reasons: list[str] = []
    marker_hits = [m for m in TEMPLATE_SPAM_MARKERS if m in lowered]
    if marker_hits:
        reasons.append("generic template phrase")

    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text) if s.strip()]
    starts = [" ".join(_tokens(s)[:3]) for s in sentences if len(_tokens(s)) >= 3]
    repeated_starts = [start for start, count in Counter(starts).items() if count >= 3]
    if repeated_starts:
        reasons.append("repeated sentence opening")

    tokens = [t for t in _tokens(essay_text) if len(t) >= 4]
    lexical_ratio = len(set(tokens)) / max(len(tokens), 1)
    if len(tokens) >= 80 and lexical_ratio < 0.34:
        reasons.append("low lexical variety")

    if len(reasons) >= 2:
        return 1.0, reasons
    if reasons:
        return 0.5, reasons
    return 0.0, reasons


def _match_case(source: str, replacement: str) -> str:
    if not source:
        return replacement
    if source.isupper():
        return replacement.upper()
    if source[0].isupper():
        return replacement.capitalize()
    return replacement


def _to_third_person_singular(verb: str) -> str:
    lowered = verb.lower()
    irregular = {
        "have": "has",
        "do": "does",
        "go": "goes",
    }
    if lowered in irregular:
        return _match_case(verb, irregular[lowered])
    if re.search(r"[^aeiou]y$", lowered):
        return _match_case(verb, lowered[:-1] + "ies")
    if lowered.endswith(("s", "sh", "ch", "x", "z", "o")):
        return _match_case(verb, lowered + "es")
    return _match_case(verb, lowered + "s")


def _to_base_form(verb: str) -> str:
    lowered = verb.lower()
    irregular = {
        "has": "have",
        "does": "do",
        "goes": "go",
        "is": "are",
        "was": "were",
    }
    if lowered in irregular:
        return _match_case(verb, irregular[lowered])
    if lowered.endswith("ies") and len(lowered) > 3:
        return _match_case(verb, lowered[:-3] + "y")
    if lowered.endswith("es") and lowered[:-2].endswith(("s", "sh", "ch", "x", "z", "o")):
        return _match_case(verb, lowered[:-2])
    if lowered.endswith("s") and not lowered.endswith("ss"):
        return _match_case(verb, lowered[:-1])
    return verb


def _starts_with_vowel_sound(word: str) -> bool:
    return starts_with_vowel_sound(word)


def evaluate_prompt_fit(prompt_text: str, essay_text: str) -> dict:
    pkeys = _keywords(prompt_text, top_n=12)
    essay_tokens = _tokens(essay_text)
    essay_words = set(essay_tokens)
    essay_stems = {_stem_token(t) for t in essay_tokens}
    matched = [k for k in pkeys if k in essay_words or _stem_token(k) in essay_stems]
    missing = [k for k in pkeys if k not in matched and _stem_token(k) not in essay_stems]

    overlap_ratio = (len(matched) / len(pkeys)) if pkeys else 0.0
    met_reqs, missing_reqs = _requirement_match(prompt_text, essay_text)
    req_total = len(met_reqs) + len(missing_reqs)
    requirement_ratio = (len(met_reqs) / req_total) if req_total else 0.0
    _, template_reasons = _template_spam_penalty(essay_text)

    score = 1.5 + (overlap_ratio * 2.0)
    if req_total:
        score += requirement_ratio * 1.5
    elif any(marker in essay_text.lower() for marker in CLAIM_MARKERS):
        score += 0.4

    if _has_any(essay_text, (r"\b(for example|for instance|because|according to|research|data)\b",)):
        score += 0.4

    if len(essay_tokens) < 90 and overlap_ratio < 0.3 and req_total:
        score -= 0.5
    if pkeys and overlap_ratio < 0.15 and (not req_total or requirement_ratio < 0.35):
        score = min(score, 2.0)

    score = max(0.0, min(5.0, round(score * 2) / 2))

    reason_en = (
        f"Diagnostic surface overlap {len(matched)}/{len(pkeys)}. "
        f"Requirements met {len(met_reqs)}/{req_total}. "
        f"Matched: {', '.join(matched[:4]) if matched else 'none'}"
    )
    reason_ko = (
        f"진단용 표면 키워드 일치 {len(matched)}/{len(pkeys)}, "
        f"요구사항 충족 {len(met_reqs)}/{req_total}. "
        f"일치 단어: {', '.join(matched[:4]) if matched else '없음'}"
    )
    if template_reasons:
        reason_en += f". Separate template observation: {', '.join(template_reasons)}"
        reason_ko += f". 별도 템플릿 관찰: {', '.join(template_reasons)}"

    return {
        "score": score,
        "reason_en": reason_en,
        "reason_ko": reason_ko,
        "matched_keywords": matched[:8],
        "missing_keywords": ([f"required:{r}" for r in missing_reqs] + missing)[:8],
    }


def map_claim_evidence(essay_text: str) -> list[dict]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    tagged: list[dict] = []

    for sentence in sentences[:14]:
        lowered = sentence.lower()
        tag: Literal["claim", "evidence", "explanation", "other"] = "other"
        note = "General sentence"

        if any(marker in lowered for marker in CLAIM_MARKERS):
            tag = "claim"
            note = "Main position or stance"
        elif any(marker in lowered for marker in EVIDENCE_MARKERS):
            tag = "evidence"
            note = "Example, source, or supporting detail"
        elif any(marker in lowered for marker in EXPLANATION_MARKERS):
            tag = "explanation"
            note = "Explains implication or causal logic"

        tagged.append({"sentence": sentence, "tag": tag, "note": note})

    return tagged


def grammar_error_stats(essay_text: str, prompt_type: str | None = None) -> dict:
    """공유 문법 모듈(app.grammar)에 위임한다. 규칙 중복/불일치 제거."""
    return analyze_grammar(grammar_analysis_text(essay_text, prompt_type)).as_stats_dict()


def detailed_grammar_corrections(essay_text: str, limit: int = 18) -> list[dict[str, Any]]:
    sentence_spans: list[tuple[str, int, int]] = []
    for m in re.finditer(r"[^.!?]+[.!?]?", essay_text):
        raw = m.group(0)
        stripped = raw.strip()
        if not stripped:
            continue
        lead = len(raw) - len(raw.lstrip())
        start = m.start() + lead
        end = start + len(stripped)
        sentence_spans.append((stripped, start, end))

    corrections: list[dict[str, Any]] = []

    def locate_focus(sentence: str, sentence_start: int, focus_text: str) -> tuple[int | None, int | None]:
        if not focus_text:
            return None, None
        m = re.search(re.escape(focus_text), sentence, flags=re.IGNORECASE)
        if not m:
            return None, None
        return sentence_start + m.start(), sentence_start + m.end()

    def push(
        sentence: str,
        sentence_start: int,
        error_type: str,
        focus_text: str,
        corrected: str,
        explanation: str,
        severity: Literal["low", "medium", "high"],
    ) -> None:
        if sentence == corrected:
            return
        f_start, f_end = locate_focus(sentence, sentence_start, focus_text)
        corrections.append(
            {
                "sentence": sentence,
                "error_type": error_type,
                "focus_text": focus_text,
                "focus_start": f_start,
                "focus_end": f_end,
                "corrected": corrected,
                "explanation": explanation,
                "severity": severity,
            }
        )

    for sentence, sentence_start, _ in sentence_spans:
        if len(corrections) >= limit:
            break

        original_sentence = sentence
        working_sentence = sentence

        def current_lowered() -> str:
            return working_sentence.lower()

        def apply_fix(
            error_type: str,
            focus_text: str,
            corrected: str,
            explanation: str,
            severity: Literal["low", "medium", "high"],
        ) -> None:
            nonlocal working_sentence
            if working_sentence == corrected:
                return
            push(
                original_sentence,
                sentence_start,
                error_type,
                focus_text,
                corrected,
                explanation,
                severity,
            )
            working_sentence = corrected

        lowered = current_lowered()
        m_subj = re.search(r"\b(people|students|they)\s+is\b", lowered)
        if m_subj:
            fixed = re.sub(r"\bis\b", "are", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_subj.group(0), fixed, "복수 주어(people/students/they)에는 보통 are를 사용합니다.", "high")

        lowered = current_lowered()
        m_plural_aux = re.search(r"\b(i|we|they|people|students)\s+(has|does|needs|makes|suggests|shows|gives|takes|helps)\b", lowered)
        if m_plural_aux:
            fixed = re.sub(
                r"\b(i|we|they|people|students)\s+(has|does|needs|makes|suggests|shows|gives|takes|helps)\b",
                lambda match: f"{match.group(1)} {_to_base_form(match.group(2))}",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_plural_aux.group(0), fixed, "복수 주어나 I 뒤에는 단수형 동사 대신 원형/복수형 동사가 와야 합니다.", "high")

        lowered = current_lowered()
        # 조동사/to부정사 뒤 원형("does he have", "to make it work")은 정상이므로 제외
        _3p_pattern = (
            r"(?<!do\s)(?<!does\s)(?<!did\s)(?<!to\s)(?<!not\s)(?<!can\s)(?<!will\s)"
            r"(?<!would\s)(?<!should\s)(?<!might\s)(?<!must\s)(?<!may\s)(?<!let\s)(?<!help\s)"
            r"\b(he|she|it)\s+(go|have|do|need|make|suggest|show|mean|help|give|take|mention)\b"
        )
        m_3p = re.search(_3p_pattern, lowered)
        if m_3p:
            fixed = re.sub(
                _3p_pattern,
                lambda match: f"{match.group(1)} {_to_third_person_singular(match.group(2))}",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_3p.group(0), fixed, "3인칭 단수 주어(he/she/it)에는 동사에 -s 형태가 필요합니다.", "high")

        lowered = current_lowered()
        # "that/it + 복수동사"는 관계대명사("students that have...")에서 정상이므로 this 만 교정
        m_neutral_subject = re.search(r"\bthis\s+(are|were)\b", lowered)
        if m_neutral_subject:
            fixed = re.sub(
                r"\bthis\s+(are|were)\b",
                lambda match: f"this {'is' if match.group(1).lower() == 'are' else 'was'}",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_neutral_subject.group(0), fixed, "this는 단수 주어이므로 단수 동사 형태가 필요합니다.", "high")

        lowered = current_lowered()
        m_singular_noun = re.search(r"^(the|this|that)\s+(teacher|student|child|professor|policy|school|government|internet|technology|idea|method)\s+(are|were|have|do|need|make|suggest|show|mean|help|give|take|mention|discuss)\b", lowered)
        if m_singular_noun:
            fixed = re.sub(
                r"^(the|this|that)\s+(teacher|student|child|professor|policy|school|government|internet|technology|idea|method)\s+(are|were|have|do|need|make|suggest|show|mean|help|give|take|mention|discuss)\b",
                lambda match: f"{match.group(1)} {match.group(2)} {_to_third_person_singular(match.group(3)) if match.group(3).lower() not in {'are', 'were'} else ('is' if match.group(3).lower() == 'are' else 'was')}",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_singular_noun.group(0), fixed, "단수 명사 주어 뒤에는 3인칭 단수 동사 형태가 와야 합니다.", "high")

        lowered = current_lowered()
        m_num = re.search(r"\b(many|several|few)\s+(student|reason|problem|example|factor|benefit)\b", lowered)
        if m_num:
            fixed = re.sub(
                r"\b(many|several|few)\s+(student|reason|problem|example|factor|benefit)\b",
                lambda match: f"{match.group(1)} {match.group(2)}s",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("noun_number", m_num.group(0), fixed, "many/several/few 뒤에는 보통 복수형 명사가 필요합니다.", "medium")

        lowered = current_lowered()
        m_uncount2 = re.search(r"\bmany\s+information\b", lowered)
        if m_uncount2:
            fixed = re.sub(r"\bmany\s+information\b", "much information", working_sentence, flags=re.IGNORECASE)
            apply_fix("article", m_uncount2.group(0), fixed, "information은 불가산명사이므로 many보다 much를 사용합니다.", "high")

        lowered = current_lowered()
        m_teacher = re.search(r"\bteacher\s+discuss\b", lowered)
        if m_teacher:
            fixed = re.sub(r"\bteacher\s+discuss\b", "teacher discusses", working_sentence, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_teacher.group(0), fixed, "단수 주어(teacher)에는 일반적으로 동사에 -es가 필요합니다.", "high")

        lowered = current_lowered()
        m_i_agree = re.search(r"\bi\s+am\s+agree\b|\bi'm\s+agree\b", lowered)
        if m_i_agree:
            fixed = re.sub(r"\bi\s+am\s+agree\b", "I agree", working_sentence, count=1, flags=re.IGNORECASE)
            fixed = re.sub(r"\bi'm\s+agree\b", "I agree", fixed, count=1, flags=re.IGNORECASE)
            apply_fix("style", m_i_agree.group(0), fixed, "agree는 보통 be동사 없이 동사로 직접 써서 I agree라고 표현합니다.", "high")

        lowered = current_lowered()
        m_art1 = None
        for cand in re.finditer(r"\ba\s+([A-Za-z][A-Za-z'\-]*)", working_sentence, flags=re.IGNORECASE):
            if _starts_with_vowel_sound(cand.group(1)):
                m_art1 = cand
                break
        if m_art1:
            word = m_art1.group(1)
            fixed = (
                working_sentence[: m_art1.start()]
                + _match_case(m_art1.group(0), f"an {word}")
                + working_sentence[m_art1.end() :]
            )
            apply_fix("article", m_art1.group(0), fixed, "모음 소리로 시작하는 단어 앞에서는 a보다 an이 자연스럽습니다.", "medium")

        lowered = current_lowered()
        m_art2 = None
        for cand in re.finditer(r"\ban\s+([A-Za-z][A-Za-z'\-]*)", working_sentence, flags=re.IGNORECASE):
            if not _starts_with_vowel_sound(cand.group(1)):
                m_art2 = cand
                break
        if m_art2:
            word = m_art2.group(1)
            fixed = (
                working_sentence[: m_art2.start()]
                + _match_case(m_art2.group(0), f"a {word}")
                + working_sentence[m_art2.end() :]
            )
            apply_fix("article", m_art2.group(0), fixed, "자음 소리로 시작하는 단어 앞에서는 an보다 a가 자연스럽습니다.", "medium")

        lowered = current_lowered()
        m_uncount = re.search(r"\b(a|an)\s+(information|advice|research|evidence)\b", lowered)
        if m_uncount:
            fixed = re.sub(
                r"\b(a|an)\s+(information|advice|research|evidence)\b",
                r"\2",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("article", m_uncount.group(0), fixed, "information/advice/research/evidence는 셀 수 없는 명사로 관사 a/an을 보통 쓰지 않습니다.", "medium")

        lowered = current_lowered()
        m_internet = re.search(r"\bfrom\s+internet\b", lowered)
        if m_internet:
            fixed = re.sub(r"\bfrom\s+internet\b", "from the internet", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("article", m_internet.group(0), fixed, "internet은 일반적으로 the internet 형태가 더 자연스럽습니다.", "low")

        lowered = current_lowered()
        m_prep = re.search(r"\bdiscuss(?:es)? about\b|\bmentions? about\b", lowered)
        if m_prep:
            fixed = re.sub(r"\bdiscuss about\b", "discuss", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bdiscusses about\b", "discusses", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmention about\b", "mention", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmentions about\b", "mentions", fixed, flags=re.IGNORECASE)
            apply_fix("preposition", m_prep.group(0), fixed, "discuss/mention은 보통 about 없이 직접 목적어를 받습니다.", "medium")

        lowered = current_lowered()
        m_prep2 = re.search(r"\bin nowadays\b|\bmarried with\b", lowered)
        if m_prep2:
            fixed = re.sub(r"\bin nowadays\b", "nowadays", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmarried with\b", "married to", fixed, flags=re.IGNORECASE)
            apply_fix("preposition", m_prep2.group(0), fixed, "전치사 결합이 부자연스럽습니다. in nowadays -> nowadays, married with -> married to를 권장합니다.", "medium")

        lowered = current_lowered()
        m_prep3 = re.search(r"\bdepend of\b|\binterested on\b|\bdiscuss on\b", lowered)
        if m_prep3:
            fixed = re.sub(r"\bdepend of\b", "depend on", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\binterested on\b", "interested in", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bdiscuss on\b", "discuss", fixed, flags=re.IGNORECASE)
            apply_fix("preposition", m_prep3.group(0), fixed, "전치사 결합 오류입니다. depend on, interested in, discuss(about/on 없이)를 사용하세요.", "high")

        lowered = current_lowered()
        m_prep4 = re.search(r"\baccording to me\b", lowered)
        if m_prep4:
            fixed = re.sub(r"\baccording to me\b", "in my opinion", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("preposition", m_prep4.group(0), fixed, "자기 의견에는 according to me보다 in my opinion이 더 자연스럽습니다.", "medium")

        lowered = current_lowered()
        m_prep5 = re.search(r"\bdespite of\b|\bbetween\s+\w+\s+to\s+\w+\b", lowered)
        if m_prep5:
            fixed = re.sub(r"\bdespite of\b", "despite", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(
                r"\bbetween\s+(\w+)\s+to\s+(\w+)\b",
                lambda m: f"between {m.group(1)} and {m.group(2)}",
                fixed,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("preposition", m_prep5.group(0), fixed, "despite는 of 없이 쓰고, between은 and와 짝을 맞춰야 합니다.", "medium")

        lowered = current_lowered()
        m_prep6 = re.search(r"\bdifferent with\b", lowered)
        if m_prep6:
            fixed = re.sub(r"\bdifferent with\b", "different from", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("preposition", m_prep6.group(0), fixed, "different는 보통 from과 결합하는 것이 표준적입니다.", "low")

        lowered = current_lowered()
        m_there = re.search(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lowered)
        if m_there:
            fixed = re.sub(r"\bthere\s+is\b", lambda match: _match_case(match.group(0), "there are"), working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_there.group(0), fixed, "복수 명사 앞에서는 there is보다 there are가 자연스럽습니다.", "high")

        lowered = current_lowered()
        m_oneof = re.search(r"\bone of\s+the\s+\w+\s+are\b", lowered)
        if m_oneof:
            fixed = re.sub(r"\bare\b", "is", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_oneof.group(0), fixed, "one of + 복수명사는 문장 주어가 one(단수)이므로 동사 is가 맞습니다.", "high")

        lowered = current_lowered()
        m_oneof2 = re.search(r"\bone of\s+the\s+\w+\s+(have|do|were)\b", lowered)
        if m_oneof2:
            fixed = re.sub(
                r"\bone of\s+the\s+(\w+)\s+have\b",
                lambda m: f"one of the {m.group(1)} has",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            fixed = re.sub(
                r"\bone of\s+the\s+(\w+)\s+do\b",
                lambda m: f"one of the {m.group(1)} does",
                fixed,
                count=1,
                flags=re.IGNORECASE,
            )
            fixed = re.sub(
                r"\bone of\s+the\s+(\w+)\s+were\b",
                lambda m: f"one of the {m.group(1)} was",
                fixed,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_oneof2.group(0), fixed, "one of 구문은 단수 주어로 취급되어 has/does/was가 자연스럽습니다.", "high")

        lowered = current_lowered()
        m_number = re.search(r"\bthe\s+number\s+of\s+\w+\s+are\b|\ba\s+number\s+of\s+\w+\s+is\b", lowered)
        if m_number:
            fixed = re.sub(r"\bthe\s+number\s+of\s+(\w+)\s+are\b", lambda m: f"the number of {m.group(1)} is", working_sentence, count=1, flags=re.IGNORECASE)
            fixed = re.sub(r"\ba\s+number\s+of\s+(\w+)\s+is\b", lambda m: f"a number of {m.group(1)} are", fixed, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_number.group(0), fixed, "the number of는 단수, a number of는 복수 동사와 함께 쓰는 것이 자연스럽습니다.", "medium")

        lowered = current_lowered()
        m_children = re.search(r"\b(people|children)\s+has\b", lowered)
        if m_children:
            fixed = re.sub(r"\bhas\b", "have", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_children.group(0), fixed, "people/children은 복수 취급하므로 has 대신 have를 사용합니다.", "high")

        lowered = current_lowered()
        m_plural_was = re.search(r"\b(people|students|children|they|we)\s+was\b", lowered)
        if m_plural_was:
            fixed = re.sub(
                r"\b(people|students|children|they|we)\s+was\b",
                lambda m: f"{m.group(1)} were",
                working_sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            apply_fix("subject_verb", m_plural_was.group(0), fixed, "복수 주어에는 과거형 be동사로 were를 사용합니다.", "high")

        lowered = current_lowered()
        m_sv2 = re.search(r"\b(teacher|student|child)\s+have\b", lowered)
        if m_sv2:
            fixed = re.sub(r"\bhave\b", "has", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_sv2.group(0), fixed, "단수 주어(teacher/student/child)에는 have 대신 has를 씁니다.", "high")

        lowered = current_lowered()
        m_dont = re.search(r"\b(he|she|it)\s+don't\b|\b(i|we|they)\s+doesn't\b", lowered)
        if m_dont:
            fixed = re.sub(r"\b(he|she|it)\s+don't\b", lambda m: f"{m.group(1)} doesn't", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\b(i|we|they)\s+doesn't\b", lambda m: f"{m.group(1)} don't", fixed, flags=re.IGNORECASE)
            apply_fix("subject_verb", m_dont.group(0), fixed, "don't/doesn't 수일치를 주어에 맞게 조정해야 합니다.", "high")

        lowered = current_lowered()
        m_of = re.search(r"\b(could|should|would)\s+of\b", lowered)
        if m_of:
            fixed = re.sub(r"\bcould\s+of\b", "could have", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bshould\s+of\b", "should have", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bwould\s+of\b", "would have", fixed, flags=re.IGNORECASE)
            apply_fix("style", m_of.group(0), fixed, "구어체 표기(could/should/would of)는 문어체에서 could/should/would have가 정확합니다.", "medium")

        lowered = current_lowered()
        m_if_i_was = re.search(r"\bif\s+i\s+was\b", lowered)
        if m_if_i_was:
            fixed = re.sub(r"\bif\s+i\s+was\b", "if I were", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("style", m_if_i_was.group(0), fixed, "가정법 맥락에서는 If I was보다 If I were가 더 표준적입니다.", "low")

        lowered = current_lowered()
        m_rel = re.search(r"\b(people|students|children)\s+which\b", lowered)
        if m_rel:
            fixed = re.sub(r"\b(people|students|children)\s+which\b", lambda m: f"{m.group(1)} who", working_sentence, count=1, flags=re.IGNORECASE)
            apply_fix("style", m_rel.group(0), fixed, "사람을 수식하는 관계대명사는 which보다 who가 자연스럽습니다.", "low")

        lowered = current_lowered()
        m_comp = re.search(r"\bmore\s+better\b|\bmore\s+worse\b", lowered)
        if m_comp:
            fixed = re.sub(r"\bmore\s+better\b", "better", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmore\s+worse\b", "worse", fixed, flags=re.IGNORECASE)
            apply_fix("style", m_comp.group(0), fixed, "비교급 중복 표현(more better/worse)은 감점 요인이므로 단일 비교급으로 쓰세요.", "medium")

        lowered = current_lowered()
        # yesterday 와 같은 절 안에서 is/are 가 함께 쓰인 경우만 시제 불일치로 본다.
        m_tense = re.search(r"\byesterday\b[^.?!,]{0,40}\b(is|are)\b", lowered)
        if m_tense:
            fixed = re.sub(r"\bis\b", "was", working_sentence, count=1, flags=re.IGNORECASE)
            fixed = re.sub(r"\bare\b", "were", fixed, count=1, flags=re.IGNORECASE)
            apply_fix("tense", m_tense.group(0), fixed, "과거 시점(yesterday)과 현재 시제(is/are)가 섞이면 시제 일관성이 깨집니다.", "high")

        lowered = current_lowered()
        # "I was" 는 올바른 영어 — we/they was 와 (가정법 제외) he/she/it were 만 교정
        m_tense2 = re.search(r"\b(we|they)\s+was\b|(?<!if\s)(?<!wish\s)(?<!though\s)\b(he|she|it)\s+were\b", lowered)
        if m_tense2:
            fixed = re.sub(r"(?<!if\s)(?<!wish\s)(?<!though\s)\b(he|she|it)\s+were\b", lambda m: f"{m.group(1)} was", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\b(we|they)\s+was\b", lambda m: f"{m.group(1)} were", fixed, flags=re.IGNORECASE)
            apply_fix("tense", m_tense2.group(0), fixed, "be동사 수일치가 어색합니다. he/she/it was, we/they were를 사용하세요.", "high")

        lowered = current_lowered()
        # 종속절 도입부("When ..., I ...")는 정상 구조 — 진짜 comma splice 만 교정
        if find_comma_splices([working_sentence]) > 0:
            m_comma = re.search(r",\s+(i|we|they|he|she|it|this|that|there)\s+[a-z]+", lowered)
            fixed = working_sentence.replace(",", ";", 1)
            apply_fix("comma_splice", m_comma.group(0) if m_comma else original_sentence, fixed, "독립절 2개를 콤마만으로 연결하면 comma splice 오류가 됩니다. 세미콜론/마침표를 사용하세요.", "high")

        lowered = current_lowered()
        m_style = re.search(r"\b(firstly|secondly|thirdly)\b", lowered)
        if m_style:
            fixed = re.sub(r"\bfirstly\b", "first", working_sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bsecondly\b", "second", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bthirdly\b", "third", fixed, flags=re.IGNORECASE)
            apply_fix("style", m_style.group(0), fixed, "TOEFL 라이팅에서는 first/second/third가 더 자연스럽고 간결합니다.", "low")

        if working_sentence and not re.search(r"[.!?]$", working_sentence):
            fixed = working_sentence + "."
            apply_fix("punctuation", "missing sentence end punctuation", fixed, "문장 끝 마침표/물음표/느낌표가 없으면 문장 경계가 흐려집니다.", "low")

    # Keep only unique (sentence, error_type) pairs for readability.
    unique: dict[tuple[str, str, str], dict[str, Any]] = {}
    for item in corrections:
        key = (item["sentence"], item["error_type"], item.get("focus_text", ""))
        if key not in unique:
            unique[key] = item

    return list(unique.values())[:limit]


def build_smart_recommendations(
    essay_text: str,
    prompt_type: str,
    grammar_stats: dict[str, int],
    prompt_fit_score: float,
    current_score_0_5: float,
) -> list[dict[str, str]]:
    metrics = analyze_essay(essay_text)
    recs: list[dict[str, str]] = []

    # 실제로 감지된 문법 오류가 있을 때만 문법 교정을 최우선으로 권한다.
    if grammar_stats.get("total", 0) > 0:
        recs.append(
            {
                "title": "문법 오류 우선 제거",
                "why": "반복되는 언어 오류는 ETS의 언어 정확성 판단에 직접 관련됩니다.",
                "how_to": "검출 결과를 원문과 대조한 뒤, 의미 전달을 방해하는 오류 유형부터 교정하세요.",
                "impact": "언어 정확성 개선",
                "confidence": "high",
            }
        )

    if grammar_stats.get("run_on", 0) > 0:
        recs.append(
            {
                "title": "Run-on 분리 훈련",
                "why": "독립절을 콤마만으로 연결한 경우 문장 경계가 불분명해집니다.",
                "how_to": "표시된 절 경계를 확인하고 마침표·세미콜론·적절한 접속사 중 하나를 선택하세요.",
                "impact": "문장 정확성 개선",
                "confidence": "high",
            }
        )

    if prompt_fit_score < 3.5:
        recs.append(
            {
                "title": "질문 응답 직접 확인",
                "why": "표면 키워드 진단의 일치도가 낮습니다. 바꿔쓰기를 놓친 것인지 실제 주제 이탈인지 사람이 확인해야 합니다.",
                "how_to": "질문에 대한 입장이나 이메일 목적이 독자에게 바로 보이는지만 확인하세요. 문제 표현을 그대로 복사할 필요는 없습니다.",
                "impact": "진단 항목·점수 자동 반영 없음",
                "confidence": "low",
            }
        )

    if metrics.evidence_hits < 2:
        recs.append(
            {
                "title": "근거 밀도 강화",
                "why": "관련 설명·예시·세부 정보는 공식 루브릭의 전개 판단에 중요합니다.",
                "how_to": "가장 중요한 주장 하나에 이유, 구체적 상황, 결과 중 필요한 내용을 보태세요.",
                "impact": "전개 충실도 개선",
                "confidence": "medium",
            }
        )

    if prompt_type == "email":
        recs.append(
            {
                "title": "이메일 격식 마감",
                "why": "수신자와 상황에 맞는 사회적 관습은 이메일 루브릭의 한 부분입니다.",
                "how_to": "상황에 맞는 인사·목적·정중성을 확인하되 고정 문구를 억지로 늘리지 마세요.",
                "impact": "의사소통 적절성 개선",
                "confidence": "medium",
            }
        )
    else:
        recs.append(
            {
                "title": "토론 기여 명료화",
                "why": "명확한 입장과 관련 지원이 온라인 토론 기여의 핵심입니다.",
                "how_to": "입장과 그 이유가 자연스럽게 이어지는지 확인하세요. 결론·학생 이름·특정 문단 수는 필수가 아닙니다.",
                "impact": "과제 수행 명료도 개선",
                "confidence": "medium",
            }
        )

    if current_score_0_5 >= 3.5:
        recs.append(
            {
                "title": "고득점 어휘 치환",
                "why": "상위 구간에서는 어휘 정밀도가 당락을 만듭니다.",
                "how_to": "good/bad/thing 같은 일반어를 beneficial/detrimental/factor로 치환하세요.",
                "impact": "+0.1~0.2",
                "confidence": "medium",
            }
        )

    return recs[:8]


def build_top_priority_actions(recs: list[dict[str, str]], top_n: int = 3) -> list[dict[str, str]]:
    def impact_value(text: str) -> float:
        nums = [float(x) for x in re.findall(r"\d+\.\d+|\d+", text)]
        if not nums:
            return 0.0
        return max(nums)

    confidence_weight = {"high": 0.2, "medium": 0.1, "low": 0.0}
    ranked = sorted(
        recs,
        key=lambda x: impact_value(str(x.get("impact", ""))) + confidence_weight.get(str(x.get("confidence", "medium")), 0.0),
        reverse=True,
    )
    return ranked[:top_n]


def apply_corrections_to_essay(essay_text: str, corrections: list[dict[str, Any]]) -> str:
    sentence_fixes: dict[str, str] = {}
    for item in corrections:
        sentence = str(item.get("sentence", "")).strip()
        corrected = str(item.get("corrected", "")).strip()
        if not sentence or not corrected:
            continue
        sentence_fixes[sentence] = corrected

    rewritten = essay_text
    for original, improved in sentence_fixes.items():
        rewritten = rewritten.replace(original, improved, 1)
    return rewritten


def build_revision_diff(original: str, revised: str, max_lines: int = 80) -> list[str]:
    old_lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", original.strip()) if s.strip()]
    new_lines = [s.strip() for s in re.split(r"(?<=[.!?])\s+", revised.strip()) if s.strip()]
    diff = list(difflib.ndiff(old_lines, new_lines))
    compact = [line for line in diff if line.startswith("- ") or line.startswith("+ ")]
    return compact[:max_lines]


def build_target_eta(rows: list[dict[str, Any]], current_score_0_5: float, target_score_0_5: float) -> dict[str, Any]:
    if current_score_0_5 >= target_score_0_5:
        return {
            "estimated_attempts": 0,
            "pace_label": "on_target",
            "message": "이미 목표 점수권에 도달했습니다.",
        }

    return {
        "estimated_attempts": 0,
        "pace_label": "not_estimated",
        "message": "제출 횟수만으로 목표 도달 시점을 신뢰성 있게 예측할 수 없습니다. 수정본을 같은 문제와 조건으로 재채점해 변화를 확인하세요.",
    }


def build_sentence_variety(essay_text: str) -> dict[str, Any]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    lengths = [len(_tokens(s)) for s in sentences]
    if not lengths:
        return {
            "short_ratio": 0.0,
            "medium_ratio": 0.0,
            "long_ratio": 0.0,
            "recommendation": "문장 데이터를 찾지 못했습니다.",
        }

    n = len(lengths)
    short = sum(1 for x in lengths if x <= 10) / n
    medium = sum(1 for x in lengths if 11 <= x <= 24) / n
    long = sum(1 for x in lengths if x >= 25) / n

    if long > 0.35:
        rec = "긴 문장 비중이 높지만 길이 자체는 오류가 아닙니다. 절 관계와 문장부호가 명확한지만 확인하세요."
    elif short > 0.45:
        rec = "짧은 문장 비중이 높습니다. 근거 문장을 1~2개 확장하세요."
    elif medium < 0.35:
        rec = "문장 길이 분포가 한쪽에 치우쳤습니다. 의미 단위가 자연스럽게 읽히는지 확인하세요."
    else:
        rec = "문장 길이 분포가 균형적입니다. 현재 리듬을 유지하세요."

    return {
        "short_ratio": round(short, 2),
        "medium_ratio": round(medium, 2),
        "long_ratio": round(long, 2),
        "recommendation": rec,
    }


def rewrite_for_target(essay_text: str, current_score: float, target_score: float) -> dict:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    if not sentences:
        return {"minimal": essay_text, "aggressive": essay_text}

    minimal = essay_text
    if target_score > current_score:
        minimal = essay_text.replace("I think", "I strongly argue", 1)
        if "For example" not in minimal:
            minimal += " For example, this pattern can be observed in classroom collaboration outcomes."

    aggressive_parts = []
    for idx, sentence in enumerate(sentences[:6], start=1):
        if idx == 1:
            aggressive_parts.append(f"I firmly maintain that {sentence[0].lower() + sentence[1:] if len(sentence) > 1 else sentence}")
        else:
            aggressive_parts.append(sentence)
    aggressive = " ".join(aggressive_parts)
    if target_score > current_score:
        aggressive += " Therefore, the argument becomes stronger when each claim is linked to specific evidence and clear consequences."

    return {"minimal": minimal, "aggressive": aggressive}


def sample_compare(essay_text: str, prompt_type: str) -> dict:
    if prompt_type == "email":
        expected_points = [
            "greeting",
            "stated purpose",
            "specific details / request",
            "polite closing",
        ]
        hints = {
            "greeting": ["dear", "hi", "hello", "good morning", "to whom"],
            "stated purpose": ["i am writing", "i would like", "i want", "i am contacting", "purpose"],
            "specific details / request": ["because", "therefore", "please", "would you", "could you", "i need"],
            "polite closing": ["sincerely", "regards", "best", "thank you", "yours"],
        }
    else:
        expected_points = [
            "clear position",
            "reason 1 + example",
            "reason 2 + explanation",
            "closing insight",
        ]
        hints = {
            "clear position": ["i agree", "i disagree", "i believe", "i think"],
            "reason 1 + example": ["first", "for example", "for instance"],
            "reason 2 + explanation": ["second", "because", "therefore", "as a result"],
            "closing insight": ["overall", "in conclusion", "therefore"],
        }

    lowered = essay_text.lower()
    matched = []
    missing = []
    for point in expected_points:
        if any(key in lowered for key in hints[point]):
            matched.append(point)
        else:
            missing.append(point)

    overlap_score = round((len(matched) / len(expected_points)) * 5, 1)
    return {
        "matched_points": matched,
        "missing_points": missing,
        "overlap_score": overlap_score,
    }


def confidence_reason(
    level: str,
    prompt_fit_score: float,
    grammar_total: int,
    essay_text: str,
) -> str:
    metrics = analyze_essay(essay_text)
    reasons = []

    if metrics.word_count < 80:
        reasons.append("분량이 짧아 추정 안정성이 낮습니다")
    if prompt_fit_score < 3.0:
        reasons.append("표면 키워드 진단이 낮아 의미 적합성을 자동 확인하기 어렵습니다")
    if grammar_total >= 5:
        reasons.append("문법 오류 패턴이 다수 관찰됩니다")

    if not reasons:
        reasons.append("분량과 검출 가능한 문장 안정성이 균형적입니다")

    return f"{level.upper()} 신뢰도 판단 근거: " + "; ".join(reasons[:3])


def _rewrite_priority_action(weakness: str) -> str:
    lowered = weakness.lower()
    if "분량" in weakness:
        return "과제별 권장 최소 분량을 채우고, 주장-근거-결론 순서로 논리를 완성하세요."
    if "문단" in weakness:
        return "문단 수를 맞추기보다 아이디어 경계가 독자에게 분명한지 확인하세요."
    if "근거" in weakness or "예시" in weakness:
        return "주장마다 구체적 예시 1개와, 그 예시가 왜 중요한지 설명 1문장을 붙이세요."
    if "문법" in weakness or "수일치" in weakness or "시제" in weakness:
        return "각 문장에서 주어-동사 수일치와 시제를 먼저 확인한 뒤 제출하세요."
    if "프롬프트" in weakness or "키워드" in weakness or "적합성" in weakness:
        return "문제 표현을 복사하기보다 입장이나 의사소통 목적이 직접 드러나는지 확인하세요."
    if "문장" in weakness and ("경계" in weakness or "run-on" in lowered):
        return "표시된 독립절 경계에 마침표·세미콜론·적절한 접속사를 사용하세요."
    if weakness.endswith(("하세요.", "합니다.", "입니다.")):
        return weakness
    return weakness + "을 먼저 고치세요."


def bilingual_summary(
    total_score: float,
    prompt_fit_score: float,
    weaknesses: list[str],
    prompt_fit_evaluated: bool = True,
) -> dict:
    if weaknesses:
        priority = _rewrite_priority_action(weaknesses[0])
    elif total_score >= 4.5:
        priority = "현재의 과제 충족도와 언어 정확성을 일관되게 유지하세요."
    else:
        priority = "근거를 더 구조적으로 쓰세요."
    warn = " (추가 개선 필요)" if total_score < 4.0 else ""
    fit_ko = (
        f"점수에 반영되지 않는 표면 주제 진단은 {prompt_fit_score:.1f}/5.0입니다."
        if prompt_fit_evaluated
        else "문제 지문이 없어 주제 반영도는 측정하지 않았습니다."
    )
    fit_en = (
        f"The non-scoring surface task-fit diagnostic is {prompt_fit_score:.1f}/5.0."
        if prompt_fit_evaluated
        else "Task-response fit was not measured because the prompt was not supplied."
    )
    summary_ko = f"현재 예상 과제 점수는 {total_score:.1f}/5.0{warn}입니다. {fit_ko} 가장 먼저 할 일은 {priority}"
    summary_en = f"Your current estimated task score is {total_score:.1f}/5.0{warn}. {fit_en} Top priority: {priority}"
    return {"summary_ko": summary_ko, "summary_en": summary_en, "max_score": 5.0}


def build_dashboard(rows: list[dict]) -> dict:
    if not rows:
        return {
            "attempt_count": 0,
            "avg_score_0_5": 0.0,
            "avg_prompt_fit": 0.0,
            "score_trend": [],
            "top_grammar_issues": [],
            "grammar_error_trend": [],
            "recommended_focus": [
                "첫 제출을 완료해 개인 대시보드를 시작하세요.",
                "입장·목적과 관련 지원이 명확한지 먼저 확인하세요.",
            ],
        }

    avg_score = round(
        sum(float(row.get("estimated_score_0_5", 0)) for row in rows) / len(rows), 2
    )
    evaluated_fit_rows = [row for row in rows if row.get("prompt_fit_evaluated") is not False]
    avg_prompt_fit = (
        round(
            sum(float(row.get("prompt_fit_score", 0)) for row in evaluated_fit_rows)
            / len(evaluated_fit_rows),
            2,
        )
        if evaluated_fit_rows
        else 0.0
    )

    trend = [
        {
            "submission_id": int(row.get("id", 0)),
            "score_0_5": float(row.get("estimated_score_0_5", 0)),
        }
        for row in rows[-10:]
    ]

    issues = Counter()
    for row in rows:
        g = row.get("grammar_stats", {})
        for key in ["tense", "article", "preposition", "run_on", "subject_verb", "punctuation"]:
            issues[key] += int(g.get(key, 0))

    top_grammar = [
        {"type": key, "count": count}
        for key, count in issues.most_common(3)
        if count > 0
    ]

    grammar_trend = []
    for row in rows[-10:]:
        g = row.get("grammar_stats", {})
        total_errors = int(g.get("total", 0))
        grammar_trend.append(
            {
                "submission_id": int(row.get("id", 0)),
                "total_errors": total_errors,
            }
        )

    focus = []
    if avg_prompt_fit < 3.5:
        focus.append("표면 키워드 진단을 참고하되, 실제 질문에 직접 답했는지 사람이 확인하세요.")
    if top_grammar and top_grammar[0]["type"] == "run_on":
        focus.append("표시된 독립절 연결 오류에 적절한 문장부호나 접속사를 사용하세요.")
    if avg_score < 3.5:
        focus.append("핵심 주장에 관련 이유·예시·해석 중 필요한 지원을 보태세요.")
    if not focus:
        focus.append("현재 강점을 유지하며 근거 정밀도만 높이면 0.5점 상승이 가능합니다.")

    return {
        "attempt_count": len(rows),
        "avg_score_0_5": avg_score,
        "avg_prompt_fit": avg_prompt_fit,
        "score_trend": trend,
        "top_grammar_issues": top_grammar,
        "grammar_error_trend": grammar_trend,
        "recommended_focus": focus,
    }


def build_pre_submit_checklist(prompt_type: str, prompt_text: str, essay_text: str) -> dict:
    metrics = analyze_essay(essay_text)
    grammar = grammar_error_stats(essay_text)
    prompt_fit = evaluate_prompt_fit(prompt_text, essay_text)
    min_words = 80 if prompt_type == "email" else 100

    items = [
        {
            "label": f"권장 연습 분량 {min_words}+ 단어(자동 감점 없음)",
            "status": "good" if metrics.word_count >= min_words else "warn",
            "score": 25 if metrics.word_count >= min_words else 10,
        },
        {
            "label": "관련 설명·세부 정보 포함",
            "status": "good" if metrics.evidence_hits >= 1 or metrics.sentence_count >= 4 else "warn",
            "score": 20 if metrics.evidence_hits >= 1 or metrics.sentence_count >= 4 else 8,
        },
        {
            "label": "문법 리스크 낮음",
            "status": "good" if grammar["total"] <= 2 else "warn",
            "score": 30 if grammar["total"] <= 2 else 12,
        },
        {
            "label": "표면 프롬프트 진단(점수 미반영)",
            "status": "good" if prompt_fit["score"] >= 3.5 else "warn",
            "score": 25 if prompt_fit["score"] >= 3.5 else 10,
        },
    ]
    return {"total_score": sum(i["score"] for i in items), "items": items}


def build_grammar_drills(grammar_stats: dict[str, int]) -> list[dict[str, str]]:
    drills: list[dict[str, str]] = []
    if grammar_stats.get("subject_verb", 0) > 0:
        drills.append(
            {
                "issue": "수일치",
                "wrong": "Students is under pressure.",
                "correct": "Students are under pressure.",
                "tip": "복수 주어(students)는 are/verb base를 사용하세요.",
            }
        )
    if grammar_stats.get("article", 0) > 0:
        drills.append(
            {
                "issue": "관사",
                "wrong": "This is an university policy.",
                "correct": "This is a university policy.",
                "tip": "발음 기준으로 a/an을 선택하세요 (you- 소리는 a).",
            }
        )
    if grammar_stats.get("preposition", 0) > 0:
        drills.append(
            {
                "issue": "전치사",
                "wrong": "We discussed about the plan.",
                "correct": "We discussed the plan.",
                "tip": "discuss는 about 없이 바로 목적어를 받습니다.",
            }
        )
    if grammar_stats.get("tense", 0) > 0:
        drills.append(
            {
                "issue": "시제",
                "wrong": "Yesterday, she is absent.",
                "correct": "Yesterday, she was absent.",
                "tip": "과거 시간 표현(yesterday)과 과거시제를 일치시키세요.",
            }
        )
    if grammar_stats.get("run_on", 0) > 0:
        drills.append(
            {
                "issue": "런온 문장",
                "wrong": "I studied all night, I was still nervous in class.",
                "correct": "I studied all night. However, I was still nervous in class.",
                "tip": "독립절 2개는 마침표/세미콜론+연결부사로 분리하세요.",
            }
        )
    return drills[:5]


def build_score_simulator(current_score_0_5: float, grammar_stats: dict[str, int], evidence_hits: int) -> list[dict]:
    return [
        {
            "action": "문법 교정 후 수정본을 같은 조건으로 재채점",
            "expected_delta_0_5": 0.0,
            "projected_score_0_5": current_score_0_5,
            "projected_band_1_6": None,
        },
        {
            "action": "전개 보완 후 수정본을 같은 조건으로 재채점",
            "expected_delta_0_5": 0.0,
            "projected_score_0_5": current_score_0_5,
            "projected_band_1_6": None,
        },
    ]


def build_grammar_impact(grammar_stats: dict[str, int]) -> list[dict[str, Any]]:
    issues = ["run_on", "subject_verb", "tense", "article", "preposition", "punctuation"]
    items: list[dict[str, Any]] = []
    for issue in issues:
        count = int(grammar_stats.get(issue, 0))
        if count <= 0:
            continue
        items.append(
            {
                "issue": issue,
                "count": count,
                "estimated_penalty_0_5": 0.0,
            }
        )
    items.sort(key=lambda x: int(x["count"]), reverse=True)
    return items[:6]


def build_before_after_projection(current_score_0_5: float, grammar_stats: dict[str, int]) -> dict[str, float | None]:
    return {
        "current_score_0_5": current_score_0_5,
        "projected_score_0_5": current_score_0_5,
        "current_band_1_6": None,
        "projected_band_1_6": None,
        "expected_gain_0_5": 0.0,
    }


def build_target_band_strategy(target_score_0_5: float, current_score_0_5: float) -> list[dict[str, str]]:
    gap = max(0.0, target_score_0_5 - current_score_0_5)

    if target_score_0_5 <= 3.5:
        return [
            {"title": "문법 안정화 우선", "detail": "수일치/시제/문장부호 오류를 먼저 제거해 기본 점수를 확보하세요."},
            {"title": "목적 명료화", "detail": "입장 또는 이메일 목적이 첫 읽기에 분명한지 확인하세요."},
            {"title": "지원 구체화", "detail": "가장 중요한 주장에 관련 이유나 세부 정보를 보태세요."},
        ]

    plans = [
        {"title": "논리 밀도 강화", "detail": "주장과 지원의 관계가 독자에게 명확한지 검토하세요."},
        {"title": "어휘 정밀도", "detail": "어려운 단어보다 문맥에 가장 정확한 동사와 명사를 선택하세요."},
        {"title": "문장 다양성", "detail": "짧은 문장+중간 문장+복문을 섞어 리듬과 가독성을 동시에 확보하세요."},
    ]
    if gap >= 1.0:
        plans.append({"title": "강제 재작성 루틴", "detail": "동일 주제를 2회 재작성해 오류 패턴을 줄이세요."})
    return plans[:4]


def build_repetition_training(essay_text: str) -> list[dict[str, Any]]:
    words = [w.lower() for w in re.findall(r"[A-Za-z']+", essay_text)]
    targets = {
        "good": ["beneficial", "effective", "constructive"],
        "bad": ["detrimental", "counterproductive", "harmful"],
        "thing": ["factor", "element", "aspect"],
        "very": ["highly", "significantly", "substantially"],
        "important": ["crucial", "vital", "essential"],
        "help": ["facilitate", "support", "enhance"],
    }
    items: list[dict[str, Any]] = []
    for w, alts in targets.items():
        c = words.count(w)
        if c >= 2:
            items.append({"word": w, "count": c, "alternatives": alts})
    items.sort(key=lambda x: int(x.get("count", 0)), reverse=True)
    return items[:6]


def build_examiner_feedback(total_score_0_5: float, grammar_stats: dict[str, int], prompt_fit_score: float, exam_mode: bool) -> dict:
    if not exam_mode:
        return {
            "mode": "normal",
            "comments": [
                "현재 모드는 학습형 피드백입니다.",
                "실전 채점 모드를 원하면 타이머 자동제출로 연습하세요.",
            ],
        }

    comments = []
    comments.append(f"Estimated task score: {total_score_0_5:.1f}/5.0")
    if grammar_stats.get("total", 0) >= 4:
        comments.append("Grammar control is unstable. Repeated errors limit higher bands.")
    else:
        comments.append("Grammar control is mostly stable for this level.")
    if prompt_fit_score < 3.5:
        comments.append("Surface keyword overlap is low; verify task relevance manually. This diagnostic did not change the score.")
    comments.append("Use tighter evidence and clearer sentence boundaries.")
    return {"mode": "exam", "comments": comments[:4]}


def personal_weakness_ranking(rows: list[dict[str, Any]], limit: int = 10) -> list[str]:
    recent = rows[-limit:]
    counter = Counter()
    for row in recent:
        g = row.get("grammar_stats", {})
        for key in ["run_on", "subject_verb", "tense", "article", "preposition", "punctuation"]:
            counter[key] += int(g.get(key, 0))
    ranking = [f"{k} ({v})" for k, v in counter.most_common(3) if v > 0]
    return ranking or ["no dominant pattern"]


def build_weekly_plan(weaknesses: list[str], weakness_ranking: list[str] | None = None) -> list[str]:
    # 점수 5.5 미만일 때만 학습계획 반환, 아니면 빈 리스트 (더 엄격하게)
    if weaknesses and ("점수" in weaknesses[0] or "score" in weaknesses[0] or "band" in weaknesses[0]):
        try:
            score = float(re.findall(r"[0-9.]+", weaknesses[0])[0])
            if score >= 5.5:
                return []
        except Exception:
            pass
    primary = weaknesses[0] if weaknesses else "문법 정확성"
    ranking = weakness_ranking or []
    rank_hint = ranking[0] if ranking else "run_on"
    return [
        f"월: {primary} 관련 약점 문장 15개 교정",
        "화: Task 유형별 목적·독자·지원 방식 비교 연습",
        "수: 25분 타이머 실전 작성 2회",
        "목: 첨삭 결과로 패러프레이징 20개 재작성",
        f"금: 상위 약점({rank_hint}) 집중 드릴 30문장",
        "토: 전체 에세이 2편 재작성 후 비교",
        "일: 약점 상위 3개만 집중 복습",
    ]
def template_coach(prompt_type: str) -> dict:
    if prompt_type == "email":
        return {
            "opening_templates": [
                "Dear Professor [Name], I am writing to request / inform you about ____.",
                "Hi [Name], I hope this message finds you well. I am contacting you regarding ____.",
            ],
            "body_templates": [
                "I would like to ____ because ____. Specifically, ____.",
                "The reason for my request is that ____. As a result, ____.",
            ],
            "transition_bank": ["Furthermore", "In addition", "Also", "As a result", "Therefore"],
            "closing_templates": [
                "Thank you for your time and consideration. I look forward to hearing from you. Sincerely, [Name]",
                "Please let me know if you need any additional information. Best regards, [Name]",
            ],
        }

    return {
        "opening_templates": [
            "I agree with the statement because practical outcomes matter more than theory alone.",
            "From my perspective, this policy should be supported for two key reasons.",
        ],
        "body_templates": [
            "First, ____ because ____. For example, ____.",
            "Second, ____ leads to ____. As a result, ____.",
        ],
        "transition_bank": ["First", "For example", "In addition", "Therefore", "Overall"],
        "closing_templates": [
            "For these reasons, I strongly support this approach.",
        ],
    }


def score_highlights(essay_text: str) -> list[dict]:
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]
    highlights: list[dict] = []

    for sentence in sentences[:10]:
        lowered = sentence.lower()
        length = len(_tokens(sentence))
        impact: Literal["positive", "negative", "neutral"] = "neutral"
        reason = "Sentence is acceptable but not strongly score-driving."

        if any(k in lowered for k in ["for example", "for instance", "because", "therefore"]):
            impact = "positive"
            reason = "Signals a support relationship; the surrounding idea still determines its value."
        if length < 5:
            impact = "negative"
            reason = "Too short to develop meaning for rubric credit."
        elif "thing" in lowered or "stuff" in lowered:
            impact = "negative"
            reason = "Vague wording lowers lexical precision."

        highlights.append({"sentence": sentence, "impact": impact, "reason": reason})

    return highlights


def weakness_dictionary(
    essay_text: str,
    grammar_stats: dict[str, int],
    historical_rows: list[dict[str, Any]],
) -> list[dict]:
    cards: list[dict] = []
    lowered = essay_text.lower()

    if grammar_stats.get("run_on", 0) > 0:
        cards.append(
            {
                "category": "run_on",
                "wrong_pattern": "One sentence contains too many ideas joined by commas.",
                "fix_pattern": "Split into 2 sentences and add a clear connector.",
                "tip": "Limit one sentence to one core claim + one support.",
            }
        )

    if "discuss about" in lowered:
        cards.append(
            {
                "category": "preposition",
                "wrong_pattern": "discuss about",
                "fix_pattern": "discuss",
                "tip": "The verb discuss does not take about.",
            }
        )

    if "a evidence" in lowered or "an information" in lowered:
        cards.append(
            {
                "category": "article",
                "wrong_pattern": "a evidence / an information",
                "fix_pattern": "evidence / information (uncountable)",
                "tip": "Use uncountable nouns without a/an.",
            }
        )

    historical_issue_counter = Counter()
    for row in historical_rows[-5:]:
        g = row.get("grammar_stats", {})
        for key in ["tense", "article", "preposition", "run_on", "subject_verb", "punctuation"]:
            historical_issue_counter[key] += int(g.get(key, 0))

    if historical_issue_counter:
        top_issue, top_count = historical_issue_counter.most_common(1)[0]
        cards.append(
            {
                "category": "historical_pattern",
                "wrong_pattern": f"Frequent issue: {top_issue}",
                "fix_pattern": f"Daily 5-sentence drill targeting {top_issue}",
                "tip": f"This issue appeared {top_count} times in recent submissions.",
            }
        )

    if not cards:
        cards.append(
            {
                "category": "precision",
                "wrong_pattern": "general wording",
                "fix_pattern": "claim + evidence + implication",
                "tip": "Make each body sentence carry a specific role.",
            }
        )

    return cards[:5]


def paraphrase_recommendations(essay_text: str, prompt_type: str) -> list[dict[str, str]]:
    rules = [
        (r"\bi think\b", "I would argue that", "주장 강도를 높여 학술적 톤을 만듭니다."),
        (r"\ba lot of\b", "a considerable number of", "구어체를 학술 표현으로 바꿉니다."),
        (r"\bthings\b", "factors", "모호한 일반어를 정확한 어휘로 대체합니다."),
        (r"\bvery important\b", "crucial", "문맥이 같을 때 사용할 수 있는 간결한 대안입니다."),
        (r"\bgood\b", "beneficial", "실제로 긍정적 효과를 뜻할 때 사용할 수 있는 대안입니다."),
        (r"\bbad\b", "harmful", "실제로 해로운 효과를 뜻할 때 사용할 수 있는 대안입니다."),
        (r"\bhelp\b", "support", "문맥에 따라 더 구체화할 수 있는 대안입니다."),
        (r"\bshow\b", "demonstrate", "근거가 명확히 입증할 때 사용할 수 있는 대안입니다."),
    ]
    if prompt_type == "email":
        rules.extend(
            [
                (r"\bi want to\b", "I would like to", "이메일의 공손한 요청 톤으로 조정합니다."),
                (r"\bthank you\b", "I sincerely appreciate your consideration", "맺음 문장의 정중함을 강화합니다."),
            ]
        )
    else:
        rules.extend(
            [
                (r"\bi agree\b", "I agree", "현재 표현은 이미 자연스럽습니다. 강도를 억지로 높일 필요가 없습니다."),
                (r"\bi disagree\b", "I disagree", "현재 표현은 이미 자연스럽습니다. 불필요하게 복잡하게 바꾸지 마세요."),
            ]
        )

    lowered = essay_text.lower()
    picks: list[dict[str, str]] = []
    for pattern, improved, reason in rules:
        if re.search(pattern, lowered):
            original = re.search(pattern, lowered)
            if not original:
                continue
            picks.append(
                {
                    "original": original.group(0),
                    "improved": improved,
                    "reason": reason,
                }
            )
        if len(picks) >= 6:
            break

    return picks


def personalization_advice(rows: list[dict[str, Any]]) -> dict:
    recent = rows[-5:]
    if not recent:
        return {
            "coaching_tone": "starter",
            "repeated_issues": ["Not enough history yet"],
            "next_focus": "Submit 3 essays to activate personalized trend coaching.",
        }

    avg_score = sum(float(r.get("estimated_score_0_5", 0)) for r in recent) / len(recent)
    evaluated_fit_rows = [r for r in recent if r.get("prompt_fit_evaluated") is not False]
    avg_fit = (
        sum(float(r.get("prompt_fit_score", 0)) for r in evaluated_fit_rows)
        / len(evaluated_fit_rows)
        if evaluated_fit_rows
        else 5.0
    )

    issue_counter = Counter()
    for row in recent:
        g = row.get("grammar_stats", {})
        for k, v in g.items():
            if k != "total":
                issue_counter[k] += int(v)

    repeated = [f"{k} ({v})" for k, v in issue_counter.most_common(3) if v > 0]
    tone = "direct" if avg_score >= 3.5 else "supportive"

    if avg_fit < 3.2:
        next_focus = "Verify that the response answers the task directly; exact prompt wording is not required."
    elif repeated:
        next_focus = f"Eliminate the top repeated issue first: {repeated[0]}."
    else:
        next_focus = "Increase evidence density in each body paragraph."

    return {
        "coaching_tone": tone,
        "repeated_issues": repeated or ["No dominant repeated issue"],
        "next_focus": next_focus,
    }


def pre_submit_risk(prompt_type: str, prompt_text: str, essay_text: str) -> dict:
    metrics = analyze_essay(essay_text)
    prompt_fit = evaluate_prompt_fit(prompt_text, essay_text)
    grammar = grammar_error_stats(essay_text)

    warnings: list[str] = []
    min_words = 80 if prompt_type == "email" else 100
    if metrics.word_count < min_words:
        warnings.append("분량이 권장 범위보다 부족합니다.")
    if prompt_type == "email":
        import re as _re
        if not _re.search(r"\b(dear|hi|hello|good morning|to whom)\b", essay_text, _re.IGNORECASE):
            warnings.append("이메일 인사말(Dear / Hi 등)이 없습니다.")
        if not _re.search(r"\b(sincerely|regards|best|thank you|yours)\b", essay_text, _re.IGNORECASE):
            warnings.append("이메일 맺음말(Sincerely / Best regards 등)이 없습니다.")
    if prompt_fit["score"] < 3.0:
        warnings.append("표면 키워드 일치도가 낮습니다. 실제 주제 이탈인지 바꿔쓰기인지 직접 확인하세요.")
    if grammar["run_on"] > 0:
        warnings.append("독립절 연결 오류 가능성이 있어 문장 경계를 확인하세요.")

    risk_level: Literal["low", "medium", "high"] = "low"
    if len(warnings) >= 3:
        risk_level = "high"
    elif len(warnings) >= 1:
        risk_level = "medium"

    return {
        "risk_level": risk_level,
        "warnings": warnings,
        "ready": len(warnings) == 0,
    }
