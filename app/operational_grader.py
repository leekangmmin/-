"""Production bridge from configured cloud AI to the strict 2026 task grader.

Cloud grading is opt-in through the existing local settings.  Provider or
schema failures are returned as an explicit fallback outcome so the evaluation
endpoint can keep working without silently presenting an LLM score.
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from typing import Any, Literal
from urllib.parse import quote

import httpx

from app.ai_mode import ai_enabled
from app.claude_provider import ClaudeScoringProvider
from app.shadow_config import ShadowConfig
from app.toefl_2026_grader import (
    FeedbackLanguage,
    TaskGradeResult,
    TaskType,
    build_grader_request,
    parse_task_grade,
    schema_error_message,
    task_grade_json_schema,
)

logger = logging.getLogger(__name__)

ScoreSource = Literal["llm", "heuristic", "heuristic_fallback"]


@dataclass(frozen=True)
class OperationalGradeOutcome:
    grade: TaskGradeResult | None
    source: ScoreSource
    provider: str
    model: str
    detail: str


def _prompt_points(prompt_text: str) -> list[str]:
    points = [line.strip(" \t-*\u2022") for line in prompt_text.splitlines() if line.strip(" \t-*\u2022")]
    if points:
        return points
    return [
        "Original task prompt was not supplied. Infer only the visible communicative purpose; "
        "do not invent or mark unseen requirements as missed."
    ]


def _openai_output_text(payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for item in payload.get("output", []):
        if not isinstance(item, dict):
            continue
        for part in item.get("content", []):
            if isinstance(part, dict) and part.get("type") == "output_text":
                texts.append(str(part.get("text", "")))
    return "\n".join(texts).strip()


def _grade_openai(
    cfg: dict[str, Any],
    *,
    task_type: TaskType,
    essay_text: str,
    prompt_bullets: list[str],
    feedback_language: FeedbackLanguage,
    client: httpx.Client | None = None,
) -> TaskGradeResult:
    api_key = str(cfg.get("openai_api_key", "")).strip()
    model = str(cfg.get("openai_model", "gpt-4o")).strip() or "gpt-4o"
    system, base_payload = build_grader_request(
        task_type=task_type,
        essay_text=essay_text,
        prompt_bullets=prompt_bullets,
        feedback_language=feedback_language,
    )
    schema = task_grade_json_schema(task_type)
    own_client = client is None
    http_client = client or httpx.Client(timeout=35.0)
    last_error: Exception | None = None
    try:
        for attempt in range(2):
            user_payload = dict(base_payload)
            if attempt:
                user_payload["retry_instruction"] = schema_error_message(
                    last_error or ValueError("invalid response")
                )
            response = http_client.post(
                "https://api.openai.com/v1/responses",
                headers={
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": model,
                    "instructions": system,
                    "input": json.dumps(user_payload, ensure_ascii=False),
                    "max_output_tokens": 2400,
                    "store": False,
                    "text": {
                        "format": {
                            "type": "json_schema",
                            "name": "toefl_2026_task_grade",
                            "strict": True,
                            "schema": schema,
                        }
                    },
                },
            )
            response.raise_for_status()
            raw = _openai_output_text(response.json())
            if not raw:
                last_error = ValueError("provider returned no output_text")
                continue
            try:
                return parse_task_grade(
                    raw,
                    expected_task_type=task_type,
                    essay_text=essay_text,
                )
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
        raise ValueError(schema_error_message(last_error or ValueError("invalid response")))
    finally:
        if own_client:
            http_client.close()


def _gemini_output_text(payload: dict[str, Any]) -> str:
    texts: list[str] = []
    for candidate in payload.get("candidates", []):
        if not isinstance(candidate, dict):
            continue
        content = candidate.get("content", {})
        for part in content.get("parts", []) if isinstance(content, dict) else []:
            if isinstance(part, dict) and "text" in part:
                texts.append(str(part.get("text", "")))
    return "\n".join(texts).strip()


def _grade_gemini(
    cfg: dict[str, Any],
    *,
    task_type: TaskType,
    essay_text: str,
    prompt_bullets: list[str],
    feedback_language: FeedbackLanguage,
    client: httpx.Client | None = None,
) -> TaskGradeResult:
    api_key = str(cfg.get("gemini_api_key", "")).strip()
    model = str(cfg.get("gemini_model", "gemini-1.5-pro-latest")).strip() or "gemini-1.5-pro-latest"
    model_path = model.removeprefix("models/")
    system, base_payload = build_grader_request(
        task_type=task_type,
        essay_text=essay_text,
        prompt_bullets=prompt_bullets,
        feedback_language=feedback_language,
    )
    own_client = client is None
    http_client = client or httpx.Client(timeout=35.0)
    last_error: Exception | None = None
    try:
        for attempt in range(2):
            user_payload = dict(base_payload)
            if attempt:
                user_payload["retry_instruction"] = schema_error_message(
                    last_error or ValueError("invalid response")
                )
            response = http_client.post(
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{quote(model_path, safe='-_.')}:generateContent",
                headers={
                    "x-goog-api-key": api_key,
                    "Content-Type": "application/json",
                },
                json={
                    "systemInstruction": {"parts": [{"text": system}]},
                    "contents": [
                        {
                            "role": "user",
                            "parts": [{"text": json.dumps(user_payload, ensure_ascii=False)}],
                        }
                    ],
                    "generationConfig": {
                        "temperature": 0.1,
                        "maxOutputTokens": 2400,
                        "responseMimeType": "application/json",
                        "responseJsonSchema": task_grade_json_schema(task_type),
                    },
                },
            )
            response.raise_for_status()
            raw = _gemini_output_text(response.json())
            if not raw:
                last_error = ValueError("provider returned no candidate text")
                continue
            try:
                return parse_task_grade(
                    raw,
                    expected_task_type=task_type,
                    essay_text=essay_text,
                )
            except (ValueError, TypeError, json.JSONDecodeError) as exc:
                last_error = exc
        raise ValueError(schema_error_message(last_error or ValueError("invalid response")))
    finally:
        if own_client:
            http_client.close()


def grade_operational_task(
    *,
    task_type: TaskType,
    essay_text: str,
    prompt_text: str,
    cfg: dict[str, Any],
    feedback_language: FeedbackLanguage = "ko",
    client: httpx.Client | None = None,
) -> OperationalGradeOutcome:
    """Return an opt-in LLM grade or an explicit deterministic fallback state."""
    provider = str(cfg.get("provider", "local")).strip().lower() or "local"
    model_key = {
        "openai": "openai_model",
        "claude": "anthropic_model",
        "gemini": "gemini_model",
    }.get(provider, "")
    model = str(cfg.get(model_key, "")).strip() if model_key else ""

    if not ai_enabled(cfg) or provider == "local":
        return OperationalGradeOutcome(
            grade=None,
            source="heuristic",
            provider="local",
            model="deterministic",
            detail="클라우드 AI 채점이 꺼져 있어 내장 기준 점수를 사용했습니다.",
        )
    if provider not in {"openai", "claude", "gemini"}:
        return OperationalGradeOutcome(
            grade=None,
            source="heuristic_fallback",
            provider=provider,
            model=model or "unknown",
            detail="지원하지 않는 AI 공급자라 내장 기준 점수를 사용했습니다.",
        )

    points = _prompt_points(prompt_text)
    try:
        if provider == "openai":
            grade = _grade_openai(
                cfg,
                task_type=task_type,
                essay_text=essay_text,
                prompt_bullets=points,
                feedback_language=feedback_language,
                client=client,
            )
        elif provider == "claude":
            shadow_cfg = ShadowConfig(
                enabled=True,
                provider="claude",
                anthropic_api_key=str(cfg.get("anthropic_api_key", "")).strip(),
                model=model,
                timeout_seconds=35.0,
                max_retries=0,
            )
            grade = ClaudeScoringProvider(shadow_cfg, client=client).grade_task(
                task_type=task_type,
                essay_text=essay_text,
                prompt_bullets=points,
                feedback_language=feedback_language,
            )
        else:
            grade = _grade_gemini(
                cfg,
                task_type=task_type,
                essay_text=essay_text,
                prompt_bullets=points,
                feedback_language=feedback_language,
                client=client,
            )
        return OperationalGradeOutcome(
            grade=grade,
            source="llm",
            provider=provider,
            model=model,
            detail=(
                "2026 과제 루브릭 AI 채점값입니다."
                if prompt_text.strip()
                else "문제 원문이 없어 답안에서 확인 가능한 과제 수행만 AI로 평가했습니다."
            ),
        )
    except Exception as exc:
        logger.warning("operational grader fallback provider=%s error=%s", provider, type(exc).__name__)
        return OperationalGradeOutcome(
            grade=None,
            source="heuristic_fallback",
            provider=provider,
            model=model,
            detail="AI 채점 응답을 검증하지 못해 내장 기준 점수를 사용했습니다.",
        )


__all__ = ["OperationalGradeOutcome", "ScoreSource", "grade_operational_task"]
