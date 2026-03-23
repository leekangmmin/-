# 2026 개정 TOEFL 라이팅 첨삭 프로그램

> FastAPI 기반 토플 라이팅 첨삭 프로그램 — macOS 네이티브 앱 / Windows 데스크톱 지원

## 다운로드

아래 버튼을 클릭하면 최신 버전이 바로 다운로드됩니다.

<p align="center">
  <a href="https://github.com/leekangmmin/-/releases/download/latest/TOEFLScorer-macOS.dmg">
    <img src="https://img.shields.io/badge/macOS-다운로드-000000?style=for-the-badge&logo=apple&logoColor=white" alt="macOS 다운로드" height="50"/>
  </a>
  &nbsp;&nbsp;&nbsp;
  <a href="https://github.com/leekangmmin/-/releases/tag/latest">
    <img src="https://img.shields.io/badge/Windows-다운로드-0078D4?style=for-the-badge&logo=windows&logoColor=white" alt="Windows 다운로드" height="50"/>
  </a>
</p>

| 플랫폼 | 파일 | 요구사항 |
|--------|------|----------|
| macOS 12+ | `TOEFLScorer-macOS.dmg` | Apple Silicon / Intel 모두 지원 |
| Windows 10/11 | `TOEFLScorer-Setup.exe` | 64비트, Python 불필요 |

> **참고:** 릴리즈 파일은 GitHub Actions에서 자동으로 빌드·업데이트됩니다. 항상 최신 버전이 유지됩니다.

---

FastAPI 기반의 토플 라이팅 첨삭 웹앱입니다.

macOS에서는 순수 SwiftUI 네이티브 앱으로 바로 실행할 수 있습니다.

## 포함 기능

- 통합형 / Academic Discussion 답안 평가
- 4개 루브릭(Task Fulfillment, Organization, Development, Language Use)
- 프롬프트 적합성 점수 + 매칭/누락 키워드
- 주장-근거-설명 문장 매핑 시각화
- 문법 오류 유형 통계(시제/관사/전치사/Run-on/수일치/문장부호)
- 목표 점수 기반 리라이팅(최소 수정 / 적극 수정)
- 샘플 답안 요소 비교(포함 요소/누락 요소)
- 신뢰도 근거 설명 + 한영 요약 피드백
- 템플릿 코치(오프닝/바디/전환어/클로징)
- 점수 근거 하이라이트(문장별 positive/negative/neutral)
- 약점 사전(오답 패턴 -> 교정 패턴)
- 개인화 코칭(최근 제출 기반 다음 집중 영역)
- 외부 AI 연결 설정(OpenAI/Claude/Gemini) 및 연결 테스트
- 프롬프트 라이브러리(저장/불러오기)
- 리라이팅 결과 원클릭 복사(최소 수정/적극 수정)
- 제출 전 위험 경고(precheck)
- PDF 리포트 내보내기
- 성장 대시보드(점수 추이, 상위 오류, 추천 학습 과제)
- 강점/보완점/즉시 실행 액션 플랜 제시
- 문장 단위 첨삭 예시와 고득점 샘플 문단 제공
- 제출 이력 SQLite 저장 및 조회

## 실행 방법

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

브라우저에서 아래 주소를 열면 됩니다.

- http://127.0.0.1:8000

## macOS 앱처럼 실행하기

- 프로젝트 루트에서 [실행.command](실행.command) 더블클릭
- 또는 [토플첨삭기 by이강민.app](토플첨삭기%20by이강민.app) 실행

위 방식은 외부 브라우저를 열지 않고 네이티브 앱 창에서 바로 동작합니다.

## 네이티브 앱 개발 소스

- SwiftUI 클라이언트: [NativeMacApp](NativeMacApp)
- 실행 파일 빌드: `swift build -c release --package-path NativeMacApp`

## Windows 배포

현재 macOS SwiftUI UI는 Windows에서 직접 실행되지 않으므로, Windows에서는 FastAPI + 데스크톱 웹뷰(pywebview) 런처(exe)로 배포합니다.

- 런처 소스: [windows/app_launcher.py](windows/app_launcher.py)
- Windows 즉시 실행(소스 기반): [windows/run_windows.bat](windows/run_windows.bat)
- Windows exe 빌드 스크립트: [windows/build_windows.ps1](windows/build_windows.ps1)

### Windows exe 만들기

1. Windows PC에서 PowerShell 실행
2. 프로젝트 루트로 이동
3. 아래 명령 실행

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_windows.ps1
```

빌드가 완료되면 `dist_windows/TOEFLScorer.exe`가 생성됩니다.

### Windows 설치파일(Setup.exe) 만들기

1. Inno Setup 6 설치
2. 아래 명령 실행

```powershell
powershell -ExecutionPolicy Bypass -File windows/build_installer.ps1
```

완료되면 `dist_windows/installer/TOEFLScorer-Setup.exe`가 생성됩니다.

실행 시 기본 동작:

- 서버를 자동 실행
- 앱 창 내부(데스크톱 웹뷰)에서 UI 표시
- 웹뷰 런타임 이슈가 있으면 자동으로 브라우저 모드로 폴백

## macOS 설치파일(.dmg) 만들기

macOS에서는 아래 스크립트로 설치 이미지(dmg)를 만듭니다.

```bash
./macos/build_installer.command
```

완료되면 `dist_macos/TOEFLScorer-macOS.dmg`가 생성됩니다.

## GitHub Actions로 설치파일 자동 빌드

- 워크플로 파일: [.github/workflows/build-installers.yml](.github/workflows/build-installers.yml)
- 트리거:
  - 수동 실행(`workflow_dispatch`)
  - `v*` 태그 푸시

실행 후 GitHub Actions 아티팩트에서 아래 파일을 다운로드할 수 있습니다.

- `TOEFLScorer-macOS-dmg`
- `TOEFLScorer-Windows-Setup`

### 네이티브 앱 확장 기능

- 현재 결과 탭: 점수/요약/강점/약점/액션/문법 통계
- 성장 대시보드 탭: 평균 지표, 점수 추이, 문법 이슈 바 차트
- 제출 히스토리 탭: 최근 제출 목록, 항목별 PDF 다운로드
- 최신 리포트 PDF 버튼: 가장 최근 제출 결과 바로 다운로드/열기

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

최근 제출 내역을 반환합니다.

### GET /api/dashboard?limit=200

누적 제출 기반 성장 대시보드 데이터를 반환합니다.

### GET /api/report/{submission_id}.pdf

제출별 PDF 리포트를 생성해 다운로드합니다.

## 구조

- app/main.py: FastAPI 엔트리포인트
- app/scorer.py: 루브릭 기반 점수 추정 엔진
- app/feedback.py: 첨삭/개선 피드백 생성
- app/db.py: SQLite 저장
- static/: 프론트엔드 UI

## 주의

- ETS 공식 채점을 대체하는 도구가 아니라, 학습용 추정/피드백 도구입니다.

---

## 기능 추천 (개발 로드맵)

현재 앱을 더 강력하게 만들 수 있는 추천 기능 목록입니다.

### 고우선순위 (학습 효과 직결)

| 기능 | 설명 |
|------|------|
| ⏱ **내장 타이머** | TOEFL 실제 시험 시간(통합형 20분 / Discussion 10분) 기반 카운트다운 타이머 |
| 📊 **어휘 수준 분석** | CEFR B2/C1 기준 학술 어휘 사용 비율 표시, 대체 어휘 제안 |
| 🔁 **이전 답안 비교** | 같은 프롬프트에 대한 이전 제출과 현재 제출 나란히 비교 |
| 📝 **자동 초안 저장** | 작성 중 2분마다 자동 저장, 실수로 지워도 복구 가능 |

### 중우선순위 (사용 편의 개선)

| 기능 | 설명 |
|------|------|
| 🌙 **다크 모드** | 장시간 학습 시 눈 피로 감소 |
| 📋 **교정문 원클릭 복사** | 리라이팅 결과 전체를 버튼 하나로 클립보드에 복사 |
| 🔍 **문장 단위 점수** | 각 문장에 점수(초록/노랑/빨강)를 인라인으로 표시 |
| 🗂 **프롬프트 라이브러리** | 자주 쓰는 프롬프트 저장·불러오기 기능 |

### 장기 목표 (고급 기능)

| 기능 | 설명 |
|------|------|
| 🤖 **AI 리라이팅 강화** | GPT/Claude API 연동으로 문체·논리 흐름까지 개선하는 고급 첨삭 |
| 📈 **주간 학습 리포트** | 주간 제출 횟수·평균 점수·주요 오류 패턴을 이메일/노티로 발송 |
| 🎯 **목표 점수 달성 예측** | 현재 추세 기반으로 목표 점수 도달 예상 제출 횟수 계산 |
| 🌐 **웹 버전 배포** | 설치 없이 브라우저에서 바로 사용 (Vercel/Railway 배포) |
