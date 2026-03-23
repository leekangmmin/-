from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.db import get_setting


SYSTEM_PROMPT = (
    "You are a TOEFL writing correction engine, not a casual editor. "
    "Return strict JSON only. Never wrap output with markdown. "
    "Detect and correct every material grammar issue with high recall: "
    "subject-verb agreement, tense consistency, article usage, preposition choice, run-on/comma splice, "
    "relative pronouns, and common learner collocation errors. "
    "When unsure, choose conservative minimal edits that preserve original meaning. "
    "Do not paraphrase first; fix grammar first. "
    "After grammar-focused thinking, provide concise TOEFL-style paraphrases and one improved sample paragraph. "
    "Keep the final style clear, formal, and exam-appropriate."
)

LOCAL_TOEFL_PROMPT = (
    "Embedded local TOEFL mode: prioritize strict grammar correction over style, "
    "preserve meaning, and produce exam-appropriate phrasing with minimal safe edits first."
)


def _sentence_split(text: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+", text.strip()) if s.strip()]


def _normalize_sentence_end(text: str) -> str:
    stripped = text.strip()
    if not stripped:
        return ""
    if stripped.endswith((".", "!", "?")):
        return stripped
    return stripped + "."


def _to_gerund(verb: str) -> str:
    v = verb.strip().lower()
    if len(v) >= 3 and v.endswith("ie"):
        return v[:-2] + "ying"
    if len(v) >= 3 and v.endswith("e") and not v.endswith("ee"):
        return v[:-1] + "ing"
    return v + "ing"


def _toefl_style_polish_sentence(sentence: str) -> str:
    s = sentence
    # Conservative academic-register upgrades for TOEFL writing.
    s = re.sub(r"\ba lot of\b", "many", s, flags=re.IGNORECASE)
    s = re.sub(r"\bkids\b", "children", s, flags=re.IGNORECASE)
    s = re.sub(r"\bget better\b", "improve", s, flags=re.IGNORECASE)
    s = re.sub(r"\bvery important\b", "essential", s, flags=re.IGNORECASE)
    s = re.sub(r"\bin these days\b", "nowadays", s, flags=re.IGNORECASE)
    s = re.sub(r"\bon the internet\b", "online", s, flags=re.IGNORECASE)
    s = re.sub(r"\bin the internet\b", "on the internet", s, flags=re.IGNORECASE)
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return _normalize_sentence_end(s)


def _task_transition(prompt_type: str, index: int) -> str:
    p = (prompt_type or "").lower()
    if index <= 0:
        return ""
    if "integrated" in p:
        transitions = ["Furthermore,", "Moreover,", "As a result,"]
        return transitions[(index - 1) % len(transitions)]
    transitions = ["First,", "In addition,", "Therefore,"]
    return transitions[(index - 1) % len(transitions)]


def _apply_task_linking(sentence: str, prompt_type: str, index: int) -> str:
    s = sentence.strip()
    if not s:
        return s
    if re.match(r"^(first|second|third|moreover|furthermore|therefore|as a result|in addition|however),", s, flags=re.IGNORECASE):
        return s
    t = _task_transition(prompt_type, index)
    if not t:
        return s
    if len(s) > 1 and s[0].isupper() and s[1].islower():
        s = s[0].lower() + s[1:]
    return f"{t} {s}"


def _strict_fix_sentence(sentence: str) -> str:
    s = sentence
    for _ in range(2):
        s = re.sub(r"\b(people|students|children|they|we)\s+is\b", lambda m: f"{m.group(1)} are", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(people|students|children)\s+tends\b", lambda m: f"{m.group(1)} tend", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(he|she|it)\s+don't\b", lambda m: f"{m.group(1)} doesn't", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(i|we|they)\s+doesn't\b", lambda m: f"{m.group(1)} don't", s, flags=re.IGNORECASE)
        s = re.sub(r"\bi\s+am\s+agree\b|\bi'm\s+agree\b", "I agree", s, flags=re.IGNORECASE)
        s = re.sub(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lambda m: f"there are {m.group(1)}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bdiscuss(?:es)?\s+about\b", lambda m: "discusses" if m.group(0).lower().startswith("discusses") else "discuss", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmention(?:s)?\s+about\b", lambda m: "mentions" if m.group(0).lower().startswith("mentions") else "mention", s, flags=re.IGNORECASE)
        s = re.sub(r"\baccording to me\b", "in my opinion", s, flags=re.IGNORECASE)
        s = re.sub(r"\bin my opinion,?\s+i think\b", "in my opinion", s, flags=re.IGNORECASE)
        s = re.sub(r"\bdespite of\b", "despite", s, flags=re.IGNORECASE)
        s = re.sub(r"\bbetween\s+(\w+)\s+to\s+(\w+)\b", lambda m: f"between {m.group(1)} and {m.group(2)}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bif\s+i\s+was\b", "if I were", s, flags=re.IGNORECASE)
        s = re.sub(r"\b(people|students|children)\s+which\b", lambda m: f"{m.group(1)} who", s, flags=re.IGNORECASE)
        s = re.sub(r"\bone of\s+the\s+(\w+)\s+have\b", lambda m: f"one of the {m.group(1)} has", s, flags=re.IGNORECASE)
        s = re.sub(r"\bone of\s+the\s+([a-z]+)\s+has\b", lambda m: f"one of the {m.group(1)}s has" if not m.group(1).endswith("s") else m.group(0), s, flags=re.IGNORECASE)
        s = re.sub(r"\bthe\s+number\s+of\s+(\w+)\s+are\b", lambda m: f"the number of {m.group(1)} is", s, flags=re.IGNORECASE)
        s = re.sub(r"\ba\s+number\s+of\s+(\w+)\s+is\b", lambda m: f"a number of {m.group(1)} are", s, flags=re.IGNORECASE)
        s = re.sub(r"\bprefer\s+to\s+([a-z]+ing)\b", lambda m: f"prefer {m.group(1)}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmake\s+([a-z]+)\s+to\s+([a-z]+)\b", lambda m: f"make {m.group(1)} {m.group(2)}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bsuggest\s+to\s+([a-z]+)\b", lambda m: f"suggest {_to_gerund(m.group(1))}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bcan\s+able\s+to\b", "can", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmore\s+better\b", "better", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmore\s+easier\b", "easier", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmost\s+easiest\b", "easiest", s, flags=re.IGNORECASE)
        s = re.sub(r"\bless\s+people\b", "fewer people", s, flags=re.IGNORECASE)
        s = re.sub(r"^\s*because\s+(.+?),\s*so\s+(.+)$", lambda m: f"Because {m.group(1)}, {m.group(2)}", s, flags=re.IGNORECASE)
        s = re.sub(r"\bbecause\s+([^,.!?]+),\s*so\s+", lambda m: f"because {m.group(1)} and ", s, flags=re.IGNORECASE)
        s = re.sub(r"\balthough\s+([^,.!?]+),\s*but\s+", lambda m: f"although {m.group(1)}, ", s, flags=re.IGNORECASE)
        s = re.sub(r"\bfor example\s*,?\s*such as\b", "for example", s, flags=re.IGNORECASE)
        s = re.sub(r"\bthe reason why\s+([^,.!?]+)\s+is because\b", lambda m: f"the reason {m.group(1)} is that", s, flags=re.IGNORECASE)
        s = re.sub(r"\bon the one hand\b", "on the one hand", s, flags=re.IGNORECASE)
        s = re.sub(r"\bon the other hand,?\s*but\b", "on the other hand", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmany\s+informations\b", "much information", s, flags=re.IGNORECASE)
        s = re.sub(r"\bmany\s+advices\b", "much advice", s, flags=re.IGNORECASE)
        s = re.sub(r"\bhomeworks\b", "homework", s, flags=re.IGNORECASE)
        s = re.sub(r"\bthere\s+are\s+much\s+information\b", "there is much information", s, flags=re.IGNORECASE)
        s = re.sub(r"\bthere\s+are\s+much\s+advice\b", "there is much advice", s, flags=re.IGNORECASE)
        s = re.sub(
            r"\bnot only\s+([a-z]+)(\s+[a-z]+)?\s+but also\s+([a-z]+ing)\b",
            lambda m: f"not only {m.group(1)}{m.group(2) or ''} but also {m.group(1)}",
            s,
            flags=re.IGNORECASE,
        )
        s = re.sub(r"\bin order to\s+be\s+([a-z]+ed)\b", lambda m: f"to be {m.group(1)}", s, flags=re.IGNORECASE)
    # Encourage formal sentence starts for TOEFL tone.
    if s and s[0].islower():
        s = s[0].upper() + s[1:]
    return _toefl_style_polish_sentence(s)


def _score_confidence(original: str, improved: str) -> dict[str, float]:
    # Simple heuristic: more edits = lower confidence, more formal = higher
    grammar = 1.0
    logic = 1.0
    vocab = 1.0
    if original.lower() == improved.lower():
        return {"grammar": 1.0, "logic": 1.0, "vocab": 1.0}
    # Grammar: penalize if verb/noun forms or structure changed
    if re.search(r"\b(is|are|was|were|has|have|had|do|does|did|can|will|would|should|could|may|might|must|shall)\b", original, re.I) and not re.search(r"\b(is|are|was|were|has|have|had|do|does|did|can|will|would|should|could|may|might|must|shall)\b", improved, re.I):
        grammar -= 0.2
    if len(improved) < len(original) - 5:
        logic -= 0.2
    # Vocab: penalize if simple word replaced with more academic
    if re.search(r"children|essential|nowadays|improve|fewer|information", improved, re.I):
        vocab += 0.1
    if re.search(r"kids|very important|a lot of|get better|less people|informations", original, re.I):
        vocab -= 0.2
    # Normalize
    return {"grammar": max(0.5, min(grammar, 1.0)), "logic": max(0.5, min(logic, 1.0)), "vocab": max(0.5, min(vocab, 1.0))}

from typing import Union

def _build_local_paraphrases(prompt_type: str, essay_text: str, fallback: list[dict[str, str]]) -> list[dict[str, Union[str, dict[str, float]]]]:
    recs: list[dict[str, Union[str, dict[str, float]]]] = []
    seen: set[tuple[str, str]] = set()

    for original in _sentence_split(essay_text):
        improved = _strict_fix_sentence(original)
        orig_norm = _normalize_sentence_end(original)
        if not improved or improved == orig_norm:
            continue
        key = (orig_norm.lower(), improved.lower())
        if key in seen:
            continue
        seen.add(key)
        recs.append(
            {
                "original": orig_norm,
                "improved": improved,
                "reason": (
                    "토플 통합형 기준에 맞춰 근거 연결이 자연스럽도록 문장 전개를 보정했습니다."
                    if "integrated" in (prompt_type or "").lower()
                    else "토플 독립형 기준에 맞춰 문법 정확도와 논리 전개를 함께 보정했습니다."
                ),
                "confidence": _score_confidence(orig_norm, improved),
            }
        )
        if len(recs) >= 8:
            break

    if recs:
        return recs
    return [dict(item) for item in fallback[:8]]


def _build_local_drills(essay_text: str, fallback: list[dict[str, str]]) -> list[dict[str, str]]:
    drills = list(fallback[:6])
    lowered = essay_text.lower()

    def add(issue: str, wrong: str, correct: str, tip: str) -> None:
        if len(drills) >= 6:
            return
        key = (issue, wrong, correct)
        seen = {(d.get("issue", ""), d.get("wrong", ""), d.get("correct", "")) for d in drills}
        if key in seen:
            return
        drills.append({"issue": issue, "wrong": wrong, "correct": correct, "tip": tip})

    if re.search(r"\b(he|she|it)\s+don't\b|\b(i|we|they)\s+doesn't\b", lowered):
        add("subject_verb", "He don't agree.", "He doesn't agree.", "Match do/does with the subject before stylistic edits.")
    if re.search(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lowered):
        add("subject_verb", "There is many reasons.", "There are many reasons.", "Use there are before plural nouns.")
    if re.search(r"\bdiscuss(?:es)?\s+about\b|\bmention(?:s)?\s+about\b", lowered):
        add("preposition", "discuss about the issue", "discuss the issue", "Discuss/mention usually take direct objects.")
    if re.search(r"\bif\s+i\s+was\b", lowered):
        add("style", "If I was you", "If I were you", "Use were in this common hypothetical frame.")
    if re.search(r"\b(people|students|children)\s+which\b", lowered):
        add("relative_pronoun", "people which", "people who", "Use who for persons in relative clauses.")
    if re.search(r"\bone of\s+the\s+\w+\s+have\b", lowered):
        add("subject_verb", "One of the students have...", "One of the students has...", "One of + plural noun takes a singular verb.")
    if re.search(r"\bthe\s+number\s+of\s+\w+\s+are\b|\ba\s+number\s+of\s+\w+\s+is\b", lowered):
        add("subject_verb", "The number of X are...", "The number of X is...", "Use singular verb with the number of, plural with a number of.")
    if re.search(r"\bprefer\s+to\s+\w+ing\b", lowered):
        add("verb_pattern", "prefer to studying", "prefer studying", "Use a natural verb pattern for preference statements.")
    if re.search(r"\bnot only\b.*\bbut also\b", lowered):
        add("parallelism", "not only improve but also improving", "not only improve but also develop", "Keep parallel grammatical forms after not only ... but also ...")
    if re.search(r"\bmake\s+\w+\s+to\s+\w+\b", lowered):
        add("verb_pattern", "make students to study", "make students study", "After make + object, use base verb without to.")
    if re.search(r"\bsuggest\s+to\s+\w+\b", lowered):
        add("verb_pattern", "suggest to improve", "suggest improving", "Suggest is usually followed by a gerund or a that-clause.")
    if re.search(r"\bmany\s+(informations|advices)\b|\bhomeworks\b", lowered):
        add("countability", "many informations", "much information", "Information/advice/homework are uncountable in standard academic English.")
    if re.search(r"\bcan\s+able\s+to\b|\bmore\s+better\b|\bless\s+people\b", lowered):
        add("word_choice", "more better / less people", "better / fewer people", "Avoid double comparatives and use fewer with countable plural nouns.")
    if re.search(r"\bbecause\b.+?,\s*so\b", lowered):
        add("clause_linking", "Because A, so B", "Because A, B", "Do not use because and so together in one causal clause.")
    if re.search(r"\balthough\b.+?,\s*but\b", lowered):
        add("clause_linking", "Although A, but B", "Although A, B", "Do not pair although with but in the same clause.")
    if re.search(r"\bfor example\s*,?\s*such as\b", lowered):
        add("redundancy", "for example such as", "for example", "Avoid stacking equivalent markers like for example and such as.")
    if re.search(r"\bthe reason why\s+.+\s+is because\b", lowered):
        add("sentence_form", "The reason why ... is because ...", "The reason ... is that ...", "Use is that to avoid redundancy in reason clauses.")
    if re.search(r"\bmore\s+easier\b|\bmost\s+easiest\b", lowered):
        add("comparative", "more easier / most easiest", "easier / easiest", "Do not use double comparative or superlative forms.")
    if re.search(r"\bin my opinion,?\s+i think\b", lowered):
        add("style", "In my opinion, I think", "In my opinion", "Avoid redundant stance markers in formal TOEFL writing.")

    return drills[:6]


def _build_local_sample_paragraph(prompt_type: str, essay_text: str, fallback: str) -> str:
    sentences = _sentence_split(essay_text)
    if not sentences:
        return fallback.strip()
    fixed = [_apply_task_linking(_strict_fix_sentence(s), prompt_type, i) for i, s in enumerate(sentences[:4])]
    paragraph = " ".join([s for s in fixed if s])
    if len(paragraph) < 40:
        return fallback.strip() or paragraph
    return paragraph


def _read_cfg(key: str, fallback: str = "") -> str:
    db_val = get_setting(key, "").strip()
    if db_val:
        return db_val
    env_name = key.upper()
    return os.getenv(env_name, fallback).strip()


def ai_runtime_config() -> dict[str, Any]:
    provider = _read_cfg("ai_provider", "local") or "local"
    enabled = (_read_cfg("ai_enabled", "0") == "1")

    openai_key = _read_cfg("openai_api_key", "")
    claude_key = _read_cfg("anthropic_api_key", "")
    gemini_key = _read_cfg("gemini_api_key", "")

    openai_model = _read_cfg("openai_model", "gpt-4.1-mini") or "gpt-4.1-mini"
    claude_model = _read_cfg("anthropic_model", "claude-3-5-sonnet-latest") or "claude-3-5-sonnet-latest"
    gemini_model = _read_cfg("gemini_model", "gemini-1.5-pro-latest") or "gemini-1.5-pro-latest"

    return {
        "provider": provider,
        "enabled": enabled,
        "openai_api_key": openai_key,
        "anthropic_api_key": claude_key,
        "gemini_api_key": gemini_key,
        "openai_model": openai_model,
        "anthropic_model": claude_model,
        "gemini_model": gemini_model,
    }


def ai_enabled(cfg: dict[str, Any] | None = None) -> bool:
    c = cfg or ai_runtime_config()
    if not bool(c.get("enabled")):
        return False
    provider = str(c.get("provider", "openai"))
    if provider == "local":
        return True
    if provider == "claude":
        return bool(str(c.get("anthropic_api_key", "")).strip())
    if provider == "gemini":
        return bool(str(c.get("gemini_api_key", "")).strip())
    return bool(str(c.get("openai_api_key", "")).strip())


def _extract_json(content: str) -> dict[str, Any] | None:
    text = content.strip()
    if not text:
        return None
    try:
        parsed = json.loads(text)
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        pass

    m = re.search(r"\{.*\}", text, re.DOTALL)
    if not m:
        return None
    try:
        parsed = json.loads(m.group(0))
        if isinstance(parsed, dict):
            return parsed
    except Exception:
        return None
    return None


def _openai_enhance(cfg: dict[str, Any], user_prompt: dict[str, Any]) -> dict[str, Any] | None:
    api_key = str(cfg.get("openai_api_key", "")).strip()
    if not api_key:
        return None
    model = str(cfg.get("openai_model", "gpt-4.1-mini")).strip() or "gpt-4.1-mini"
    with httpx.Client(timeout=20.0) as client:
        resp = client.post(
            "https://api.openai.com/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.3,
                "response_format": {"type": "json_object"},
                "messages": [
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                ],
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        content = payload["choices"][0]["message"]["content"]
    return _extract_json(str(content))


def _anthropic_enhance(cfg: dict[str, Any], user_prompt: dict[str, Any]) -> dict[str, Any] | None:
    api_key = str(cfg.get("anthropic_api_key", "")).strip()
    if not api_key:
        return None
    model = str(cfg.get("anthropic_model", "claude-3-5-sonnet-latest")).strip() or "claude-3-5-sonnet-latest"
    with httpx.Client(timeout=25.0) as client:
        resp = client.post(
            "https://api.anthropic.com/v1/messages",
            headers={
                "x-api-key": api_key,
                "anthropic-version": "2023-06-01",
                "Content-Type": "application/json",
            },
            json={
                "model": model,
                "temperature": 0.3,
                "max_tokens": 1400,
                "system": SYSTEM_PROMPT,
                "messages": [
                    {"role": "user", "content": json.dumps(user_prompt, ensure_ascii=False)},
                ],
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        parts = payload.get("content", [])
        text = ""
        for p in parts:
            if isinstance(p, dict) and p.get("type") == "text":
                text += str(p.get("text", ""))
    return _extract_json(text)


def _gemini_enhance(cfg: dict[str, Any], user_prompt: dict[str, Any]) -> dict[str, Any] | None:
    api_key = str(cfg.get("gemini_api_key", "")).strip()
    if not api_key:
        return None
    model = str(cfg.get("gemini_model", "gemini-1.5-pro-latest")).strip() or "gemini-1.5-pro-latest"
    prompt_text = (
        SYSTEM_PROMPT
        + "\n\nReturn JSON object only.\n"
        + json.dumps(user_prompt, ensure_ascii=False)
    )
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
    with httpx.Client(timeout=25.0) as client:
        resp = client.post(
            url,
            headers={"Content-Type": "application/json"},
            json={
                "contents": [{"parts": [{"text": prompt_text}]}],
                "generationConfig": {"temperature": 0.3},
            },
        )
        resp.raise_for_status()
        payload = resp.json()
        texts: list[str] = []
        for cand in payload.get("candidates", []):
            content = cand.get("content", {}) if isinstance(cand, dict) else {}
            for part in content.get("parts", []) if isinstance(content, dict) else []:
                if isinstance(part, dict) and "text" in part:
                    texts.append(str(part.get("text", "")))
    return _extract_json("\n".join(texts))


def ai_enhance(
    essay_text: str,
    prompt_type: str,
    paraphrase_fallback: list[dict[str, str]],
    grammar_drills_fallback: list[dict[str, str]],
    sample_paragraph_fallback: str,
    cfg: dict[str, Any] | None = None,
) -> dict[str, Any] | None:
    runtime = cfg or ai_runtime_config()
    if not ai_enabled(runtime):
        return None

    user_prompt = {
        "task": "enhance_feedback",
        "prompt_type": prompt_type,
        "essay_text": essay_text,
        "strict_judgement_policy": [
            "catch_all_material_grammar_errors",
            "prefer_minimal_exact_edits_before_style",
            "preserve_original_meaning",
            "toefl_formal_register",
        ],
        "constraints": {
            "paraphrase_items_max": 8,
            "grammar_drills_max": 6,
            "output_language": "ko",
        },
        "fallback": {
            "paraphrase_recommendations": paraphrase_fallback,
            "grammar_drills": grammar_drills_fallback,
            "upgraded_sample_paragraph": sample_paragraph_fallback,
        },
        "output_schema": {
            "paraphrase_recommendations": [
                {"original": "str", "improved": "str", "reason": "str"}
            ],
            "grammar_drills": [
                {"issue": "str", "wrong": "str", "correct": "str", "tip": "str"}
            ],
            "upgraded_sample_paragraph": "str",
        },
    }

    try:
        provider = str(runtime.get("provider", "local"))
        if provider == "local":
            _ = LOCAL_TOEFL_PROMPT  # Explicitly keep local TOEFL prompt contract in code path.
            paragraph = _build_local_sample_paragraph(prompt_type, essay_text, sample_paragraph_fallback)
            return {
                "paraphrase_recommendations": _build_local_paraphrases(prompt_type, essay_text, paraphrase_fallback),
                "grammar_drills": _build_local_drills(essay_text, grammar_drills_fallback),
                "upgraded_sample_paragraph": paragraph or sample_paragraph_fallback,
            }
        if provider == "claude":
            return _anthropic_enhance(runtime, user_prompt)
        if provider == "gemini":
            return _gemini_enhance(runtime, user_prompt)
        return _openai_enhance(runtime, user_prompt)
    except Exception:
        return None
