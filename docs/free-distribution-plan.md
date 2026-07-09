# 무료 배포 계획

상태: Phase 9 계획 문서. 공개 배포 선언이 아니다.

## 원칙

- Offline Core는 항상 무료로 동작해야 한다.
- 일반 사용자는 OpenAI, Claude, Gemini, Ollama, llama.cpp API 키나 모델을 준비하지 않아도 된다.
- 로컬 AI와 클라우드 AI는 보조 분석이며, 전문가 검증 전에는 표시 점수를 바꾸지 않는다.
- 답안은 사용자가 명시적으로 켠 외부 AI 기능 외에는 외부로 전송하지 않는다.

## Windows

- 초기 무료 배포 형태: GitHub Releases의 ZIP 또는 설치 프로그램.
- 코드 서명 전 내부/무료 알파에서는 SmartScreen 경고가 예상된다.
- 배포물에는 사용자 DB, 로그, 백업, `.env`, API 키, 모델 파일, release 작업 폴더를 포함하지 않는다.
- 배포마다 checksum, release notes, known limitations를 제공한다.
- 실제 Windows 머신에서 `windows/build_windows.ps1` 빌드와 smoke test가 끝나기 전에는 Windows 완료로 표시하지 않는다.

## macOS

- 초기 무료 배포 형태: GitHub Releases의 ZIP/DMG.
- Developer ID 서명과 Apple notarization 전에는 Gatekeeper 경고가 예상된다.
- 외부 공개 배포는 codesign + notarization 완료 후가 원칙이다.
- ad-hoc/internal build는 신뢰 가능한 내부 테스트용으로만 안내한다.

## Web / No-download

- iPad, Galaxy Tab, iPhone, Android phone, Mac/Windows 브라우저 사용은 hosted web app이 필요하다.
- 휴대폰/태블릿 브라우저에서 무거운 로컬 LLM을 안정적으로 돌리는 것은 목표가 아니다.
- 무료 public AI는 abuse/cost control 없이 열지 않는다.
- 1단계는 FastAPI가 정적 UI를 제공하는 self-host/local web 모드다.
- PWA 완료 조건: manifest, service worker, offline cache policy, installability 검증, mobile viewport 검증.

## AI 비용 방침

- public hosted AI는 서버 키만 사용한다. 사용자에게 서버 키를 노출하지 않는다.
- rate limit, daily quota, per-IP/account limit, max essay length, timeout, cost logging이 없으면 public AI를 켜지 않는다.
- 예산이 없을 때 web 기본값은 Offline Core만 제공한다.
