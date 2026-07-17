"""문법 신호 엔진(app/grammar.py) 품질 평가용 라벨링 데이터셋.

Phase 1 하네스는 "정상 문장 15개 오탐 0건"만 확인했다. 이는 정밀도(precision)의
일부만 보여줄 뿐, 실제 오류를 놓치지 않는지(recall)는 검증하지 않았다.
이 데이터셋은 카테고리별로 정답 라벨을 부여해 precision/recall/F1을 계산할 수 있게 한다.

라벨링 원칙:
- expects_error=True  → 이 문장은 최소 1개의 문법 오류를 포함해야 하며,
                         analyze_grammar(text).total > 0 이어야 정답(TP)이다.
- expects_error=False → 이 문장은 문법적으로 올바르며, total == 0 이어야 정답(TN)이다.
- item_type:
    true_positive : 명백한 단일 오류 문장
    true_negative : 명백히 올바른 문장
    minimal_pair  : 바로 위/아래 항목과 한 부분만 다른 대응쌍 (TP/TN 세트로 배치)
    adversarial   : 현재 정규식이 헷갈리기 쉬운 표층 패턴 (양쪽 다 포함)
    contextual    : 문장만 보면 애매하지만 이 데이터셋 맥락에서는 명확한 사례

category는 app/grammar.py 의 세부 카운터에 최대한 매핑하되, 엔진이 아예 다루지
않는 언어 현상(예: pronoun reference, word form, collocation)은 "not_implemented"로
표시한 category를 사용해 recall이 0으로 나오는 것이 버그가 아니라 커버리지 공백임을
명시한다.
"""

from __future__ import annotations

# 라벨/카테고리/문항 구성을 바꾸면 올린다.
GRAMMAR_FIXTURE_VERSION = "1.0.0"

from dataclasses import dataclass


@dataclass(frozen=True)
class GrammarEvalItem:
    id: str
    category: str
    item_type: str
    text: str
    expects_error: bool
    note: str = ""


DATASET: list[GrammarEvalItem] = [
    # ── a/an ─────────────────────────────────────────────────────────────
    GrammarEvalItem("aan_tp_1", "a_an", "true_positive", "She ate a apple this morning.", True),
    GrammarEvalItem("aan_tp_2", "a_an", "true_positive", "He read an book about history.", True),
    GrammarEvalItem("aan_tn_1", "a_an", "true_negative", "She ate an apple this morning.", False),
    GrammarEvalItem("aan_tn_2", "a_an", "true_negative", "He read a book about history.", False),
    GrammarEvalItem("aan_mp_err", "a_an", "minimal_pair", "It was a honor to receive the award.", True, "silent h"),
    GrammarEvalItem("aan_mp_ok", "a_an", "minimal_pair", "It was an honor to receive the award.", False, "silent h"),
    GrammarEvalItem("aan_adv_ok", "a_an", "adversarial", "She is a university student studying economics.", False, "university sounds like starts with vowel letter but consonant sound"),
    GrammarEvalItem("aan_adv_ok2", "a_an", "adversarial", "It took an hour to finish the assignment.", False, "silent h"),

    # ── subject-verb agreement ──────────────────────────────────────────
    GrammarEvalItem("sva_tp_1", "subject_verb", "true_positive", "The students is preparing for the exam.", True),
    GrammarEvalItem("sva_tp_2", "subject_verb", "true_positive", "There is many reasons to support this policy.", True),
    GrammarEvalItem("sva_tp_3", "subject_verb", "true_positive", "He don't understand the assignment.", True),
    GrammarEvalItem("sva_tn_1", "subject_verb", "true_negative", "The students are preparing for the exam.", False),
    GrammarEvalItem("sva_tn_2", "subject_verb", "true_negative", "There are many reasons to support this policy.", False),
    GrammarEvalItem("sva_mp_err", "subject_verb", "minimal_pair", "One of the students have finished the project.", True),
    GrammarEvalItem("sva_mp_ok", "subject_verb", "minimal_pair", "One of the students has finished the project.", False),
    GrammarEvalItem("sva_adv_ok", "subject_verb", "adversarial", "Students that have completed the internship report higher confidence.", False, "관계절 that have는 정상"),
    GrammarEvalItem("sva_adv_ok2", "subject_verb", "adversarial", "Does he have enough evidence to support the claim?", False, "조동사 의문문"),

    # ── tense ────────────────────────────────────────────────────────────
    GrammarEvalItem("tense_tp_1", "tense", "true_positive", "Yesterday, the results is announced to the class.", True),
    GrammarEvalItem("tense_tp_2", "tense", "true_positive", "They was excited about the upcoming trip.", True),
    GrammarEvalItem("tense_tn_1", "tense", "true_negative", "Yesterday, the results were announced to the class.", False),
    GrammarEvalItem("tense_tn_2", "tense", "true_negative", "They were excited about the upcoming trip.", False),
    GrammarEvalItem("tense_mp_err", "tense", "minimal_pair", "He were tired after the long meeting.", True),
    GrammarEvalItem("tense_mp_ok", "tense", "minimal_pair", "He was tired after the long meeting.", False),
    GrammarEvalItem("tense_adv_ok", "tense", "adversarial", "I was late for class because of traffic.", False, "'I was'는 정상"),
    GrammarEvalItem("tense_adv_ok2", "tense", "adversarial", "If it were possible, I would attend the seminar.", False, "가정법"),

    # ── comma splice ─────────────────────────────────────────────────────
    GrammarEvalItem("splice_tp_1", "comma_splice", "true_positive", "I like the class, it is very interesting.", True),
    GrammarEvalItem("splice_tp_2", "comma_splice", "true_positive", "She finished the report, she submitted it early.", True),
    GrammarEvalItem("splice_tn_1", "comma_splice", "true_negative", "I like the class because it is very interesting.", False),
    GrammarEvalItem("splice_tn_2", "comma_splice", "true_negative", "She finished the report, and she submitted it early.", False),
    GrammarEvalItem("splice_mp_err", "comma_splice", "minimal_pair", "The exam was difficult, many students struggled.", True),
    GrammarEvalItem("splice_mp_ok", "comma_splice", "minimal_pair", "The exam was difficult, so many students struggled.", False),

    # ── subordinate clause (오탐 방지 검증) ──────────────────────────────
    GrammarEvalItem("subord_tn_1", "subordinate_clause", "true_negative", "When I was young, I joined a debate club.", False),
    GrammarEvalItem("subord_tn_2", "subordinate_clause", "true_negative", "Because they practiced daily, they improved quickly.", False),
    GrammarEvalItem("subord_tn_3", "subordinate_clause", "true_negative", "Although the task was difficult, we finished it together.", False),
    GrammarEvalItem("subord_tn_4", "subordinate_clause", "true_negative", "While she was studying, her phone kept ringing.", False),
    GrammarEvalItem("subord_adv_ok", "subordinate_clause", "adversarial", "Since last year, she has improved significantly in writing.", False, "since+현재완료는 정상"),

    # ── relative clause ──────────────────────────────────────────────────
    GrammarEvalItem("rel_tn_1", "relative_clause", "true_negative", "Students that have completed an internship report higher confidence.", False),
    GrammarEvalItem("rel_tn_2", "relative_clause", "true_negative", "The book which I borrowed from the library was excellent.", False),
    GrammarEvalItem("rel_tp_1", "relative_clause", "true_positive", "Students which have completed an internship report higher confidence.", True, "사람에 which 사용"),

    # ── conditional ──────────────────────────────────────────────────────
    GrammarEvalItem("cond_tn_1", "conditional", "true_negative", "If it were possible, I would join the program.", False),
    GrammarEvalItem("cond_tp_1", "conditional", "true_positive", "If I was a teacher, I will help students more.", True),
    GrammarEvalItem("cond_tn_2", "conditional", "true_negative", "If I were a teacher, I would help students more.", False),

    # ── article omission ─────────────────────────────────────────────────
    GrammarEvalItem("artom_tp_1", "article", "true_positive", "She gave me a information about the program.", True),
    GrammarEvalItem("artom_tn_1", "article", "true_negative", "She gave me some information about the program.", False),
    GrammarEvalItem("artom_tp_2", "article", "true_positive", "Many information is available online.", True),

    # ── countability ─────────────────────────────────────────────────────
    GrammarEvalItem("count_tp_1", "countability", "true_positive", "I need many advices before the interview.", True),
    GrammarEvalItem("count_tn_1", "countability", "true_negative", "I need much advice before the interview.", False),

    # ── preposition ──────────────────────────────────────────────────────
    GrammarEvalItem("prep_tp_1", "preposition", "true_positive", "We should discuss about the plan tomorrow.", True),
    GrammarEvalItem("prep_tp_2", "preposition", "true_positive", "This result depends of many factors.", True),
    GrammarEvalItem("prep_tn_1", "preposition", "true_negative", "We should discuss the plan tomorrow.", False),
    GrammarEvalItem("prep_tn_2", "preposition", "true_negative", "This result depends on many factors.", False),
    GrammarEvalItem("prep_adv_ok", "preposition", "adversarial", "Compared with last semester, her grades improved.", False, "compared with은 정상"),

    # ── pronoun reference (엔진 미구현 — 커버리지 공백 확인용) ───────────
    GrammarEvalItem("pron_tp_1", "pronoun_reference", "true_positive", "When Sarah met Amy, she gave her the book.", True, "지시대상 모호 — 현재 엔진은 탐지 불가"),
    GrammarEvalItem("pron_tn_1", "pronoun_reference", "true_negative", "Sarah gave Amy the book because Amy needed it.", False),

    # ── fragments ────────────────────────────────────────────────────────
    GrammarEvalItem("frag_tp_1", "fragment", "true_positive", "Although the weather being terrible outside today.", True),
    GrammarEvalItem("frag_tn_1", "fragment", "true_negative", "Although the weather was terrible, we went outside today.", False),
    GrammarEvalItem("frag_tp_2", "fragment", "true_positive", "Because of the new policy affecting every department here.", True),

    # ── run-on sentence ──────────────────────────────────────────────────
    GrammarEvalItem(
        "long_complex_tn_1", "run_on", "true_negative",
        "The professor explained the assignment in great detail and then answered every single question from students "
        "and continued discussing the grading rubric and the deadline extension policy for over thirty minutes without "
        "any pause at all before finally moving on to the next topic of the lecture.",
        False,
        "길고 다소 무거운 문장이지만 길이 자체는 문법 오류가 아님",
    ),
    GrammarEvalItem(
        "runon_tn_1", "run_on", "true_negative",
        "The professor explained the assignment in detail. Then she answered every question from students.",
        False,
    ),

    # ── punctuation ──────────────────────────────────────────────────────
    GrammarEvalItem("punc_tp_1", "punctuation", "true_positive", "This is wrong..He forgot the period before.", True),
    GrammarEvalItem("punc_tn_1", "punctuation", "true_negative", "This is correct. He remembered the period before.", False),

    # ── abbreviation (오탐 방지 검증) ────────────────────────────────────
    GrammarEvalItem("abbr_tn_1", "abbreviation", "true_negative", "The U.S. economy grew rapidly, e.g. in the tech sector.", False),
    GrammarEvalItem("abbr_tn_2", "abbreviation", "true_negative", "She has a Ph.D. in linguistics from a top university.", False),

    # ── capitalization (엔진 미구현 — 커버리지 공백 확인용) ──────────────
    GrammarEvalItem("cap_tp_1", "capitalization", "true_positive", "the teacher explained the assignment clearly.", True, "문두 소문자 — 현재 엔진은 탐지 불가"),
    GrammarEvalItem("cap_tn_1", "capitalization", "true_negative", "The teacher explained the assignment clearly.", False),

    # ── word form (엔진 미구현 — 커버리지 공백 확인용) ───────────────────
    GrammarEvalItem("wf_tp_1", "word_form", "true_positive", "She was very success in her final presentation.", True, "success(명사) vs successful(형용사) — 미구현"),
    GrammarEvalItem("wf_tn_1", "word_form", "true_negative", "She was very successful in her final presentation.", False),

    # ── infinitive/gerund ────────────────────────────────────────────────
    GrammarEvalItem("infger_tp_1", "infinitive_gerund", "true_positive", "The professor suggested to review the material again.", True, "style 카운터로 집계"),
    GrammarEvalItem("infger_tn_1", "infinitive_gerund", "true_negative", "The professor suggested reviewing the material again.", False),

    # ── collocation (엔진 미구현 — 커버리지 공백 확인용) ─────────────────
    GrammarEvalItem("colloc_tp_1", "collocation", "true_positive", "He made a big mistake by doing this decision.", True, "make a decision 관용결합 — 미구현"),
    GrammarEvalItem("colloc_tn_1", "collocation", "true_negative", "He made a big mistake by making this decision.", False),
]
