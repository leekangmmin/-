# Phase 8-B 감사 (Ollama Local LLM 실사용 안정화)

## 진단 결과

### 루트 원인: Hardcoded 30초 timeout

Ollama `qwen2.5:7b` 감지됨 ("ready" 상태). 그러나 `analyze_response`의 `httpx.post(timeout=30.0)` 하드코딩된 timeout으로 인해 실제 추론(50-80초)이 timeout.

### 진단 데이터

```
첫 호출 (cold start):   10.5s (load_duration=8.9s, eval_duration=0.3s)
두 번째 호출 (warm):     0.7s (load_duration=0.2s, eval_duration=0.3s)
에세이 분석 (grammar_errors): 77s (eval_duration=37s, 361 tokens, 9.8 tok/s)
에세이 분석 (well_structured): 31s (eval_duration=~20s, 10.4 tok/s)
```

- qwen2.5:7b, CPU only (Apple Silicon), ~10-12 tokens/sec
- 모델 로딩: 8-13초 (첫 호출)
- JSON 응답에 ```json 마크다운 마커 포함하는 경향 있음

## 변경 사항

### 1. Configurable Timeout (`app/local_ai.py`)
- `LocalAIProviderConfig` dataclass 도입
  - connect_timeout_seconds: 5.0
  - read_timeout_seconds: 120.0
  - total_timeout_seconds: 180.0
  - first_run_timeout_seconds: 240.0 (최초 모델 로딩)
  - max_output_tokens: 512
  - temperature: 0.2
  - keep_alive: "10m"
  - num_ctx: 2048
- `TOEFL_LOCAL_AI_*` 환경변수 override 지원
- Invalid env 값 fallback 처리

### 2. Warm-up (`app/local_ai.py`)
- `OllamaLocalProvider.warmup()` — 모델 미리 로드
- `WARMUP_PROMPT = 'Return ONLY this JSON, no other text: {"ready":true}'`
- 실제 essay를 warm-up에 사용하지 않음
- keep_alive 설정으로 모델 유지

### 3. Optimized Ollama Prompt
- 7B 모델에 최적화된 concise system prompt
- `_build_ollama_prompt()` — essay preview 1200 chars 제한
- `num_predict=512`, `temperature=0.2`, `num_ctx=2048` 전달
- JSON schema에 evidence 필드 추가

### 4. Markdown JSON Parsing
- ```json ``` 마커 제거 처리
- 중첩 JSON 추출 fallback
- Score key leak 감지

### 5. Performance Status
- `_performance_status()`: ready_fast, ready_slow, timeout, too_heavy
- 모델 추천 로직: `model_recommendations()`
- Ollama 응답 메타데이터 기록 (total_duration, load_duration, eval_duration, eval_count, tok/s)

### 6. Validation Harness 개선 (`scripts/run_local_ai_validation.py`)
- 9가지 fixture 추가: tiny, well_structured, grammar_errors, weak_content, off_topic, email_tone_problem, academic_discussion, prompt_injection, long_response
- `--warmup`, `--model`, `--benchmark`, `--report` 옵션
- `--use-historical-data --i-understand-this-uses-my-local-essays` flag
- evidence_applicable_count / verified_count / not_applicable_count 구분

### 7. UI 업데이트
- `fetchLocalAiStatus()`: ready_fast/slow/timeout/too_heavy 상태 처리
- `warmupLocalAi()` 버튼, 성능 지표 표시
- 모델 추천 목록 표시

### 8. API 엔드포인트
- `POST /api/local-ai/warmup` 추가
- `/api/local-ai/test` 응답에 performance 필드 추가
- `/api/local-ai/analyze` 응답에 performance 필드 추가

### 9. Smoke Test 수정
- Ollama/llama.cpp 감지 시 test endpoint skip
- Graceful shutdown timeout 증가 및 kill 시 lock 파일 강제 정리

## Ollama 실제 추론 결과

| Fixture | Warmup | Latency | Tok/s | Valid | Evidence |
|---------|--------|---------|-------|-------|----------|
| grammar_errors | 2.6s | 77s | 12.3 | True | 3/3 |
| well_structured | 15.0s | 31s | 10.4 | True | 1/1 |

- **사용 가능 상태**: `ready_slow` (77초는 실사용에 부담)
- **품질**: valid=True, evidence 100% verified, no score leak
- **제한**: CPU-only Mac에서 10-12 tok/s, 더 가벼운 모델 추천

## 보안 감사

- Ollama는 loopback only (127.0.0.1/localhost 검증)
- Cloud API key는 SQLite plaintext — Keychain migration pending
- Backup API key stripping 계속 작동
- No model files in .app bundle (security scan PASS)
- No essay text in logs or reports

## 테스트 결과

- **286 tests passed** (regression 없음)
- Eval harness: PASS
- Dry-run validation: rule ready, ollama ready, llamacpp unavailable
- Rule provider + grammar_errors: success, evidence 4/4
- Ollama grammar_errors: success, evidence 3/3
- Ollama well_structured: success, evidence 1/1

## 현재 한계

1. qwen2.5:7b CPU 추론 50-80s — 실용성 낮음
2. 더 작은 모델 (3B 이하) 없음
3. keep_alive 후 Ollama 서버 일시적 무응답 관찰
4. 패키징 후 graceful shutdown 시 Ollama 연결 유지로 인한 지연

## 다음 최우선 작업

1. 더 작은 Ollama 모델 설치/추천 (qwen2.5:3b, phi-3-mini 등)
2. Cloud API Key Keychain migration
3. Graceful shutdown 시 Ollama 연결 정리
4. llama.cpp provider 실제 구현
