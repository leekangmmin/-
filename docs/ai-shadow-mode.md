# AI Scoring Shadow Mode (Phase 2)

## 원칙
현재 사용자에게 보이는 점수는 **오직 결정론적 휴리스틱 엔진**(`app/scorer.py`)이
산출한다. AI provider는 shadow mode로만 실행되며, 그 결과는 내부 비교/연구
용도로만 저장되고 어떤 API 응답에도 섞이지 않는다.

**검증된 사실**: `app/main.py`의 `evaluate()` 함수는 `shadow_mode`를 import하지
않는다 (`tests/test_shadow_mode.py::test_main_evaluate_function_does_not_use_shadow_mode`
로 회귀 방지). shadow 비교를 아무리 실행해도 `score_essay()`의 반환값은 완전히
동일하다 (같은 테스트 파일에서 실측 확인).

## 파이프라인 (`app/scoring_provider.py`)
한 번의 "점수+피드백 생성" 호출로 뭉뚱그리지 않고 단계를 분리했다:

1. `analyze_input` — 입력 유효성 검사 + 요구사항/주장 추출
2. `score_dimensions` — 차원별 독립 점수 (evidence span 포함)
3. **evidence 코드 강제 검증** — provider 주장을 신뢰하지 않고
   `response_text[start:end] == text`를 Python에서 직접 확인
   (`validate_evidence_spans`). 불일치 시 `evidence_hallucination_detected`
   reason code를 남기고 해당 evidence는 `verified=False`로 표시
4. `critique_assessment` — 독립 critic. **새 점수를 만들지 않고** severity만 보고
5. 점수 조정 — critic severity에 따른 **명시적 규칙** (major: -0.5, minor: -0.2,
   none: 조정 없음) — "AI가 알아서 결정"하는 블랙박스 없음
6. confidence 산출 — evidence 검증율 + critic severity 조합

## Provider 추상화
```python
class ScoringProvider(ABC):
    def analyze_input(...) -> (InputValidation, InputAnalysis): ...
    def score_dimensions(...) -> DimensionScoreResult: ...
    def critique_assessment(...) -> AssessmentCritique: ...
    def generate_feedback(...) -> FeedbackResult: ...
```

- **MockScoringProvider**: 네트워크 호출 없이 텍스트 통계로 그럴듯한 구조를
  생성. 파이프라인 배관(스키마, evidence 검증, reconciliation, confidence)을
  검증하는 용도. **채점 품질의 증거가 아니다.**
- **Claude provider**: `app/claude_provider.py`에 4단계 shadow 호출·스키마
  검증·재시도·비용 추정 경로가 구현되어 있다. 2026 과제별 4개 평가
  축을 사용하며, `grade_task()`는 첨부된 단일 과제 strict-JSON 계약을
  실행한다. 다만 실제 모델 채점 정확도는 전문가 골드 데이터 없이
  검증되었다고 보지 않는다.
- **OpenAI/Gemini shadow provider**: 아직 4단계 `ScoringProvider`로는 구현되지
  않았다. 선택형 피드백 보강 경로와 shadow 채점 provider는 구분한다.

## 실행 결과 (MockProvider, 실제 저장된 답안 10건)
```
.venv/bin/python scripts/run_shadow_comparison.py --limit 10

  #68: heuristic=3.5 ai=3.5 delta=0.0   evidence=2/2 confidence=high
  #67: heuristic=2.0 ai=3.75 delta=1.75 evidence=2/2 confidence=high
  ...
=== Summary ===
{'count': 10, 'avg_score_delta': 0.525, 'avg_evidence_success_rate': 1.0,
 'avg_latency_ms': 0.037, 'schema_valid_rate': 1.0}
```
delta가 큰 경우(#67, #62)가 보이는데, 이는 **MockProvider가 실제 채점 지능이
없고 단어 수 기반 근사치만 내기 때문**이다 — 실제 LLM의 채점 경향을 보여주는
수치가 아니라 파이프라인이 정상 작동한다는 것만 증명한다.

## 비교 리포트 저장 (`app/shadow_mode.py`)
- 저장 위치: `data/shadow_assessments.db` (프로덕션 DB와 분리)
- 기록 항목: heuristic/AI 점수 차이, 차원별 차이(모델 확장 시), evidence
  검증 성공률, schema 성공 여부, critic severity, confidence, latency, reason codes
- 조회: `GET /api/shadow/summary` — 기본 비활성화, `TOEFL_ADMIN_API_ENABLED=1` +
  로컬 접근(`127.0.0.1`, `X-Forwarded-For` 미신뢰)이 모두 필요. 응답은 집계
  수치만 포함하며 답안 원문을 포함하지 않는다 (`tests/test_admin_api_security.py`).

## 검증됨 vs 미검증
| 항목 | 상태 |
|---|---|
| Provider 인터페이스 구조 | 구현 완료, 테스트 통과 |
| Evidence offset 강제 검증 | 구현 완료, 실측 확인 (일치/불일치/범위초과 3케이스) |
| Critic → 점수 조정 규칙 | 구현 완료, 테스트 통과 |
| MockProvider 파이프라인 | 구현 완료, 실제 DB 10건 실행 확인 |
| production 경로 미개입 | **실측 확인** (동일 입력 shadow 실행 전/후 점수 동일) |
| Claude shadow 호출/스키마 처리 | MockTransport로 통합 테스트 완료 |
| Claude 실제 모델 채점 품질 | **미검증** — 전문가 골드 데이터 없음 |
| OpenAI/Gemini shadow 채점 | **미구현** |
| shadow 점수의 정확도(전문가 대비) | **측정 불가** — 전문가 데이터 없음 |
