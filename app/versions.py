"""전역 버전 상수 — 평가 결과 재현성의 단일 진실 소스.

이 파일의 값이 바뀌면 그 변경이 채점 결과에 영향을 줄 수 있다는 뜻이다.
값을 바꿀 때는 반드시 CHANGELOG 성격의 주석을 남기고, 가능하면
tests/eval_harness.py 를 재실행해 회귀가 없는지 확인하라.
"""

from __future__ import annotations

# 시험 사양: 어떤 시험 구조/문항 유형 정의를 따르는지.
# ETS 공식 사양서를 직접 재현한 것이 아니라, 공개된 일반 정보를 참고해 이 프로젝트가
# 자체적으로 정의한 연습용 사양이다. 공식 사양이 아니라는 점을 코드 밖(문서/UI)에서도 명시한다.
EXAM_SPEC_VERSION = "toefl-writing-2026-practice-v1"

# 루브릭 버전은 app/scorer.py 의 RUBRIC_VERSION 을 그대로 참조한다 (단일 소스 유지).
# 여기서는 재수출만 한다.
from app.scorer import RUBRIC_VERSION, SCORING_ENGINE_VERSION  # noqa: E402
from app.grammar import GRAMMAR_RULES_VERSION  # noqa: E402

# 이 결과 스키마(EvaluationResult/저장 JSON 구조) 버전.
# 필드를 추가/삭제/의미변경 할 때마다 올린다. 과거 레코드는 이 필드가 아예 없으므로
# 로드 시 "legacy-unknown"으로 표시한다 (LEGACY_RESULT_SCHEMA_VERSION 참고).
RESULT_SCHEMA_VERSION = "2.0.0"
LEGACY_RESULT_SCHEMA_VERSION = "legacy-unknown"

# 프롬프트 버전: 현재 채점 로직은 결정론적 휴리스틱이며 채점 자체에 LLM 프롬프트를
# 사용하지 않는다 (app/ai_mode.py 의 AI 보강은 패러프레이즈/드릴/샘플 문단 생성에만
# 관여하고 점수에는 개입하지 않는다). 따라서 채점 경로의 prompt_version은
# "not-applicable"이 정확한 표현이다. AI 채점(shadow mode)이 프로덕션에 반영되면
# 그때 실제 프롬프트 버전을 기록한다.
SCORING_PROMPT_VERSION = "not-applicable-heuristic-only"

# 비공개 고득점 답안 41개(토론 16, 이메일 25)의 집계 패턴으로 false-low를
# 줄이는 보수적 구조 보정. 원문/문장 자체는 점수 코드나 저장소에 포함하지 않는다.
CALIBRATION_VERSION = "private-high-score-aggregate-v1"

# 채점에 실제로 사용된 provider/model. 현재는 100% 결정론적 로컬 휴리스틱이다.
SCORING_PROVIDER = "heuristic"
SCORING_MODEL = "not-applicable"
SCORING_MODEL_IDENTIFIER = "not-applicable"

__all__ = [
    "EXAM_SPEC_VERSION",
    "RUBRIC_VERSION",
    "SCORING_ENGINE_VERSION",
    "GRAMMAR_RULES_VERSION",
    "RESULT_SCHEMA_VERSION",
    "LEGACY_RESULT_SCHEMA_VERSION",
    "SCORING_PROMPT_VERSION",
    "CALIBRATION_VERSION",
    "SCORING_PROVIDER",
    "SCORING_MODEL",
    "SCORING_MODEL_IDENTIFIER",
]
