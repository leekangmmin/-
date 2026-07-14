<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/logo.png" alt="토플 라이팅 채점기 아이콘" width="104">
</p>

<h1 align="center">토플 라이팅 채점기</h1>

<p align="center">
  <strong>API 키 없이 바로 TOEFL Writing 답안을 분석할 수 있는 로컬 우선·웹 기반 연습 채점기</strong><br>
  <sub>A local-first TOEFL Writing practice scorer — usable in the browser, with no API key required for core scoring.</sub>
</p>

<p align="center">
  <a href="https://leekangmmin.github.io/-/"><strong>웹앱 바로 사용하기</strong></a>
  · <a href="#quick-start">직접 실행하기</a>
  · <a href="#features">기능</a>
  · <a href="#privacy">개인정보</a>
</p>

<p align="center">
  <a href="https://github.com/leekangmmin/-/actions/workflows/tests.yml"><img src="https://img.shields.io/github/actions/workflow/status/leekangmmin/-/tests.yml?branch=main&label=tests&style=flat-square" alt="테스트 상태"></a>
  <a href="https://github.com/leekangmmin/-/actions/workflows/pages.yml"><img src="https://img.shields.io/github/actions/workflow/status/leekangmmin/-/pages.yml?branch=main&label=web%20deploy&style=flat-square" alt="웹 배포 상태"></a>
  <img src="https://img.shields.io/badge/core-no%20API%20key-6d5dfc?style=flat-square" alt="핵심 채점 API 키 불필요">
  <img src="https://img.shields.io/badge/scoring-practice%20estimate-f59e0b?style=flat-square" alt="연습용 예상 점수">
  <a href="LICENSE"><img src="https://img.shields.io/badge/license-MIT-22a06b?style=flat-square" alt="MIT License"></a>
</p>

> [!IMPORTANT]
> 이 프로젝트는 **연습용 비공식 채점 도구**입니다. ETS의 공식 채점 서비스가 아니며 TOEFL 또는 ETS와 제휴·보증 관계가 없습니다.

## Preview

<table>
  <tr>
    <td width="50%"><img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_main.png" alt="답안 작성 화면"></td>
    <td width="50%"><img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_report.png" alt="채점 결과 화면"></td>
  </tr>
  <tr>
    <td align="center"><sub>답안 작성 · 유형 자동 감지 · 성장 대시보드</sub></td>
    <td align="center"><sub>영역별 점수 · 문장 첨삭 · 실행 계획</sub></td>
  </tr>
</table>

<a id="features"></a>
## Features

| 기능 | 상태 | 비고 |
|---|---:|---|
| TOEFL Writing 연습용 채점 | ✅ | Write an Email·Academic Discussion 자동 구분 |
| 구조·내용·일관성·예시·문법·어휘 진단 | ✅ | 결정론적 Offline Core |
| 고득점 구조 체크 | ✅ | 감지된 구성, 누락 구성, 다음 연습 목표 |
| 문법 피드백·문장별 첨삭 | ✅ | FastAPI/데스크톱 전체판 |
| 어휘 분석·패러프레이징 제안 | ✅ | FastAPI/데스크톱 전체판 |
| PDF 리포트·기록·백업 | ✅ | FastAPI/데스크톱 전체판 |
| Build a Sentence | ✅ | 자체 제작 15문항, FastAPI/데스크톱 전체판 |
| 설치 없는 GitHub Pages 웹앱 | ✅ | 브라우저 내부에서 동작하는 경량판 |
| Docker self-host | ✅ | 전체 웹 기능 사용 가능 |
| 로컬 AI | 선택 | Ollama/llama.cpp 확장 경로, 첨삭 보강용 |
| 클라우드 AI | 선택·기본 꺼짐 | 직접 활성화하면 검증된 2026 루브릭 과제 점수를 운영 화면에 사용 |
| macOS 앱 | 내부 RC | 서명·공증 전, Gatekeeper 경고 가능 |
| Windows 네이티브 앱 | 미검증 | 빌드 스크립트만 준비, 공개 릴리스 없음 |
| ETS 공식 채점 | 해당 없음 | 비공식 연습용 예상치 |

### 어떤 버전을 사용해야 하나요?

- **빠르게 연습:** [GitHub Pages 웹앱](https://leekangmmin.github.io/-/) — 설치 없이 구조와 6개 영역을 즉시 분석합니다.
- **전체 기능:** Docker 또는 소스 실행 — 기록, 상세 문법 첨삭, PDF, Build a Sentence를 제공합니다.
- **개인 로컬 환경:** macOS 내부 RC 또는 로컬 서버 — 답안과 기록을 자기 기기에서 관리합니다.

<a id="quick-start"></a>
## Quick Start

### 1. Try in Browser

**[https://leekangmmin.github.io/-/](https://leekangmmin.github.io/-/)**

설치·로그인·사용자 API 키가 필요 없습니다. GitHub Pages 경량판의 채점은 브라우저 JavaScript로 실행되며 답안을 별도 채점 서버에 제출하지 않습니다. 브라우저 저장소에 임시 초안을 보관할 수 있습니다.

> [!NOTE]
> Pages 경량판은 전체 FastAPI 앱과 기능 범위가 다릅니다. PDF, 제출 기록, 정밀 문법 교정, Build a Sentence가 필요하면 아래 Docker 실행을 사용하세요.

### 2. Run with Docker

```bash
git clone https://github.com/leekangmmin/-.git toefl-writing-scorer
cd toefl-writing-scorer
docker build -t toefl-writing-scorer .
docker run --rm -p 8000:8000 -e TOEFL_WEB_MODE=1 toefl-writing-scorer
```

브라우저에서 **http://localhost:8000**을 엽니다. 핵심 채점에는 API 키가 필요하지 않습니다.

### 3. Run from Source

macOS/Linux:

```bash
git clone https://github.com/leekangmmin/-.git toefl-writing-scorer
cd toefl-writing-scorer
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Windows PowerShell은 Python 3.11 이상에서 다음과 같이 실행할 수 있습니다. 이는 **웹 서버 실행 경로**이며 Windows 네이티브 데스크톱 앱 검증을 의미하지 않습니다.

```powershell
py -3.11 -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Architecture

```text
GitHub Pages                         Desktop / Docker / source
┌─────────────────────┐             ┌──────────────────────────┐
│ Browser-only web app│             │ Browser / pywebview      │
│ Offline Core Web    │             └────────────┬─────────────┘
└──────────┬──────────┘                          │
           │                              FastAPI application
           │                                      │
           └──── deterministic analysis ──────────┤
                                                  ├─ scoring + prompt fit
                                                  ├─ grammar + vocabulary
                                                  ├─ high-score structure
                                                  ├─ Build a Sentence
                                                  ├─ history / backup
                                                  └─ PDF report

Optional enhancement paths
├─ Local AI: Ollama / llama.cpp
└─ Cloud AI: explicit setup only, disabled by default
```

운영 화면은 Email/Academic Discussion 한 과제의 **0–5 점수**를 표시합니다. 클라우드 AI가 꺼져 있으면 결정론적 Offline Core를 사용하고, 사용자가 OpenAI·Claude·Gemini를 직접 설정해 켜면 엄격한 2026 루브릭 JSON 검증을 통과한 AI 점수를 사용합니다. AI 응답이 실패하거나 스키마·의미 검증을 통과하지 못하면 내장 점수로 안전하게 돌아가며, 화면에 점수 출처와 대체 사유를 표시합니다.

## Modes

| 모드 | 용도 | 처리 위치 | AI/API 요구사항 |
|---|---|---|---|
| GitHub Pages 웹앱 | 설치 없는 빠른 연습 | 사용자의 브라우저 | 핵심 채점에 불필요 |
| Docker/FastAPI 웹 | 전체 기능 self-host | 실행 중인 FastAPI 서버 | 핵심 채점에 불필요 |
| 데스크톱 로컬 | 개인 기기에서 전체 기능 | 사용자 기기 | 핵심 채점에 불필요 |
| AI-enhanced | 선택형 심화 피드백 | 로컬 모델 또는 설정한 제공자 | 로컬 모델 또는 명시적 클라우드 설정 |

<a id="privacy"></a>
## Privacy

개인정보 설명은 실행 방식별로 다릅니다. “모든 모드에서 답안이 기기를 떠나지 않는다”고 주장하지 않습니다.

### GitHub Pages 웹앱

답안 분석은 브라우저에서 실행됩니다. 별도 채점 API로 답안을 보내지 않으며 초안은 브라우저 저장소에 보관됩니다. GitHub는 정적 HTML·JavaScript·이미지 파일을 제공합니다.

### Desktop/local mode

기본적으로 답안과 기록을 자신의 컴퓨터에서 처리·저장합니다. 데스크톱 서버는 loopback 주소에 바인딩합니다.

### Docker/FastAPI hosted mode

브라우저가 답안을 **해당 FastAPI 서버로 전송**해 채점합니다. 자신의 컴퓨터에서 Docker를 실행하면 서버도 자기 컴퓨터에 있습니다. 제3자가 운영하는 서버에 배포했다면 답안은 그 운영자의 서버로 전송됩니다. 기본 hosted 모드는 외부 AI 제공자에게 답안을 보내지 않습니다.

### Cloud AI

클라우드 AI는 선택 기능이며 기본적으로 비활성화되어 있습니다. 사용자가 직접 활성화하고 제공자를 설정한 경우에만 해당 제공자에게 텍스트가 전송될 수 있습니다. 비공개 고득점 코퍼스는 클라우드 AI로 전송하지 않습니다.

자세한 내용: [웹 개인정보 안내](docs/web-privacy.md) · [로컬/클라우드 AI 비교](docs/privacy-local-vs-cloud-ai.md) · [비공개 코퍼스 정책](docs/corpus-privacy-and-copyright.md)

## Accuracy & Limitations

- 점수는 학습과 수정 방향을 위한 **연습용 예상치**입니다.
- ETS 공식 채점이 아니며 TOEFL 또는 ETS와 제휴·보증 관계가 없습니다.
- 전문가 채점 데이터 기반의 대규모 정확도 캘리브레이션은 아직 완료되지 않았습니다.
- 높은 점수는 실제 시험 성적을 보장하지 않습니다.
- 휴리스틱 분석은 문맥, 독창성, 미묘한 어조를 완전히 이해하지 못할 수 있습니다.
- 고득점 답안 코퍼스에서는 원문을 재배포하거나 암기용 답안을 출력하지 않고 추상적 구조 신호만 사용합니다.
- 클라우드 AI를 활성화하면 검증된 AI 과제 점수가 운영 표시 점수가 됩니다. 로컬 AI는 첨삭 보강용입니다.
- GitHub Pages 경량판과 FastAPI 전체판은 서로 다른 실행 환경이므로 세부 결과가 완전히 같다고 보장하지 않습니다.

## Roadmap

- [x] 결정론적 Offline Core
- [x] Email / Academic Discussion 자동 감지
- [x] GitHub Pages 공개 웹앱
- [x] Docker/FastAPI self-host
- [x] PDF 리포트
- [x] Build a Sentence
- [x] 비공개 고득점 코퍼스 집계·구조 분석 도구
- [ ] 전문가 채점 데이터 기반 캘리브레이션
- [ ] Windows 네이티브 빌드 검증 및 서명 릴리스
- [ ] Apple Developer ID 서명·공증된 macOS 릴리스
- [ ] GitHub Pages PWA 설치 동작의 기기별 검증
- [ ] 공개 다중 사용자 서버 운영에 필요한 rate limit·관측성 검증

## Development

```bash
python -m pytest tests/ -q
python -m tests.eval_harness
python scripts/run_local_ai_validation.py --dry-run
./scripts/docker_sanity_test.sh
```

GitHub Pages 빌드:

```bash
python scripts/build_github_pages.py
python -m http.server 4173 --directory dist_pages
```

주요 문서: [채점 시스템](docs/scoring-system.md) · [제약 사항](docs/scoring-engine-current-limitations.md) · [배포 안내](docs/hosted-web-deployment.md) · [릴리스 체크리스트](docs/release-checklist.md)

## License & Disclaimer

[MIT License](LICENSE)로 배포됩니다.

TOEFL and ETS are trademarks of their respective owners. This independent project is not affiliated with, endorsed by, or sponsored by ETS. 제공되는 점수와 피드백은 교육·연습 목적이며 공식 시험 결과를 대체하지 않습니다.

<p align="center"><sub>Local-first · Web-ready · Practice-focused</sub></p>
