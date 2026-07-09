# Scoring Engine Current Limitations

- 현재 정확도는 전문가 채점 데이터로 검증되지 않았다.
- 합성 fixture는 회귀 방지용이지 실제 TOEFL 점수 정확도 증거가 아니다.
- prompt requirement extraction은 규칙 기반이므로 복잡한 지문에서 누락될 수 있다.
- contradiction detection은 제한적이다.
- 너무 짧지만 문법적으로 매끄러운 답안을 완벽히 판별하지 못할 수 있다.
- 0.5 단위 반올림 경계에서는 작은 변화가 표시 밴드를 바꿀 수 있다.
- AI 분석은 점수에 반영되지 않는다.
