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
RESULT_SCHEMA_VERSION = "4.0.0"
LEGACY_RESULT_SCHEMA_VERSION = "legacy-unknown"

# 내장 대체 경로는 LLM 프롬프트를 사용하지 않으므로 not-applicable이다.
# 검증된 클라우드 AI 채점을 사용한 결과는 main.py가 실제
# TOEFL_2026_GRADER_PROMPT_VERSION을 engine.prompt_version에 기록한다.
SCORING_PROMPT_VERSION = "not-applicable-heuristic-only"

# ETS 공개 루브릭·공개 연구의 평가 구인을 반영한 휴리스틱 프록시다.
# 전문가 골드 데이터에 대한 통계적 보정은 아직 완료되지 않았음을 명시한다.
CALIBRATION_VERSION = "ets-public-rubric-uncalibrated-v3"

# 내장 대체 경로의 provider/model. 클라우드 AI 채점이 성공하면 main.py가
# 실제 provider/model과 TOEFL_2026_GRADER_PROMPT_VERSION으로 교체해 저장한다.
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
