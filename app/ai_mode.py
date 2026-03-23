from __future__ import annotations

import json
import os
from typing import Any

import httpx


SYSTEM_PROMPT = (
    "You are a strict TOEFL writing coach focused on grammar accuracy and high-score phrasing. "
    "Return strict JSON only. Prioritize tense/article/S-V agreement/preposition/run-on fixes first, "
    "then provide concise paraphrases and one upgraded sample paragraph."
)


def ai_enabled() -> bool:
    return bool(os.getenv("OPENAI_API_KEY", "").strip())


def ai_model() -> str:
    return os.getenv("OPENAI_MODEL", "gpt-4.1-mini").strip() or "gpt-4.1-mini"


def ai_enhance(
    essay_text: str,
    prompt_type: str,
    paraphrase_fallback: list[dict[str, str]],
    grammar_drills_fallback: list[dict[str, str]],
    sample_paragraph_fallback: str,
) -> dict[str, Any] | None:
    api_key = os.getenv("OPENAI_API_KEY", "").strip()
    if not api_key:
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
        with httpx.Client(timeout=12.0) as client:
            resp = client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": ai_model(),
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
            parsed = json.loads(content)

            if not isinstance(parsed, dict):
                return None
            return parsed
    except Exception:
        return None
