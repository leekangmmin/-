# Scoring Engine Improvement Report

## Phase 9 변경

- prompt-fit가 단순 keyword overlap만 보지 않고 요구사항 충족률을 함께 본다.
- 이메일 프롬프트에서 recipient/tone, request/purpose, reason, progress, proposed deadline을 감지한다.
- 학술 토론 프롬프트에서 clear position, reasoning, specific example, discussion engagement를 감지한다.
- template spam phrase, repeated sentence opening, low lexical variety를 감점 신호로 본다.
- missing keywords에는 요구사항 누락을 `required:*` 형태로 우선 노출한다.
- SCORING_ENGINE_VERSION을 `2.1.0`으로 올렸다.

## 검증

- synthetic eval harness v1.1.0에 이메일 요구사항 누락과 template spam 케이스를 추가했다.
- 전문가 데이터 기반 정확도 검증은 아직 없다.

## 정책

- 로컬 AI/클라우드 AI 결과는 표시 점수를 바꾸지 않는다.
- Offline Core가 공식 표시 점수의 단일 경로다.
