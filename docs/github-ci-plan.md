# GitHub CI Plan

현재 `.github/workflows/tests.yml`이 안전한 무료 CI 역할을 한다.

## 현재 실행

- Python 3.11 설치
- requirements + pytest 설치
- py_compile
- repository hygiene check
- pytest
- eval harness
- local AI dry-run

## 의도적으로 하지 않는 것

- release artifact 업로드
- 유료 AI 호출
- secrets 요구
- Windows/macOS release publish

## 이후 추가 가능

- Windows build workflow
- macOS build workflow
- draft release workflow

단, signing/notarization secrets가 필요한 workflow는 public CI에 바로 추가하지 않는다.
