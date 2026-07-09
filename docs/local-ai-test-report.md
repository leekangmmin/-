# Local AI Test Report (Phase 7)

**Date**: 2026-07-08
**Test Suite**: `tests/test_local_ai.py`
**Result**: 23/23 passed

---

## Test Coverage Summary

### RuleLocalAIProvider (5 tests)
| Test | Status |
|------|--------|
| 항상 사용 가능 | ✅ |
| 짧은 에세이 분석 | ✅ |
| 긴 에세이 분석 (강점/문제점 식별) | ✅ |
| 주어-동사 오류 수정 | ✅ |
| 생산 점수에 영향 없음 | ✅ |

### OllamaLocalProvider (5 tests)
| Test | Status |
|------|--------|
| 비loopback URL 거부 | ✅ |
| loopback URL 허용 (mock) | ✅ |
| 서버 미실행 시 unavailable | ✅ |
| 모델 없을 시 unavailable | ✅ |
| 모델 없이 analyze 호출 시 valid=False | ✅ |

### LlamaCppLocalProvider (3 tests)
| Test | Status |
|------|--------|
| 비loopback URL 거부 | ✅ |
| 서버 응답 시 available | ✅ |
| 서버 미실행 시 unavailable | ✅ |

### LocalAIManager (5 tests)
| Test | Status |
|------|--------|
| 모든 제공자 unavailable 시 rule로 fallback | ✅ |
| Ollama available 시 Ollama 선택 | ✅ |
| status_summary 항상 offline_core 포함 | ✅ |
| Ollama unavailable 시 rule로 analyze | ✅ |
| 싱글톤 패턴 | ✅ |

### LocalAIResult / Safety (5 tests)
| Test | Status |
|------|--------|
| 필수 필드 존재 | ✅ |
| Rule provider 외부 호출 없음 | ✅ |
| 실패 시 예외 발생하지 않음 | ✅ |
| Ollama 비loopback 거부 | ✅ |
| 결과에 점수 없음 | ✅ |

---

## 실제 로컬 LLM 테스트 현황

- **Ollama**: 로컬에 설치되어 있지 않음 → mock 테스트만 통과
- **llama.cpp**: 로컬에 설치되어 있지 않음 → mock 테스트만 통과
- **MLX-LM**: 미구현 (향후 Phase 8)
- **RuleLocalAIProvider**: 실제 동작 검증 완료

**결론**: 실제 로컬 LLM 품질은 검증되지 않음. RuleLocalAIProvider만 프로덕션에서 동작.

---

## Eval Harness

```
=== Evaluation Harness (engine 2.0.0, dataset v1.0.0) ===
오탐: 0건 | 순위 역전: 0/5 | 최대 편차: 0.0
경계 입력 안전: OK | 주제 이탈 감지: True
PASS: 모든 품질 게이트 통과
```

---

## 회귀 테스트

- 기존 260개 테스트 중 260개 통과
- Offline Core 점수 불변
- Build a Sentence 불변
- Backup/Restore 불변

---

## Phase 9 실제 런타임 확인 (macOS 개발 환경)

명령:

```bash
.venv/bin/python scripts/run_local_ai_validation.py --dry-run
.venv/bin/python scripts/run_local_ai_validation.py --provider rule --fixture grammar_errors --limit 2
ollama list
.venv/bin/python scripts/run_local_ai_validation.py --provider ollama --fixture grammar_errors --timeout 180 --warmup --limit 1
.venv/bin/python scripts/run_local_ai_validation.py --provider llamacpp --fixture grammar_errors --timeout 180 --warmup --limit 1
```

결과:

- Rule provider: ready, evidence 4/4 verified, score leak 없음.
- Ollama: `qwen2.5:7b` 감지, 모델 크기 4.7GB.
- Ollama warmup: 10.443s, actual analysis latency 19.659s, tokens/sec 17.9.
- Ollama evidence: 3/3 verified, suggestion count OK, score leak 없음.
- llama.cpp: runtime_missing.

해석:

- `qwen2.5:7b`는 사용 가능하지만 느린 편이다. Windows 일반 사용자에게 기본 요구사항으로 삼으면 안 된다.
- 더 가벼운 모델 추천 로직과 timeout fallback이 필요하다.
- Local AI는 보조 피드백 전용이며 production 표시 점수를 바꾸지 않는다.
