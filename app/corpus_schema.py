"""Validated private-corpus records. Instances must stay outside version control."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


TaskType = Literal["email", "academic_discussion"]
SourceType = Literal[
    "self_written", "teacher_provided", "public_licensed", "unknown", "official_or_proprietary"
]
PermissionStatus = Literal["granted", "private_use_only", "unknown", "restricted"]


class HighScoreSample(BaseModel):
    sample_id: str = Field(min_length=8)
    task_type: TaskType
    prompt_id: str | None = None
    prompt_text: str | None = None
    answer_text: str = Field(min_length=40)
    score: float | None = Field(default=None, ge=0, le=5)
    score_label: str | None = None
    source_type: SourceType = "unknown"
    source_notes: str | None = None
    permission_status: PermissionStatus = "unknown"
    can_redistribute: bool = False
    language_notes: list[str] = Field(default_factory=list)
    structure_tags: list[str] = Field(default_factory=list)
    quality_tags: list[str] = Field(default_factory=list)
    content_hash: str

    @model_validator(mode="after")
    def restrict_unknown_sources(self) -> "HighScoreSample":
        if self.source_type in {"unknown", "official_or_proprietary"} and self.can_redistribute:
            raise ValueError("unknown or proprietary material cannot be marked redistributable")
        return self
