"""문법 신호 분석 단일 모듈.

scorer.py / advanced.py 세 곳에 중복돼 있던 정규식 휴리스틱을 통합하고,
올바른 영어를 오류로 계산하던 규칙(관사 "an apple", 시제 "I was",
종속절 뒤 콤마, 관계대명사 "that have", 약어 "U.S." 등)을 제거했다.

이 모듈은 결정론적이다: 같은 입력은 항상 같은 결과를 반환한다.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field

# 규칙 변경 시 반드시 버전을 올리고, 저장된 평가 결과와의 비교에 사용한다.
GRAMMAR_RULES_VERSION = "2.0.0"

_SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

# 문두에 오면 뒤따르는 "콤마 + 주어" 구조가 정상인 표지들 (종속절/전환어)
_DEPENDENT_OPENERS = re.compile(
    r"^(when|if|because|although|though|since|while|after|before|as|unless|once|"
    r"whereas|whenever|wherever|even|during|despite|in|on|at|for|from|by|with|"
    r"according|first|firstly|second|secondly|third|thirdly|finally|however|"
    r"therefore|moreover|furthermore|overall|consequently|meanwhile|thus|also|"
    r"unfortunately|fortunately|personally|generally|additionally|to|regarding|"
    r"considering|given|having|being|based|compared|thanks|besides|instead|"
    r"unlike|like)\b",
    re.IGNORECASE,
)

# 콤마 뒤 절을 정상적으로 잇는 접속사/관계사
_COMMA_CONJUNCTION = re.compile(
    r",\s*(and|but|or|so|yet|nor|for|which|who|whom|whose|where|because|although|"
    r"though|while|since|as|if|when|after|before|unless|whereas|not)\b",
    re.IGNORECASE,
)

# be동사는 유한형(is/are/was/were/am)만 포함한다. be/been/being은 원형·분사로
# 비유한(non-finite)이며, "The weather being terrible"처럼 그 자체로 절을
# 완성하지 못한다 — 여기 포함하면 문장 파편을 놓친다.
_FINITE_AUX = (
    "is|are|was|were|am|has|have|had|can|could|will|would|"
    "should|must|shall|may|might|do|does|did"
)

_FINITE_AUX_RE = re.compile(rf"^(?:{_FINITE_AUX})$", re.IGNORECASE)

# 3인칭 단수 오류 검사에서 제외할 직전 단어 (조동사/사역·지각동사/to부정사 등)
_AUX_BEFORE = {
    "do", "does", "did", "don't", "doesn't", "didn't", "can", "can't", "could",
    "couldn't", "may", "might", "must", "will", "won't", "would", "wouldn't",
    "shall", "should", "shouldn't", "to", "not", "help", "helps", "helped",
    "let", "lets", "make", "makes", "made", "watch", "see", "hear", "and", "or",
}

_UNCOUNTABLE = "information|advice|research|evidence|homework|luggage|furniture|knowledge|feedback"

# 파편(fragment) 검사에서 동사로 인정하는 흔한 원형 동사들
_COMMON_BASE_VERBS = {
    "agree", "disagree", "think", "believe", "feel", "want", "need", "know",
    "like", "argue", "support", "recommend", "hope", "prefer", "learn", "work",
    "help", "join", "offer", "enjoy", "say", "see", "go", "come", "get", "give",
    "take", "make", "let", "put", "find", "become", "seem", "mean", "keep",
    "begin", "start", "grow", "improve", "develop", "provide", "allow", "require",
    "spend", "write", "read", "teach", "study", "live", "use", "focus", "depend",
    "matter", "benefit", "suggest", "show", "understand", "remember", "choose",
    # 흔한 불규칙 과거형
    "gave", "ate", "went", "came", "got", "took", "made", "said", "saw", "found",
    "thought", "felt", "knew", "grew", "ran", "wrote", "read", "spoke", "told",
    "became", "began", "brought", "built", "bought", "chose", "drank", "drove",
    "fell", "held", "kept", "left", "lost", "met", "paid", "put", "sat", "sent",
    "spent", "stood", "taught", "understood", "won", "wore", "rose", "led",
}


def split_sentences(text: str) -> list[str]:
    return [s.strip() for s in _SENTENCE_SPLIT.split(text.strip()) if s.strip()]


def starts_with_vowel_sound(word: str) -> bool:
    lowered = word.lower()
    if lowered.startswith(("uni", "usa", "use", "user", "usu", "euro", "one", "once", "ufo", "uk", "us")):
        return False
    if lowered.startswith(("hour", "honest", "honor", "honour", "heir")):
        return True
    return bool(re.match(r"^[aeiou]", lowered))


def count_article_mismatch(text: str) -> int:
    """a/an 이 뒤 단어의 '소리'와 어긋나는 경우만 계산한다 ("a apple", "an book")."""
    count = 0
    for m in re.finditer(r"\b(a|an)\s+([A-Za-z][A-Za-z'\-]*)", text, flags=re.IGNORECASE):
        article = m.group(1).lower()
        word = m.group(2)
        vowel = starts_with_vowel_sound(word)
        if (article == "a" and vowel) or (article == "an" and not vowel):
            count += 1
    return count


def _prev_word(text: str, start: int) -> str:
    m = re.search(r"([a-z']+)\W*$", text[:start].lower())
    return m.group(1) if m else ""


def _count_filtered(text: str, pattern: str, banned_prev: set[str]) -> int:
    """직전 단어가 banned_prev 에 없을 때만 매치를 계산한다."""
    count = 0
    for m in re.finditer(pattern, text, flags=re.IGNORECASE):
        if _prev_word(text, m.start()) not in banned_prev:
            count += 1
    return count


def _has_finite_verb_evidence(text: str) -> bool:
    """절(clause) 후보에 유한동사가 있는지 판단한다 (주어가 대명사든 명사든 무관).

    -ing 단독은 비유한(분사/동명사)이므로 증거로 인정하지 않는다 — be동사가
    있으면 그 be동사 자체가 이미 유한동사 증거로 잡힌다.
    """
    tokens = re.findall(r"[A-Za-z']+", text)
    return any(
        _FINITE_AUX_RE.fullmatch(t)
        or t.lower() in _COMMON_BASE_VERBS
        or (t.lower().endswith(("ed", "s")) and not t.lower().endswith("'s"))
        for t in tokens
    )


def find_comma_splices(sentences: list[str]) -> int:
    """진짜 comma splice 만 계산: 종속절 도입부/접속사 연결은 제외.

    양쪽 절이 모두 "주어 역할을 하는 단어 + 유한동사"를 갖춘 독립절처럼 보일 때만
    콤마 접속으로 판정한다. 도입구("For example, ...")는 유한동사가 없어 왼쪽
    조건에서 걸러진다.
    """
    count = 0
    for s in sentences:
        if _DEPENDENT_OPENERS.match(s):
            continue
        if "," not in s:
            continue
        if _COMMA_CONJUNCTION.search(s):
            continue
        parts = [p.strip() for p in s.split(",")]
        left_tokens = re.findall(r"[A-Za-z']+", parts[0])
        left = len(left_tokens) >= 2 and _has_finite_verb_evidence(parts[0])
        right = any(
            len(re.findall(r"[A-Za-z']+", p)) >= 2 and _has_finite_verb_evidence(p)
            for p in parts[1:]
        )
        if left and right:
            count += 1
    return count


@dataclass
class GrammarSignals:
    tense: int = 0
    article: int = 0
    preposition: int = 0
    run_on: int = 0
    comma_splice: int = 0
    subject_verb: int = 0
    punctuation: int = 0
    style: int = 0
    fragment: int = 0
    rules_version: str = GRAMMAR_RULES_VERSION
    examples: list[str] = field(default_factory=list)

    @property
    def total(self) -> int:
        return (
            self.tense + self.article + self.preposition + self.run_on
            + self.comma_splice + self.subject_verb + self.punctuation
            + self.style + self.fragment
        )

    @property
    def repeated_error(self) -> bool:
        worst = max(
            self.tense, self.article, self.preposition,
            self.run_on + self.comma_splice, self.subject_verb,
            self.punctuation, self.style,
        )
        return self.total >= 6 or worst >= 4

    @property
    def severe_breakdown(self) -> bool:
        return (
            (self.run_on + self.comma_splice) >= 3
            or self.fragment >= 3
            or self.total >= 12
        )

    def as_stats_dict(self) -> dict[str, int]:
        """기존 GrammarStats 모델(7키) 하위 호환 형태."""
        return {
            "tense": self.tense,
            "article": self.article,
            "preposition": self.preposition,
            "run_on": self.run_on + self.comma_splice,
            "subject_verb": self.subject_verb,
            "punctuation": self.punctuation,
            "total": self.total,
        }


def analyze_grammar(essay_text: str) -> GrammarSignals:
    lowered = essay_text.lower()
    sentences = split_sentences(essay_text)
    sig = GrammarSignals()

    # ── 관사 ────────────────────────────────────────────────────────────
    sig.article += count_article_mismatch(essay_text)
    sig.article += len(re.findall(rf"\b(a|an)\s+({_UNCOUNTABLE})\b", lowered))
    sig.article += len(re.findall(rf"\bmany\s+({_UNCOUNTABLE})s?\b", lowered))
    sig.article += len(re.findall(r"\bfewer\s+peoples\b|\bmuch\s+(books|people|students|reasons)\b", lowered))
    sig.article += len(re.findall(r"\bfrom\s+internet\b", lowered))

    # ── 전치사 결합 ─────────────────────────────────────────────────────
    sig.preposition += len(re.findall(r"\bdiscuss(?:es|ed)?\s+about\b|\bmention(?:s|ed)?\s+about\b", lowered))
    sig.preposition += len(re.findall(r"\bin\s+nowadays\b|\bmarried\s+with\b|\bdepends?\s+of\b|\binterested\s+on\b|\bdiscuss\s+on\b", lowered))
    sig.preposition += len(re.findall(r"\baccording\s+to\s+me\b|\bdespite\s+of\b|\bdifferent\s+with\b", lowered))
    sig.preposition += len(re.findall(r"\bbetween\s+\w+\s+to\s+\w+\b", lowered))

    # ── 시제 ────────────────────────────────────────────────────────────
    # 과거 표지 + 현재형 be 가 같은 절에 있는 경우 (has 는 현재완료 정상 사용이 많아 제외)
    sig.tense += len(re.findall(r"\byesterday\b[^.?!]{0,40}\b(is|are|go|goes|come|comes)\b", lowered))
    sig.tense += len(re.findall(r"\b(last\s+(?:year|week|month))\b[^.?!]{0,40}\b(is|are)\b", lowered))
    # "I was" 는 올바른 영어 — we/they was 만 오류
    sig.tense += len(re.findall(r"\b(we|they)\s+was\b", lowered))
    # 가정법(if/wish/though ... were)은 제외
    sig.tense += len(re.findall(r"(?<!if\s)(?<!wish\s)(?<!though\s)\b(he|she|it)\s+were\b", lowered))
    sig.tense += len(re.findall(r"\bwill\s+(goes|comes|went|came|did|has)\b", lowered))
    sig.tense += len(re.findall(r"\bdid\s+not\s+(went|came|had|was|were|got|took|made|said)\b", lowered))
    sig.tense += len(re.findall(r"\bhave\s+(went|came|ate|wrote|took|drank|ran|began|spoke)\b", lowered))

    # ── 수일치 ──────────────────────────────────────────────────────────
    sig.subject_verb += len(re.findall(r"\b(people|students|children|they|we)\s+is\b", lowered))
    # 조동사/사역동사 뒤 원형은 정상이므로 직전 단어 필터 적용
    sig.subject_verb += _count_filtered(
        essay_text,
        r"\b(he|she|it)\s+(go|have|do|need|want|make|mention|suggest|show|mean|help|give|take)\b",
        _AUX_BEFORE,
    )
    sig.subject_verb += len(re.findall(r"\b(they|we|i)\s+(needs|goes|has|does|wants|makes|suggests|shows|gives|takes|helps)\b", lowered))
    sig.subject_verb += len(re.findall(r"\bthere\s+is\s+(many|several|numerous|two|three|four|five|six|students|people|reasons|ways|benefits)\b", lowered))
    sig.subject_verb += len(re.findall(r"\bone\s+of\s+the\s+\w+\s+(are|have|do|were)\b", lowered))
    sig.subject_verb += len(re.findall(r"\bthe\s+number\s+of\s+\w+\s+are\b|\ba\s+number\s+of\s+\w+\s+is\b", lowered))
    sig.subject_verb += len(re.findall(r"\b(people|children)\s+has\b", lowered))
    sig.subject_verb += len(re.findall(r"\b(many|several|few)\s+(student|reason|way|benefit|problem|example|idea|factor)\b(?!s)", lowered))
    # 관계대명사 that/it 은 선행사에 따라 복수 동사가 정상이므로 this 만 검사
    sig.subject_verb += len(re.findall(r"\bthis\s+(are|were)\b", lowered))
    sig.subject_verb += len(re.findall(r"\beveryone\s+(are|have|were)\b", lowered))
    sig.subject_verb += len(re.findall(r"\b(he|she|it)\s+don't\b|\b(i|we|they)\s+doesn't\b", lowered))

    # ── run-on / comma splice ───────────────────────────────────────────
    # 35단어 이상 단문(접속사 나열)은 가독성/문법 위험이 커진다는 기존 제품 기준과 일치.
    sig.run_on += sum(len(re.findall(r"[A-Za-z']+", s)) > 35 for s in sentences)
    sig.comma_splice += find_comma_splices(sentences)

    # ── 문장부호 ────────────────────────────────────────────────────────
    # 마지막 문장 외 중간 문장의 종결부호 누락 (최대 2까지만 반영)
    missing_terminal = sum(1 for s in sentences if not re.search(r"[.!?]$", s))
    sig.punctuation += min(2, missing_terminal)
    sig.punctuation += len(re.findall(r"\s,{2,}|\.{3,}", essay_text))
    # 마침표 두 개(생략부호 3개 미만) — 흔한 오타. 약어 뒤 대문자 시작 문장은 제외.
    sig.punctuation += len(re.findall(r"[a-z]\.\.(?!\.)", essay_text))
    # 마침표 뒤 공백 누락 — "word.Next" 형태만 (약어 "U.S.", "e.g." 는 제외)
    sig.punctuation += len(re.findall(r"[a-z]{2}[.!?][A-Z][a-z]", essay_text))

    # ── 스타일/어법 ─────────────────────────────────────────────────────
    sig.style += len(re.findall(r"\b(could|should|would)\s+of\b", lowered))
    sig.style += len(re.findall(r"\bmore\s+(better|worse|easier|harder|bigger|smaller)\b|\bmost\s+(best|easiest|biggest)\b", lowered))
    sig.style += len(re.findall(r"\bi\s+am\s+agree\b|\bi'm\s+agree\b", lowered))
    sig.style += len(re.findall(r"\bif\s+i\s+was\b", lowered))
    sig.style += len(re.findall(r"\b(people|students|children)\s+which\b", lowered))
    sig.style += len(re.findall(r"\bcan\s+able\s+to\b", lowered))
    # 동명사만 취하는 동사 뒤에 to부정사가 온 경우 (suggest/enjoy/avoid/finish/mind/recommend)
    sig.style += len(re.findall(r"\b(suggest|suggests|suggested|enjoy|enjoys|enjoyed|avoid|avoids|avoided|finish|finishes|finished|mind|minds|minded|recommend|recommends|recommended|consider|considers|considered)\s+to\s+[a-z]+\b", lowered))

    # ── 문장 파편 ───────────────────────────────────────────────────────
    for s in sentences:
        tokens = re.findall(r"[A-Za-z']+", s)
        if len(tokens) < 6:
            continue
        if not _has_finite_verb_evidence(s):
            sig.fragment += 1

    return sig


def grammar_stats(essay_text: str) -> dict[str, int]:
    """기존 grammar_error_stats 하위 호환 래퍼."""
    return analyze_grammar(essay_text).as_stats_dict()
