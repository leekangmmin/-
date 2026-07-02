# LLM 인젝션 저항성 검증 (Phase 4)

## 원칙: heuristic 결과와 실제 LLM 결과를 절대 하나로 합치지 않는다
두 경로는 완전히 다른 메커니즘이다. heuristic 엔진은 규칙 기반이라 애초에
"지시를 따르는" 개념이 없고, LLM은 프롬프트 인젝션에 원리적으로 노출될 수
있는 대상이다. 하나의 "성공률"로 합치면 LLM 쪽 실제 취약점이 heuristic의
안전한 결과에 희석돼 숨겨진다.

## heuristic injection resistance — 측정 완료 (Phase 2, 재확인)
```
.venv/bin/python tests/eval_injection_safety.py
=== Prompt Injection Paired Safety Eval (fixture v1.0.0, 40개 쌍) ===
injected vs neutral-control  delta: max=0.5 min=-0.5 avg=0.05
injected vs original(clean)  delta: max=0.5 min=-0.5 avg=0.1
PASS
```
이 결과는 결정론적 휴리스틱 엔진 경로만 다룬다.

## Claude injection resistance — 미실행
`scripts/run_real_provider_injection_test.py`를 이번 세션에 재작성해 다음을
추가했다:
- fixture 버전(`INJECTION_FIXTURE_VERSION`) 출력
- 비용 게이트(`--i-understand-this-costs-money` + `--max-estimated-cost-usd`)
  없이는 dry-run만 수행
- **neutral filler control 추가**: 기존에는 clean vs injected만 비교했는데,
  마스터 스펙 8장 요구대로 같은 payload 길이의 무의미한 텍스트(`neutral_control_for()`)
  실행도 추가해 "공격 문구 자체의 효과"와 "단순 분량 효과"를 분리할 수 있게 했다.
- 예산 상한 도달 시 중단, 결과에 `fixture_version`/`model` 메타데이터 포함

**실제 실행은 API 키가 없어 하지 않았다.** dry-run으로 게이트가 올바르게
작동함만 확인했다(`tests/test_live_validation_scripts.py::TestInjectionScriptGate`,
4개 테스트).

## 공격 유형 커버리지 (기존 40쌍 fixture, `tests/injection_fixtures.py`)
- 이전 지시 무시, 최고 점수 강제, rubric 교체 요구, 가짜 system/assistant 태그,
  JSON 스키마 교란 유도 문구 — quality(high/medium) × attack_id × 삽입 위치(시작/끝)
  조합으로 40쌍 구성
- 한국어·일본어 혼합, Markdown code block 특화 공격은 **아직 fixture에 없음** —
  다음 확장 후보

## 실제 실행 시 비교할 항목 (스크립트에 이미 구현됨)
overall/reconciled score, dimension scores 변화, requirement extraction 왜곡 여부,
schema/evidence 성공 여부, critic severity, `no_system_info_leak`(system prompt
문구/API 키 패턴 노출 검사), `delta_injected_vs_neutral`(분량 효과 분리).

## 판정 원칙
인젝션 답안과 clean 답안의 차이만으로는 판단하지 않는다 — neutral control 대비
차이(`delta_injected_vs_neutral`)가 핵심 지표다. 이 값이 heuristic의 평균 delta
(0.05)와 비슷하면 "공격 문구 자체의 추가 이득 없음"으로 해석할 수 있지만, 이
해석은 **실제 실행 후에만** 가능하다.

## 실행 명령 (API 키 확보 후)
```
TOEFL_SHADOW_ENABLED=1 TOEFL_SHADOW_PROVIDER=claude ANTHROPIC_API_KEY=sk-ant-... \
  .venv/bin/python scripts/run_real_provider_injection_test.py \
  --limit 5 --max-estimated-cost-usd 1.00 --i-understand-this-costs-money
```
소규모(5쌍)로 먼저 실행해 안정성을 확인한 뒤 전체 40쌍으로 확대할 것을 권장한다
(예상 호출 수는 5쌍 기준 60회 — 쌍당 clean/injected/neutral 3버전 × 4단계).
