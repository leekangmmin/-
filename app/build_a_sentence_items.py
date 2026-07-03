"""Build a Sentence 프로덕션 문항 뱅크 (SYNTHETIC — ETS 공식 문항 아님).

이 파일의 모든 문항은 이 프로젝트를 위해 직접 작성한 자체 제작 연습 문항이다.
provenance.source_type="synthetic", is_official=False로 명시하며, UI에는 반드시
"자체 제작 연습 문제 · ETS 공식 문항이 아닙니다"를 표시한다.

Phase 6: 15문항 / 난이도 3단계(easy 5, medium 5, hard 5) / 문법 태그 /
정답 설명(explanation) 포함. 문항 구성·정답·정책을 바꾸면 버전을 올린다.

`tests/build_a_sentence_fixtures.py`의 문항(엔진 단위 테스트 전용, 3개)과는
별개로, 이 모듈은 실제 사용자 UI에 노출되는 연습 문제 세트다.
"""

from __future__ import annotations

from app.build_a_sentence_models import AllowedAnswer, BuildASentenceItem
from app.expert_models import DataSourceRecord

BUILD_SENTENCE_ITEMS_VERSION = "1.1.0"

_PROVENANCE = DataSourceRecord(
    source_id="synthetic-bas-production-v1",
    title="TOEFL Writing 채점기 자체 제작 Build a Sentence 연습 문항",
    source_type="synthetic",
    accessed_at="2026-07-03T00:00:00Z",
    license_status="permissive",
    is_official=False,
    intended_usage="ui-demo",
    limitations=[
        "자체 제작 연습 문항 — ETS 공식 문항이 아님",
        "TOEFL 실제 출제 경향의 보증 없음",
    ],
)

_RUBRIC_VERSION = "bas-rubric-1.0.0"


def _item(**kwargs) -> BuildASentenceItem:
    return BuildASentenceItem(rubric_version=_RUBRIC_VERSION, provenance=_PROVENANCE, **kwargs)


BUILD_A_SENTENCE_ITEMS: list[BuildASentenceItem] = [
    # ── easy ──────────────────────────────────────────────────────────
    _item(
        item_id="bas-001",
        source_fragments=["the students", "finished", "their homework", "before dinner"],
        primary_answer="The students finished their homework before dinner.",
        allowed_answers=[
            AllowedAnswer(
                text="Before dinner, the students finished their homework.",
                rationale="부사구 전치 어순도 의미가 동일하여 허용",
            ),
        ],
        difficulty="easy",
        grammar_tag="기본 어순",
        explanation="영어 평서문의 기본 어순은 주어(the students) + 동사(finished) + 목적어(their homework)이고, 시간 부사구(before dinner)는 문장 끝이나 맨 앞에 올 수 있어요.",
    ),
    _item(
        item_id="bas-002",
        source_fragments=["she", "is not", "ready", "yet"],
        primary_answer="She is not ready yet.",
        allowed_answers=[AllowedAnswer(text="She isn't ready yet.", rationale="축약형도 허용")],
        difficulty="easy",
        grammar_tag="부정문",
        explanation="be동사 부정문은 be동사(is) 뒤에 not을 붙이고, '아직'을 뜻하는 yet은 부정문에서 문장 끝에 와요.",
    ),
    _item(
        item_id="bas-009",
        source_fragments=["we", "usually", "study", "in the library"],
        primary_answer="We usually study in the library.",
        allowed_answers=[],
        difficulty="easy",
        grammar_tag="빈도 부사",
        explanation="usually 같은 빈도 부사는 일반동사(study) 바로 앞에 와요. 장소 표현(in the library)은 문장 끝에 둡니다.",
    ),
    _item(
        item_id="bas-010",
        source_fragments=["there", "are", "many reasons", "to learn English"],
        primary_answer="There are many reasons to learn English.",
        allowed_answers=[],
        difficulty="easy",
        grammar_tag="There is/are",
        explanation="'~이 있다'는 There + be동사 구문을 써요. many reasons가 복수이므로 are를 쓰고, to learn English가 reasons를 꾸며줍니다.",
    ),
    _item(
        item_id="bas-011",
        source_fragments=["reading books", "is", "a good habit"],
        primary_answer="Reading books is a good habit.",
        allowed_answers=[],
        difficulty="easy",
        grammar_tag="동명사 주어",
        explanation="동명사구(Reading books)가 주어일 때는 단수 취급해서 동사 is를 써요.",
    ),
    # ── medium ────────────────────────────────────────────────────────
    _item(
        item_id="bas-003",
        source_fragments=["Professor Kim", "will announce", "the results", "tomorrow"],
        primary_answer="Professor Kim will announce the results tomorrow.",
        allowed_answers=[],
        case_sensitive=True,
        difficulty="medium",
        grammar_tag="고유명사·미래",
        explanation="고유명사(Professor Kim)는 항상 대문자로 시작해요. 미래 조동사 will 뒤에는 동사원형(announce)이 옵니다.",
    ),
    _item(
        item_id="bas-004",
        source_fragments=["although", "it was raining", "the game", "continued"],
        primary_answer="Although it was raining, the game continued.",
        allowed_answers=[
            AllowedAnswer(
                text="The game continued although it was raining.",
                rationale="종속절 후치 어순도 허용",
            ),
        ],
        difficulty="medium",
        grammar_tag="양보 접속사",
        explanation="although(비록 ~이지만)가 이끄는 종속절은 문장 앞이나 뒤에 올 수 있어요. 앞에 올 때는 쉼표로 주절과 구분합니다.",
    ),
    _item(
        item_id="bas-005",
        source_fragments=["many researchers", "believe", "that", "the policy", "will succeed"],
        primary_answer="Many researchers believe that the policy will succeed.",
        allowed_answers=[],
        difficulty="medium",
        grammar_tag="that절",
        explanation="believe 뒤에 that절을 붙여 '~라고 믿는다'를 표현해요. that절 안은 다시 주어(the policy) + 동사(will succeed) 순서입니다.",
    ),
    _item(
        item_id="bas-012",
        source_fragments=["the report", "was written", "by the committee", "last month"],
        primary_answer="The report was written by the committee last month.",
        allowed_answers=[],
        difficulty="medium",
        grammar_tag="수동태",
        explanation="행위의 대상(the report)을 주어로 내세울 때 수동태(was written)를 써요. 행위자는 by로 표시하고, 시간 표현은 그 뒤에 옵니다.",
    ),
    _item(
        item_id="bas-013",
        source_fragments=["students", "who study regularly", "tend to", "perform better"],
        primary_answer="Students who study regularly tend to perform better.",
        allowed_answers=[],
        difficulty="medium",
        grammar_tag="관계절",
        explanation="관계절(who study regularly)은 꾸며주는 명사(students) 바로 뒤에 붙어요. 전체 주어 뒤에 동사구(tend to perform better)가 옵니다.",
    ),
    # ── hard ──────────────────────────────────────────────────────────
    _item(
        item_id="bas-006",
        source_fragments=["neither", "the manager", "nor", "the staff", "agreed"],
        primary_answer="Neither the manager nor the staff agreed.",
        allowed_answers=[],
        difficulty="hard",
        grammar_tag="상관 접속사",
        explanation="neither A nor B(A도 B도 아닌)는 짝을 이루는 상관 접속사예요. Neither the manager nor the staff 전체가 주어가 됩니다.",
    ),
    _item(
        item_id="bas-007",
        source_fragments=["having finished", "the report", "she", "left", "the office"],
        primary_answer="Having finished the report, she left the office.",
        allowed_answers=[],
        punctuation_policy="ignore_all",
        difficulty="hard",
        grammar_tag="분사구문",
        explanation="완료 분사구문(Having finished ~)은 '~을 끝낸 후'라는 뜻으로 주절보다 먼저 일어난 일을 나타내요. 주절의 주어(she)가 분사구문의 의미상 주어입니다.",
    ),
    _item(
        item_id="bas-008",
        source_fragments=["the more", "you practice", "the better", "you become"],
        primary_answer="The more you practice, the better you become.",
        allowed_answers=[],
        punctuation_policy="ignore_all",
        difficulty="hard",
        grammar_tag="비교 구문",
        explanation="'the 비교급 ~, the 비교급 ~' 구문은 '~할수록 더 ~하다'는 뜻이에요. 각 절 안은 주어 + 동사 순서를 유지합니다.",
    ),
    _item(
        item_id="bas-014",
        source_fragments=["if", "I had known", "the answer", "I would have said", "so"],
        primary_answer="If I had known the answer, I would have said so.",
        allowed_answers=[
            AllowedAnswer(
                text="I would have said so if I had known the answer.",
                rationale="if절 후치 어순도 허용",
            ),
        ],
        punctuation_policy="ignore_all",
        difficulty="hard",
        grammar_tag="가정법 과거완료",
        explanation="과거 사실의 반대를 가정할 때 if절에는 had + 과거분사(had known), 주절에는 would have + 과거분사(would have said)를 써요.",
    ),
    _item(
        item_id="bas-015",
        source_fragments=["not only", "does exercise", "improve health", "but it also", "reduces stress"],
        primary_answer="Not only does exercise improve health, but it also reduces stress.",
        allowed_answers=[],
        punctuation_policy="ignore_all",
        difficulty="hard",
        grammar_tag="도치 구문",
        explanation="Not only가 문장 맨 앞에 오면 주어와 조동사가 도치돼요(does exercise improve). 뒤에는 but (it) also가 짝을 이룹니다.",
    ),
]


def get_item(item_id: str) -> BuildASentenceItem | None:
    for item in BUILD_A_SENTENCE_ITEMS:
        if item.item_id == item_id:
            return item
    return None
