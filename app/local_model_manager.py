"""Local model pack manager — tracks installation state via JSON files.

No model binaries are downloaded or bundled. This module only manages metadata
and filesystem state for GGUF model files that the user may place manually
(or via a future download UI layer).
"""

from __future__ import annotations

import json
import logging
import platform
import sys
from pathlib import Path
from typing import Literal

from app.local_model_registry import BUILTIN_REGISTRY, ModelInfo
from app.paths import models_dir

logger = logging.getLogger("toefl.local_model_manager")

ModelState = Literal[
    "not_supported",
    "not_installed",
    "license_required",
    "download_available",
    "downloading",
    "checksum_failed",
    "installed",
    "ready",
    "incompatible_hardware",
    "low_memory_warning",
    "removed",
    "error",
]

_METADATA_VERSION = 1


def _registry_by_id() -> dict[str, ModelInfo]:
    return {m.model_id: m for m in BUILTIN_REGISTRY}


def _state_path(models_root: Path) -> Path:
    return models_root / "model_state.json"


def _license_path(models_root: Path) -> Path:
    return models_root / "licenses.json"


def _read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return {}


def _write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")


def _guess_gguf_filename(model_id: str) -> str:
    return f"{model_id}.gguf"


class LocalModelManager:
    def __init__(self, models_dir_path: Path | None = None):
        self._root = models_dir_path or models_dir()
        self._root.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Registry access
    # ------------------------------------------------------------------

    def get_registry(self) -> list[ModelInfo]:
        return list(BUILTIN_REGISTRY)

    def get_info(self, model_id: str) -> ModelInfo | None:
        return _registry_by_id().get(model_id)

    # ------------------------------------------------------------------
    # State query
    # ------------------------------------------------------------------

    def get_model_state(self, model_id: str) -> ModelState:
        info = self.get_info(model_id)
        if info is None:
            return "not_supported"

        hw = self.check_hardware_compatibility(model_id)
        if not hw["compatible"]:
            return "incompatible_hardware"

        state_data = _read_json(_state_path(self._root)).get(model_id)
        if state_data is None:
            return "not_installed"

        tracked_state = state_data.get("state")
        if tracked_state in {"downloading", "error", "checksum_failed", "removed"}:
            return tracked_state

        install_path = self.get_install_path(model_id)
        if not install_path.exists():
            return "not_installed"

        if not self.has_accepted_license(model_id):
            return "license_required"

        return "ready"

    def is_model_installed(self, model_id: str) -> bool:
        state = self.get_model_state(model_id)
        return state in {"installed", "ready", "low_memory_warning"}

    def get_installed_models(self) -> list[dict]:
        result: list[dict] = []
        for info in BUILTIN_REGISTRY:
            if self.is_model_installed(info.model_id):
                install_path = self.get_install_path(info.model_id)
                result.append(
                    {
                        "model_id": info.model_id,
                        "family": info.family,
                        "parameter_count": info.parameter_count,
                        "quantization": info.quantization,
                        "size_bytes": install_path.stat().st_size
                        if install_path.exists()
                        else 0,
                        "state": self.get_model_state(info.model_id),
                        "recommended_role": info.recommended_role,
                    }
                )
        return result

    def get_install_path(self, model_id: str) -> Path:
        return self._root / _guess_gguf_filename(model_id)

    # ------------------------------------------------------------------
    # Checksum
    # ------------------------------------------------------------------

    def verify_checksum(self, model_id: str) -> bool:
        import hashlib

        info = self.get_info(model_id)
        if info is None or info.checksum_sha256 is None:
            return False

        install_path = self.get_install_path(model_id)
        if not install_path.exists():
            return False

        try:
            sha = hashlib.sha256()
            with open(install_path, "rb") as f:
                for chunk in iter(lambda: f.read(64 * 1024), b""):
                    sha.update(chunk)
            return sha.hexdigest() == info.checksum_sha256
        except OSError:
            return False

    # ------------------------------------------------------------------
    # Storage accounting
    # ------------------------------------------------------------------

    def get_total_installed_size(self) -> int:
        total = 0
        for info in BUILTIN_REGISTRY:
            path = self.get_install_path(info.model_id)
            if path.exists():
                try:
                    total += path.stat().st_size
                except OSError:
                    pass
        return total

    # ------------------------------------------------------------------
    # Install / uninstall
    # ------------------------------------------------------------------

    def uninstall_model(self, model_id: str) -> None:
        info = self.get_info(model_id)
        if info is None:
            raise ValueError(f"Unknown model: {model_id}")

        install_path = self.get_install_path(model_id)
        if install_path.exists():
            install_path.unlink()

        self._set_state(model_id, "removed")
        logger.info("Uninstalled model %s", model_id)

    # ------------------------------------------------------------------
    # License tracking
    # ------------------------------------------------------------------

    def accept_license(self, model_id: str) -> None:
        info = self.get_info(model_id)
        if info is None:
            raise ValueError(f"Unknown model: {model_id}")

        licenses = _read_json(_license_path(self._root))
        licenses[model_id] = {
            "accepted": True,
            "license_name": info.license_name,
            "accepted_at": None,  # placeholder for timestamp if needed
        }
        _write_json(_license_path(self._root), licenses)

    def has_accepted_license(self, model_id: str) -> bool:
        licenses = _read_json(_license_path(self._root))
        entry = licenses.get(model_id)
        if entry is None:
            return False
        return bool(entry.get("accepted"))

    # ------------------------------------------------------------------
    # Hardware compatibility
    # ------------------------------------------------------------------

    def check_hardware_compatibility(self, model_id: str) -> dict:
        info = self.get_info(model_id)
        if info is None:
            return {"compatible": False, "reason": "unknown_model"}

        system = platform.system()
        if system == "Darwin":
            is_apple_silicon = platform.processor() != "i386" and sys.platform == "darwin"
            if is_apple_silicon and not info.mac_apple_silicon_supported:
                return {"compatible": False, "reason": "not_supported_on_apple_silicon"}
            if not is_apple_silicon and not info.mac_intel_supported:
                return {"compatible": False, "reason": "not_supported_on_intel_mac"}
        elif system == "Windows":
            if not info.windows_supported:
                return {"compatible": False, "reason": "not_supported_on_windows"}
        else:
            # Unknown platform: be conservative, allow user to proceed
            pass

        return {
            "compatible": True,
            "estimated_ram_min_bytes": info.estimated_ram_min_bytes,
        }

    # ------------------------------------------------------------------
    # Status summary
    # ------------------------------------------------------------------

    def status_summary(self) -> dict:
        installed = self.get_installed_models()
        return {
            "models_dir": str(self._root),
            "registry_count": len(BUILTIN_REGISTRY),
            "installed_count": len(installed),
            "installed": installed,
            "total_size_bytes": self.get_total_installed_size(),
        }

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _set_state(self, model_id: str, state: str) -> None:
        state_file = _state_path(self._root)
        data = _read_json(state_file)
        data[model_id] = {"state": state, "version": _METADATA_VERSION}
        _write_json(state_file, data)
