"""Built-in model registry for local GGUF model packs.

Lists known-compatible models with metadata (license, hardware requirements,
quality/risk notes). This registry is the single source of truth for what the
manager can track — no model binary is bundled or downloaded automatically.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class ModelInfo:
    model_id: str
    family: str
    parameter_count: str  # "7.6B"
    format: str  # "GGUF"
    quantization: str  # "Q4_K_M"
    license_name: str
    commercial_use: bool
    redistribution_allowed: bool
    download_size_bytes: int
    estimated_ram_min_bytes: int
    mac_apple_silicon_supported: bool
    mac_intel_supported: bool
    windows_supported: bool
    quality_risk: str
    moderation_risk: str
    source_url: str | None = None
    checksum_sha256: str | None = None
    recommended_role: str = "feedback"  # grammar | paraphrase | feedback | scoring


BUILTIN_REGISTRY: list[ModelInfo] = [
    ModelInfo(
        model_id="qwen2.5-7b-instruct-q4km",
        family="Qwen 2.5",
        parameter_count="7.6B",
        format="GGUF",
        quantization="Q4_K_M",
        license_name="Apache 2.0",
        commercial_use=True,
        redistribution_allowed=True,
        download_size_bytes=4_683_000_000,
        estimated_ram_min_bytes=8_000_000_000,
        mac_apple_silicon_supported=True,
        mac_intel_supported=True,
        windows_supported=True,
        quality_risk="중간 — TOEFL 채점 정확도는 전문가 검증 전",
        moderation_risk="낮음 — Apache 2.0, Chinese model but English-trained",
        recommended_role="feedback",
    ),
    ModelInfo(
        model_id="mistral-7b-instruct-v0.3-q4km",
        family="Mistral",
        parameter_count="7B",
        format="GGUF",
        quantization="Q4_K_M",
        license_name="Apache 2.0",
        commercial_use=True,
        redistribution_allowed=True,
        download_size_bytes=4_370_000_000,
        estimated_ram_min_bytes=8_000_000_000,
        mac_apple_silicon_supported=True,
        mac_intel_supported=True,
        windows_supported=True,
        quality_risk="중간 — TOEFL 채점 정확도는 전문가 검증 전",
        moderation_risk="낮음 — Apache 2.0, English-focused",
        recommended_role="feedback",
    ),
]
