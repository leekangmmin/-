# macOS 빌드 (Phase 5 내부 알파)

## 빌드 명령

```bash
./scripts/build_macos.sh
```

프로젝트 루트에서 실행한다. 사용자의 기존 개발 `.venv`에 의존하지 않고
매번 전용 `.build-venv`를 새로 만든다(clean build). 스크립트가 순서대로
수행하는 것:

1. `build/`, `dist/` clean
2. `.build-venv` 확인/생성 (python3.11)
3. `requirements.txt` + `pyinstaller` 설치
4. `py_compile app/*.py desktop/*.py scripts/*.py`
5. `pytest tests/ -q` (215개 전부 통과해야 진행)
6. `python -m tests.eval_harness` (품질 회귀 게이트)
7. `pyinstaller packaging/toefl-writing-macos.spec --clean --noconfirm`
8. `scripts/packaged_app_smoke_test.py`로 실제 `.app`을 실행해 자동 검증
9. 산출물 요약 출력 (경로/크기/내부 디렉터리 목록)

## spec 파일

`packaging/toefl-writing-macos.spec` — PyInstaller one-dir + macOS BUNDLE.

- 진입점: `packaging/entry_point.py` (`desktop.launcher.main()` 호출 wrapper)
- **중요한 버그와 수정**: `desktop/server_manager.py`가 `uvicorn.Config("app.main:app", ...)`
  처럼 **문자열**로 앱을 참조한다. PyInstaller의 정적 의존성 분석(Analysis)은
  문자열 기반 런타임 임포트를 추적하지 못해, 처음 빌드에서 `app.main`과 그
  하위 의존성 전체가 번들에서 누락되는 문제가 있었다(`ERROR: Error loading
  ASGI app. Could not import module "app.main"` — 실제로 최초 빌드 시 재현,
  아래 "실제 발견된 문제" 절 참고). `packaging/entry_point.py`에
  `import app.main  # noqa: F401`을 명시적으로 추가해 PyInstaller가 전체
  의존성 트리를 정적으로 발견하도록 강제해 해결했다.
- 포함 데이터: `static/index.html`, `static/app.js`, `static/styles.css`만
  명시적으로 나열한다(전체 `static/` 폴더를 통째로 넣지 않는다 — `logo.png`,
  `screenshot_*.png`는 README.md에서 GitHub raw URL로만 참조되는 0바이트
  placeholder이고 앱 UI 어디서도 로드하지 않으므로 제외했다).
- `hiddenimports`에 uvicorn의 lazy-import 계열(`uvicorn.loops.auto` 등)과
  `webview.platforms.cocoa`를 명시했다.
- 버전 메타데이터는 `app/version.py`(단일 출처)에서 읽어 spec과 Info.plist에
  주입한다 — 여러 곳에 하드코딩하지 않는다.
- 아이콘: `.icns` 파일을 아직 준비하지 못했다(`icon=None`) — pywebview
  기본 아이콘으로 대체 표시된다. **향후 작업**: `packaging/resources/app.icns`
  준비 후 spec의 `icon=` 값 교체.

## 산출물

| 항목 | 값 |
| --- | --- |
| 경로 | `dist/TOEFL Writing.app` |
| 실행 파일 | `Contents/MacOS/TOEFL Writing` (12.7MB) |
| 전체 크기 | 54MB |
| CFBundleName | `TOEFL Writing` |
| CFBundleDisplayName | `토플첨삭기 by이강민` |
| CFBundleIdentifier | `com.leekangmin.toeflwriting` |
| CFBundleShortVersionString / CFBundleVersion | `0.5.0` (app/version.py APP_VERSION) |
| LSMinimumSystemVersion | `12.0` |
| NSHighResolutionCapable | true |

## 서명·공증 상태 (정직한 상태 표기)

**Apple Developer 인증서가 없으므로 실제 서명·공증을 완료했다고 주장하지
않는다.**

- package build complete ✅
- **unsigned internal alpha** (인증서 없이 ad-hoc 서명만 자동 적용됨 —
  PyInstaller가 빌드 로그에 `Re-signing the EXE`, `Signing the BUNDLE...`를
  출력하지만 이는 Apple Developer 서명이 아니라 로컬 ad-hoc 서명이다)
- codesign pending (실제 Developer ID 인증서 필요)
- notarization pending (Apple 계정 및 `xcrun notarytool` 필요)
- **external distribution prohibited** — Gatekeeper가 unsigned/ad-hoc
  서명 앱을 인터넷에서 받은 것으로 표시하면 실행을 막는다. 현재 산출물은
  개발자 본인 기기에서 `xattr -dr com.apple.quarantine` 등으로 격리 해제
  후 실행하는 내부 알파 용도로만 사용해야 한다.

향후 실제 인증서를 확보하면 `entitlements_file`에
`packaging/entitlements.plist`를 지정하고 `codesign_identity`를 설정한 뒤
`codesign --deep --sign "Developer ID Application: ..." --entitlements
packaging/entitlements.plist "dist/TOEFL Writing.app"`, 이어서
`xcrun notarytool submit`을 실행하는 절차가 필요하다(아직 미수행).

## 실행 결과 (실제 빌드 로그 기반, 재현 가능)

```text
명령: ./scripts/build_macos.sh
종료 코드: 0
결과: 215 tests passed, eval_harness 통과, PyInstaller 빌드 성공,
      packaged_app_smoke_test.py 전체 통과 (아래 internal-alpha-test-report.md 참고)
```

## 실제 발견된 문제와 수정 (빌드 반복 과정 기록)

1. **`app.main` 정적 임포트 누락** (위 spec 절 참고) — `entry_point.py`에
   `import app.main` 추가로 해결. 수정 전/후 각각 실제로 빌드하고
   smoke test를 실행해 재현 및 해결을 확인했다(반복 빌드 로그
   `/tmp/build_macos_log.txt` → 실패, `/tmp/build_macos_log2.txt` → 통과).
2. **SIGTERM graceful shutdown 미흡** — 초기 `desktop/launcher.py`는 창
   닫기 이벤트(`window.events.closing`)에서만 서버를 정리했다. 프로세스가
   신호(SIGTERM/SIGINT)로 종료되는 경로(예: 자동화 테스트, 강제 종료)에
   대한 보조 안전망이 없어서 `signal.signal(SIGTERM/SIGINT, handler)`를
   추가했다. 실제 패키징된 `.app`에서 `subprocess.Popen` + `send_signal`로
   두 번 검증해 exit code 0으로 정상 종료됨을 확인했다.
3. **불필요한 정적 자산 포함** — 최초 spec은 `static/` 폴더 전체를
   포함했는데, README 전용 스크린샷 placeholder(`logo.png`,
   `screenshot_*.png`, 모두 0바이트)가 딸려 들어갔다. 실제 서빙되는 3개
   파일만 명시적으로 나열하도록 수정했다.
