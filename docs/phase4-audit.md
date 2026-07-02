# Phase 4 감사 요약

## 핵심 결과 (한 문장)
API 키 부재로 실제 Claude 호출은 미실행이지만, live validation runner·비용
게이트·evidence 스키마 강제 검증·pilot comparison 계산 로직을 전부 실제로
구현·테스트하고 176개 테스트로 고정했다.

## 시작 상태 (재확인됨)
- Phase 3 커밋 7개(`d0bfb34`~`0a1411f`) 그대로 존재, 원격 push 없음
- 사용자 미커밋 작업(`app/feedback.py`, `app/vocab_analysis.py`, `실행.command`,
  macOS 앱 run 스크립트, `.vscode/launch.json`) 이번 세션에서도 건드리지 않음
- `git diff --check`: 공백 오류 0건
- baseline: pytest 141 passed, `py_compile` OK, 3개 harness 전부 PASS,
  앱 기동/evaluate/PDF 생성 실측 확인 (Phase 3와 동일한 수치 — 회귀 없음)
- `ANTHROPIC_API_KEY` 없음 확인 (환경변수 스캔) — Phase 4 전체가 이 제약 아래 수행됨

## 실제 Claude provider
- 실제 호출 여부: **미실행**
- 모델: `claude-3-5-sonnet-latest` (환경변수로 재설정 가능, 하드코딩 아님)
- 호출 수/성공/실패/schema success rate/evidence success rate/latency/비용:
  **전부 미측정** — mock으로 로직만 검증됨
- 이번 세션 추가: score_dimensions 응답에 대한 코드 레벨 스키마 강제 검증
  (`_validate_dimension_schema`)으로 `schema_validation_failed`/`score_out_of_range`
  reason code를 명시적으로 분리 (기존에는 필드 누락 시 조용히 기본값으로
  넘어가 실패를 관찰할 수 없었음 — 이번에 고침)

## 실제 LLM 인젝션 검증
- 실행 여부: **미실행**
- fixture: v1.0.0, 40쌍
- 이번 세션 추가: neutral filler control 비교(`delta_injected_vs_neutral`)를
  스크립트에 새로 넣어 분량 효과와 공격 문구 효과를 분리할 수 있게 함
- heuristic 결과와 절대 하나로 합치지 않음 (`docs/llm-injection-validation.md`)

## 전문가 파일럿
- 실제 전문가 데이터: **0건** (`scripts/import_expert_data.py --summary` 실측)
- import pipeline: 준비 완료, 대기 상태
- 이번 세션 추가: `app/pilot_comparison.py` + `scripts/run_pilot_comparison.py` —
  실제 데이터가 들어오면 즉시 휴리스틱/Claude/전문가 3자 비교를 생성하는 구조.
  현재는 0건이므로 정직하게 0으로 보고함을 실측 확인 (가상 데이터 생성 없음)

## 인간·Claude·휴리스틱 비교
- 비교 가능한 답안 수: **0건** (전문가 데이터가 없어 매칭 대상 자체가 없음)
- 계산 로직(MAE, ±0.5 agreement, task_type별 분해, 복수 채점자 합의, 양자화
  경계 분석)은 합성 값으로 15개 단위 테스트 통과 — 로직 검증이지 정확도 증거 아님

## 점수 양자화 분석
- `pre_round_raw_score`/`distance_to_rounding_boundary`/`component_scores`는
  Phase 3부터 모든 평가에 계속 저장 중 (변경 없음)
- 이번 세션에 `boundary_region_analysis()` 계산 함수를 추가해 전문가 데이터가
  들어오면 바로 경계 근처 MAE를 비교할 수 있게 준비 — **공식은 바꾸지 않았다**

## 안전성과 개인정보
- API 키: 서버 환경변수에서만 로드, 클라이언트 번들 미노출, 없어도 앱 정상 기동
- 원문 로그: 모든 로그 호출이 핑거프린트(길이+해시)만 사용, 회귀 테스트 있음
- admin API: `TOEFL_ADMIN_API_ENABLED` 기본 비활성화(404) + 로컬 접근만 허용 +
  `X-Forwarded-For` 미신뢰(소스 레벨 확인) — 변경 없음, 재검증만 수행
- production 점수 미개입: `evaluate()` 소스에 shadow 관련 import 없음 (회귀
  테스트로 고정), shadow DB는 프로덕션 DB와 완전 분리
- 비용 게이트: 가짜 키로도 예산 초과 시 네트워크 호출 전에 abort함을 실측 확인

## 테스트와 명령
```
명령: .venv/bin/python -m pytest tests/ -q
종료 코드: 0
결과: 176 passed, 2 warnings

명령: python3 -m py_compile app/*.py scripts/*.py
종료 코드: 0
결과: COMPILE OK

명령: PYTHONPATH=. .venv/bin/python tests/eval_harness.py
종료 코드: 0
결과: PASS: 모든 품질 게이트 통과

명령: PYTHONPATH=. .venv/bin/python tests/eval_grammar_quality.py
종료 코드: 0
결과: PASS: 구현된 카테고리 전부 정답 (미구현 카테고리 4개는 Phase 1부터 알려진 상태, 변경 없음)

명령: PYTHONPATH=. .venv/bin/python tests/eval_injection_safety.py
종료 코드: 0
결과: PASS: heuristic injection resistance 유지 (avg delta 0.05)

명령: 앱 기동 + POST /api/evaluate + GET /api/report/{id}.pdf (TestClient)
종료 코드: 0 (전부 200)
결과: PDF 헤더 %PDF 확인, 62080 bytes

명령: PYTHONPATH=. .venv/bin/python scripts/run_real_shadow_validation.py --limit 20 --dry-run
종료 코드: 0
결과: 실제 과거 제출 20건 후보 확인, 실제 호출 없음

명령: PYTHONPATH=. .venv/bin/python scripts/run_real_provider_injection_test.py --limit 1
종료 코드: 0
결과: dry-run, fixture v1.0.0 확인, 실제 호출 없음

명령: PYTHONPATH=. .venv/bin/python scripts/run_pilot_comparison.py
종료 코드: 0
결과: 전문가 레코드 0건 정직하게 보고, 가상 데이터 미생성
```

## 주요 변경 파일
```
파일: app/claude_provider.py
목적: score_dimensions 응답의 스키마를 코드에서 강제 검증
핵심 변경: _validate_dimension_schema() 추가 — schema_validation_failed/score_out_of_range reason code 분리
검증: tests/test_claude_provider.py 신규 5개 테스트 + 기존 pipeline 테스트 dimension_id 수정

파일: scripts/run_real_shadow_validation.py (신규)
목적: 실제 Claude shadow validation을 안전하게 확대 실행하는 러너
핵심 변경: 비용 게이트, 사전 출력, budget/consecutive-failure stop, idempotency, Ctrl+C 안전 종료
검증: subprocess 기반 6개 게이트 테스트 (test_live_validation_scripts.py)

파일: scripts/run_real_provider_injection_test.py (재작성)
목적: neutral control 비교 추가, 비용 게이트 강화
핵심 변경: delta_injected_vs_neutral 지표 추가, fixture_version 결과에 포함
검증: subprocess 기반 4개 게이트 테스트

파일: app/pilot_comparison.py (신규)
목적: 전문가/Claude/휴리스틱 3자 비교 계산 로직
핵심 변경: MAE, agreement, 대표 사례 탐지, 복수 채점자 합의, 양자화 경계 분석
검증: tests/test_pilot_comparison.py 15개 테스트 (전부 합성 값)

파일: scripts/run_pilot_comparison.py (신규)
목적: 3개 DB를 조인해 pilot_comparison 모듈을 실제 데이터에 적용
핵심 변경: exact_hash 기반 매칭, 0건일 때 정직한 보고
검증: 실제 DB로 실행해 0건 정직 보고 확인

파일: app/shadow_mode.py
목적: 중복 실행 방지를 위한 idempotency 조회 함수 추가
핵심 변경: already_processed_submission_ids() 추가
검증: run_real_shadow_validation.py에서 실사용, 기존 테스트 영향 없음

파일: docs/production-promotion-gate.md, docs/live-claude-shadow-validation.md,
      docs/live-provider-cost-and-safety.md, docs/llm-injection-validation.md,
      docs/expert-pilot-results.md, docs/human-ai-heuristic-comparison.md (신규)
목적: 구현됨/mock 검증됨/실제 검증됨/미검증을 구분해 문서화
검증: 각 문서가 실제 실행 결과와 일치하는지 대조 확인
```

## 검증된 상태 (요구된 표현 그대로)
- **live provider implementation complete**: 예 (4단계 파이프라인 + 비용 게이트 + 스키마 검증)
- **live provider smoke validated**: 아니오 — API 키 없음
- **live provider quality unverified**: 예 (미검증)
- **shadow pipeline validated**: 예 (mock 기반, 실제 DB 대상 실행 포함)
- **expert pilot imported**: 아니오 — 0건
- **expert accuracy pilot measured**: 아니오 — 측정 불가
- **statistically inconclusive**: 해당 없음(비교할 데이터 자체가 없음)
- **production promotion prohibited**: 예, 유지됨
- **production score path unchanged**: 예, 회귀 테스트로 고정됨

## 현재 한계 (솔직히)
- API 키 없음 — 이번 Phase 4의 가장 큰 제약. 모든 "실제" 검증이 dry-run/mock에 머묾
- 실제 호출 수 0건, 전문가 데이터 0건 — 정확도/비용/latency에 대해 할 수 있는
  말이 전혀 없음
- 복수 채점자 데이터 없음 — 인간 합의 범위 기준선을 아직 세울 수 없음
- 점수 공식 문제(0.5 양자화)에 대한 실측 데이터 없음 — 계속 관찰만 함
- Build a Sentence UI는 이번 단계에서 손대지 않음 (Phase 4는 Claude/전문가
  검증이 핵심이므로 의도적으로 후순위)
- evidence 품질(오프셋 정확성 이상의 "타당성")은 자동 검증이 불가능한 영역 —
  실제 호출 후 수동 표본 검토가 반드시 필요
- 실제 LLM 인젝션 실패 사례: 존재 여부조차 아직 모름(미실행)

## 다음 최우선 작업
1. `ANTHROPIC_API_KEY` 확보 → `scripts/run_real_shadow_validation.py --limit 1`로
   Stage A smoke부터 시작 (email 1건 + discussion 1건) — 이번 Phase 4에서 가장
   가치가 큰 미실행 작업
2. 실제 전문가 5~10명분 파일럿 데이터 수집 시작 (`docs/expert-pilot-procedure.md`) —
   Claude 검증과 병행 가능하며, 준비된 import/비교 파이프라인을 처음으로 실사용
3. Stage A/B가 안정적이면 `scripts/run_real_provider_injection_test.py --limit 5`로
   실제 LLM 인젝션 저항성 최초 측정
