# Hosted AI Architecture

상태: 설계 문서. public hosted AI는 아직 구현/배포하지 않는다.

## 원칙

- provider API key는 서버에만 둔다.
- 사용자는 서버 키를 볼 수 없다.
- hosted AI는 기본 비활성이다.
- Offline Core fallback은 항상 제공한다.
- hosted AI는 전문가 검증 전 표시 점수를 바꾸지 않는다.

## 요청 흐름

1. 사용자가 웹 UI에서 분석 요청.
2. 서버가 길이, rate limit, quota를 확인.
3. 큐/동시성 제한을 통과한 요청만 provider로 보냄.
4. 결과는 피드백 보조로만 표시.
5. 실패/timeout/cost limit 초과 시 Offline Core 결과 유지.

## 필요한 API

- `/api/hosted-ai/status`
- `/api/hosted-ai/analyze`
- `/api/account/quota`
- `/api/admin/costs`는 admin guard 뒤에서만.

## 개인정보

- privacy notice에 외부 전송 사실과 provider를 표시한다.
- delete/export 정책이 있어야 한다.
- 로그에는 원문 답안을 남기지 않는다.
