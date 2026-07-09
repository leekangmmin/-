# Web Deployment Plan

## 1단계: 개인/로컬 웹

- FastAPI를 `127.0.0.1` 또는 private host에서 실행한다.
- 정적 UI는 FastAPI가 제공한다.
- AI 없이 Offline Core를 제공한다.

## 2단계: Self-hosted

- Docker 또는 VM에 FastAPI 배포.
- HTTPS reverse proxy.
- 데이터 저장 위치와 백업 정책 문서화.
- public AI endpoint 없음.

## 3단계: Public hosted

필수 조건:

- HTTPS
- rate limit
- max essay length
- abuse monitoring
- privacy notice
- export/delete policy
- cost logging
- admin cost dashboard
- hosted AI disabled until controls exist

## 정적 호스팅만으로는 부족한 점

현재 앱은 FastAPI API, SQLite 저장, PDF 생성이 필요하다. GitHub Pages/Cloudflare Pages만으로 전체 기능을 제공하려면 별도 backend가 필요하다.
