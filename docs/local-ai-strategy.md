# Local AI Strategy (Phase 7)

**Date**: 2026-07-08
**Version**: 0.6.0 → 0.7.0

---

## Recommended Strategy

### Short-Term (Phase 7 — now)

1. Keep Offline Core as default product mode
2. Rename current "local" AI → "기본 분석" (Basic Analysis) — always available, rule-based
3. Add Local AI Adapter layer (`app/local_ai.py`) with provider abstraction
4. Support Ollama and llama.cpp local endpoints through optional adapters
5. No model bundling yet
6. No score changes from local/cloud AI

### Medium-Term (Phase 8 — planned)

1. App-managed GGUF model pack for Apple Silicon
2. Built-in model downloader with checksum verification
3. User consent and license acceptance flow
4. Model removal from settings

### Long-Term (post RC)

1. Expert data calibration of all AI providers
2. Quality comparisons: Rule vs Local LLM vs Cloud AI vs Human
3. Provider quality dashboard (admin only)
4. Possible score offset from verified high-quality local models

---

## Local AI Adapter Architecture

```
┌──────────────────────────────────────┐
│         LocalAIManager               │
│  (detects, selects, exposes status)  │
├──────────────────────────────────────┤
│  LocalAIProvider (ABC)               │
│  ├── RuleLocalAIProvider             │ <- always available
│  ├── OllamaLocalProvider             │ <- detects localhost:11434
│  ├── LlamaCppLocalProvider           │ <- detects localhost:8080
│  └── MLXLocalProvider (future)       │ <- Apple Silicon local
├──────────────────────────────────────┤
│  CloudAIProvider (existing)          │
│  ├── OpenAI / Claude / Gemini        │ <- optional, API key required
│  └── DeepSeek (future)               │
└──────────────────────────────────────┘
```

## Model Pack Planning

### Criteria for bundled model:
- License: Must permit redistribution and commercial use
- Size: < 4GB (quantized)
- Format: GGUF (llama.cpp compatible)
- Quality: Must show > 0.6 correlation with expert scores in pilot
- Speed: < 5s per essay on Apple Silicon M1
- Memory: < 8GB RAM requirement

### Candidate families (pending evaluation):
- Mistral 7B Instruct
- Llama 3 8B Instruct  
- Gemma 2 9B Instruct
- Qwen 2.5 7B Instruct

**None are bundled yet.** All require license/commercial-use verification.
