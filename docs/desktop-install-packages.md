# 데스크톱 설치 패키지 (macOS / Windows)

사용자가 소스나 Docker를 다루지 않고 **더블클릭으로 설치·실행**할 수 있는
네이티브 앱 패키지를 빌드하는 방법과 현재 검증 상태를 정리한다.

## macOS (.app / DMG) — 로컬 빌드 검증됨

```bash
./scripts/build_macos.sh   # 테스트→아이콘→PyInstaller→검증→스모크→manifest→zip
./scripts/make_dmg.sh      # dist/TOEFL-Writing-macOS-<버전>.dmg
```

- 산출물: `dist/TOEFL Writing.app`, `TOEFL-Writing-macOS-0.6.0.dmg`(32MB),
  `TOEFL-Writing-macOS-0.6.0.zip`(46MB), `release-manifest.json`, `checksums.txt`
- 아이콘: `packaging/resources/app.icns`가 번들에 포함되고 Info.plist가 참조
- 검증(로컬 실제 실행): 최초 실행·평가·기록·PDF·재실행 데이터 유지·graceful
  shutdown(exit 0)·업데이트 데이터 보존·보안 스캔 전부 PASS
- **서명·공증: 없음(ad-hoc).** Apple Developer 인증서가 없어 Gatekeeper 경고가
  뜨며, 정식 외부 배포용이 아니다. 인증서 확보 후 `scripts/sign_and_notarize.sh`
  실행 절차는 `docs/signing-and-notarization.md` 참고.

### 설치 방법 (사용자)
1. DMG를 열고 앱을 Applications로 드래그
2. 첫 실행 시 **우클릭 → 열기**(Gatekeeper 경고 우회)

## Windows (.exe / 설치본) — CI 빌드, 런타임 미검증

Windows 실행 파일은 Windows에서만 빌드할 수 있어, GitHub Actions
`windows-latest` 러너에서 실제로 빌드한다(`.github/workflows/build-desktop.yml`).

- 빌드 스크립트: `windows/build_windows.ps1` (PyInstaller onefile,
  `packaging/resources/app.ico` 아이콘, `app/version.py` 버전 반영)
- 인스톨러: `windows/installer/TOEFLScorer.iss` (Inno Setup) →
  `TOEFL-Writing-Setup-<버전>.exe`
- 산출물: `dist_windows/TOEFL Writing.exe`, 설치본 `.exe`
- 트리거: 버전 태그(`v*`) 푸시 또는 수동 실행. 태그 빌드는 GitHub Release에
  첨부되고, 그 외에는 워크플로 아티팩트로 올라간다.

### 정직한 한계
- **CI가 windows-latest에서 실제로 .exe를 빌드하지만, 물리 Windows 데스크톱에서
  창(pywebview WebView2)이 정상적으로 뜨는지는 이 프로젝트에서 검증하지 못했다.**
  Windows 실기기 스모크 테스트가 남아 있다.
- 코드 서명 없음 → 실행 시 SmartScreen 경고가 예상된다.
- Windows에서 지금 확실히 쓰려면 Docker 경로(README 참고)를 권장한다.

## 헤드리스 모드 (`TOEFL_NO_WINDOW=1`)

패키징 스모크 테스트와 CI는 디스플레이가 없으므로, 이 환경변수를 주면 런처가
네이티브 창을 열지 않고 서버만 유지한다(종료는 SIGTERM/SIGINT). 네이티브 창
자체의 육안 렌더링은 여전히 수동 검증 대상이다.

## 버전·아이콘 단일 출처

- 버전: `app/version.py`의 `APP_VERSION`/`APP_BUNDLE_NAME` — spec·Info.plist·
  Inno Setup·manifest가 모두 이 값을 읽는다.
- 아이콘: `scripts/generate_app_icon.py`가 자체 디자인을 `.icns`(macOS)와
  `.ico`(Windows)로 함께 생성한다. `.icns`는 iconutil이 있는 macOS에서만,
  `.ico`는 Pillow만으로 어디서든 생성된다.
