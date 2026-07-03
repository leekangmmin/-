# 패키징 앱 보안 감사 (Phase 5)

`dist/TOEFL Writing.app`을 실제로 빌드한 뒤 내부를 직접 검사했다(Python
패키징 특성상 소스 복원이 완전히 불가능하다고 주장하지 않는다 — 목표는
비밀정보를 포함하지 않는 것이다).

## 검사 결과

| 검색 대상 | 명령/방법 | 결과 |
| --- | --- | --- |
| `.env` 파일 | `find "$APP" -iname "*.env*"` | 없음 |
| API 키 패턴 (`sk-...`, `sk-ant-...`, `AIza...`) | 텍스트/설정 파일 grep (`-E "sk-[a-zA-Z0-9]{20,}\|..."`) | 없음 |
| `.db`/`.sqlite` 파일 | `find "$APP" -iname "*.db" -o -iname "*.sqlite*"` | 없음 |
| Git 메타데이터 | `find "$APP" -iname ".git*"` | 없음 |
| 테스트 캐시/conftest | `find "$APP" -iname "*pytest_cache*" -o -iname "conftest*"` | 없음 |
| 개발 스크린샷 | `find "$APP" -iname "*screenshot*"` | 없음 (spec에서 static 전체 대신 3개 런타임 파일만 명시적으로 포함하도록 수정 후 재확인) |
| 전문가 데이터/실제 답안 마커 | `find "$APP" -iname "*expert*" -o -iname "*submission*"` | 없음 |
| 개발 절대경로 (`/Users/igangmin/...`) | PYZ 아카이브를 직접 압축 해제해 모든 bytecode의 `co_filename` 검사 (1691개 모듈, 5개 디코드 실패 제외) | 0건 — PyInstaller가 `app/main.py`처럼 프로젝트 루트 기준 상대경로만 기록함을 직접 확인 |
| localhost-only binding | `desktop/server_manager.py`의 `HOST = "127.0.0.1"` 상수, 패키징 앱 실행 후 `/api/health`를 127.0.0.1로만 호출해 응답 확인 | 통과 |
| admin API 기본 비활성 | 패키징 앱 실행 후 `GET /api/expert-data/summary`, `GET /api/shadow/summary` 실제 호출 | 둘 다 404 |
| shadow mode 기본 비활성 | 패키징 앱 실행 후 `/api/health`의 `shadow_enabled` 확인 (API 키 미설정 상태) | `false` |

## `find` 명령 재현 (참고용)

```bash
APP="dist/TOEFL Writing.app"
find "$APP" -iname "*.env*"
find "$APP" -iname "*.db" -o -iname "*.sqlite*"
find "$APP" -iname ".git*"
find "$APP" -iname "*pytest_cache*" -o -iname "conftest*" -o -iname "test_*.py"
find "$APP" -iname "*screenshot*" -o -iname "*.log"
find "$APP" -iname "*expert*" -o -iname "*submission*"
```

## 빌드 산출물 파일 목록/크기

```text
전체 크기: 54M
Contents/MacOS/TOEFL Writing        12.7M (실행 파일)
Contents/Resources/static/          index.html, app.js, styles.css (3개 파일만)
Contents/Frameworks/                Python.framework, WebKit, AppKit, Security,
                                     uvloop, websockets, httptools, pydantic_core 등
Contents/_CodeSignature/            ad-hoc 서명 메타데이터
Contents/Info.plist
```

`Contents/Resources/static/`에 `logo.png`, `screenshot_main.png`,
`screenshot_report.png`(모두 0바이트, README 전용 placeholder)가 처음에는
같이 포함됐으나, `packaging/toefl-writing-macos.spec`을 수정해 앱이 실제
서빙하는 3개 파일만 남기도록 정리했다(`docs/macos-build.md`의 "실제 발견된
문제" 참고).

## Info.plist에 개인정보/비밀정보 없음 확인

```xml
<CFBundleDisplayName>토플첨삭기 by이강민</CFBundleDisplayName>
<CFBundleIdentifier>com.leekangmin.toeflwriting</CFBundleIdentifier>
<CFBundleShortVersionString>0.5.0</CFBundleShortVersionString>
```

버전 문자열은 `app/version.py`(단일 출처)에서 빌드 시점에 주입되며, 개발자
개인정보(이메일, 홈 디렉터리 등)는 포함하지 않는다.

## 검증하지 않은 것 (정직한 한계)

- **바이너리(.so/.dylib) 내부 문자열까지 전수 검사하지는 않았다** — PyZ
  아카이브(순수 Python bytecode)는 전수 검사했지만, `Contents/Frameworks/`
  아래의 컴파일된 확장 모듈(예: `pydantic_core`, `uvloop`)은 서드파티
  배포 바이너리이므로 별도로 열어보지 않았다. 이들은 PyPI 공개 wheel에서
  그대로 온 것이라 프로젝트 고유의 비밀정보가 담길 경로가 없다고 판단했다.
- codesign/notarization 관련 서명 체인 검증은 하지 않았다(현재 unsigned —
  `docs/macos-build.md` 참고).
