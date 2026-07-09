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
