# Mobile / Tablet UI Audit

상태: CSS 보강 및 in-app browser viewport smoke 완료. 실제 기기 검증은 아직 미완료.

## 대상 폭

- 360px: 소형 Android phone
- 390px: iPhone 계열
- 430px: 큰 phone
- 768px: iPad portrait
- 834px: iPad/tablet portrait
- 1024px: tablet landscape / small desktop
- 1280px, 1440px: desktop browser

## 이번 보강

- 버튼 묶음이 좁은 폭에서 100% 폭으로 줄바꿈된다.
- score secondary 영역은 430px 이하에서 1열로 바뀐다.
- rubric row는 430px 이하에서 1열로 바뀐다.
- history/backup row는 tablet 이하에서 줄바꿈된다.
- dialog와 card padding을 작은 화면에 맞게 줄였다.

## 브라우저 viewport smoke

in-app browser에서 360, 390, 430, 768, 834, 1024, 1280, 1440px 폭을 확인했다.

- 모든 대상 폭에서 `overflowX = 0`.
- `essayText`, `evaluateBtn`, `basSection`, cloud AI config, data management 섹션이 DOM에 존재하고 viewport 안에 배치됨.
- 390px 폭에서 답안 입력, 채점, 결과 표시, history 업데이트, PDF 버튼 활성화 확인.
- Build a Sentence 섹션 표시 확인.

## 미검증

- 실제 iPad Safari
- 실제 Galaxy Tab Chrome/Samsung Internet
- 실제 iPhone Safari
- 실제 Android phone Chrome
- PWA 설치성

## 결론

브라우저 반응형 기반은 개선됐지만, real-device support complete로 표기하면 안 된다.
