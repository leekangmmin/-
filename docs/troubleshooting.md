# 문제 해결

## Python 명령이 없을 때

macOS에서는 `python` 대신 `python3`만 있을 수 있다. 개발 실행은 다음처럼 한다.

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt pytest
pytest -q
```

## 앱이 이미 실행 중이라고 나올 때

앱은 중복 실행을 막기 위해 lock 파일을 쓴다. 정상 실행 중인 창이 있는지 먼저 확인한다. 비정상 종료 후에도 stale lock은 다음 실행 때 자동 정리되도록 설계되어 있다.

## macOS Gatekeeper 경고

Developer ID 서명·notarization 전 내부 빌드는 경고가 예상된다. 공개 배포 전에는 반드시 서명과 공증을 완료해야 한다.

## Windows SmartScreen 경고

코드 서명 전 무료 알파 빌드는 SmartScreen 경고가 예상된다. release notes에 unsigned build임을 명시한다.

## 로컬 AI가 느릴 때

Offline Core 점수는 정상 유지된다. 로컬 AI가 느리거나 timeout이면 더 가벼운 모델을 권장하고, AI 분석은 점수에 반영하지 않는다.

## 클라우드 AI가 작동하지 않을 때

기본 채점은 정상 작동한다. 클라우드 AI는 선택 기능이며, API 키가 없으면 비활성 상태가 정상이다.
