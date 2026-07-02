# Build a Sentence 엔진 (Phase 2, 구조 준비 단계)

## 현재 상태
**공식 ETS Build a Sentence 문항은 제품에 포함하지 않았다.** 저작권 자료를
무단으로 포함하지 않기 위해서다. 이 단계에서 구현한 것은 **엔진과 데이터
구조**이며, 문항은 엔진 검증을 위한 자체 제작 합성 문항(`tests/build_a_sentence_fixtures.py`)뿐이다.

## 스키마 (`app/build_a_sentence_models.py`)
`BuildASentenceItem`: `item_id`, `source_fragments`(어순이 섞인 구성요소),
`primary_answer`, `allowed_answers`(변형 정답 + 근거), `case_sensitive`,
`punctuation_policy`(strict/ignore_terminal/ignore_all),
`contraction_policy`(require_expanded/require_contracted/either_allowed),
`rubric_version`, `provenance`(DataSourceRecord 재사용).

## 채점 순서 (`app/build_a_sentence_engine.py`)
1. **정규화** — case/구두점/축약형 정책 적용
2. **정확 일치** — `primary_answer`와 정규화 후 비교
3. **허용 답안 일치** — `allowed_answers` 목록과 비교 (근거 필드 포함)
4. **구조 규칙 검사** — 필수 구성요소가 모두 포함됐는지 확인하는 **보조 신호**.
   이것만으로는 정답 처리하지 않는다 (`match_type="structural_partial"`,
   `is_correct=False`) — 어순/정확한 표현이 정답 목록에 없으면 그럴듯해
   보여도 관대하게 정답 처리하지 않는다.
5. **의미 동등성 보조 검사** — 현재 미구현 (임베딩/의역 판단 필요, 결정론적
   엔진 범위 밖). 나중에 shadow mode의 `ScoringProvider`를 훅으로 연결할 수
   있도록 구조만 남겨뒀다.
6. **AI 검토** — 현재 비활성. 필요해지면 `ScoringProvider`를 여기에 연결한다.

## 실제 버그 발견 및 수정
개발 중 `case_sensitive=True` 문항에서 대소문자가 무시되는 버그를 테스트로
잡아냈다: 축약형 치환 함수가 내부적으로 항상 `.lower()`를 호출해 상위
`case_sensitive` 설정을 무시하고 있었다. 정규화 순서를 "축약형 치환 → 구두점
정책 → 마지막에 한 번만 소문자 변환"으로 재배치해 수정했고, 회귀 테스트로
고정했다 (`TestCaseSensitivePolicy`).

## 검증 결과
자체 제작 문항 3종, 15개 테스트 전부 통과 (정확 일치, 허용 변형, 축약형
정책, 구조 부분 일치의 오분류 방지, 완전 오답, 대소문자 구분 정책, 정규화
결정론성, provenance 필수 확인). **이 정확도는 "우리가 만든 합성 문항에서
엔진이 의도대로 동작한다"는 것이지, 실제 시험 정확도의 증거가 아니다.**

## 다음 단계
- 공식 문항 확보 시(라이선스 확인 후) provenance를 `source_type: official-practice`
  등으로 정확히 기록하고 이 fixtures 디렉터리와 분리된 위치에 저장
- UI 화면 연결 (현재 미구현 — 엔진/데이터 구조만 준비된 상태)
- 의미 동등성 검사에 shadow mode provider 연결 검토
