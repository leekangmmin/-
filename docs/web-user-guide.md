# Web 사용자 가이드

상태: self-host/local browser 사용 안내. 공개 hosted PWA 완료 안내가 아니다.

## 로컬 브라우저 실행

```bash
source .venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

브라우저에서 `http://127.0.0.1:8000`을 연다.

## 가능한 기능

- Offline Core 채점
- history/dashboard
- PDF
- Build a Sentence
- draft autosave

## 주의

- iPad/iPhone/Android에서 no-download로 쓰려면 hosted web 배포가 필요하다.
- 아직 PWA 설치 지원은 완료되지 않았다.
- hosted AI는 cost/abuse control 전까지 public으로 켜지 않는다.
