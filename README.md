<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/logo.png" alt="토플 라이팅 채점기 아이콘" width="112"/>
</p>

<h1 align="center">토플 라이팅 채점기</h1>

<p align="center">
  <b>API·인터넷 없이도 바로 쓰는 TOEFL Writing 연습·첨삭 앱</b><br/>
  <sub>문법·어휘·구조 기반 Offline Core · 성장 대시보드 · PDF 리포트 · 문장 조립 연습</sub>
</p>

<p align="center">
  <img src="https://img.shields.io/badge/platform-macOS%20%7C%20Windows%20planned-000000?style=flat-square"/>
  <img src="https://img.shields.io/badge/tests-288%20passing-17a05d?style=flat-square"/>
  <img src="https://img.shields.io/badge/version-0.6.0%20(internal%20RC)-3182f6?style=flat-square"/>
  <img src="https://img.shields.io/badge/offline-core-8b5cf6?style=flat-square"/>
  <img src="https://img.shields.io/badge/license-MIT-lightgrey?style=flat-square"/>
</p>

<p align="center">
  <a href="#-실행하기">실행하기</a> ·
  <a href="#-주요-기능">주요 기능</a> ·
  <a href="#-개발자로-실행하기">개발자 실행</a> ·
  <a href="#-아키텍처">아키텍처</a> ·
  <a href="#-데이터-안전과-개인정보">개인정보</a>
</p>

<br/>

<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_main.png" alt="작성 화면과 성장 대시보드" width="820"/>
</p>

---

## ✨ 한눈에 보기

> **점수보다 "다음에 무엇을 고칠지"가 먼저 보이는 라이팅 연습 앱입니다.**
> 답안을 붙여넣으면 이메일 / 학술 토론 유형을 자동으로 구분해, 문법·어휘·구조·주제
> 적합성을 분석하고 **가장 먼저 고칠 것 한 가지**부터 알려줍니다. 모든 채점은
> 인터넷·API 키 없이 이 기기 안에서 이루어집니다.

| | |
|---|---|
| 🔌 **오프라인 우선** | API 키·인터넷 없이 채점·기록·PDF·문장 조립 연습이 모두 작동 |
| 🎯 **연습용 밴드 추정** | 2026 개정 기준 1–6 밴드 + 30점 환산(참고용). 공식 점수가 아님을 항상 표시 |
| 🧩 **영역별 진단** | 구조·내용·일관성·예시·문법·어휘 6개 영역 점수와 문장별 첨삭 |
| 📈 **성장 대시보드** | 점수 추이·반복 약점·유형별 성과를 데이터가 쌓일수록 자동 표시 |
| 🧱 **문장 조립 연습** | 자체 제작 15문항(난이도 3단계)으로 어순·문법 감각 훈련 |
| 📄 **PDF 리포트** | 제출별 상세 리포트를 로컬에서 생성 |
| 💾 **백업 · 복원** | 기록을 언제든 백업하고 되돌릴 수 있고, 업데이트 후에도 데이터 보존 |
| 🔒 **로컬 저장** | 답안·점수는 이 기기에만 저장. 동의 없이 외부로 전송하지 않음 |

<br/>

<p align="center">
  <img src="https://raw.githubusercontent.com/leekangmmin/-/main/static/screenshot_report.png" alt="채점 결과와 영역별 점수" width="720"/>
</p>

---

## 📦 실행하기

이 앱은 현재 **v0.6.0 내부 릴리스 후보** 단계입니다. 기본 기능은 API 키 없이 작동하지만,
공개 무료 배포용 서명·공증·Windows 실기 빌드는 아직 완료되지 않았습니다.

### macOS

1. 내부 테스트 빌드는 GitHub Releases의 DMG/ZIP으로 배포할 수 있습니다.
2. Apple Developer ID 서명·공증 전에는 Gatekeeper 경고가 예상됩니다.
3. 외부 공개 배포 전에는 `docs/release-checklist.md`와 `docs/macos-user-guide.md`를 확인하세요.

### Windows

Windows 빌드 스크립트는 준비되어 있지만, 이 저장소에서는 아직 실제 Windows 머신에서
최종 smoke test가 완료되지 않았습니다.

```powershell
.\windows\build_windows.ps1
```

완성된 내부 알파 산출물은 `dist_windows\TOEFLScorer.exe`로 생성됩니다. 서명 전에는
SmartScreen 경고가 예상됩니다. 자세한 절차는 `docs/windows-user-guide.md`와
`docs/windows-release-report.md`를 보세요.

### 브라우저 / 자체 호스팅

개발 또는 개인 서버에서는 FastAPI가 정적 UI를 함께 제공합니다.

```bash
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000`을 열면 됩니다. 공개 no-download 서비스는 별도
호스팅·보안·요금 통제가 필요하며 아직 완료된 PWA가 아닙니다.

---

## 🎯 주요 기능

### 오프라인 채점
답안을 붙여넣고 **채점하기**만 누르면 됩니다. 이메일·학술 토론 유형 자동 구분,
1–6 밴드 추정, 구조·내용·일관성·예시·문법·어휘 6개 영역 점수, 문장별 첨삭,
목표 점수까지의 리라이팅 예시를 제공합니다. 처리 단계를 정직하게 보여주고
가짜 진행률을 쓰지 않습니다.

### 문장 조립 연습 (Build a Sentence)
난이도 3단계 자체 제작 15문항. 조각을 클릭·드래그·키보드로 배열하거나 직접
입력해 정답 문장을 완성하고, 왜 그 어순이 정답인지 문법 설명을 확인합니다.

### 성장 기록 & 백업
제출할수록 점수 추이·반복 약점·유형별 성과가 쌓입니다. 언제든 백업 파일을
만들고 되돌릴 수 있으며, 앱을 업데이트해도 기록이 유지됩니다.

---

## 🚀 개발자로 실행하기

```bash
git clone https://github.com/leekangmmin/-.git toefl-writing-scorer
cd toefl-writing-scorer

python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest

# ① 브라우저에서 개발 서버로 실행
uvicorn app.main:app --reload
#   → http://127.0.0.1:8000

# ② 데스크톱 앱(네이티브 창)으로 실행
python -m desktop.launcher
```

### 테스트 & 품질 게이트

```bash
pytest -q                        # 288개 테스트
python -m tests.eval_harness     # 채점 품질 회귀 게이트(오탐·순위·재현성)
python scripts/run_local_ai_validation.py --dry-run
```

### macOS 앱 빌드 (릴리스 파이프라인)

```bash
./scripts/build_macos.sh
#  clean venv → 테스트 → 아이콘 → PyInstaller → Info.plist 검증
#  → 보안 스캔 → 패키징 스모크 → 업데이트 보존 테스트 → manifest·checksum·zip
./scripts/make_dmg.sh            # 내부 테스트용 DMG
```

---

## 🧱 아키텍처

```
desktop/            네이티브 실행·생명주기 (비즈니스 로직 없음)
 ├─ launcher.py       중복 실행 방지 → 동적 포트 서버 → pywebview 창 → graceful shutdown
 ├─ server_manager.py in-process uvicorn 스레드 (고아 프로세스 구조적 차단)
 └─ single_instance.py

app/                모든 기능 (오프라인 코어)
 ├─ scorer / feedback / vocab_analysis   문법·어휘·구조 휴리스틱 채점
 ├─ build_a_sentence_*                    문장 조립 (결정론 엔진 + 15문항)
 ├─ backup.py                             백업·복원 (롤백·키 제거·경로 차단)
 ├─ db.py / paths.py / version.py         SQLite · OS 표준 경로 · 버전 단일 출처
 └─ main.py                               FastAPI 엔드포인트

static/             토스 스타일 웹 UI (외부 CDN 의존성 0)
```

**스택:** FastAPI · pywebview · SQLite · PyInstaller (one-dir) · platformdirs
데이터는 `~/Library/Application Support/TOEFL Writing/` 에 저장되어 앱을 지워도 남고,
업데이트 시에도 보존됩니다.

### 세 가지 분석 모드

| 모드 | 상태 | 설명 |
|---|---|---|
| **오프라인 코어** | ✅ 기본 | 문법·어휘·구조 기반 채점. API·인터넷 불필요 |
| **로컬 AI** | 🔧 선택 | Ollama/llama.cpp 감지 구조. 없으면 규칙 기반 분석으로 fallback · 점수 미반영 |
| **클라우드 AI** | 🔧 선택 | 기본 비활성 · 사용자가 직접 켠 경우에만 전송 · 점수 미반영 |

문서: [`docs/`](docs/) — 아키텍처, 오프라인 코어, 백업·복원, 빌드, 보안 감사,
Phase별 검증 보고서 등.

---

## 🔒 데이터 안전과 개인정보

- **로컬 전용 저장** — 답안·점수·연습 기록은 이 기기에만 저장됩니다.
- **외부 전송 없음** — 클라우드 AI를 직접 켜기 전까지 어떤 데이터도 외부로 나가지 않습니다.
- **작성 중 복구** — 앱이 강제 종료돼도 작성하던 답안을 되살립니다.
- **백업 · 복원** — 설정에서 백업을 만들고 되돌릴 수 있으며, 백업 파일에는 **API 키가 담기지 않습니다.**
- **안전한 삭제** — 전체 삭제 전 자동 백업을 만들어 실수로 지워도 복구할 수 있습니다.
- **로컬 서버** — `127.0.0.1` 에만 바인딩하고 외부 네트워크에 노출하지 않습니다.

---

## ⚠️ 아직 완료되지 않은 것

투명하게 밝힙니다.

- Apple Developer 서명·공증 (현재 ad-hoc, **외부 배포 불가**)
- Windows 실기 빌드/스모크 테스트 (Windows 머신에서 미검증)
- 실제 대규모 클라우드 AI 채점 품질 검증
- 전문가 채점 데이터 기반 정확도 캘리브레이션
- 공개 hosted web/PWA 배포

밴드 점수는 **공개 기준을 참고한 연습용 추정치**이며 **ETS 공식 점수가 아닙니다.**
문장 조립 문항은 전부 자체 제작이며 ETS 공식 문항이 아닙니다.

---

## 📜 라이선스

MIT License — 자유롭게 사용·수정·재배포할 수 있습니다.
단, "TOEFL"과 "ETS"는 Educational Testing Service의 상표이며, 이 프로젝트는 ETS와
제휴·보증 관계가 없는 **비공식 학습 도구**입니다.

<p align="center"><sub>Made with care · 오프라인에서도 안심하고 쓰는 라이팅 연습</sub></p>
