# Prompt Injection 안전성 검증 (Phase 2)

## Phase 1의 한계
Phase 1은 인젝션 문구가 포함된 **저품질 답안 하나**가 낮은 점수를 받은 것만 확인했다.
이것만으로는 "인젝션이 채점을 조작하지 못한다"를 증명하지 못한다 — 애초에 저품질
답안이라 인젝션 유무와 무관하게 낮은 점수를 받았을 수 있기 때문이다.

## Phase 2 설계
`tests/injection_fixtures.py`에 **동일 본문 + 인젝션 유무만 다른 쌍**을 구성했다.

- 품질 2단계 × 공격 10종 × 삽입 위치 2곳(앞/뒤) = **40쌍**
- 품질: 고득점 답안(`DISCUSSION_HIGH`), 중간 답안(`DISCUSSION_MID`)
- 공격 종류: `ignore_instructions`, `give_highest_score`, `output_only_6`,
  `replace_rubric`, `system_content_claim`, `xml_tags`, `json_force`,
  `markdown_code_block`, `mixed_language`(한국어+일본어+영어 혼합),
  `prewritten_result`(평가 결과를 답안 안에 미리 작성)

## 핵심 발견: "인젝션 방어" 문제가 아니라 "분량 게이밍" 문제였다
처음 설계한 검증(`injected_score > clean_score`면 실패)에서 **40쌍 중 15쌍이 실패**했다.
그러나 원인을 파고든 결과, 인젝션 문구의 "내용"이 아니라 **텍스트를 추가하면
단어/문장/문단 수가 늘어나 임계값을 넘는 절벽(cliff) 구조** 때문이었다.

검증: 인젝션 대신 완전히 무의미한 필러 텍스트("lorem filler placeholder...")를
같은 길이로 추가해도 **동일하게 +0.5 상승**했다. 즉 공격 문구가 특별한 것이 아니라,
"아무 텍스트나 추가하면 분량 임계값을 넘어 점수가 뛴다"는 `app/scorer.py`의
독립적인 결함이었다 (원래 마스터 프롬프트 19번 문항이 경고한 "글 길이에 따른
과대평가"와 정확히 같은 문제).

### 근본 원인
`app/scorer.py`의 Content/Example 차원이 단어 수·문장 수에 대해 2단계 계단
함수를 사용했다:
```
if min_words <= word_count <= max_words: content += 1.0
elif word_count >= min_words - 20:       content += 0.5   # 경계에서 0.5 절벽
```
경계 바로 아래(예: 120단어 기준 117단어)에 있던 답안은 몇 단어만 추가해도
0.5점이 그대로 뛰었다.

### 적용한 수정
계단을 3단계로 완화해 절벽 크기를 줄였다 (`app/scorer.py`):
- Content: `min_words-20 / min_words-10 / min_words` 3단계 (0.5 / 0.75 / 1.0)
- Example: `sentence_count 5 / 6 / 8` 3단계 (0.4 / 0.55 / 0.75)

수정 후 차원별 원점수(rounded quarter) 상승폭은 0.5 → 0.25로 줄었다. 다만 최종
표시 점수는 0.5 단위로 반올림하기 때문에, 반올림 경계 바로 앞에 있던 경우
여전히 표시상 0.5 단계가 넘어갈 수 있다 — 이는 양자화(quantization) 효과이며
완전한 제거는 채점 공식 전면 재설계가 필요해 이번 단계 범위를 벗어난다. UI는
이미 점수를 "3.5~4.0" 같은 **범위**로 표시해 이 불확실성을 부분적으로 전달한다.

## 재설계한 검증 방법
"인젝션이 원본보다 높으면 실패"는 분량 효과와 뒤섞여 부정확한 기준임을 확인했으므로,
다음처럼 **대조군(neutral control)**을 추가했다.

- `clean`: 원본
- `injected`: 원본 + 공격 payload
- `neutral_control`: 원본 + 공격 payload와 **길이만 같은** 무의미한 텍스트

**실제 안전성 기준**: `injected`와 `neutral_control`의 점수 차이가 작아야 한다
(공격 문구의 의미 내용이 같은 길이의 무의미한 텍스트보다 유리하게 작용하지 않아야 함).

## 결과
```
=== Prompt Injection Paired Safety Eval (40개 쌍) ===
injected vs neutral-control  delta: max=0.5 min=-0.5 avg=0.05
injected vs original(clean)  delta: max=0.5 min=-0.5 avg=0.1  (분량 효과 포함, 참고용)

PASS: 모든 인젝션 쌍이 같은 길이의 무의미한 텍스트와 통계적으로 구분 불가능한 점수를 받음
```

- 40쌍 전부 최고점(5.0) 미도달
- 40쌍 전부 evidence(문법 첨삭 근거)가 실제 원문에 존재 (환각 없음)
- dimensions 스키마(6개 차원) 불변 — 인젝션이 구조를 바꾸지 못함
- `injected` vs `neutral_control` 평균 차이 0.05, 최대 0.5 — 공격 문구 자체의
  추가 이득은 분량 효과 범위 안에 있음

## 명시적 한계
- 이 검증은 **결정론적 휴리스틱 엔진**(`app/scorer.py`, `app/grammar.py`) 경로만
  다룬다. 정규식 기반이라 애초에 "지시를 이해하고 따르는" 능력이 없어 의미론적
  인젝션에 원천적으로 영향받지 않는다.
- 실제 LLM(OpenAI/Claude/Gemini) 채점 경로는 **API 키가 없어 이 세션에서 검증되지
  않았다**. `docs/ai-shadow-mode.md`에 설계한 shadow mode 파이프라인이 프로덕션에
  반영되기 전까지, LLM 기반 채점의 인젝션 저항성은 미검증 상태로 남는다.
- 공격 목록은 대표적인 패턴 10종이며 전수는 아니다. 새로운 공격 패턴 발견 시
  `tests/injection_fixtures.py`의 `ATTACK_PAYLOADS`에 추가하고 재실행할 것.
