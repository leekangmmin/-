# Local AI Architecture Audit (Phase 7)

**Date**: 2026-07-08
**Version**: 0.6.0 pre-Phase-7

---

## 1. What does current "local" AI mode actually do?

`app/ai_mode.py:487-489` — When `provider == "local"`:

1. `_build_local_paraphrases()` → rule-based sentence-level regex fixes (50+ rules)
2. `_build_local_drills()` → rule-based grammar drill generation
3. `_build_local_sample_paragraph()` → rule-based paragraph assembly

It is **not a real LLM**. It's a deterministic rule engine with:
- Subject-verb agreement fixes
- Article corrections (a/an)
- Preposition corrections (discuss about → discuss)
- Tense fixes
- Style fixes (more better → better)
- Word choice (kids → children)

## 2. Is it a real LLM or rule-based helper?

**Rule-based helper.** No model file. No semantic reasoning. No context-aware generation.

## 3. Which features are already fully offline?

| Feature | Offline | API Needed |
|---------|---------|------------|
| Heuristic Scoring | Yes | No |
| Grammar Analysis | Yes | No |
| Vocabulary Analysis (AWL) | Yes | No |
| Prompt Fit Analysis | Yes | No |
| Claim/Evidence Tagging | Yes | No |
| Detailed Grammar Corrections | Yes | No |
| Dashboard | Yes | No |
| History | Yes | No |
| PDF Generation | Yes | No |
| Backup/Restore | Yes | No |
| Build a Sentence | Yes | No |
| Smart Recommendations | Yes | No |
| Score Simulator | Yes | No |
| Auto-rewrite | Yes | No |
| Sentence Edits | Yes | No |
| Local Paraphrases (rule-based) | Yes | No |
| Local Drills (rule-based) | Yes | No |
| Sample Paragraph (template) | Yes | No |

## 4. Which features require cloud APIs?

| Feature | Requires |
|---------|----------|
| AI-enhanced paraphrases | OpenAI/Claude/Gemini API |
| AI-generated grammar drills | OpenAI/Claude/Gemini API |
| AI-generated sample paragraph | OpenAI/Claude/Gemini API |
| Claude shadow scoring | ANTHROPIC_API_KEY |
| Expert data | Manual import only |
| Pilot comparison | Expert data + API key |

## 5. Is any normal user forced to enter an API key?

**No.** The app works fully with `ai_enabled = false` (default).
The "local" AI mode in the current code is always available without API keys.
The AI settings UI says provider="local" by default.

## 6. Are cloud AI settings visible too prominently?

**Partially.** The current UI (`static/index.html`) has an AI settings card that:
- Shows provider: local / openai / claude / gemini as a dropdown
- Shows enabled/disabled toggle
- Shows API key inputs for each provider
- "테스트 연결" (test connection) button

This is fine for power users but could be simplified for normal users.

## 7. Is the UI implying AI quality that has not been verified?

**Partially.** The term "로컬 AI" appears alongside "OpenAI", "Claude", "Gemini"
which may suggest local AI is equivalent to cloud AI. The actual rule-based
engine works but is not a real LLM.

## 8. Are essays ever sent outside the device by default?

**No.** Default is `ai_enabled = false`. Even when enabled, default provider is "local"
which runs entirely in-process with no HTTP calls.

## 9. Are API keys stored securely?

**Partially.** API keys are stored in `app_settings` SQLite table. They are:
- NOT in the app bundle
- NOT in environment variables (except local .env for development)
- Stripped from backups automatically
- VACUUM'd from backup DBs

But they ARE stored in plaintext in the SQLite DB file. This is acceptable for
a local desktop app but should be documented.

## 10. Is there a clean extension point for local LLM providers?

**No.** `app/ai_mode.py` has a single monolithic flow:
- `ai_enhance()` checks `provider` string and branches to openai/claude/gemini/local
- No abstract base class for providers
- No pluggable local AI architecture
- No separate local AI status API

`app/scoring_provider.py` has a clean `ScoringProvider` ABC, but it's for **shadow scoring only**,
not for user-facing AI features.

## 11. Can local AI fail without breaking Offline Core?

**Yes.** The current code in `ai_enhance()` returns `None` on exception. `app/main.py`
line 382-399 wraps the AI call in a try-except and falls back to rule-based results.

## 12. Are AI results clearly separated from production scores?

**Yes.** `ai_mode` and `ai_provider` are stored in the submission record.
Production score is always from `app/scorer.py` (heuristic engine).
AI only enhances `paraphrase_recommendations`, `grammar_drills`, and `upgraded_sample_paragraph`.

---

## Summary of Issues Found

### Critical
- None. The app is functional offline.

### High Priority
1. **No local LLM provider abstraction** — monolithic if-else in ai_mode.py
2. **"local" mode misleading** — named like an AI but is rule-based
3. **No local AI status API** — UI can't show what local AI is available

### Medium Priority
4. **AI settings UI exposes too much** — provider dropdown, API key fields for all providers
5. **No local runtime detection** — Ollama/llama.cpp/MLX not probed
6. **API keys in plaintext** — acceptable for desktop but documented

### Low Priority
7. **Monolithic ai_enhance()** — 150-line function mixing local/cloud logic
8. **No model metadata tracking** — can't show what model is being used
