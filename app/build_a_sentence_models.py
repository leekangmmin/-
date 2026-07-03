"""Build a Sentence 문항/정답 스키마.

**중요**: 이 모듈과 관련 데이터 파일 어디에도 ETS 공식 문항을 포함하지 않는다.
`tests/build_a_sentence_fixtures.py`의 모든 문항은 이 프로젝트를 위해 직접
작성한 자체 제작 연습 문항이며, provenance에 `source_type: synthetic`으로
명시한다. UI/문서 어디에서도 "공식 문제"로 표시하면 안 된다.
"""

from __future__ import annotations

from typing import Literal, Optional

from pydantic import BaseModel, Field

from app.expert_models import DataSourceRecord

PunctuationPolicy = Literal["strict", "ignore_terminal", "ignore_all"]
ContractionPolicy = Literal["require_expanded", "require_contracted", "either_allowed"]


class AllowedAnswer(BaseModel):
    text: str
    rationale: str = ""  # 왜 이 변형도 정답으로 인정하는지


Difficulty = Literal["easy", "medium", "hard"]


class BuildASentenceItem(BaseModel):
    item_id: str
    source_fragments: list[str]  # 학생에게 주어지는 어순이 섞인 구성요소
    primary_answer: str
    allowed_answers: list[AllowedAnswer] = Field(default_factory=list)

    case_sensitive: bool = False
    punctuation_policy: PunctuationPolicy = "ignore_terminal"
    contraction_policy: ContractionPolicy = "either_allowed"

    difficulty: Difficulty = "medium"
    grammar_tag: str = ""       # 예: "어순", "수동태", "관계절"
    explanation: str = ""       # 왜 이 어순/형태가 정답인지 (제출 후 표시)

    rubric_version: str
    provenance: DataSourceRecord


class BuildASentenceResult(BaseModel):
    item_id: str
    match_type: Literal["exact", "allowed_variant", "structural_partial", "none"]
    is_correct: bool
    matched_answer: Optional[str] = None
    normalized_submission: str
    missing_fragments: list[str] = Field(default_factory=list)
    extra_tokens: list[str] = Field(default_factory=list)
    feedback: str
    engine_version: str
