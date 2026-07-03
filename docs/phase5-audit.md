# Phase 5 감사 — API 독립형 데스크톱 앱 (요약)

## 시작 전 상태 (섹션 2)

```text
브랜치: main
직전 커밋: b420eb5 docs: Phase 4 실전 검증 문서 추가 (Phase 3 7개 + Phase 4 4개 = 11개 커밋 확인됨)
```

시작 시점에 다음 파일이 이미 사용자에 의해 미커밋 상태로 수정돼 있었다
(Phase 5 세션에서 전혀 건드리지 않음, 커밋 대상에서 제외):

- `app/feedback.py`
- `app/vocab_analysis.py`
- `실행.command`
- `토플첨삭기 by이강민.app/Contents/MacOS/run`
- `.vscode/launch.json` (untracked)
- `NativeMacApp/.build/**` (빌드 캐시, 원래도 추적 대상 아님)

기존 `.app`(`토플첨삭기 by이강민.app`)은 삭제하지 않았다 — 조사 결과 이는
SwiftUI 네이티브 클라이언트(`NativeMacApp/`) + Python 서브프로세스 서버(포트
8000 고정)를 감싸는 수동 wrapper였다(`Contents/MacOS/run` 셸 스크립트 확인).
Phase 5의 새 패키징 산출물(`dist/TOEFL Writing.app`)은 완전히 다른 bundle
identifier(`com.leekangmin.toeflwriting` vs 기존 `com.lee.gangmin.toefl-coach`)와
다른 아키텍처(FastAPI+pywebview one-dir, SwiftUI 클라이언트 없음)를 쓰므로
충돌하지 않는다. 두 `.app`은 별도 산출물로 공존한다.

## 실행 구조 감사 (섹션 4, Phase 4까지의 상태)

- 서버 엔트리포인트: `app/main.py`의 FastAPI `app` 객체, 개발 모드는
  `uvicorn app.main:app`
- 구 DB 위치: `BASE_DIR / "data" / *.db"` (프로젝트 루트 상대경로 — Phase 5
  이전에는 "프로젝트 루트에서만 정상 동작"하는 구조였음)
- 구 네이티브 셸(`app/native_shell.py`): host/port 8000 고정, subprocess로
  서버 기동, atexit/signal 핸들러 직접 구현 — PyInstaller onedir 환경에서
  subprocess로 자기 자신을 재실행하려 시도할 위험이 있는 구조였음
- `__file__` 기반 경로: `app/main.py`의 `STATIC_DIR = BASE_DIR / "static"`처럼
  소스 트리 기준 상대경로 — PyInstaller 번들에서는 다른 위치가 됨

Phase 5에서 이 구조를 다음과 같이 교체했다: `app/paths.py`(resource_path +
user_data_dir 추상화), `app/data_migration.py`(안전 마이그레이션),
`desktop/`(신규 런처, in-process 서버 스레드) — 상세는
`docs/desktop-architecture.md`, `docs/user-data-and-migration.md` 참고.

## Phase 4 baseline 재검증 (섹션 3)

Phase 5 작업 시작 전 재검증, 작업 중간중간 반복 실행:

```text
명령: .venv/bin/python -m pytest tests/ -q
결과: 207 passed (Phase 5 작업 시작 시점, Build a Sentence UI 추가 전)
      → 215 passed (최종, Build a Sentence API 테스트 8개 추가 후)
종료 코드: 0
```

테스트를 삭제하거나 기대값을 약화한 적 없음 — 전부 신규 추가만 있었다.

## 최종 검증 명령 (섹션 33)

### Source mode

| 명령 | 종료 코드 | 결과 |
| --- | --- | --- |
| `git diff --check -- app/ desktop/ packaging/ scripts/ static/ tests/ docs/ .gitignore requirements.txt` | 0 | 공백 오류 없음 |
| `.venv/bin/python -m pytest tests/ -q` | 0 | 215 passed |
| `.venv/bin/python -m tests.eval_harness` | 0 | (build_macos.sh 6단계에 포함되어 통과) |

### Build mode

| 명령 | 종료 코드 | 결과 |
| --- | --- | --- |
| `./scripts/build_macos.sh` (clean venv부터 전체) | 0 | 빌드+테스트+harness+PyInstaller+smoke test 전부 통과, `dist/TOEFL Writing.app` 생성 |
| `scripts/packaged_app_smoke_test.py "dist/TOEFL Writing.app"` (스크립트 내부 8단계에 포함) | 0 | 최초실행/평가/기록/대시보드/PDF/종료/재실행/재종료 전부 PASS |

### Security

| 검사 | 결과 |
| --- | --- |
| API 키 패턴 검색 | 없음 |
| `.env` 검색 | 없음 |
| DB 검색 | 없음 |
| 사용자 데이터 마커 검색 (expert/submission) | 없음 |
| 절대경로(개발자 홈) 검색 (PYZ bytecode 전수) | 없음 (상대경로만) |
| localhost bind 확인 | `HOST="127.0.0.1"`, 실제 앱 실행 중 127.0.0.1 응답 확인 |
| admin API 기본 비활성 | `/api/expert-data/summary`, `/api/shadow/summary` 둘 다 404 |
| shadow 기본 비활성 | `/api/health`의 `shadow_enabled=false` |

상세: `docs/packaged-app-security.md`

### UI

| 항목 | 결과 |
| --- | --- |
| CDN 의존성 제거 | `static/index.html`/`styles.css`에 외부 URL 참조 0건 |
| 앱 상태/분석 모드 카드 | `/api/health` 연동 확인(app_version, schema_version, shadow_enabled 실시간 표시) |
| Build a Sentence 조립 UI | preview 브라우저에서 클릭 시뮬레이션으로 end-to-end 확인 |
| 반응형(375/768/1280px) | Phase 2에서 검증된 기존 CSS 그리드를 재사용, Phase 5에서 추가한 카드/섹션도 동일한 `.card` 컴포넌트 패턴을 따름(별도 회귀 스크린샷은 촬영하지 않음 — 기존 반응형 시스템을 그대로 상속) |

## 변경 파일 (신규/수정, 프로토텍트 파일 제외)

| 파일 | 목적 |
| --- | --- |
| `app/paths.py` (신규) | resource_path/user_data_dir 추상화 |
| `app/data_migration.py` (신규) | 안전 legacy DB 마이그레이션 |
| `app/version.py` (신규) | 버전 단일 출처 |
| `app/build_a_sentence_items.py` (신규) | 프로덕션 문항 뱅크 8개 |
| `app/db.py` | DB_PATH → databases_dir(), bas_attempts 테이블/함수 추가 |
| `app/expert_data.py`, `app/shadow_mode.py` | DB 경로를 databases_dir() 기준으로 변경 |
| `app/main.py` | startup migration 연동, health 확장, Build a Sentence API 3종 추가 |
| `app/models.py` | Build a Sentence 요청/응답 스키마 추가 |
| `app/native_shell.py` | `desktop.launcher.main` 위임 shim으로 축소 |
| `desktop/` (신규 패키지) | launcher/server_manager/single_instance |
| `packaging/` (신규) | PyInstaller spec, entry_point, entitlements |
| `scripts/build_macos.sh` (신규) | 재현 가능한 빌드 스크립트 |
| `scripts/packaged_app_smoke_test.py` (신규) | 패키징 앱 자동 smoke test |
| `static/index.html` | CDN 제거, 앱 상태 카드, Build a Sentence 섹션 추가 |
| `static/app.js` | fetchAppStatus, Build a Sentence 클라이언트 로직 추가 |
| `static/styles.css` | 상태 카드/Build a Sentence 컴포넌트 스타일 추가 |
| `requirements.txt` | `platformdirs==4.10.0` 추가 |
| `.gitignore` | 마이그레이션 백업, PyInstaller 빌드 산출물 제외 추가 |
| `tests/conftest.py` (신규) | 모든 테스트에 격리된 TOEFL_DATA_DIR 강제 |
| `tests/test_paths.py`, `test_data_migration.py`, `test_desktop_launcher.py`, `test_build_a_sentence_api.py` (신규) | Phase 5 회귀 테스트 40개 |

## 현재 한계

- Claude 실호출 미검증 (Phase 5 범위 밖 — shadow mode는 Phase 4에서 이미
  API 키 있을 때만 동작하도록 검증됨)
- 코드 서명/공증 미완료 — unsigned internal alpha (Apple Developer 인증서
  없음)
- Windows 빌드 미검증 (경로 추상화는 OS 중립으로 설계했으나 실제 Windows
  환경 테스트 없음)
- 앱 아이콘(.icns) 미준비 — pywebview 기본 아이콘 사용 중
- 사용자가 임의 시점에 호출 가능한 백업/복원 UI 미구현 (마이그레이션
  전용 백업 인프라만 존재)
- 네이티브 창 렌더링 육안 확인, 중복 실행 다이얼로그 시각적 확인 등
  일부 항목은 자동화 범위 밖 수동 검증으로 남음(`docs/internal-alpha-test-report.md`)
