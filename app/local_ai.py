"""Local AI Provider layer (Phase 8-B).

Three-tier AI model:
  Mode A — Offline Core (always available, score_essay + heuristic analysis)
  Mode B — Built-in Local AI (optional, rule-based by default, LLM adapters optional)
  Mode C — Cloud AI (optional, explicit API key required)

Key design rules:
  - Local/Cloud AI never changes the production score (app/scorer.py).
  - Local AI runs in enhancement/shadow mode only.
  - Local AI failure does not break Offline Core.
  - No essay leaves the device unless user explicitly enables Cloud AI.
"""

from __future__ import annotations

import hashlib
import json
import logging
import os
import re
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Literal

import httpx

logger = logging.getLogger("toefl.local_ai")

# ---------------------------------------------------------------------------
# Provider configuration (Phase 8-B: configurable timeouts, env overrides)
# ---------------------------------------------------------------------------

@dataclass
class LocalAIProviderConfig:
    connect_timeout_seconds: float = 5.0
    read_timeout_seconds: float = 120.0
    total_timeout_seconds: float = 180.0
    first_run_timeout_seconds: float = 240.0
    max_output_tokens: int = 512
    temperature: float = 0.2
    keep_alive: str = "10m"
    num_ctx: int = 2048

    @classmethod
    def from_env(cls, prefix: str = "TOEFL_LOCAL_AI") -> "LocalAIProviderConfig":
        def _float(name: str, default: float) -> float:
            try:
                return float(os.environ.get(f"{prefix}_{name}", str(default)))
            except (ValueError, TypeError):
                return default

        def _int(name: str, default: int) -> int:
            try:
                return int(os.environ.get(f"{prefix}_{name}", str(default)))
            except (ValueError, TypeError):
                return default

        def _str(name: str, default: str) -> str:
            return str(os.environ.get(f"{prefix}_{name}", default))

        return cls(
            connect_timeout_seconds=_float("CONNECT_TIMEOUT", 5.0),
            read_timeout_seconds=_float("READ_TIMEOUT", 120.0),
            total_timeout_seconds=_float("TOTAL_TIMEOUT", 180.0),
            first_run_timeout_seconds=_float("FIRST_RUN_TIMEOUT", 240.0),
            max_output_tokens=_int("MAX_OUTPUT_TOKENS", 512),
            temperature=_float("TEMPERATURE", 0.2),
            keep_alive=_str("KEEP_ALIVE", "10m"),
            num_ctx=_int("NUM_CTX", 2048),
        )


# ---------------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------------

@dataclass
class LocalAIAvailability:
    available: bool
    provider_id: str = ""
    provider_name: str = ""
    model_name: str | None = None
    model_version: str | None = None
    runs_offline: bool = True
    requires_model_file: bool = False
    status: Literal["ready", "ready_fast", "ready_slow", "unavailable", "model_missing", "runtime_missing", "loading", "error", "timeout", "too_heavy"] = "unavailable"
    detail: str = ""
    performance: dict[str, Any] = field(default_factory=dict)


@dataclass
class FeedbackItem:
    text: str
    type: Literal["strength", "issue", "suggestion"] = "suggestion"
    confidence: Literal["low", "medium", "high"] = "medium"


@dataclass
class SentenceSuggestion:
    original: str
    improved: str
    reason: str
    confidence: float = 0.5


@dataclass
class LocalAIRequest:
    essay_text: str
    prompt_type: str = "academic_discussion"
    prompt_text: str = ""
    request_type: Literal["analyze", "rewrite", "feedback", "paraphrase"] = "analyze"


@dataclass
class LocalAIResult:
    provider_id: str = ""
    provider_name: str = ""
    model_name: str | None = None
    model_version: str | None = None
    runs_offline: bool = True
    generated_at: str = ""
    valid: bool = True
    confidence: float = 0.5
    latency_ms: int = 0
    warnings: list[str] = field(default_factory=list)
    summary: str = ""
    strengths: list[FeedbackItem] = field(default_factory=list)
    priority_issues: list[FeedbackItem] = field(default_factory=list)
    sentence_suggestions: list[SentenceSuggestion] = field(default_factory=list)
    rewrite: str | None = None
    next_practice_goal: str | None = None
    performance: dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Prompt templates
# ---------------------------------------------------------------------------

OLLAMA_SYSTEM_PROMPT = (
    "You are a TOEFL writing assistant for Korean students. "
    "Analyze the essay briefly. Output ONLY valid JSON, no markdown, no extra text. "
    "Do NOT generate scores. Do NOT claim this is ETS official scoring. "
    "All 'original' fields must be exact substrings from the essay. "
    "Max 3 sentence suggestions, max 3 priority issues. "
    "Keep total output under 512 tokens."
)

OLLAMA_JSON_SCHEMA = (
    '{"summary":"string (50 chars max)",'
    '"strengths":[{"text":"string","evidence":"string|null"}],'
    '"priority_issues":[{"issue":"string","why":"string","evidence":"string|null","suggestion":"string"}],'
    '"sentence_suggestions":[{"original":"exact essay text","suggested":"improved","reason":"short"}],'
    '"next_practice_goal":"string"}'
)

WARMUP_PROMPT = 'Return ONLY this JSON, no other text: {"ready":true}'


def _build_ollama_prompt(request: LocalAIRequest) -> str:
    """Build a concise Ollama prompt optimized for 7B models."""
    essay_hash = hashlib.sha256(request.essay_text.encode()).hexdigest()[:8]
    essay_preview = request.essay_text[:1200] if len(request.essay_text) > 1200 else request.essay_text

    prompt = (
        f"{OLLAMA_SYSTEM_PROMPT}\n\n"
        f"Type: {request.prompt_type}\n"
        f"Essay:\n{essay_preview}\n\n"
        f"Output only this JSON structure (fill in the values in Korean or English):\n"
        f"{OLLAMA_JSON_SCHEMA}\n"
        f"No markdown, no backticks, just the JSON object."
    )
    return prompt


# ---------------------------------------------------------------------------
# Provider ABC
# ---------------------------------------------------------------------------

class LocalAIProvider(ABC):
    id: str
    display_name: str
    requires_model_file: bool = False

    @abstractmethod
    def is_available(self) -> LocalAIAvailability: ...

    @abstractmethod
    def analyze_response(self, request: LocalAIRequest) -> LocalAIResult: ...


# ---------------------------------------------------------------------------
# Rule-based local provider (always available)
# ---------------------------------------------------------------------------

class RuleLocalAIProvider(LocalAIProvider):
    id = "rule"
    display_name = "기본 로컬 분석"
    requires_model_file = False

    _VERSION = "2.0.0"

    def is_available(self) -> LocalAIAvailability:
        return LocalAIAvailability(
            available=True,
            provider_id=self.id,
            provider_name=self.display_name,
            runs_offline=True,
            requires_model_file=False,
            status="ready",
            detail="언제나 사용 가능한 규칙 기반 분석입니다",
        )

    def analyze_response(self, request: LocalAIRequest) -> LocalAIResult:
        started = time.perf_counter()
        essay = request.essay_text
        warnings: list[str] = []
        strengths: list[FeedbackItem] = []
        issues: list[FeedbackItem] = []
        suggestions: list[SentenceSuggestion] = []

        words = essay.split()
        word_count = len(words)
        sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", essay.strip()) if s.strip()]

        if word_count >= 120:
            strengths.append(FeedbackItem("답안 분량이 충분합니다 (120단어 이상)", "strength", "high"))
        elif word_count >= 100:
            strengths.append(FeedbackItem("답안 분량이 기본 수준입니다 (100단어 이상)", "strength", "medium"))
        else:
            issues.append(FeedbackItem("답안 분량이 짧습니다. 최소 120단어를 권장합니다", "issue", "high"))

        avg_len = word_count / max(len(sentences), 1)
        if 12 <= avg_len <= 24:
            strengths.append(FeedbackItem(f"문장 길이가 적절합니다 (평균 {avg_len:.0f}단어)", "strength", "high"))
        elif avg_len > 24:
            issues.append(FeedbackItem(f"문장이 평균적으로 깁니다 ({avg_len:.0f}단어). 가독성을 위해 일부 문장을 분리하세요", "issue", "medium"))

        paragraphs = [p.strip() for p in re.split(r"\n\s*\n", essay.strip()) if p.strip()]
        if len(paragraphs) >= 3:
            strengths.append(FeedbackItem("문단 구성이 명확합니다 (3개 이상)", "strength", "high"))
        elif len(paragraphs) >= 2:
            strengths.append(FeedbackItem("문단이 2개입니다. 서론-본론-결론 구조를 권장합니다", "strength", "low"))
        else:
            issues.append(FeedbackItem("문단 구분이 없습니다. 서론·본론·결론으로 나누세요", "issue", "high"))

        transitions = {"however", "therefore", "moreover", "furthermore", "for example", "in addition", "as a result", "in contrast", "consequently"}
        transition_hits = sum(1 for t in transitions if t in essay.lower())
        if transition_hits >= 4:
            strengths.append(FeedbackItem("연결어 사용이 풍부해 논리 흐름이 좋습니다", "strength", "high"))
        elif transition_hits >= 2:
            strengths.append(FeedbackItem("기본적인 연결어가 사용되었습니다", "strength", "medium"))
        else:
            issues.append(FeedbackItem("연결어가 부족합니다. however, therefore, for example 등을 사용하세요", "issue", "medium"))

        evidence = {"because", "for example", "for instance", "according to", "research", "study"}
        evidence_hits = sum(1 for e in evidence if e in essay.lower())
        if evidence_hits >= 3:
            strengths.append(FeedbackItem("근거와 예시가 충분히 제시되었습니다", "strength", "high"))
        elif evidence_hits >= 1:
            strengths.append(FeedbackItem("기본적인 근거가 제시되었습니다", "strength", "medium"))
        else:
            issues.append(FeedbackItem("구체적인 근거나 예시가 부족합니다. for example 문장을 추가하세요", "issue", "high"))

        suggestions = self._generate_suggestions(sentences)

        strong_count = len(strengths)
        issue_count = len(issues)
        if issue_count == 0:
            summary = f"전반적으로 균형 잡힌 답안입니다. 현재 강점을 유지하면서 구체적 근거를 보강하면 더 높은 점수를 기대할 수 있습니다."
        elif issue_count <= 2:
            summary = f"대체로 양호한 답안입니다. 지적된 {issue_count}개 영역을 개선하면 점수 향상이 기대됩니다."
        else:
            summary = f"개선이 필요한 영역이 {issue_count}개 있습니다. 우선순위에 따라 하나씩 교정해보세요."

        latency_ms = int((time.perf_counter() - started) * 1000)
        return LocalAIResult(
            provider_id=self.id,
            provider_name=self.display_name,
            model_name="rule-engine",
            model_version=self._VERSION,
            runs_offline=True,
            generated_at=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            valid=True,
            confidence=0.7,
            latency_ms=latency_ms,
            warnings=warnings,
            summary=summary,
            strengths=strengths,
            priority_issues=issues,
            sentence_suggestions=suggestions,
            rewrite=None,
            next_practice_goal=self._next_goal(issues),
        )

    def _generate_suggestions(self, sentences: list[str]) -> list[SentenceSuggestion]:
        suggestions: list[SentenceSuggestion] = []
        seen: set[str] = set()
        for s in sentences[:6]:
            improved = self._fix_sentence(s)
            if improved and improved != s and s.lower() not in seen:
                seen.add(s.lower())
                suggestions.append(SentenceSuggestion(
                    original=s,
                    improved=improved,
                    reason="문법 정확도와 표현을 개선했습니다",
                    confidence=0.6,
                ))
        return suggestions[:4]

    def _fix_sentence(self, s: str) -> str:
        result = s
        result = re.sub(r"\b(i|we|they|people|students|children)\s+is\b", lambda m: f"{m.group(1)} are", result, flags=re.IGNORECASE)
        result = re.sub(r"\b(he|she|it)\s+don't\b", lambda m: f"{m.group(1)} doesn't", result, flags=re.IGNORECASE)
        result = re.sub(r"\b(i|we|they)\s+doesn't\b", lambda m: f"{m.group(1)} don't", result, flags=re.IGNORECASE)
        result = re.sub(r"\bi\s+am\s+agree\b", "I agree", result, flags=re.IGNORECASE)
        result = re.sub(r"\bthere\s+is\s+(many|several|two|three|four|five|students|people)\b", lambda m: f"there are {m.group(1)}", result, flags=re.IGNORECASE)
        result = re.sub(r"\bdiscuss(?:es)?\s+about\b", lambda m: "discusses" if "discusses" in m.group(0).lower() else "discuss", result, flags=re.IGNORECASE)
        result = re.sub(r"\baccording to me\b", "in my opinion", result, flags=re.IGNORECASE)
        result = re.sub(r"\bmore\s+better\b", "better", result, flags=re.IGNORECASE)
        result = re.sub(r"\ba lot of\b", "many", result, flags=re.IGNORECASE)
        result = re.sub(r"\bkids\b", "children", result, flags=re.IGNORECASE)
        result = re.sub(r"\bcan\s+able\s+to\b", "can", result, flags=re.IGNORECASE)
        result = re.sub(r"\bdespite of\b", "despite", result, flags=re.IGNORECASE)
        result = re.sub(r"\b(i)\s+go\b", r"\1 went", result, flags=re.IGNORECASE)
        result = re.sub(r"\b(make|help)\b.*?(\w+ed|gone|done)\b", lambda m: m.group(0), result, flags=re.IGNORECASE)
        result = re.sub(r"\bnot\s+more\b", "not as", result, flags=re.IGNORECASE)
        return result

    def _next_goal(self, issues: list[FeedbackItem]) -> str:
        if not issues:
            return "현재 강점을 유지하면서 어휘 다양성을 더 높여보세요"
        issue_texts = [i.text for i in issues]
        if any("분량" in t for t in issue_texts):
            return "다음 답안에서는 최소 120단어 이상 작성해보세요"
        if any("문단" in t for t in issue_texts):
            return "다음 답안에서는 서론-본론-결론 3단 구조로 작성해보세요"
        if any("근거" in t for t in issue_texts):
            return "다음 답안에서는 각 주장마다 구체적 예시를 하나씩 추가해보세요"
        if any("연결어" in t for t in issue_texts):
            return "다음 답안에서는 however, therefore, for example 중 2개 이상 사용해보세요"
        return issue_texts[0]


# ---------------------------------------------------------------------------
# Ollama local provider (Phase 8-B: configurable timeouts, warmup, optimized)
# ---------------------------------------------------------------------------

class OllamaLocalProvider(LocalAIProvider):
    id = "ollama"
    display_name = "Ollama 로컬 모델"
    requires_model_file = True

    def __init__(self, base_url: str = "http://127.0.0.1:11434", model: str = "", config: LocalAIProviderConfig | None = None):
        self._base_url = str(base_url).strip()
        self._model = str(model).strip()
        self._detected_model = ""
        self._last_detection: float = 0.0
        self._config = config or LocalAIProviderConfig.from_env()
        self._is_warm: bool = False
        self._warmup_latency_ms: int | None = None
        self._last_performance: dict[str, Any] = {}
        self._installed_models: list[dict[str, Any]] = []

    def _make_timeout(self, read_seconds: float) -> httpx.Timeout:
        """Build httpx.Timeout requiring all four params when partial is used."""
        c = self._config.connect_timeout_seconds
        return httpx.Timeout(read_seconds, connect=c, write=c, pool=c)

    # ------------------------------------------------------------------
    # Availability
    # ------------------------------------------------------------------

    def is_available(self) -> LocalAIAvailability:
        if not self._base_url.startswith("http://127.0.0.1") and not self._base_url.startswith("http://localhost"):
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=False, requires_model_file=True, status="error",
                detail="보안상 로컬호스트(localhost/127.0.0.1) 주소만 허용됩니다",
            )
        try:
            resp = httpx.get(f"{self._base_url}/api/tags", timeout=10.0)
            if resp.status_code != 200:
                return LocalAIAvailability(
                    available=False, provider_id=self.id, provider_name=self.display_name,
                    runs_offline=True, requires_model_file=True, status="runtime_missing",
                    detail="Ollama가 실행 중이지만 모델 목록을 가져올 수 없습니다",
                )
            data = resp.json()
            models = data.get("models", [])
            self._installed_models = models
            if not models:
                return LocalAIAvailability(
                    available=False, provider_id=self.id, provider_name=self.display_name,
                    runs_offline=True, requires_model_file=True, status="model_missing",
                    detail="Ollama가 실행 중이지만 설치된 모델이 없습니다",
                )
            target = self._model or models[0].get("name", "")
            target_model = None
            for m in models:
                if m.get("name", "") == self._model:
                    target_model = m
                    break
            if not target_model and self._model:
                return LocalAIAvailability(
                    available=False, provider_id=self.id, provider_name=self.display_name,
                    runs_offline=True, requires_model_file=True, status="model_missing",
                    detail=f"'{self._model}' 모델이 설치되지 않았습니다. 설치된 모델: {[m.get('name') for m in models[:5]]}",
                )
            self._detected_model = target_model.get("name", models[0].get("name", "")) if target_model else models[0].get("name", "")
            self._last_detection = time.time()

            perf_status = self._performance_status()
            return LocalAIAvailability(
                available=True, provider_id=self.id, provider_name=self.display_name,
                model_name=self._detected_model, runs_offline=True, requires_model_file=True,
                status=perf_status,
                detail=self._build_detail(perf_status),
                performance=self._last_performance,
            )
        except (httpx.ConnectError, httpx.TimeoutException):
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=True, requires_model_file=True, status="runtime_missing",
                detail="Ollama 서버에 연결할 수 없습니다. Ollama가 실행 중인지 확인하세요",
            )
        except Exception as exc:
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=True, requires_model_file=True, status="error",
                detail=f"Ollama 연결 중 오류: {exc}",
            )

    def _performance_status(self) -> str:
        """Determine performance status based on last known inference data."""
        if not self._last_performance:
            return "ready"
        eval_dur = self._last_performance.get("eval_duration_ns", 0)
        total_dur = self._last_performance.get("total_duration_ns", 0)
        eval_count = self._last_performance.get("eval_count", 0)
        load_dur = self._last_performance.get("load_duration_ns", 0)

        total_s = total_dur / 1e9 if total_dur else 0
        tokens_per_sec = (eval_count / (eval_dur / 1e9)) if eval_dur and eval_count else 0

        if total_s > 180:
            return "timeout"
        if load_dur / 1e9 > 60:
            return "too_heavy"
        if total_s > 60:
            return "ready_slow"
        return "ready_fast"

    def _build_detail(self, status: str) -> str:
        base = f"Ollama 연결됨: {self._detected_model}"
        if self._warmup_latency_ms:
            base += f" (warmup: {self._warmup_latency_ms}ms)"
        if status == "ready_slow":
            base += " — 속도가 느릴 수 있습니다"
        elif status == "too_heavy":
            base += " — 더 작은 모델을 권장합니다"
        elif status == "timeout":
            base += " — 마지막 요청이 시간 초과되었습니다"
        return base

    def installed_models(self) -> list[dict[str, Any]]:
        return list(self._installed_models)

    def model_recommendations(self) -> dict[str, Any]:
        status = self._performance_status()
        recs: list[str] = []
        if status == "timeout":
            recs.append("timeout 값을 늘려보세요 (고급 설정)")
        if status in ("ready_slow", "too_heavy"):
            recs.append("더 작은 모델을 사용하면 응답이 빨라질 수 있습니다")
            smaller_models = [m.get("name") for m in self._installed_models if "7b" not in m.get("name", "").lower() and "13b" not in m.get("name", "").lower()]
            if smaller_models:
                recs.append(f"설치된 가벼운 모델: {', '.join(smaller_models[:3])}")
        if not self._is_warm:
            recs.append("keep_alive 옵션을 활성화하면 첫 호출 속도가 개선됩니다")

        return {
            "current_model": self._detected_model,
            "status": status,
            "warm": self._is_warm,
            "warmup_latency_ms": self._warmup_latency_ms,
            "recommendations": recs,
            "can_keep_current": status in ("ready", "ready_fast", "ready_slow"),
            "perf": self._last_performance,
        }

    # ------------------------------------------------------------------
    # Warm-up
    # ------------------------------------------------------------------

    def warmup(self) -> dict[str, Any]:
        """Pre-load the model with a minimal prompt. Safe, no real essay data used."""
        started = time.perf_counter()
        if not self._detected_model:
            if not self.is_available().available:
                return {"ok": False, "reason": "모델을 찾을 수 없습니다", "latency_ms": 0}

        try:
            resp = httpx.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._detected_model,
                    "prompt": WARMUP_PROMPT,
                    "stream": False,
                    "options": {
                        "temperature": 0.0,
                        "num_predict": 20,
                    },
                    "keep_alive": self._config.keep_alive,
                },
                timeout=self._make_timeout(self._config.first_run_timeout_seconds),
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "").strip()
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._warmup_latency_ms = latency_ms
            self._record_performance(data)

            ready = "ready" in response_text.lower() or response_text.strip() == "{\"ready\":true}"
            self._is_warm = ready or bool(response_text)

            return {
                "ok": self._is_warm,
                "latency_ms": latency_ms,
                "response": response_text[:100],
                "performance": self._last_performance,
            }
        except Exception as exc:
            latency_ms = int((time.perf_counter() - started) * 1000)
            self._is_warm = False
            return {"ok": False, "reason": str(exc), "latency_ms": latency_ms}

    # ------------------------------------------------------------------
    # Analyze
    # ------------------------------------------------------------------

    def analyze_response(self, request: LocalAIRequest) -> LocalAIResult:
        started = time.perf_counter()
        if not self._detected_model:
            return LocalAIResult(
                provider_id=self.id, provider_name=self.display_name,
                valid=False, confidence=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                warnings=["Ollama 모델이 감지되지 않았습니다. is_available()를 먼저 확인하세요"],
            )

        timeout = self._config.first_run_timeout_seconds if not self._is_warm else self._config.total_timeout_seconds
        prompt = _build_ollama_prompt(request)

        try:
            resp = httpx.post(
                f"{self._base_url}/api/generate",
                json={
                    "model": self._detected_model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": self._config.temperature,
                        "num_predict": self._config.max_output_tokens,
                        "num_ctx": self._config.num_ctx,
                    },
                    "keep_alive": self._config.keep_alive,
                },
                timeout=self._make_timeout(timeout),
            )
            resp.raise_for_status()
            data = resp.json()
            response_text = data.get("response", "")
            self._record_performance(data)
            self._is_warm = True

            parsed = self._parse_response(response_text, request)
            parsed.latency_ms = int((time.perf_counter() - started) * 1000)
            parsed.provider_id = self.id
            parsed.provider_name = self.display_name
            parsed.model_name = self._detected_model
            parsed.runs_offline = True
            parsed.performance = dict(self._last_performance)
            return parsed
        except httpx.TimeoutException:
            return LocalAIResult(
                provider_id=self.id, provider_name=self.display_name,
                model_name=self._detected_model, runs_offline=True,
                valid=False, confidence=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                warnings=["Ollama 요청 시간 초과 — 모델이 너무 느리거나 응답하지 않습니다"],
            )
        except Exception as exc:
            return LocalAIResult(
                provider_id=self.id, provider_name=self.display_name,
                model_name=self._detected_model, runs_offline=True,
                valid=False, confidence=0.0,
                latency_ms=int((time.perf_counter() - started) * 1000),
                warnings=[f"Ollama 호출 실패: {exc}"],
            )

    def _record_performance(self, data: dict[str, Any]):
        self._last_performance = {
            "total_duration_ns": data.get("total_duration", 0),
            "load_duration_ns": data.get("load_duration", 0),
            "prompt_eval_duration_ns": data.get("prompt_eval_duration", 0),
            "eval_duration_ns": data.get("eval_duration", 0),
            "eval_count": data.get("eval_count", 0),
            "prompt_eval_count": data.get("prompt_eval_count", 0),
        }
        if data.get("eval_duration") and data.get("eval_count"):
            self._last_performance["tokens_per_sec"] = round(
                data["eval_count"] / max(data["eval_duration"] / 1e9, 0.001), 1
            )

    def _parse_response(self, text: str, request: LocalAIRequest) -> LocalAIResult:
        """Parse Ollama response, handling markdown-wrapped JSON and extra text."""

        # Remove markdown code fences if present
        cleaned = text.strip()
        # Remove ```json ... ``` markers
        if cleaned.startswith("```"):
            cleaned = re.sub(r"^```(?:json)?\s*", "", cleaned)
            cleaned = re.sub(r"\s*```$", "", cleaned)

        # Try to parse as JSON
        try:
            data = json.loads(cleaned)
        except json.JSONDecodeError:
            # Try to extract JSON object from text
            m = re.search(r"\{.*\}", cleaned, re.DOTALL)
            if m:
                try:
                    data = json.loads(m.group(0))
                except json.JSONDecodeError:
                    return LocalAIResult(
                        valid=False, summary=text[:200],
                        warnings=["Ollama 응답 JSON 파싱 실패"],
                        performance=dict(self._last_performance),
                    )
            else:
                return LocalAIResult(
                    valid=False, summary=text[:200],
                    warnings=["Ollama 응답에서 JSON을 찾을 수 없습니다"],
                    performance=dict(self._last_performance),
                )

        summary = str(data.get("summary", ""))
        raw_strengths = data.get("strengths", [])
        raw_issues = data.get("priority_issues", [])
        raw_suggestions = data.get("sentence_suggestions", [])

        strengths = [
            FeedbackItem(
                text=str(s.get("text", s)) if isinstance(s, dict) else str(s),
                type="strength",
                confidence="medium",
            )
            for s in raw_strengths
        ]

        issues = [
            FeedbackItem(
                text=str(i.get("issue", i.get("text", str(i)) if isinstance(i, dict) else str(i))),
                type="issue",
                confidence="medium",
            )
            for i in raw_issues
        ]

        suggestions: list[SentenceSuggestion] = []
        for s in raw_suggestions[:3]:
            if isinstance(s, dict):
                suggestions.append(SentenceSuggestion(
                    original=str(s.get("original", "")),
                    improved=str(s.get("suggested", s.get("improved", ""))),
                    reason=str(s.get("reason", "")),
                ))

        next_goal = str(data.get("next_practice_goal", ""))

        # Score leak check
        warnings: list[str] = []
        score_keys = ("score", "band", "점수", "total_score", "overall_score", "final_score")
        for k in score_keys:
            if k in data:
                warnings.append(f"Ollama 응답에 '{k}' 필드가 포함되어 있습니다 — 무시됨")

        return LocalAIResult(
            valid=True, confidence=0.5, summary=summary,
            strengths=strengths, priority_issues=issues,
            sentence_suggestions=suggestions, next_practice_goal=next_goal,
            warnings=warnings,
            performance=dict(self._last_performance),
        )


# ---------------------------------------------------------------------------
# LlamaCppLocalProvider — detects local llama.cpp server
# ---------------------------------------------------------------------------

class LlamaCppLocalProvider(LocalAIProvider):
    id = "llamacpp"
    display_name = "llama.cpp 로컬 서버"
    requires_model_file = True

    def __init__(self, base_url: str = "http://127.0.0.1:8080", config: LocalAIProviderConfig | None = None):
        self._base_url = str(base_url).strip()
        self._config = config or LocalAIProviderConfig.from_env()
        self._model_name: str | None = None

    def is_available(self) -> LocalAIAvailability:
        if not self._base_url.startswith("http://127.0.0.1") and not self._base_url.startswith("http://localhost"):
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=False, requires_model_file=True, status="error",
                detail="보안상 로컬호스트 주소만 허용됩니다",
            )
        try:
            resp = httpx.get(f"{self._base_url}/v1/models", timeout=self._config.connect_timeout_seconds)
            if resp.status_code != 200:
                return LocalAIAvailability(
                    available=False, provider_id=self.id, provider_name=self.display_name,
                    runs_offline=True, requires_model_file=True, status="runtime_missing",
                    detail="llama.cpp 서버가 응답하지 않습니다",
                )
            data = resp.json()
            models = data.get("data", [])
            self._model_name = models[0].get("id", "unknown") if models else None
            return LocalAIAvailability(
                available=True, provider_id=self.id, provider_name=self.display_name,
                model_name=self._model_name, runs_offline=True, requires_model_file=True,
                status="ready",
                detail=f"llama.cpp 연결됨: {self._model_name or '모델'}",
            )
        except httpx.ConnectError:
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=True, requires_model_file=True, status="runtime_missing",
                detail="llama.cpp 서버에 연결할 수 없습니다",
            )
        except Exception as exc:
            return LocalAIAvailability(
                available=False, provider_id=self.id, provider_name=self.display_name,
                runs_offline=True, requires_model_file=True, status="error",
                detail=f"llama.cpp 확인 중 오류: {exc}",
            )

    def analyze_response(self, request: LocalAIRequest) -> LocalAIResult:
        started = time.perf_counter()
        return LocalAIResult(
            provider_id=self.id, provider_name=self.display_name,
            model_name=self._model_name, runs_offline=True,
            valid=True, confidence=0.3,
            latency_ms=int((time.perf_counter() - started) * 1000),
            warnings=["llama.cpp 분석은 아직 구현되지 않았습니다"],
            summary="llama.cpp provider is detected but analysis function is not yet implemented.",
        )


# ---------------------------------------------------------------------------
# LocalAIManager — orchestrates provider detection and selection
# ---------------------------------------------------------------------------

class LocalAIManager:
    def __init__(self, ollama_config: LocalAIProviderConfig | None = None):
        self._config = ollama_config or LocalAIProviderConfig.from_env()
        self._providers: list[LocalAIProvider] = [
            RuleLocalAIProvider(),
            OllamaLocalProvider(config=self._config),
            LlamaCppLocalProvider(config=self._config),
        ]
        self._selected: LocalAIProvider | None = None
        self._status_cache: dict[str, LocalAIAvailability] = {}
        self._last_probe: float = 0.0

    @property
    def providers(self) -> list[LocalAIProvider]:
        return list(self._providers)

    @property
    def ollama(self) -> OllamaLocalProvider | None:
        for p in self._providers:
            if isinstance(p, OllamaLocalProvider):
                return p
        return None

    def probe_all(self, force: bool = False) -> dict[str, LocalAIAvailability]:
        now = time.time()
        if not force and self._status_cache and (now - self._last_probe) < 30:
            return dict(self._status_cache)
        results: dict[str, LocalAIAvailability] = {}
        for p in self._providers:
            results[p.id] = p.is_available()
        self._status_cache = results
        self._last_probe = now
        return results

    def select_provider(self) -> LocalAIProvider:
        statuses = self.probe_all()
        if statuses.get("ollama", LocalAIAvailability(False)).available:
            self._selected = self.ollama
            return self._selected
        if statuses.get("llamacpp", LocalAIAvailability(False)).available:
            self._selected = LlamaCppLocalProvider(config=self._config)
            return self._selected
        self._selected = RuleLocalAIProvider()
        return self._selected

    def get_selected(self) -> LocalAIProvider:
        if self._selected is None:
            return self.select_provider()
        return self._selected

    def warmup_ollama(self) -> dict[str, Any]:
        ollama = self.ollama
        if ollama is None:
            return {"ok": False, "reason": "Ollama provider가 없습니다"}
        avail = ollama.is_available()
        if not avail.available:
            return {"ok": False, "reason": avail.detail}
        return ollama.warmup()

    def status_summary(self) -> dict[str, Any]:
        """Return a user-friendly status summary for the API endpoint."""
        probe = self.probe_all()
        rule_status = probe.get("rule", LocalAIAvailability(False, status="unavailable"))
        ollama_status = probe.get("ollama", LocalAIAvailability(False, status="unavailable"))
        llamacpp_status = probe.get("llamacpp", LocalAIAvailability(False, status="unavailable"))

        local_llm: dict[str, Any] | None = None
        if ollama_status.available:
            ollama = self.ollama
            recs = ollama.model_recommendations() if ollama else {}
            local_llm = {
                "provider_id": ollama_status.provider_id,
                "provider_name": ollama_status.provider_name,
                "model_name": ollama_status.model_name,
                "status": ollama_status.status,
                "detail": ollama_status.detail,
                "performance": ollama_status.performance,
                "recommendations": recs.get("recommendations", []),
                "warm": recs.get("warm", False),
            }
        elif llamacpp_status.available:
            local_llm = {
                "provider_id": llamacpp_status.provider_id,
                "provider_name": llamacpp_status.provider_name,
                "model_name": llamacpp_status.model_name,
                "status": llamacpp_status.status,
                "detail": llamacpp_status.detail,
                "performance": {},
                "recommendations": [],
                "warm": False,
            }

        return {
            "offline_core": {
                "available": True,
                "label": "기본 분석",
                "description": "기기 안에서 바로 분석해요. 인터넷이나 API 키가 필요하지 않아요.",
                "status": "ready",
            },
            "local_ai": {
                "available": local_llm is not None,
                "label": "로컬 AI 분석",
                "description": "설치된 로컬 AI 모델을 사용해 더 자세한 표현 개선을 제안해요. 답안은 기기 밖으로 나가지 않아요.",
                "status": local_llm["status"] if local_llm else "unavailable",
                "model": local_llm,
                "providers_checked": {
                    "rule": {"status": rule_status.status, "detail": rule_status.detail},
                    "ollama": {"status": ollama_status.status, "detail": ollama_status.detail},
                    "llamacpp": {"status": llamacpp_status.status, "detail": llamacpp_status.detail},
                },
            },
        }

    def analyze(self, essay_text: str, prompt_type: str = "academic_discussion", prompt_text: str = "") -> LocalAIResult:
        provider = self.get_selected()
        request = LocalAIRequest(essay_text=essay_text, prompt_type=prompt_type, prompt_text=prompt_text)
        result = provider.analyze_response(request)
        return result


# Singleton
_local_ai_manager: LocalAIManager | None = None


def get_local_ai_manager() -> LocalAIManager:
    global _local_ai_manager
    if _local_ai_manager is None:
        _local_ai_manager = LocalAIManager()
    return _local_ai_manager
