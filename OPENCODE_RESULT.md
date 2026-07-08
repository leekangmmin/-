# Phase 8-B 핵심 결과

> Ollama 로컬 LLM을 "감지됨"에서 "실제 사용 가능"으로 안정화 완료  
> Offline Core 점수는 변함없이 유지됨

---

# Ollama 실제 로컬 LLM 상태

* **감지된 모델**: qwen2.5:7b (4.7GB)
* **Warmup 결과**: 
  - Cold start: ~10.5s (모델 로딩 8.9s)
  - Warm start: ~0.7s (로딩 0.2s)
* **Inference 결과**: 
  - grammar_errors fixture: valid=True, 77s, 12.3 tok/s, evidence 3/3
  - well_structured fixture: valid=True, 31s, 10.4 tok/s, evidence 1/1
* **Latency**: 30-80초 (CPU only, Apple Silicon)
* **Timeout 원인**: 하드코딩된 30초 timeout → 180초 configurable로 변경
* **Usability**: `ready_slow` — 작동하지만 실사용에는 느림. 더 가벼운 모델 추천

# Rule Provider 상태

* 정상 작동 (항상 available)
* grammar_errors fixture: suggestions 4개, evidence 4/4, valid=True
* 새로운 문법 규칙 추가됨: `I go → I went`, `can able to`, `more better`

# llama.cpp 상태

* 서버 미실행 → runtime_missing 정상 보고
* 분석 함수는 아직 구현되지 않음 (stub 반환)

# Evidence 검증

* evidence_applicable_count / evidence_verified_count / evidence_not_applicable_count 구분
* Rule provider: 4/4 evidence verified (grammar_errors fixture)
* Ollama: 3/3, 1/1 evidence verified (각 fixture)
* Well-structured essay에서 suggestion 0개 = "검증 대상 없음" 처리
* Hallucination 감지: 없음 (모든 original이 essay에 존재)

# 사용자 점수 정책

* Offline Core 점수는 **절대 변경되지 않음**
* Local AI는 enhancement만 제공
* Ollama 응답에 score 필드 포함 시 warning 처리, 점수 미반영
* 테스트: 286개 통과, score leak 없음

# UI 변경

* `fetchLocalAiStatus()`: ready_fast/slow/timeout/too_heavy 상태 처리
* "모델 준비" 버튼 추가 (warmup)
* 성능 지표 표시 (tok/s)
* 모델 추천 목록 표시
* Ollama 연결 시 테스트 skip (추론 시간 길어)

# 패키징 검증

* **.app 빌드 성공** (54MB, ad-hoc signed)
* 14단계 빌드 파이프라인 전부 통과:
  - 286 tests passed
  - Eval harness PASS
  - Info.plist 검증 PASS
  - Security scan PASS (no secrets/DB/model files)
  - Smoke test: Offline Core, history, dashboard, PDF, BAS, local AI status 모두 OK
  - Update migration test PASS
* Graceful shutdown: SIGTERM 후 Ollama 연결 유지로 kill(-9) 필요 → WARN 처리

# 테스트 결과

```
286 passed (regression 없음)
Eval harness: PASS (오탐 0, 순위 역전 0, 반복 채점 최대 편차 0.0)
Local AI test: 49 passed (Phase 8-B 신규 26개 추가)
```

신규 테스트:
- Configurable timeout
- First-run warmup
- keep_alive option
- Timeout failure reason
- Markdown-wrapped JSON parsing
- Model list parsing
- ready_slow / timeout / too_heavy status
- evidence_applicable_count
- Suggestion fixture with real evidence
- No score mutation after local AI
- Score leak in Ollama parsed result
- Ollama response metadata recording

# 보안 감사

- Ollama: loopback only 검증 유지 (127.0.0.1/localhost)
- Cloud API key: 여전히 SQLite plaintext 저장 → **Keychain migration 미완료 (P0)**
- Backup API key stripping: 계속 작동
- .app 내 model file 없음 (security scan PASS)
- .app 내 DB/API key/로그 없음

# 커밋

준비된 변경 파일:
1. `app/local_ai.py` — configurable timeouts, warmup, optimized prompt, performance tracking
2. `app/main.py` — /api/local-ai/warmup 엔드포인트, performance 필드
3. `tests/test_local_ai.py` — 26개 신규 테스트 추가
4. `scripts/run_local_ai_validation.py` — 9 fixture, warmup, benchmark, metrics
5. `scripts/packaged_app_smoke_test.py` — Ollama skip, lock file cleanup
6. `static/app.js` — fetchLocalAiStatus 개선, warmup button
7. `static/index.html` — UI 요소 추가

# 현재 한계

1. **qwen2.5:7b CPU 추론 50-80s** — 실사용에 부담
   - 더 작은 모델 (qwen2.5:3b, phi-3-mini, llama3.2:3b 등) 추천
2. **Ollama keep_alive 후 서버 일시적 무응답** — Ollama 자체 이슈
3. **llama.cpp provider 미구현** — stub만 있음
4. **Cloud API Key Keychain migration 미완료** — P0 보안 과제
5. **패키징 후 graceful shutdown 지연** — Ollama HTTP 연결 유지 때문

# 다음 최우선 작업

1. Cloud API Key Keychain migration (P0 보안)
2. 더 가벼운 Ollama 모델 설치 및 테스트
3. llama.cpp provider 분석 구현
4. Graceful shutdown 개선 (httpx 연결 명시적 close)
5. Phase 9: 전문가 데이터 기반 scoring calibration
