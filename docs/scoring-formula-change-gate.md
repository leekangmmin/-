# 점수 공식 변경 게이트

## v3 변경 기록

사용자 반례에서 문법적으로 통제된 36단어 문장 두 개가 run-on으로 오인되고,
빈 줄이 없는 줄바꿈이 1단락으로 계산되어 4점대 답안이 2.5를 받았다. 이는 단순한
반올림 문제가 아니라 공식 루브릭에 없는 형식 편향이었다.

v3에서 다음을 제거했다.

- 35단어 초과 문장 자동 문법 오류
- 한 단락 감점
- 3단락·연결어 개수 보너스/감점
- 전역 `strict_penalty`
- 고득점 구조 체크리스트 기반 사후 보정
- 프롬프트 키워드 겹침에 따른 표시 점수 감점
- 학생 이름 언급 및 요구사항 누락에 대한 AI 기계적 상한

대신 ETS 공개 루브릭·연구가 다루는 전개, 응집성, 구문 복잡성, 문법 정확성,
어휘 다양성을 진단 축으로 사용한다.

## 앞으로의 변경 규칙

공식 변경은 다음 중 하나가 있어야 한다.

1. 공식 ETS 루브릭·시험 사양이 바뀜
2. 재현 가능한 false-positive/false-negative 반례
3. 전문가 골드 데이터에서 현재 공식의 편향이 측정됨

변경 시 반드시:

- `SCORING_ENGINE_VERSION` 또는 `GRAMMAR_RULES_VERSION`을 올린다.
- 반례 회귀 테스트를 먼저 추가한다.
- 기존 validation과 잠금 test set을 분리해 비교한다.
- MAE뿐 아니라 exact/adjacent agreement, weighted kappa, 과대·과소평가 방향,
  과제 유형별·점수대별 오차를 기록한다.
- 단락 수, 단어 수, 연결어 수 같은 쉽게 조작 가능한 표면 신호 하나로 점수를
  직접 움직이지 않는다.

## 관찰 메타데이터

각 평가에는 `pre_round_raw_score`, `rounded_display_score`,
`distance_to_rounding_boundary`, `component_scores`,
`scoring_formula_version`을 저장한다. 이는 공식 변경 전후의 실제 영향을
비교하기 위한 내부 진단값이다.
