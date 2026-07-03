"""Build a Sentence 프로덕션 문항 뱅크 (SYNTHETIC — ETS 공식 문항 아님).

이 파일의 모든 문항은 이 프로젝트를 위해 직접 작성한 자체 제작 연습 문항이다.
provenance.source_type="synthetic", is_official=False로 명시하며, UI에는 반드시
"자체 제작 연습 문제 · ETS 공식 문항이 아닙니다"를 표시한다 (static/index.html
Build a Sentence 섹션 참고).

`tests/build_a_sentence_fixtures.py`의 문항(엔진 단위 테스트 전용, 3개)과는
별개로, 이 모듈은 실제 사용자 UI에 노출되는 연습 문제 세트다.
"""

from __future__ import annotations

from app.build_a_sentence_models import AllowedAnswer, BuildASentenceItem
from app.expert_models import DataSourceRecord

BUILD_SENTENCE_ITEMS_VERSION = "1.0.0"

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

BUILD_A_SENTENCE_ITEMS: list[BuildASentenceItem] = [
    BuildASentenceItem(
        item_id="bas-001",
        source_fragments=["the students", "finished", "their homework", "before dinner"],
        primary_answer="The students finished their homework before dinner.",
        allowed_answers=[
            AllowedAnswer(
                text="Before dinner, the students finished their homework.",
                rationale="부사구 전치 어순도 의미가 동일하여 허용",
            ),
        ],
        case_sensitive=False,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-002",
        source_fragments=["she", "is not", "ready", "yet"],
        primary_answer="She is not ready yet.",
        allowed_answers=[
            AllowedAnswer(text="She isn't ready yet.", rationale="축약형도 허용"),
        ],
        case_sensitive=False,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-003",
        source_fragments=["Professor Kim", "will announce", "the results", "tomorrow"],
        primary_answer="Professor Kim will announce the results tomorrow.",
        allowed_answers=[],
        case_sensitive=True,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-004",
        source_fragments=["although", "it was raining", "the game", "continued"],
        primary_answer="Although it was raining, the game continued.",
        allowed_answers=[
            AllowedAnswer(
                text="The game continued although it was raining.",
                rationale="종속절 후치 어순도 허용",
            ),
        ],
        case_sensitive=False,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-005",
        source_fragments=["many researchers", "believe", "that", "the policy", "will succeed"],
        primary_answer="Many researchers believe that the policy will succeed.",
        allowed_answers=[],
        case_sensitive=False,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-006",
        source_fragments=["neither", "the manager", "nor", "the staff", "agreed"],
        primary_answer="Neither the manager nor the staff agreed.",
        allowed_answers=[],
        case_sensitive=False,
        punctuation_policy="ignore_terminal",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-007",
        source_fragments=["having finished", "the report", "she", "left", "the office"],
        primary_answer="Having finished the report, she left the office.",
        allowed_answers=[],
        case_sensitive=False,
        punctuation_policy="ignore_all",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
    BuildASentenceItem(
        item_id="bas-008",
        source_fragments=["the more", "you practice", "the better", "you become"],
        primary_answer="The more you practice, the better you become.",
        allowed_answers=[],
        case_sensitive=False,
        punctuation_policy="ignore_all",
        contraction_policy="either_allowed",
        rubric_version=_RUBRIC_VERSION,
        provenance=_PROVENANCE,
    ),
]


def get_item(item_id: str) -> BuildASentenceItem | None:
    for item in BUILD_A_SENTENCE_ITEMS:
        if item.item_id == item_id:
            return item
    return None
