# 2026 개정 TOEFL 라이팅 첨삭 프로그램

> FastAPI 기반 TOEFL 라이팅 첨삭기 (macOS 네이티브 앱 + Windows 데스크톱 지원)

## 다운로드

아래 버튼을 클릭하면 최신 버전이 바로 다운로드됩니다.

<p align="center">
  <a href="https://github.com/leekangmmin/-/releases/download/latest/TOEFLScorer-macOS.dmg">
    <img src="https://img.shields.io/badge/macOS-다운로드-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS 다운로드" height="50"/>
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/leekangmmin/-/releases/download/latest/TOEFLScorer-Setup.exe">
    <img src="https://img.shields.io/badge/Windows-다운로드-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 다운로드" height="50"/>
  </a>
</p>

| 플랫폼 | 파일 | 요구사항 |
|--------|------|----------|
| macOS 12+ | `TOEFLScorer-macOS.dmg` | Apple Silicon / Intel 지원 |
| Windows 10/11 | `TOEFLScorer-Setup.exe` | 64비트 |

> **참고:** 릴리즈 파일은 GitHub Actions에서 자동으로 빌드·업데이트됩니다. 항상 최신 버전이 유지됩니다.

---

## 핵심 기능

- 통합형/Academic Discussion 자동 평가
- 6개 루브릭 기반 채점(사용자 표기 6.0 기준)
- 문법 오류 유형 분석 + 정밀 교정 제안
- 목표 점수 리라이팅(최소 수정/적극 수정)
- PDF 리포트 생성 + 성장 대시보드 + 제출 이력
- 외부 AI 연동(OpenAI/Claude/Gemini)

## 빠른 실행

### 로컬 웹 실행

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 아래 주소를 열면 됩니다.

- http://127.0.0.1:8000

### macOS 앱처럼 실행

- 프로젝트 루트에서 [실행.command](실행.command) 더블클릭
- 또는 [토플첨삭기 by이강민.app](토플첨삭기%20by이강민.app) 실행

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
