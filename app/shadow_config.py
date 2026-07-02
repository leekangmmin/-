"""AI shadow mode 설정 — 서버 환경변수에서만 읽는다.

이 설정은 사용자에게 보이는 채점(app/ai_mode.py, DB app_settings 기반)과
완전히 분리된 별도 경로다. shadow mode는 관리자/운영자가 서버 환경변수로만
켤 수 있고, 일반 사용자는 이 설정에 접근하거나 변경할 수 없다.

환경변수:
  TOEFL_SHADOW_ENABLED          "1"이어야 활성화 (기본: 비활성화)
  TOEFL_SHADOW_PROVIDER         "claude" | "mock" (기본: "mock")
  ANTHROPIC_API_KEY             Claude API 키 (서버 전용, 클라이언트에 노출 안 됨)
  TOEFL_SHADOW_MODEL            모델명 (기본: "claude-3-5-sonnet-latest")
  TOEFL_SHADOW_TIMEOUT_SECONDS  요청당 timeout 초 (기본: 20)
  TOEFL_SHADOW_MAX_RETRIES      실패 시 재시도 횟수 (기본: 2)
"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class ShadowConfig:
    enabled: bool
    provider: str
    anthropic_api_key: str
    model: str
    timeout_seconds: float
    max_retries: int


def load_shadow_config() -> ShadowConfig:
    return ShadowConfig(
        enabled=os.getenv("TOEFL_SHADOW_ENABLED", "0").strip() == "1",
        provider=os.getenv("TOEFL_SHADOW_PROVIDER", "mock").strip().lower() or "mock",
        anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", "").strip(),
        model=os.getenv("TOEFL_SHADOW_MODEL", "claude-3-5-sonnet-latest").strip() or "claude-3-5-sonnet-latest",
        timeout_seconds=float(os.getenv("TOEFL_SHADOW_TIMEOUT_SECONDS", "20") or "20"),
        max_retries=max(0, int(os.getenv("TOEFL_SHADOW_MAX_RETRIES", "2") or "2")),
    )


@dataclass(frozen=True)
class ProviderAvailability:
    available: bool
    reason_code: str  # "ok" | "shadow_disabled" | "missing_api_key" | "unknown_provider"
    detail: str = ""
