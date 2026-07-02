# 실제 Claude shadow validation (Phase 4)

## 상태: live provider smoke validated — 아니오. live provider implementation complete — 예.
이 세션에는 `ANTHROPIC_API_KEY`가 없다. 따라서 **실제 Anthropic 네트워크 호출은
한 번도 수행되지 않았다.** 이 문서는 (1) 실제 호출을 위해 구현/검증된 것과
(2) 아직 검증되지 않은 것을 구분한다. "live validation complete"라고 표현하지 않는다.

## 구현됨 (코드 레벨)
- `scripts/run_real_shadow_validation.py`: Stage A(1건)/B(5건)/C(10~20건) 확대
  실행을 지원하는 러너. 비용 게이트, 사전 출력(provider/model/예상 호출수/예상
  비용/timeout/retry/저장 위치/production 미개입 확인/원문 비노출 확인), 예산
  초과 중단, 연속 3회 실패 중단, `app.shadow_mode.already_processed_submission_ids`
  기반 idempotency(중복 스킵), `Ctrl+C` 안전 종료(이미 완료된 건은 shadow DB에
  이미 저장돼 있으므로 손상 없음) 구현.
- 결과는 `data/shadow_assessments.db`에만 저장되고 `data/submissions.db`(프로덕션)는
  이 스크립트에서 전혀 열지 않는다(읽기 전용 조회만).

## Mock으로 검증된 것 (`tests/test_claude_provider.py`, `tests/test_live_validation_scripts.py`)
- 요청 페이로드 구조, JSON 파싱(정상/손상/잘린 JSON), 401/403 즉시 실패,
  429/5xx 백오프 재시도, 재시도 소진 시 실패, timeout 처리
- score_dimensions 응답의 스키마 강제 검증: `schema_validation_failed`(필드 누락,
  알 수 없는 dimension_id, evidence offset 타입 오류), `score_out_of_range`
  (점수가 max_score 초과 또는 음수)
- 답안 원문이 로그에 절대 남지 않음(핑거프린트만)
- 비용 게이트 스크립트가 실제 키 없이도, 있어도(가짜 키) 예산 초과 시 네트워크
  호출 전에 중단됨 — subprocess 기반 9개 게이트 테스트로 실측 확인

## 실제 Claude로 검증된 것
**없음.** Stage A(단일 email/discussion smoke)조차 실행되지 않았다.

## dry-run으로 확인한 것 (실제 DB 대상)
```
.venv/bin/python scripts/run_real_shadow_validation.py --limit 20 --dry-run
```
- 현재 `data/submissions.db`에 Stage A/B/C에 쓸 수 있는 실제 과거 제출이
  academic_discussion 다수 + email 최소 1건 이상 존재함을 확인 (원문은 출력하지 않고
  submission_id만 표시)
- 예상 호출 수(4단계 × 건수), 예상 비용(모델 가격표 기반 추정치), timeout/retry
  설정이 올바르게 계산·출력됨을 확인

## 아직 검증되지 않은 것 (API 키 대기)
- 실제 Claude가 반환하는 JSON이 정말 스키마를 지키는지
- 실제 evidence가 답안 원문에 실제로 존재하는지(오프셋 정확도)와, 존재하더라도
  해당 차원과 실제로 관련 있는지(자동 검증 불가 영역, 수동 표본 검토 필요)
- 실제 latency/토큰 사용량/비용
- 실제 critic 단계가 draft 점수의 문제를 실제로 잡아내는지

## 다음 단계
`ANTHROPIC_API_KEY` 확보 후:
```
.venv/bin/python scripts/run_real_shadow_validation.py \
  --limit 1 --max-estimated-cost-usd 0.10 --i-understand-this-costs-money   # Stage A
.venv/bin/python scripts/run_real_shadow_validation.py \
  --limit 5 --max-estimated-cost-usd 0.50 --i-understand-this-costs-money   # Stage B
```
Stage A/B가 안정적이면 Stage C(10~20건)로 확대한다. 전체 DB를 한 번에 돌리지 않는다.
