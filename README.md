
<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/logo.png" alt="TOEFL 첨삭기 로고" width="120"/>
</p>

<h1 align="center">2026 개정 TOEFL 라이팅 첨삭기</h1>

<p align="center">
  <b>AI 실시간 첨삭, 성장 대시보드, PDF 리포트까지 한 번에</b><br>
  <img src="https://img.shields.io/github/v/release/leekangmmin/-?style=flat-square"/>
  <img src="https://img.shields.io/github/last-commit/leekangmmin/-?style=flat-square"/>
  <img src="https://img.shields.io/github/languages/top/leekangmmin/-?style=flat-square"/>
</p>

<p align="center">
  <a href="https://github.com/leekangmmin/-/releases/download/latest/TOEFLScorer-macOS.dmg" style="text-decoration:none;">
    <img src="https://img.shields.io/badge/macOS-앱%20다운로드-000000?style=for-the-badge&logo=apple&logoColor=white&labelColor=000000" alt="macOS 앱 다운로드" width="320"/>
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/leekangmmin/-/releases/download/latest/TOEFLScorer-Setup.exe" style="text-decoration:none;">
    <img src="https://img.shields.io/badge/Windows-앱%20다운로드-0078D4?style=for-the-badge&logo=windows&logoColor=white&labelColor=0078D4" alt="Windows 앱 다운로드" width="320"/>
  </a>
</p>

---

<div align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_main.png" alt="앱 메인화면 스크린샷" width="700"/>
</div>

---


## 주요 기능

- **AI 실시간 문법/논리/어휘 첨삭** (내장/외부 AI)
- **TOEFL 루브릭 기반 점수 예측** (6.0 만점 환산)
- **문법/논리/어휘별 신뢰도 점수**로 피드백 우선순위 제공
- **PDF 리포트 자동 생성** (제출별/누적 성장 대시보드)
- **macOS/Windows 네이티브 앱** (설치/포터블 모두 지원)
- **API 연동 및 오픈소스 확장성**

---


## 빠른 시작

- 위 다운로드 버튼 클릭 → 설치파일 실행
- 또는 포터블 exe 바로 실행
- macOS: 앱 실행 시 별도 Python/가상환경 필요 없음
- Windows: 설치파일 또는 포터블 exe 실행

### 개발자/로컬 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

- http://127.0.0.1:8000 접속

---


---


## 프로젝트 구조

- **app/**: FastAPI 백엔드/AI 엔진
- **static/**: 프론트엔드(HTML/JS/CSS)
- **NativeMacApp/**: macOS SwiftUI 클라이언트
- **windows/**: Windows 런처/빌드 스크립트

---


## 빌드/배포

- macOS: `./macos/build_standalone_server.command` → 앱 실행
- Windows: `windows/build_windows.ps1` → exe 실행
- GitHub Actions 자동 빌드/릴리즈

---


## 주의

- 본 도구는 학습/연습용 피드백 제공 목적이며, ETS 공식 채점 결과와 다를 수 있습니다.

---

<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_report.png" alt="PDF 리포트 스크린샷" width="700"/>
</p>

위 방식은 외부 브라우저 없이 네이티브 창에서 동작합니다.

---

## AI 연동

앱 내부 설정 화면에서 아래 공급자 중 하나를 선택해 API 키를 저장하면, 연결된 AI를 첨삭 보강에 사용합니다.

- ChatGPT (OpenAI)
- Claude (Anthropic)
- Gemini (Google)

기본값은 로컬 모드이며, AI 연결이 활성화되면 분석 모드가 AI로 표시됩니다.

---

## API

### POST /api/evaluate

요청 예시:

```json
{
  "prompt_type": "academic_discussion",
  "prompt_text": "Some teachers think students should take more group projects...",
  "essay_text": "I agree with the professor because ..."
}
```

### POST /api/precheck

제출 전 위험 경고(분량/키워드 반영/문단/run-on)를 반환합니다.

### GET /api/history?limit=10

최근 제출 내역 반환

### GET /api/dashboard?limit=200

누적 제출 기반 성장 대시보드 반환

### GET /api/report/{submission_id}.pdf

제출별 PDF 리포트 생성/다운로드

---

## 프로젝트 구조

- app/main.py: FastAPI 엔트리포인트
- app/scorer.py: 루브릭 기반 점수 추정 엔진
- app/feedback.py: 첨삭/개선 피드백 생성
- app/db.py: SQLite 저장
- static/: 프론트엔드 UI

---

## 빌드/배포

### macOS 네이티브 개발 소스

- SwiftUI 클라이언트: [NativeMacApp](NativeMacApp)
- 실행 파일 빌드: `swift build -c release --package-path NativeMacApp`

### Windows 배포

macOS SwiftUI UI는 Windows에서 직접 실행되지 않으므로, Windows에서는 FastAPI + pywebview 런처(exe)로 배포합니다.

- 런처 소스: [windows/app_launcher.py](windows/app_launcher.py)
- Windows 실행(소스): [windows/run_windows.bat](windows/run_windows.bat)
- exe 빌드 스크립트: [windows/build_windows.ps1](windows/build_windows.ps1)

#### Windows exe 만들기

1. Windows PowerShell 실행
2. 프로젝트 루트 이동
3. 아래 명령 실행

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_windows.ps1
```

완료 후 `dist_windows/TOEFLScorer.exe`가 생성됩니다.

#### Windows 설치파일(Setup.exe) 만들기

1. Inno Setup 6 설치
2. 아래 명령 실행

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_installer.ps1
```

완료 후 `dist_windows/installer/TOEFLScorer-Setup.exe`가 생성됩니다.

#### Windows 포터블 실행파일(.exe) 만들기

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_windows.ps1
```

완료 후 `dist_windows/TOEFLScorer.exe`가 생성됩니다.

### macOS 설치파일(.dmg) 만들기

```bash
./macos/build_installer.command
```

완료 후 `dist_macos/TOEFLScorer-macOS.dmg`가 생성됩니다.

### GitHub Actions 자동 빌드

- 워크플로: [.github/workflows/build-installers.yml](.github/workflows/build-installers.yml)
- 트리거: `workflow_dispatch`, `main` 푸시, `v*` 태그 푸시

---

## 주의

- ETS 공식 채점을 대체하는 도구가 아니라, 학습용 추정/피드백 도구입니다.
