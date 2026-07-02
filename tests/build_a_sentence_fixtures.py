"""Build a Sentence 자체 제작 연습 문항 (SYNTHETIC — ETS 공식 문항 아님).

이 파일의 모든 문항은 엔진 검증을 위해 이 프로젝트에서 직접 작성했다.
provenance.source_type="synthetic", intended_usage="ui-demo"로 명시한다.
"""

from __future__ import annotations

from app.build_a_sentence_models import AllowedAnswer, BuildASentenceItem
from app.expert_models import DataSourceRecord

# 문항 구성/정답/정책을 바꾸면 올린다.
BUILD_SENTENCE_FIXTURE_VERSION = "1.0.0"

_PROVENANCE = DataSourceRecord(
    source_id="synthetic-bas-fixtures",
    title="Synthetic Build a Sentence practice items",
    source_type="synthetic",
    accessed_at="2026-07-01T00:00:00Z",
    license_status="permissive",
    is_official=False,
    intended_usage="ui-demo",
    limitations=["자체 제작 연습 문항 — ETS 공식 문항 아님", "채점 정확도의 증거로 사용 금지"],
)

ITEM_SIMPLE = BuildASentenceItem(
    item_id="bas-synthetic-001",
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
    rubric_version="bas-rubric-1.0.0",
    provenance=_PROVENANCE,
)

ITEM_CONTRACTION = BuildASentenceItem(
    item_id="bas-synthetic-002",
    source_fragments=["she", "is not", "ready", "yet"],
    primary_answer="She is not ready yet.",
    allowed_answers=[
        AllowedAnswer(text="She isn't ready yet.", rationale="축약형도 허용"),
    ],
    case_sensitive=False,
    punctuation_policy="ignore_terminal",
    contraction_policy="either_allowed",
    rubric_version="bas-rubric-1.0.0",
    provenance=_PROVENANCE,
)

ITEM_CASE_SENSITIVE = BuildASentenceItem(
    item_id="bas-synthetic-003",
    source_fragments=["Professor Kim", "will announce", "the results", "tomorrow"],
    primary_answer="Professor Kim will announce the results tomorrow.",
    allowed_answers=[],
    case_sensitive=True,
    punctuation_policy="strict",
    contraction_policy="either_allowed",
    rubric_version="bas-rubric-1.0.0",
    provenance=_PROVENANCE,
)

ALL_ITEMS = [ITEM_SIMPLE, ITEM_CONTRACTION, ITEM_CASE_SENSITIVE]
