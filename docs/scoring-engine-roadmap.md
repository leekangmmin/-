# Scoring Engine Roadmap

## 다음 개선

1. task profile 분리 강화
2. prompt requirement extractor를 별도 모듈로 분리
3. evidence span 기반 feedback 구조화
4. expert data import 후 MAE/agreement report
5. 점수 공식 변경 gate와 calibration layer 분리

## Email dimensions

- purpose completion
- required content points
- tone/register
- clarity
- organization
- grammar
- vocabulary

## Academic Discussion dimensions

- clear position
- relevance
- reasoning
- support
- engagement with others
- new contribution
- academic tone
- cohesion
- grammar
- vocabulary

## 금지

- 전문가 검증 없이 AI 점수를 production score로 승격하지 않는다.
- 합성 fixture만으로 expert-level accuracy를 주장하지 않는다.
# 고득점 코퍼스 통합 상태 (2026-07-12)

- 완료: 비공개 코퍼스 스키마, TXT/Markdown/CSV/PDF 로컬 수집, 중복 제거, PII 형태 마스킹
- 완료: 유형별 추상 구조 동작 감지와 한국어 `고득점 구조 체크` 피드백
- 완료: 원문 비노출 집계 분석 및 false-low 로컬 평가 도구
- 완료: 점수 공식 2.2.0의 목적별 이메일 평가와 비공개 상위권 집계 보정
- 유지: 결정론적 Offline Core, API 키 불필요, AI의 운영 표시 점수 미반영
- 다음 게이트: 출처·허가가 정리된 전문가 라벨 표본으로 오차를 검증한 뒤에만 점수 가중치 변경 검토
