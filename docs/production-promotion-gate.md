# 프로덕션 승격 게이트 (Phase 4)

## 현재 상태
**AI(Claude shadow) 결과는 프로덕션 사용자 점수에 전혀 반영되지 않는다.**
`app/main.py`의 `evaluate()`는 `shadow_mode`/`claude_provider`/`scoring_provider`를
import하지 않으며, 이는 회귀 테스트로 고정돼 있다
(`tests/test_shadow_mode.py::test_main_evaluate_function_does_not_use_shadow_mode`).
이 문서는 "언제 반영해도 되는가"의 **조건만** 정의한다 — 이번 단계에서 어떤
조건도 충족됐다고 선언하지 않는다.

## 왜 지금 반영하지 않는가
- 실제 Claude 네트워크 호출이 이 세션에서 한 번도 검증되지 않았다 (API 키 없음)
- 실제 전문가 데이터가 0건이다
- 전문가 대비 오차(MAE)를 한 번도 측정하지 못했다
- 실제 LLM 인젝션 저항성이 한 번도 측정되지 않았다

데이터 없이 "아마 괜찮을 것"이라는 추측으로 반영하지 않는다.

## 승격 후보 조건 (전부 충족 시 "검토 가능", 자동 승격 아님)

### 기술 안정성
| 조건 | 현재 상태 |
|---|---|
| structured output 성공률 목표치 충족 | 미측정 (mock으로만 배관 검증) |
| evidence 검증 성공률 목표치 충족 | 미측정 |
| invalid_assessment 비율이 허용 범위 이내 | 미측정 |
| timeout/provider 오류 시 안전한 fallback | 코드 레벨 구현·mock 검증 완료, 실제 네트워크 미검증 |
| API 비용이 예산 상한 이내로 예측 가능 | 추정 함수만 존재 (`estimate_cost_usd`), 실측 없음 |
| P95 latency 허용 범위 이내 | 미측정 |
| shadow 경로와 production 경로 완전 격리 유지 | **실측 확인됨** (동일 입력 shadow 실행 전/후 점수 동일, DB 분리) |

### 안전성
| 조건 | 현재 상태 |
|---|---|
| 실제 LLM 인젝션 paired test 통과 (heuristic과 별도) | 미실행 — API 키 없음. 스크립트는 비용 게이트까지 검증 완료 |
| system prompt leakage 0건 | 미측정 (mock 테스트에서 leak 검출 로직만 검증) |
| schema 교란 공격 성공 0건 | 미측정 |
| 미검증 evidence가 사용자에게 노출된 적 없음 | 코드 레벨 보장(`_validate_and_filter_evidence`가 항상 제거), 회귀 테스트 있음 |
| 답안 원문 로그 노출 0건 | 코드 레벨 보장 + 테스트 있음 (`test_essay_text_not_in_log_records` 등) |

### 평가 품질
| 조건 | 현재 상태 |
|---|---|
| 충분한 전문가 데이터 (task_type/점수 구간별 표본 확보) | **0건** — 파일럿조차 시작 안 됨 |
| 복수 채점 표본 확보 | 0건 |
| 전문가 대비 MAE 측정 | 측정 불가 (계산 코드는 존재: `app/pilot_comparison.py`) |
| ±0.5 agreement 측정 | 측정 불가 |
| 점수 구간별 편향 분석 | 측정 불가 |
| 휴리스틱 대비 실제 개선 확인 | 측정 불가 |
| 대표 실패 사례 검토 | 불가 (사례 자체가 없음) |

### 제품 원칙 (설계상 이미 충족)
- AI 결과가 실패해도 답안은 유실되지 않는다 — `run_shadow_comparison`이 예외를
  잡아 `failure_reason`으로 기록하고 사용자 응답 흐름과 무관하게 동작한다.
- AI 결과가 없어도(shadow 비활성/오류) 사용자는 항상 휴리스틱 점수를 받는다.
- (향후 노출 시 필요) 예상 점수라는 표시, 버전과 한계 표시, 공식 ETS 점수와
  혼동하지 않게 하는 UI 문구 — **아직 UI에 AI 점수를 노출하지 않으므로 미구현.**

## 구체적 수치 기준을 지금 정하지 않는 이유
"schema 성공률 95% 이상", "MAE 0.5 이하" 같은 구체적 숫자는 실제 파일럿 결과와
인간 채점자 간 합의 범위를 보기 전에는 임의의 숫자에 불과하다. 예를 들어
인간 채점자끼리도 ±0.5 이상 차이가 나는 경우가 있다면, 모델에게 그보다 엄격한
기준을 요구하는 것은 모순이다 (`app.pilot_comparison.multi_rater_agreement_summary`가
이 비교를 위해 준비돼 있다). 구체적 수치는 실제 파일럿 데이터 확보 후 확정한다.

## 다음에 필요한 것 (순서대로)
1. `ANTHROPIC_API_KEY` 확보 → Stage A(1건) → Stage B(5건) → 조건부 Stage C(10~20건)
2. 실제 LLM 인젝션 검증 실행 (`scripts/run_real_provider_injection_test.py`)
3. 실제 전문가 파일럿 10~20건 수집·import (`docs/expert-pilot-procedure.md`)
4. `scripts/run_pilot_comparison.py`로 최초 3자 비교 생성
5. 위 표의 "미측정" 항목을 실측치로 채운 뒤, 그때 처음으로 구체적 승격 기준 수치를 정한다
