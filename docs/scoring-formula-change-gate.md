# 점수 공식 변경 금지 게이트

## 규칙
**전문가 데이터로 실측 오차가 확인되기 전까지, `app/scorer.py`의 점수 계산
공식(가중치, 임계값, 페널티)을 미적 판단이나 추측만으로 다시 바꾸지 않는다.**

Phase 2에서 인젝션 검증 중 "0.5 단위 반올림 경계 근처에서 사소한 분량 변화가
점수를 한 단계 움직인다"는 현상을 발견했다. 이는 실제 버그(오탐)와 달리
데이터 없이는 "좋은 방향으로 고친 것"인지 "다른 왜곡을 만든 것"인지 판단할
수 없는 종류의 변경이라 건드리지 않고 있다.

## 지금 하는 것: 관찰 가능하게만 만든다
공식을 바꾸는 대신, 모든 평가에 다음 진단 데이터를 저장한다
(`app/scorer.py`의 `score_essay_detailed()` → `ScoringBreakdown`,
`app/main.py`가 `data/submissions.db`의 `result_json.scoring_quantization`에 저장):

| 필드 | 설명 |
|---|---|
| `pre_round_raw_score` | 0.5 단위로 반올림하기 **전** 원점수 |
| `rounded_display_score` | 사용자에게 보이는 최종 점수 (반올림 후) |
| `distance_to_rounding_boundary` | 원점수가 가장 가까운 0.5 경계에서 얼마나 떨어져 있는지 (0에 가까울수록 사소한 변화에 취약) |
| `component_scores` | 6개 차원별 반올림 전 점수 |
| `scoring_formula_version` | 공식 자체의 버전 (현재 `SCORING_ENGINE_VERSION`과 동일하게 관리) |

이 데이터는 **사용자에게 노출되지 않는다** — 내부 저장소에만 기록되는 진단용
데이터다. "raw vs rounded" 개념을 사용자에게 보여주면 오히려 신뢰를 해칠 수
있다고 판단했다.

## 전문가 데이터 확보 후 할 수 있는 분석
1. **경계 구간 MAE**: `distance_to_rounding_boundary`가 작은(예: <0.1) 평가들만
   따로 모아 전문가 점수 대비 오차(MAE)를 계산 — 경계 근처가 실제로 더 부정확한지 확인
2. **반올림 편향**: 반올림으로 인해 점수가 올라간 케이스와 내려간 케이스 각각에서
   전문가 점수 대비 과대/과소평가 경향이 다른지 확인
3. **양자화로 인한 순위 역전**: `pre_round_raw_score` 기준으로는 A > B였는데
   `rounded_display_score` 기준으로는 A = B 또는 A < B가 되는 케이스 빈도 측정
4. **연속 함수 후보 비교**: 위 분석에서 실제로 문제가 확인되면, 계단 함수를
   연속 함수로 바꾸는 안을 만들어 같은 validation/locked_test 세트에서
   `SCORING_FORMULA_VERSION`을 올린 신버전과 구버전을 나란히 비교
   (`docs/scoring-system.md`의 실험 기록 방식 참고)

## 이번 세션에서 하지 않은 것 (의도적으로)
- Content/Example 차원의 계단 함수를 연속 함수로 재설계하지 않았다
- 전역 `strict_penalty` 값(0.55)을 데이터 없이 재조정하지 않았다
- 가중치(Grammar 2.4x 등)를 바꾸지 않았다

이 세 가지는 전부 "이렇게 하면 더 나을 것 같다"는 추측으로는 건드리지 않기로
한 것이다 — 위 분석이 실제로 문제를 확인시켜준 뒤에만 변경한다.
