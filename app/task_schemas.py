"""유형별(Email / Academic Discussion) 평가 스키마.

Write an Email과 Academic Discussion은 요구되는 것이 근본적으로 다르므로
같은 프롬프트/차원 목록으로 뭉뚱그리지 않는다. 이 모듈은 AI shadow 파이프라인
(app/claude_provider.py)이 task_type에 맞는 요구사항 구조와 평가 차원을
사용하도록 스키마와 프롬프트 조각을 제공한다.

주의: 이 스키마 자체가 채점을 하지 않는다 — LLM이 이 구조를 채워서 반환하고,
코드가 evidence를 검증한다 (app/scoring_provider.validate_evidence_spans).
"""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

from app.toefl_2026_grader import (
    ACADEMIC_DISCUSSION_DIMENSIONS,
    EMAIL_DIMENSIONS as TOEFL_2026_EMAIL_DIMENSIONS,
)

RequirementStatus = Literal["met", "partially_met", "missing"]

# These are the four task-specific 2026 rubric axes.  Keep aliases as lists for
# backward-compatible imports in the shadow-mode reporting/tests.
EMAIL_DIMENSIONS: list[str] = list(TOEFL_2026_EMAIL_DIMENSIONS)
DISCUSSION_DIMENSIONS: list[str] = list(ACADEMIC_DISCUSSION_DIMENSIONS)


class TaskRequirementAssessment(BaseModel):
    requirement: str
    status: RequirementStatus
    evidence: str = ""
    explanation: str = ""


class EmailTaskContext(BaseModel):
    """이메일 문제에서 추출해야 하는 구조. score_dimensions 이전 단계(analyze_input)에서
    LLM이 채워야 하는 필드다."""

    writer_role: str = ""
    recipient_role: str = ""
    communicative_purpose: list[str] = Field(default_factory=list)
    required_content_points: list[str] = Field(default_factory=list)
    tone_expectation: str = ""
    constraints: list[str] = Field(default_factory=list)
    requirement_assessments: list[TaskRequirementAssessment] = Field(default_factory=list)


class DiscussionTaskContext(BaseModel):
    """학술 토론 문제에서 추출해야 하는 구조."""

    discussion_question: str = ""
    other_participant_positions: list[str] = Field(default_factory=list)
    requirement_assessments: list[TaskRequirementAssessment] = Field(default_factory=list)


def dimension_ids_for(task_type: str) -> list[str]:
    if task_type == "email":
        return list(EMAIL_DIMENSIONS)
    if task_type == "academic_discussion":
        return list(DISCUSSION_DIMENSIONS)
    raise ValueError(f"지원하지 않는 task_type: {task_type}")


def requirement_extraction_instructions(task_type: str) -> str:
    """analyze_input 단계 system prompt에 삽입할 task_type별 지시문."""
    if task_type == "email":
        return (
            "이메일 문제에서 다음을 추출하라: writer_role(작성자 역할), "
            "recipient_role(수신자 역할), communicative_purpose(의사소통 목적 목록), "
            "required_content_points(반드시 포함해야 하는 내용 목록), "
            "tone_expectation(기대되는 어조), constraints(제약조건). "
            "각 required_content_point마다 답안에서 충족(met)/부분충족(partially_met)/"
            "누락(missing) 여부와 근거(evidence, 답안 원문 발췌)를 판단하라. "
            "누락이나 어조 문제는 실제 의사소통 효과에 미친 영향만 홀리스틱하게 "
            "반영하고 기계적인 밴드 상한을 적용하지 마라."
        )
    if task_type == "academic_discussion":
        return (
            "학술 토론 문제에서 다음을 평가하라: 질문에 대한 명확한 입장(position), "
            "질문과의 관련성(relevance), 근거의 타당성(reasoning), 구체성(supporting_detail), "
            "새로운 기여 여부(new_contribution, 단순 동의/반복이 아닌지), "
            "다른 참여자 의견과의 연결(engagement_with_other_views), "
            "다른 참여자 의견을 왜곡하지 않았는지(distortion_of_other_views). "
            "다른 참여자 의견을 언급하는 것은 선택 사항이며, 이름을 언급하지 "
            "않았다는 이유만으로 감점하지 마라. 각 요구사항마다 충족 여부와 "
            "답안 원문 근거를 판단하라."
        )
    raise ValueError(f"지원하지 않는 task_type: {task_type}")


def dimension_scoring_instructions(task_type: str) -> str:
    dims = dimension_ids_for(task_type)
    task_rule = (
        "purposeful_communication을 중심으로 목적·세부 정보·사회적 관습의 "
        "실제 효과를 종합하고 기계적 상한을 적용하지 마라."
        if task_type == "email"
        else "명확한 입장·구체적 전개·관련성·조직과 언어 통제력을 평가하라. "
        "다른 학생 언급은 선택 사항이다."
    )
    return (
        f"다음 {len(dims)}개 차원 각각에 대해 점수와 근거를 산출하라 (dimension_id는 "
        f"정확히 이 목록의 값을 사용하라): {', '.join(dims)}. "
        f"{task_rule} 초안으로서 의미를 방해하지 않는 소수 오류는 과도하게 "
        "감점하지 말고, 완성도를 문장의 세련됨보다 우선하라. 사실 정확성은 "
        "검증하지 말며, 지어낸 구체적 세부 내용을 감점하지 말라. 명백한 템플릿 "
        "필러를 감지하고 관련 언어/담화 차원과 전체 점수에 반영하라. 최종 "
        "overall_draft_score는 단순 평균이 아닌 0~5 정수 홀리스틱 점수여야 한다. "
        "한 차원이 2점 이하이면 overall 5를 주지 말라."
    )
