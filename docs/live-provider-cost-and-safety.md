# 실제 provider 비용·안전 게이트 (Phase 4)

## 비용 게이트 조건 (전부 충족해야 실제 호출)
`scripts/run_real_shadow_validation.py`, `scripts/run_real_provider_injection_test.py`
둘 다 다음 조건을 **전부** 요구한다. 하나라도 빠지면 dry-run만 수행하고 종료한다:

1. `ANTHROPIC_API_KEY` 환경변수 존재
2. `TOEFL_SHADOW_ENABLED=1`
3. `TOEFL_SHADOW_PROVIDER=claude`
4. CLI 플래그 `--i-understand-this-costs-money`
5. `--max-estimated-cost-usd`로 예산 상한 명시
6. (shadow validation runner만) `--limit`으로 최대 실행 건수 명시

실측: 이 세션에서 위 조건을 의도적으로 하나씩 빼며 게이트가 정말 막는지 확인했다
(`tests/test_live_validation_scripts.py`, 11개 테스트, 전부 subprocess로 실제 CLI를
실행해 검증 — mock이 아니라 실제 스크립트 종료 코드/출력을 확인).

## 실행 전 출력 (실측 확인됨)
실제 호출 직전에 다음을 반드시 출력한다: provider, model, 대상 답안 수, 예상 호출
수, 예상 비용, timeout, retry 설정, 결과 저장 위치(`data/shadow_assessments.db`),
"production score path: unaffected" 확인 문구, "raw essay logging: never printed"
확인 문구.

## 실행 중 안전장치
| 안전장치 | 구현 | 검증 상태 |
|---|---|---|
| 예산 상한 초과 시 중단 | `running_cost >= max_cost` 체크 후 break | 실측 확인 (가짜 키로 예산 초과 시 네트워크 호출 전에 abort) |
| 연속 실패 임계값 초과 시 중단 | 연속 3회 실패 시 중단 (`_CONSECUTIVE_FAILURE_STOP_THRESHOLD`) | 코드 구현 완료, 실제 연속 실패는 미재현(API 키 없음) |
| 429 반복 시 backoff 후 중단 | `call_claude`의 재시도 루프가 429에 backoff 적용, 소진 시 `call_failed_after_retries` | mock으로 검증 (`test_429_retries_with_backoff_then_succeeds`, `test_429_exhausted_retries_fails_with_reason_code`) |
| 동일 submission 중복 호출 방지 | `already_processed_submission_ids(provider, model)`로 스킵 | 코드 구현 완료, 실제 중복 스킵은 실제 실행 후에나 검증 가능 |
| Ctrl+C 시 기존 결과 보존 | 각 답안 처리 직후 즉시 shadow DB에 저장(`persist=True`)하므로 중단 시점까지 결과는 이미 커밋됨 | 설계상 보장 (배치 커밋이 아니라 건별 즉시 저장) |
| 실패한 답안은 reason code만 기록 | `ProviderCallError`의 `reason_code`가 `failure_reason`에 저장, 원문 없음 | 코드 레벨 보장 |
| 답안 원문 콘솔 미출력 | 러너는 submission_id/점수/상태만 출력, essay_text 직접 출력 없음 | 실측 확인 (`test_never_prints_essay_text_in_dry_run`) |

## API 키 보호
- `ANTHROPIC_API_KEY`는 `app/shadow_config.load_shadow_config()`가 서버 프로세스
  환경변수에서만 읽는다. 클라이언트 정적 자산(`static/`)에는 참조가 없다.
- 키가 없어도 앱은 정상 기동한다 (`get_shadow_provider()`가 예외 대신
  `(None, availability)` 반환) — `test_app_does_not_crash_without_api_key`로 회귀 검증.
- `ProviderCallError`의 예외 메시지는 `reason_code`/`request_id`/`detail`만 포함하며,
  `detail`은 HTTP status 코드나 파싱 오류 메시지이지 요청 헤더(API 키)를 포함하지
  않는다 — `call_claude`가 예외를 만들 때 `str(status)`나 `str(last_error)`만
  사용하고 `cfg.anthropic_api_key`를 문자열 조합에 포함하는 코드 경로가 없다.

## 로그 보호
- 모든 `logger.info`/`logger.warning` 호출은 `stage`, `request_id`, `attempt`,
  HTTP status 같은 메타데이터만 남기고 답안 원문이나 API 키를 남기지 않는다.
- `_content_fingerprint()`가 길이+SHA256 앞 12자만 반환해, 로그 상관관계 확인은
  가능하되 원문 복원은 불가능하다.

## 결과 저장 위치 격리
`scripts/run_real_shadow_validation.py`, `scripts/run_real_provider_injection_test.py`
둘 다 `data/submissions.db`(프로덕션)를 열지 않는다. 전자는 `data/shadow_assessments.db`에,
후자는 `data/real_llm_injection_results.json`에 결과를 저장한다. 둘 다 `.gitignore`의
`data/*.db`, 그리고 JSON 결과 파일은 별도 관리(현재 커밋 대상 아님)에 해당한다.
