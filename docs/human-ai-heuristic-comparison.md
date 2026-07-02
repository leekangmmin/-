# 인간(전문가)·Claude·휴리스틱 비교 (Phase 4)

## 상태: 측정 불가 (전문가 데이터 0건, Claude 실제 호출 0건)

이 문서는 비교 **구조**와, 데이터가 들어왔을 때 어떤 수치가 나오는지 설명한다.
현재는 어떤 실제 비교 수치도 존재하지 않는다 — 아래 지표는 전부 계산 로직만
검증됐고(`tests/test_pilot_comparison.py`), 실측값이 아니다.

## 비교 파이프라인
```
data/expert_data.db  ──┐
                        ├─ exact_hash(response_text) 매칭 ──> MatchedTriple
data/submissions.db  ──┤   (app/pilot_comparison.py)
                        │
data/shadow_assessments.db ─┘  (historical_submission_id로 연결)
```
`scripts/run_pilot_comparison.py`가 세 저장소를 조인한다. 매칭은 텍스트
정확 해시 기준이라, 전문가가 새로 채점한 답안(앱을 거치지 않은 원본)은
매칭되지 않는다 — 파일럿에서는 이 케이스가 오히려 흔할 수 있다.

## 계산되는 지표 (구조만 존재, 값 없음)
- `comparable_count`, `insufficient_sample`(30건 미만이면 항상 True)
- `heuristic_mae`, `claude_raw_mae`, `claude_reconciled_mae`
- `heuristic_within_0_5`, `claude_within_0_5` (±0.5 agreement 건수)
- 과대/과소평가 건수 (휴리스틱, Claude 각각)
- task_type별 분해(email/academic_discussion 각각의 MAE)
- 대표 사례: Claude가 전문가와 가장 가깝거나 먼 답안, 휴리스틱도 동일,
  Claude와 휴리스틱이 반대 방향으로 틀린 답안
- 복수 채점자 합의 범위(`multi_rater_agreement_summary`) — 모델 오차를
  인간 채점자 간 불일치보다 더 정밀하게 요구하지 않기 위한 기준선
- 양자화 경계 분석(`boundary_region_analysis`) — 반올림 경계 근처
  답안의 오차가 실제로 더 큰지

## 왜 지금 수치가 없는가
- 전문가 데이터 0건 (`docs/expert-pilot-results.md`)
- Claude 실제 호출 0건 (`docs/live-claude-shadow-validation.md`)
- 위 두 조건이 모두 충족돼야 `MatchedTriple`이 하나라도 생성된다

## 판정 원칙 (실제 데이터 확보 후 적용)
- 전문가 점수가 없는 상태에서 Claude와 휴리스틱 중 어느 쪽이 "맞다"고 단정하지
  않는다 — 불일치 사례로만 분류한다
- 10~20건 파일럿 결과는 `insufficient_sample=True`와 함께 "calibration
  prohibited, production promotion prohibited" 경고를 항상 동반한다
  (`app/pilot_comparison.py`의 `_MIN_SAMPLE_FOR_ANY_CONCLUSION = 30`)
- 복수 채점자 간 불일치 범위보다 더 엄격한 정확도를 모델에게 요구하지 않는다

## 다음 단계
전문가 데이터와 Claude 실제 호출 결과가 모두 확보되면
`.venv/bin/python scripts/run_pilot_comparison.py`를 다시 실행하고, 이 문서를
실제 수치로 갱신한다.
