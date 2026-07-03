# macOS 내부 알파 — 패키징 앱 검증 보고서 (Phase 5)

대상: `dist/TOEFL Writing.app` (버전 0.5.0, `com.leekangmin.toeflwriting`)

## 자동화 검증 (재현 가능, `scripts/packaged_app_smoke_test.py`)

`./scripts/build_macos.sh`의 8단계로 매 빌드마다 자동 실행된다. 격리된 임시
`TOEFL_DATA_DIR`을 사용하므로 실제 사용자 데이터에 영향을 주지 않는다.

| 단계 | 검증 내용 | 결과 |
| --- | --- | --- |
| 최초 실행 | 사용자 데이터 폴더 없음 → 자동 생성, 서버 기동, `/api/health` 200 | PASS |
| health 응답 | `offline_core_available=true`, `shadow_enabled=false`(API 키 없음) | PASS |
| API 키 없이 평가 | `POST /api/evaluate` → 200, `1.0 <= score_band_1_6 <= 6.0` | PASS |
| 기록 | `GET /api/history`에 방금 제출한 submission_id 존재 | PASS |
| 대시보드 | `GET /api/dashboard` → 200 | PASS |
| PDF | `GET /api/report/{id}.pdf` → 200, PDF 바이트(62487 bytes) 확인 | PASS |
| graceful shutdown | SIGTERM → 10초 내 exit code 0, lock 파일 정리됨 | PASS |
| 재실행 — 기록 유지 | 같은 데이터 디렉터리로 재실행, 이전 submission_id가 history에 그대로 존재 | PASS |
| 재실행 종료 | SIGTERM → exit code 0 | PASS |

전체 실행 로그: `/tmp/build_macos_log3.txt`(최종 성공 빌드).

## 자동화 검증 (smoke test 스크립트 외부, 이 세션에서 직접 재현)

| 항목 | 방법 | 결과 |
| --- | --- | --- |
| 중복 실행 | 첫 인스턴스 실행 → lock 확인 → 두 번째 인스턴스 실행 | 두 번째 인스턴스가 `[FATAL] ...이미 실행 중입니다` 다이얼로그 표시 후 정상 종료, 첫 인스턴스는 `/api/health` 계속 200 응답(서버 중복 생성 없음) |
| admin API 기본 비활성 | 패키징 앱 실행 후 `/api/expert-data/summary`, `/api/shadow/summary` 직접 호출 | 둘 다 404 |
| localhost-only | `HOST="127.0.0.1"` 상수 확인 + 127.0.0.1로만 호출 성공 | PASS |
| graceful shutdown 재현성 | `subprocess.Popen` + `send_signal(SIGTERM)`으로 2회 추가 재현 | 2회 모두 exit code 0 |

## 수동 검증이 필요한 항목 (자동화 범위 밖, 이번 세션에서 미수행)

- **네이티브 창 렌더링 육안 확인**: pywebview가 실제로 Cocoa 창을 그리는지는
  스크립트가 서버 API만 두드리므로 검증하지 못한다. `open "dist/TOEFL
  Writing.app"`으로 직접 열어 창이 뜨는지, UI가 올바르게 렌더링되는지
  사람이 확인해야 한다.
- **중복 실행 시 다이얼로그의 시각적 확인**: 두 번째 인스턴스가 다이얼로그를
  띄우고 종료하는 것은 로그(`button returned:확인`)로 확인했지만, 실제
  다이얼로그가 사용자에게 읽기 쉽게 표시되는지 육안 확인은 하지 않았다.
- **포트 점유/데이터 폴더 쓰기 실패 등 비정상 상황**: 의도적으로 포트를
  선점하거나 데이터 폴더를 읽기 전용으로 만드는 등의 장애 주입 테스트는
  이번 범위에서 수행하지 않았다(`start_server_thread`의 최대 3회 재시도
  로직과 `_show_fatal_dialog` 경로는 코드 리뷰로만 확인).
- **실제 네트워크 차단 상태의 육안 실행**: `docs/offline-core-mode.md`의
  "검증하지 않은 것" 절 참고.
- **Windows**: 이번 Phase의 필수 산출물은 macOS이므로 다루지 않았다.

## Build a Sentence 검증

| 항목 | 결과 |
| --- | --- |
| 문제 목록 조회 (`GET /api/build-a-sentence/items`) | 8개 자체 제작 문항, 정답 노출 없음 |
| 문제 상세(셔플된 조각) 조회 | `GET /api/build-a-sentence/items/{id}` — `primary_answer` 필드 없음 확인 |
| 탭 기반 조립 → 제출 → 정답 판정 | preview 브라우저에서 실제 클릭 시뮬레이션으로 end-to-end 검증(정답/오답 모두) |
| 직접 입력 fallback | textarea 입력 후 제출 → 정상 채점 확인 |
| 오답 시 정답 노출 | `correct_answer` 필드가 오답에서만 채워짐 확인 |
| 시도 횟수 누적 | 동일 문항 반복 제출 시 `attempt_number` 1→2→3 증가 확인 |
| API 테스트 | `tests/test_build_a_sentence_api.py` 8개, `tests/test_build_a_sentence.py`(엔진, 기존) 포함 pytest 전체 통과 |
| "공식 문제 아님" 표시 | `static/index.html`에 "자체 제작 연습 문제 · ETS 공식 문항이 아닙니다" 고정 문구 확인 |

## 결론

자동화 가능한 범위(서버/API/데이터/lifecycle) 전부 통과했다. 네이티브 창의
육안 렌더링과 다이얼로그 UX 등 사람이 직접 봐야 하는 부분은 미검증 상태로
남겨 정직하게 기록한다.
