from __future__ import annotations

import difflib
import re
from collections import Counter
from typing import Any, Literal

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


def evaluate_prompt_fit(prompt_text: str, essay_text: str) -> dict:
    pkeys = _keywords(prompt_text, top_n=10)
    essay_words = set(_tokens(essay_text))
    matched = [k for k in pkeys if k in essay_words]
    missing = [k for k in pkeys if k not in essay_words]

    overlap_ratio = (len(matched) / len(pkeys)) if pkeys else 0.0

    score = 2.0
    if overlap_ratio >= 0.6:
        score += 2.2
    elif overlap_ratio >= 0.4:
        score += 1.5
    elif overlap_ratio >= 0.2:
        score += 0.8

    if any(marker in essay_text.lower() for marker in CLAIM_MARKERS):
        score += 0.4
    score = max(0.0, min(5.0, round(score * 2) / 2))

    reason_en = (
        f"Keyword overlap {len(matched)}/{len(pkeys)}. "
        f"Matched: {', '.join(matched[:4]) if matched else 'none'}"
    )
    reason_ko = (
        f"문제 핵심 키워드 일치 {len(matched)}/{len(pkeys)}. "
        f"일치 단어: {', '.join(matched[:4]) if matched else '없음'}"
    )

    return {
        "score": score,
        "reason_en": reason_en,
        "reason_ko": reason_ko,
        "matched_keywords": matched[:8],
        "missing_keywords": missing[:8],
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


def grammar_error_stats(essay_text: str) -> dict:
    lowered = essay_text.lower()
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()]

    run_on = sum(len(_tokens(s)) > 32 for s in sentences)
    run_on += sum(bool(re.search(r",\s+(i|we|they|he|she|it)\s+\w+", s.lower())) for s in sentences)
    article = len(re.findall(r"\b(a|an)\s+[aeiou]\w+", lowered))
    article += len(re.findall(r"\b(an)\s+[^aeiou\W]\w+", lowered))
    article += len(re.findall(r"\b(a|an)\s+(information|advice|research|evidence)\b", lowered))

    preposition = len(re.findall(r"\bdiscuss about\b|\bmention about\b", lowered))
    preposition += len(re.findall(r"\bin nowadays\b|\bmarried with\b", lowered))
    tense = len(re.findall(r"\byesterday\b.*\b(is|are)\b", lowered))
    tense += len(re.findall(r"\b(last year|last week|in \d{4})\b[^.?!]{0,40}\b(is|are|has)\b", lowered))
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

    total = run_on + article + preposition + tense + subject_verb + punctuation + style
    return {
        "tense": tense,
        "article": article,
        "preposition": preposition,
        "run_on": run_on,
        "subject_verb": subject_verb,
        "punctuation": punctuation,
        "total": total,
    }


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

        lowered = sentence.lower()

        m_subj = re.search(r"\b(people|students|they)\s+is\b", lowered)
        if m_subj:
            fixed = re.sub(r"\bis\b", "are", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_subj.group(0),
                fixed,
                "복수 주어(people/students/they)에는 보통 are를 사용합니다.",
                "high",
            )

        m_3p = re.search(r"\b(he|she|it)\s+(go|have|do)\b", lowered)
        if m_3p:
            fixed = re.sub(r"\b(he|she|it)\s+go\b", r"\1 goes", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\b(he|she|it)\s+have\b", r"\1 has", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\b(he|she|it)\s+do\b", r"\1 does", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_3p.group(0),
                fixed,
                "3인칭 단수 주어(he/she/it)에는 동사에 -s 형태가 필요합니다.",
                "high",
            )

        m_num = re.search(r"\b(many|several|few)\s+student\b", lowered)
        if m_num:
            fixed = re.sub(r"\b(many|several|few)\s+student\b", r"\1 students", sentence, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "noun_number",
                m_num.group(0),
                fixed,
                "many/several/few 뒤에는 보통 복수형 명사(students)가 필요합니다.",
                "medium",
            )

        m_teacher = re.search(r"\bteacher\s+discuss\b", lowered)
        if m_teacher:
            fixed = re.sub(r"\bteacher\s+discuss\b", "teacher discusses", sentence, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_teacher.group(0),
                fixed,
                "단수 주어(teacher)에는 일반적으로 동사에 -es가 필요합니다.",
                "high",
            )

        m_art1 = re.search(r"\ba\s+[aeiou]\w+", lowered)
        if m_art1:
            fixed = re.sub(r"\ba\s+([aeiou]\w*)", r"an \1", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "article",
                m_art1.group(0),
                fixed,
                "모음 소리로 시작하는 단어 앞에서는 a보다 an이 자연스럽습니다.",
                "medium",
            )

        m_art2 = re.search(r"\ban\s+[^aeiou\W]\w+", lowered)
        if m_art2:
            fixed = re.sub(r"\ban\s+([^aeiou\W]\w*)", r"a \1", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "article",
                m_art2.group(0),
                fixed,
                "자음 소리로 시작하는 단어 앞에서는 an보다 a가 자연스럽습니다.",
                "medium",
            )

        m_uncount = re.search(r"\b(a|an)\s+(information|advice|research|evidence)\b", lowered)
        if m_uncount:
            fixed = re.sub(
                r"\b(a|an)\s+(information|advice|research|evidence)\b",
                r"\2",
                sentence,
                count=1,
                flags=re.IGNORECASE,
            )
            push(
                sentence,
                sentence_start,
                "article",
                m_uncount.group(0),
                fixed,
                "information/advice/research/evidence는 셀 수 없는 명사로 관사 a/an을 보통 쓰지 않습니다.",
                "medium",
            )

        m_prep = re.search(r"\bdiscuss about\b|\bmention about\b", lowered)
        if m_prep:
            fixed = re.sub(r"\bdiscuss about\b", "discuss", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmention about\b", "mention", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "preposition",
                m_prep.group(0),
                fixed,
                "discuss/mention은 보통 about 없이 직접 목적어를 받습니다.",
                "medium",
            )

        m_prep2 = re.search(r"\bin nowadays\b|\bmarried with\b", lowered)
        if m_prep2:
            fixed = re.sub(r"\bin nowadays\b", "nowadays", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmarried with\b", "married to", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "preposition",
                m_prep2.group(0),
                fixed,
                "전치사 결합이 부자연스럽습니다. in nowadays -> nowadays, married with -> married to를 권장합니다.",
                "medium",
            )

        m_there = re.search(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lowered)
        if m_there:
            fixed = re.sub(r"\bthere\s+is\b", "there are", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_there.group(0),
                fixed,
                "복수 명사 앞에서는 there is보다 there are가 자연스럽습니다.",
                "high",
            )

        m_oneof = re.search(r"\bone of\s+the\s+\w+\s+are\b", lowered)
        if m_oneof:
            fixed = re.sub(r"\bare\b", "is", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_oneof.group(0),
                fixed,
                "one of + 복수명사는 문장 주어가 one(단수)이므로 동사 is가 맞습니다.",
                "high",
            )

        m_children = re.search(r"\b(people|children)\s+has\b", lowered)
        if m_children:
            fixed = re.sub(r"\bhas\b", "have", sentence, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "subject_verb",
                m_children.group(0),
                fixed,
                "people/children은 복수 취급하므로 has 대신 have를 사용합니다.",
                "high",
            )

        m_of = re.search(r"\b(could|should|would)\s+of\b", lowered)
        if m_of:
            fixed = re.sub(r"\bcould\s+of\b", "could have", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bshould\s+of\b", "should have", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bwould\s+of\b", "would have", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "style",
                m_of.group(0),
                fixed,
                "구어체 표기(could/should/would of)는 문어체에서 could/should/would have가 정확합니다.",
                "medium",
            )

        m_comp = re.search(r"\bmore\s+better\b|\bmore\s+worse\b", lowered)
        if m_comp:
            fixed = re.sub(r"\bmore\s+better\b", "better", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bmore\s+worse\b", "worse", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "style",
                m_comp.group(0),
                fixed,
                "비교급 중복 표현(more better/worse)은 감점 요인이므로 단일 비교급으로 쓰세요.",
                "medium",
            )

        m_tense = re.search(r"\b(is|are)\b", lowered) if "yesterday" in lowered else None
        if m_tense:
            fixed = re.sub(r"\bis\b", "was", sentence, count=1, flags=re.IGNORECASE)
            fixed = re.sub(r"\bare\b", "were", fixed, count=1, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "tense",
                m_tense.group(0),
                fixed,
                "과거 시점(yesterday)과 현재 시제(is/are)가 섞이면 시제 일관성이 깨집니다.",
                "high",
            )

        token_count = len(_tokens(sentence))
        if token_count > 32 and (", and " in lowered or ", but " in lowered or ", so " in lowered):
            fixed = sentence.replace(", and", ". In addition,", 1).replace(", but", ". However,", 1).replace(", so", ". Therefore,", 1)
            m_runon = re.search(r",\s+(and|but|so)\b", lowered)
            push(
                sentence,
                sentence_start,
                "run_on",
                m_runon.group(0) if m_runon else sentence,
                fixed,
                "긴 문장에 접속절이 과도하게 연결되면 run-on 위험이 커집니다. 두 문장으로 나누세요.",
                "high",
            )

        m_comma = re.search(r"\b[^,]+,\s+(i|we|they|he|she|it)\s+[a-z]+", lowered)
        if m_comma:
            fixed = sentence.replace(",", ";", 1)
            push(
                sentence,
                sentence_start,
                "comma_splice",
                m_comma.group(0),
                fixed,
                "독립절 2개를 콤마만으로 연결하면 comma splice 오류가 됩니다. 세미콜론/마침표를 사용하세요.",
                "high",
            )

        m_style = re.search(r"\b(firstly|secondly|thirdly)\b", lowered)
        if m_style:
            fixed = re.sub(r"\bfirstly\b", "first", sentence, flags=re.IGNORECASE)
            fixed = re.sub(r"\bsecondly\b", "second", fixed, flags=re.IGNORECASE)
            fixed = re.sub(r"\bthirdly\b", "third", fixed, flags=re.IGNORECASE)
            push(
                sentence,
                sentence_start,
                "style",
                m_style.group(0),
                fixed,
                "TOEFL 라이팅에서는 first/second/third가 더 자연스럽고 간결합니다.",
                "low",
            )

        if sentence and not re.search(r"[.!?]$", sentence):
            fixed = sentence + "."
            push(
                sentence,
                sentence_start,
                "punctuation",
                "missing sentence end punctuation",
                fixed,
                "문장 끝 마침표/물음표/느낌표가 없으면 문장 경계가 흐려집니다.",
                "low",
            )

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

    recs.append(
        {
            "title": "문법 오류 우선 제거",
            "why": "문법은 가중치가 높아 총점에 직접적인 영향을 줍니다.",
            "how_to": "상위 오류 2개(예: 수일치, run-on)만 선택해 10문장 교정 후 재작성하세요.",
            "impact": "+0.3~0.6",
            "confidence": "high",
        }
    )

    if grammar_stats.get("run_on", 0) > 0:
        recs.append(
            {
                "title": "Run-on 분리 훈련",
                "why": "긴 문장 붕괴는 문법·가독성 동시 감점 요소입니다.",
                "how_to": "35단어 이상 문장은 마침표/세미콜론 기준으로 2문장으로 분리하세요.",
                "impact": "+0.2~0.4",
                "confidence": "high",
            }
        )

    if prompt_fit_score < 3.5:
        recs.append(
            {
                "title": "프롬프트 키워드 고정",
                "why": "질문 적합성이 낮으면 고득점이 제한됩니다.",
                "how_to": "문제 핵심어 3개를 서론/본론 첫문장에 그대로 반영하세요.",
                "impact": "+0.2~0.4",
                "confidence": "medium",
            }
        )

    if metrics.evidence_hits < 3:
        recs.append(
            {
                "title": "근거 밀도 강화",
                "why": "예시·근거가 부족하면 Example와 Content 점수가 같이 낮아집니다.",
                "how_to": "본론 문단마다 For example 문장 1개 + 결과 문장 1개를 추가하세요.",
                "impact": "+0.2~0.5",
                "confidence": "high",
            }
        )

    if prompt_type == "email":
        recs.append(
            {
                "title": "이메일 격식 마감",
                "why": "형식 누락은 Structure 점수 손실로 이어집니다.",
                "how_to": "도입 인사 + 요청 목적 + 정중한 맺음말을 고정 템플릿으로 사용하세요.",
                "impact": "+0.1~0.3",
                "confidence": "medium",
            }
        )
    else:
        recs.append(
            {
                "title": "토론형 논리 프레임",
                "why": "입장-근거-결론 프레임이 Coherence 안정화에 유리합니다.",
                "how_to": "각 본론을 주장 1문장, 근거 1문장, 해석 1문장으로 고정하세요.",
                "impact": "+0.2~0.4",
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

    recent = rows[-6:]
    deltas: list[float] = []
    for i in range(1, len(recent)):
        prev = float(recent[i - 1].get("estimated_score_0_5", 0))
        curr = float(recent[i].get("estimated_score_0_5", 0))
        deltas.append(curr - prev)

    positive = [d for d in deltas if d > 0]
    avg_gain = sum(positive) / len(positive) if positive else 0.0
    if avg_gain <= 0.01:
        return {
            "estimated_attempts": 8,
            "pace_label": "slow",
            "message": "최근 상승 추세가 약합니다. 문법 우선 전략으로 2~3회 내 반등을 노리세요.",
        }

    remain = max(0.0, target_score_0_5 - current_score_0_5)
    attempts = int(max(1, round(remain / avg_gain)))
    pace = "fast" if attempts <= 2 else ("steady" if attempts <= 5 else "slow")
    return {
        "estimated_attempts": attempts,
        "pace_label": pace,
        "message": f"현재 추세 기준 약 {attempts}회 제출 시 목표 점수 도달이 예상됩니다.",
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
        rec = "긴 문장 비중이 높습니다. 긴 문장 2개 중 1개는 분리하세요."
    elif short > 0.45:
        rec = "짧은 문장 비중이 높습니다. 근거 문장을 1~2개 확장하세요."
    elif medium < 0.35:
        rec = "중간 길이 문장 비율을 늘리면 가독성과 점수 안정성이 좋아집니다."
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

    if metrics.word_count < 120:
        reasons.append("분량이 짧아 추정 안정성이 낮습니다")
    if prompt_fit_score < 3.0:
        reasons.append("프롬프트 키워드 반영률이 낮습니다")
    if grammar_total >= 5:
        reasons.append("문법 오류 패턴이 다수 관찰됩니다")

    if not reasons:
        reasons.append("분량, 프롬프트 적합성, 문장 안정성이 균형적입니다")

    return f"{level.upper()} 신뢰도 판단 근거: " + "; ".join(reasons[:3])


def bilingual_summary(total_score: float, prompt_fit_score: float, weaknesses: list[str]) -> dict:
    summary_ko = (
        f"예상 점수는 {total_score:.1f}/5.0이며, 프롬프트 적합성은 {prompt_fit_score:.1f}/5.0입니다. "
        f"우선 보완 과제는 {weaknesses[0] if weaknesses else '근거 구체화'} 입니다."
    )
    summary_en = (
        f"Your estimated score is {total_score:.1f}/5.0, with a prompt-fit score of {prompt_fit_score:.1f}/5.0. "
        f"Top priority: {weaknesses[0] if weaknesses else 'add more specific support'}"
    )
    return {"summary_ko": summary_ko, "summary_en": summary_en}


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
                "분량과 문단 구조를 먼저 안정화하세요.",
            ],
        }

    avg_score = round(
        sum(float(row.get("estimated_score_0_5", 0)) for row in rows) / len(rows), 2
    )
    avg_prompt_fit = round(
        sum(float(row.get("prompt_fit_score", 0)) for row in rows) / len(rows), 2
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
        focus.append("문제 핵심 키워드 3개를 본문에 직접 반영하세요.")
    if top_grammar and top_grammar[0]["type"] == "run_on":
        focus.append("35단어 이상 문장을 분리해 가독성을 높이세요.")
    if avg_score < 3.5:
        focus.append("각 본론 문단에 이유-예시-해석 3요소를 넣으세요.")
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
    min_words = 100 if prompt_type == "email" else 120

    items = [
        {
            "label": f"권장 분량 {min_words}+ 단어",
            "status": "good" if metrics.word_count >= min_words else "warn",
            "score": 25 if metrics.word_count >= min_words else 10,
        },
        {
            "label": "문단 구조 충족",
            "status": "good" if metrics.paragraph_count >= (2 if prompt_type == "email" else 3) else "warn",
            "score": 20 if metrics.paragraph_count >= (2 if prompt_type == "email" else 3) else 8,
        },
        {
            "label": "문법 리스크 낮음",
            "status": "good" if grammar["total"] <= 2 else "warn",
            "score": 30 if grammar["total"] <= 2 else 12,
        },
        {
            "label": "프롬프트 적합성",
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
    if not drills:
        drills.append(
            {
                "issue": "정확성 유지",
                "wrong": "I think it is good.",
                "correct": "I argue that it is beneficial.",
                "tip": "모호한 단어(good) 대신 구체적 어휘를 선택하세요.",
            }
        )
    return drills[:5]


def build_score_simulator(current_score_0_5: float, grammar_stats: dict[str, int], evidence_hits: int) -> list[dict]:
    items: list[dict] = []
    grammar_total = int(grammar_stats.get("total", 0))

    if grammar_total >= 4:
        delta = 0.5
    elif grammar_total >= 2:
        delta = 0.25
    else:
        delta = 0.1
    projected = min(6.0, round((current_score_0_5 + delta + 1.0) * 2) / 2)
    items.append(
        {
            "action": "문법 오류 3개 줄이기",
            "expected_delta_0_5": round(delta, 2),
            "projected_band_1_6": projected,
        }
    )

    ex_delta = 0.35 if evidence_hits < 2 else 0.2
    projected2 = min(6.0, round((current_score_0_5 + ex_delta + 1.0) * 2) / 2)
    items.append(
        {
            "action": "각 본론에 구체 예시 1개 추가",
            "expected_delta_0_5": round(ex_delta, 2),
            "projected_band_1_6": projected2,
        }
    )
    return items


def build_grammar_impact(grammar_stats: dict[str, int]) -> list[dict[str, Any]]:
    weights = {
        "run_on": 0.15,
        "subject_verb": 0.14,
        "tense": 0.12,
        "article": 0.08,
        "preposition": 0.07,
        "punctuation": 0.05,
    }
    items: list[dict[str, Any]] = []
    for issue, w in weights.items():
        count = int(grammar_stats.get(issue, 0))
        if count <= 0:
            continue
        items.append(
            {
                "issue": issue,
                "count": count,
                "estimated_penalty_0_5": round(min(1.2, count * w), 2),
            }
        )
    items.sort(key=lambda x: float(x["estimated_penalty_0_5"]), reverse=True)
    return items[:6]


def build_before_after_projection(current_score_0_5: float, grammar_stats: dict[str, int]) -> dict[str, float]:
    total = int(grammar_stats.get("total", 0))
    gain = 0.1
    if total >= 8:
        gain = 0.7
    elif total >= 5:
        gain = 0.5
    elif total >= 3:
        gain = 0.35
    projected = min(5.0, round((current_score_0_5 + gain) * 2) / 2)
    current_band = round((current_score_0_5 + 1.0) * 2) / 2
    projected_band = round((projected + 1.0) * 2) / 2
    return {
        "current_score_0_5": current_score_0_5,
        "projected_score_0_5": projected,
        "current_band_1_6": current_band,
        "projected_band_1_6": projected_band,
        "expected_gain_0_5": round(projected - current_score_0_5, 2),
    }


def build_target_band_strategy(target_score_0_5: float, current_score_0_5: float) -> list[dict[str, str]]:
    target_band = round((target_score_0_5 + 1.0) * 2) / 2
    current_band = round((current_score_0_5 + 1.0) * 2) / 2
    gap = max(0.0, target_band - current_band)

    if target_band <= 4.5:
        return [
            {"title": "문법 안정화 우선", "detail": "수일치/시제/문장부호 오류를 먼저 제거해 기본 점수를 확보하세요."},
            {"title": "템플릿 고정", "detail": "서론-본론-결론 틀을 고정해 구조 점수 변동을 줄이세요."},
            {"title": "근거 최소 2개", "detail": "본론마다 이유 1개+예시 1개를 넣어 내용 충실도를 확보하세요."},
        ]

    plans = [
        {"title": "논리 밀도 강화", "detail": "주장-근거-해석 3단 문장을 문단마다 반복하세요."},
        {"title": "고급 어휘 치환", "detail": "반복되는 일반어를 학술 어휘로 치환해 표현 정밀도를 높이세요."},
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
    comments.append(f"Estimated: {total_score_0_5:.1f}/5.0")
    if grammar_stats.get("total", 0) >= 4:
        comments.append("Grammar control is unstable. Repeated errors limit higher bands.")
    else:
        comments.append("Grammar control is mostly stable for this level.")
    if prompt_fit_score < 3.5:
        comments.append("Task response is partial. Address prompt keywords more directly.")
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
    primary = weaknesses[0] if weaknesses else "문법 정확성"
    ranking = weakness_ranking or []
    rank_hint = ranking[0] if ranking else "run_on"
    return [
        f"월: {primary} 관련 약점 문장 10개 교정",
        "화: Task 유형별 템플릿 2세트 암기 + 변형 연습",
        "수: 25분 타이머 실전 작성 1회",
        "목: 첨삭 결과로 패러프레이징 15개 재작성",
        f"금: 상위 약점({rank_hint}) 집중 드릴 20문장",
        "토: 전체 에세이 1편 재작성 후 비교",
        "일: 약점 상위 2개만 집중 복습",
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
            reason = "Contains support logic or evidence markers that strengthen scoring."
        if length > 35:
            impact = "negative"
            reason = "Likely run-on sentence; clarity and grammar control may drop."
        elif length < 5:
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
        (r"\bvery important\b", "crucial", "강조를 간결한 고급 어휘로 표현합니다."),
        (r"\bgood\b", "beneficial", "평가 형용사를 더 정밀하게 바꿉니다."),
        (r"\bbad\b", "detrimental", "부정 평가를 더 학술적으로 표현합니다."),
        (r"\bhelp\b", "facilitate", "동사를 더 포멀하게 교체합니다."),
        (r"\bshow\b", "demonstrate", "근거 제시 동사의 정확도를 높입니다."),
        (r"\bbecause\b", "given that", "연결어를 변형해 어휘 반복을 줄입니다."),
        (r"\bso\b", "therefore", "논리 연결을 명확한 전환어로 만듭니다."),
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
                (r"\bi agree\b", "I strongly concur", "토론형에서 주장 강도를 높입니다."),
                (r"\bi disagree\b", "I respectfully contend", "반대 의견을 학술적으로 표현합니다."),
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

    if not picks:
        picks = [
            {
                "original": "I think",
                "improved": "From my perspective,",
                "reason": "도입 표현을 다양화하면 어휘 점수 유지에 유리합니다.",
            },
            {
                "original": "for example",
                "improved": "to illustrate,",
                "reason": "예시 연결어를 순환 사용하면 반복 감점을 줄입니다.",
            },
        ]
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
    avg_fit = sum(float(r.get("prompt_fit_score", 0)) for r in recent) / len(recent)

    issue_counter = Counter()
    for row in recent:
        g = row.get("grammar_stats", {})
        for k, v in g.items():
            if k != "total":
                issue_counter[k] += int(v)

    repeated = [f"{k} ({v})" for k, v in issue_counter.most_common(3) if v > 0]
    tone = "direct" if avg_score >= 3.5 else "supportive"

    if avg_fit < 3.2:
        next_focus = "Mirror prompt keywords in thesis and topic sentences."
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
    min_words = 100 if prompt_type == "email" else 120
    if metrics.word_count < min_words:
        warnings.append("분량이 권장 범위보다 부족합니다.")
    if prompt_type == "email":
        import re as _re
        if not _re.search(r"\b(dear|hi|hello|good morning|to whom)\b", essay_text, _re.IGNORECASE):
            warnings.append("이메일 인사말(Dear / Hi 등)이 없습니다.")
        if not _re.search(r"\b(sincerely|regards|best|thank you|yours)\b", essay_text, _re.IGNORECASE):
            warnings.append("이메일 맺음말(Sincerely / Best regards 등)이 없습니다.")
    if prompt_fit["score"] < 3.0:
        warnings.append("프롬프트 핵심 키워드 반영률이 낮습니다.")
    if grammar["run_on"] > 0:
        warnings.append("긴 문장(run-on)이 있어 감점 위험이 있습니다.")
    min_paras = 2 if prompt_type == "email" else 3
    if metrics.paragraph_count < min_paras:
        warnings.append("문단 수가 부족해 논리 구조가 약해 보일 수 있습니다.")

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
