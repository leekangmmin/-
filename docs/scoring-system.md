# 채점 시스템 문서 (v3.0.0)

## 개요
이 앱은 2026 개정 TOEFL Writing 연습용 채점기다. 지원 유형:
- Write an Email (`email`)
- Writing for an Academic Discussion (`academic_discussion`)

점수는 **연습용 추정치**이며 ETS 공식 점수가 아니다. 화면은 한 Email 또는
Academic Discussion의 0–5 과제 점수만 표시한다. Build a Sentence를 포함한
세 과제 결과가 없으므로 단일 답안을 1–6 Writing 섹션 밴드나 30점 척도로
직접 환산하지 않는다.

## 아키텍처
```
static/ (vanilla JS, 토스 스타일 디자인 토큰)
   │  POST /api/evaluate { essay_text, prompt_text, ... }
   ▼
app/main.py      — 입력 검증 → 채점 → prompt-fit 감점 → 파생 분석 → 저장
app/scorer.py    — 6개 평가 차원 결정론적 채점 (SCORING_ENGINE_VERSION)
app/grammar.py   — 문법 신호 분석 단일 모듈 (GRAMMAR_RULES_VERSION)
app/advanced.py  — 첨삭·추천·대시보드 등 파생 분석 (grammar는 app/grammar.py에 위임)
app/ai_mode.py   — 선택적 로컬/AI 첨삭 보강
app/toefl_2026_grader.py — LLM 단일 과제 0–5 strict-JSON 계약·스키마 검증
app/operational_grader.py — OpenAI/Claude/Gemini 운영 채점 브릿지·실패 시 내장 대체
app/db.py        — SQLite 로컬 저장 (data/submissions.db)
```

## 평가 파이프라인 순서 (중요)
1. 입력 검증 (60단어 미만 → 400, 분석 이전에 차단)
2. 유형 감지 또는 명시 유형 사용
3. `score_essay` — 오프라인 대체용 6차원 결정론적 채점
4. 클라우드 AI가 명시적으로 켜져 있으면 2026 루브릭 구조화 채점 요청
5. AI JSON·차원 키·분량·인용 근거·상한 규칙 검증. 성공 시 AI 0–5 점수를 사용하고 실패 시 내장 점수 사용
6. 선택된 하나의 점수를 기준으로 피드백/첨삭/시뮬레이터 등 파생 분석
7. `score_source`, 대체 사유, provider/model/prompt 버전과 함께 저장

## 버전 관리
모든 평가 결과에 다음이 기록된다 (`result.engine`):
- `scoring_engine_version` — 점수 산출 로직 버전
- `rubric_version` — 루브릭 + 문법 규칙 조합 버전
- `grammar_rules_version` — 문법 신호 규칙 버전
- `exam_spec` — 시험 사양 식별자 (`toefl-writing-2026-practice-v1`)

규칙·가중치·캘리브레이션을 바꾸면 반드시 해당 버전을 올려라.
서로 다른 엔진 버전의 점수는 단순 비교하면 안 된다.
(v2.0.0 이전 기록에는 engine 필드가 없으며 `None`으로 처리된다.)

## 문법 신호 분석 (app/grammar.py)
결정론적 정규식 휴리스틱. v2.0.0에서 제거한 대표 오탐:
- "an apple" 등 올바른 a/an (소리 기반 검사로 교체)
- "I was" (we/they was만 오류)
- "if it were" 가정법
- "When ..., I ..." 종속절 (진짜 comma splice만 검출)
- "compared with", 관계대명사 "that have", 약어 "U.S."/"e.g."
- "Does he have ...?" 조동사 의문문

상한 캡: `repeated_error`(총 6+ 또는 단일 유형 4+) → 상한 2.5/5,
`severe_breakdown`(run-on+splice 3+ / fragment 3+ / 총 12+) → 상한 2.0/5.

### 품질 평가: precision/recall (Phase 2)
Phase 1은 "정상 문장 15개 오탐 0건"만 확인했다. 이는 정밀도(precision)의 일부일 뿐
재현율(recall, 실제 오류를 놓치지 않는지)은 검증하지 않은 상태였다.

`tests/grammar_eval_dataset.py`(71개 라벨링 항목, 19개 문법 카테고리) +
`tests/eval_grammar_quality.py`로 측정한 결과:

```
전체: precision=1.0  recall=0.862  f1=0.926  (TP=25 FP=0 TN=42 FN=4)
```

구현된 15개 카테고리(a/an, subject-verb, tense, comma splice, subordinate clause,
relative clause, conditional, article, countability, preposition, fragment, run-on,
punctuation, abbreviation, infinitive/gerund)는 **precision=1.0, recall=1.0**.

**알려진 커버리지 공백 (미구현, recall 0)**: pronoun reference(지시대상 모호),
capitalization(문두 소문자), word form(품사 오용, 예: success/successful),
collocation(관용 결합, 예: make a decision). 이 네 항목은 정규식 휴리스틱으로
안정적으로 탐지하기 어려운 의미·품사 판단이 필요해 현재 엔진 범위 밖이다.
`docs/phase2-audit.md`에 실패 사례 원문을 기록했다.

이 과정에서 발견하고 수정한 실제 버그(단순 커버리지 공백이 아닌 진짜 오류):
- comma splice: 대명사 뒤에 고정된 동사 목록만 인식해 "she submitted", "many
  students struggled" 같은 일반 동사를 모두 놓침 → 임의 동사를 인식하는
  유한동사(finite verb) 판별 로직으로 교체
- fragment: `be/been/being`을 유한동사로 잘못 취급해 "weather being terrible"
  같은 진짜 파편을 통과시킴 → 유한형(is/are/was/were/am)만 인정하도록 수정
- run-on: 임계값이 40단어로 너무 관대해 제품 문구("35단어 이상 분리 권장")와
  불일치 → 35로 통일
- punctuation: 마침표 2개 연속(생략부호 3개 미만)을 놓침 → 패턴 추가
- preposition: "depends of"(3인칭) 형태를 놓침 → 정규식에 `s?` 추가

## 캘리브레이션 상태
- 전역 감점 `strict_penalty` 기본 0.55 (v1의 1.35는 오탐 노이즈 보정값이라 폐기)
- 전문가 만점 답안 2개에서 확인한 추상적 구조만 보수적으로 반영했다: Email의
  완전한 목적·복수 요청·정중성·형식, Discussion의 독립 근거·복수 의견 연결·반론
  응답·구체적 예시. 원문은 저장소에 포함하지 않았다.
- 이 두 샘플만으로 MAE·kappa 같은 절대 정확도를 주장하지 않는다. 더 많은 전문가 골드
  데이터를 validation/locked-test로 확보해야 한다.

## 평가 하네스
```
.venv/bin/python -m pytest tests/          # 45개 유닛/통합 테스트
.venv/bin/python -m tests.eval_harness     # 품질 게이트
```
게이트: 오탐 0건 / 순위 역전 0건 / 반복 채점 편차 0 / 경계 입력 안전 /
인젝션 상위밴드 차단 / 주제 이탈 감지.

테스트 픽스처(tests/fixtures.py)는 전부 자체 제작 합성 데이터(Tier D)로,
회귀 방지용이지 인간 채점 대비 정확도의 증거가 아니다.

## 보안·개인정보
- 모든 답안·평가·API 키는 로컬(SQLite/.env)에만 저장, 외부 전송 없음
  (AI 보강을 명시적으로 켠 경우에만 해당 provider로 답안 전송)
- 프론트엔드는 모든 사용자 텍스트를 이스케이프 후 렌더 (XSS 방지)
- CORS는 localhost 오리진으로 제한
- 학생 답안 속 지시문은 데이터로만 취급 (로컬 엔진은 정규식 기반이라 인젝션 무영향)

## 알려진 한계
- 휴리스틱 엔진은 의미·논리 품질을 깊게 평가하지 못한다 (표면 신호 기반)
- Build a Sentence 유형 미지원 (공식 문항 데이터 확보 후 결정론적 엔진으로 추가 예정)
- 전문가 채점 데이터 부재 → 캘리브레이션·정확도 검증 불가
- 단일 과제로 Writing 섹션 1–6 밴드를 산출하지 않음
