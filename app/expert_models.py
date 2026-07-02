"""전문가 채점 데이터 수용 구조 (Pydantic 스키마).

마스터 프롬프트 9장(전문가 데이터 수용 구조)·7장(provenance)·8장(신뢰 등급) 요구사항을
따른다. 이 모듈은 스키마 정의만 담당하고, 실제 import/저장 로직은 app/expert_data.py에 있다.

중요: 이 파일 어디에도 실제 전문가 채점 데이터를 하드코딩하지 않는다. 예시/테스트
데이터는 tests/expert_data_fixtures/ 에 SYNTHETIC EXAMPLE 로 명시하여 분리한다.
"""

from __future__ import annotations

from datetime import datetime
from typing import Literal, Optional

from pydantic import BaseModel, Field

SourceType = Literal[
    "official-specification", "official-practice", "official-research",
    "academic-paper", "licensed-corpus", "expert-rating",
    "educational-content", "synthetic", "unknown",
]

LicenseStatus = Literal[
    "public-domain", "permissive", "research-only", "link-only",
    "permission-required", "unknown",
]

CompatibilityLevel = Literal["direct", "partial", "auxiliary", "incompatible", "unknown"]

IntendedUsage = Literal[
    "rubric-reference", "development", "calibration", "validation",
    "locked-test", "safety-test", "ui-demo", "research-only",
]

DatasetSplit = Literal["development", "calibration", "validation", "locked_test"]

RaterType = Literal["expert-teacher", "trained-rater", "researcher"]

AdjudicationStatus = Literal["not-required", "required", "completed"]


class DataSourceRecord(BaseModel):
    """모든 외부 자료/전문가 데이터가 반드시 연결해야 하는 provenance 레코드."""

    source_id: str
    title: str
    publisher: Optional[str] = None
    author: Optional[str] = None
    source_type: SourceType
    source_url: Optional[str] = None
    publication_date: Optional[str] = None
    accessed_at: str
    license_status: LicenseStatus
    commercial_use_allowed: Optional[bool] = None
    redistribution_allowed: Optional[bool] = None
    is_official: bool = False
    is_human_written: Optional[bool] = None
    is_human_scored: Optional[bool] = None
    rater_count: Optional[int] = None
    score_scale: Optional[str] = None
    task_type_compatibility: list[str] = Field(default_factory=list)
    compatibility_with_current_exam: CompatibilityLevel = "unknown"
    intended_usage: IntendedUsage
    limitations: list[str] = Field(default_factory=list)
    checksum: Optional[str] = None
    notes: Optional[str] = None


class EvidenceSpanRecord(BaseModel):
    start: int
    end: int
    text: str
    dimension_id: Optional[str] = None
    annotation_type: Optional[str] = None
    explanation: Optional[str] = None
    suggested_revision: Optional[str] = None


class CorrectionRecord(BaseModel):
    original: str
    revised: str
    category: str
    explanation: str


class DimensionScoreRecord(BaseModel):
    dimension_id: str
    score: float
    max_score: float
    comment: Optional[str] = None


class RaterInfo(BaseModel):
    rater_id: str
    rater_type: RaterType
    qualification: Optional[str] = None
    confidence: Optional[float] = None


class AdjudicationInfo(BaseModel):
    status: AdjudicationStatus = "not-required"
    final_score: Optional[float] = None
    adjudicator_id: Optional[str] = None
    notes: Optional[str] = None


class ExpertRatedResponse(BaseModel):
    """전문가(강사/훈련된 채점자/연구자)가 작성하거나 채점한 답안 1건.

    같은 답안(record_id 기준 그룹)에 여러 채점자의 평가가 있을 수 있으므로,
    이 모델 자체는 "답안 + 채점자 1인의 평가"를 나타내는 단위다. 저장 시
    app/expert_data.py가 response_group_id로 같은 답안의 여러 평가를 묶는다.
    """

    record_id: str
    response_group_id: Optional[str] = None  # 동일 답안 그룹 식별자 (미지정 시 자동 생성)
    prompt_id: str
    task_type: Literal["email", "academic_discussion", "build_a_sentence"]
    prompt_text: Optional[str] = None
    response_text: str

    overall_score: float
    score_scale: str

    dimension_scores: list[DimensionScoreRecord] = Field(default_factory=list)

    strengths: list[str] = Field(default_factory=list)
    weaknesses: list[str] = Field(default_factory=list)

    evidence_spans: list[EvidenceSpanRecord] = Field(default_factory=list)
    corrections: list[CorrectionRecord] = Field(default_factory=list)
    improved_response: Optional[str] = None

    rater: RaterInfo
    rubric_version: str
    rated_at: str

    adjudication: AdjudicationInfo = Field(default_factory=AdjudicationInfo)

    provenance: DataSourceRecord

    dataset_split: Optional[DatasetSplit] = None


class ImportRowError(BaseModel):
    row_index: int
    record_id: Optional[str] = None
    error: str


class ImportResult(BaseModel):
    import_id: str
    source_path: str
    imported_at: datetime
    rows_total: int
    rows_imported: int
    rows_duplicate: int
    rows_invalid: int
    errors: list[ImportRowError] = Field(default_factory=list)
    dry_run: bool = False
