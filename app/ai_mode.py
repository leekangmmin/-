from __future__ import annotations

import json
import os
import re
from typing import Any

import httpx

from app.db import get_setting


SYSTEM_PROMPT = (
    "You are a strict TOEFL writing coach focused on grammar accuracy and high-score phrasing. "
    "Return strict JSON only. Prioritize tense/article/S-V agreement/preposition/run-on fixes first. "
    "Do not smooth over mistakes: catch every material grammar issue you can see, preserve the original meaning, "
    "and prefer minimal but exact edits before stylistic improvements. Then provide concise paraphrases and one upgraded sample paragraph."
)


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
            paragraph = sample_paragraph_fallback.strip()
            if not paragraph:
                paragraph = " ".join([s.strip() for s in re.split(r"(?<=[.!?])\s+", essay_text.strip()) if s.strip()][:2])
            if paragraph and not paragraph.endswith((".", "!", "?")):
                paragraph += "."
            return {
                "paraphrase_recommendations": paraphrase_fallback[:8],
                "grammar_drills": grammar_drills_fallback[:6],
                "upgraded_sample_paragraph": paragraph or sample_paragraph_fallback,
            }
        if provider == "claude":
            return _anthropic_enhance(runtime, user_prompt)
        if provider == "gemini":
            return _gemini_enhance(runtime, user_prompt)
        return _openai_enhance(runtime, user_prompt)
    except Exception:
        return None
