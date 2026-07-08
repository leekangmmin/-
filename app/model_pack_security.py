"""Security verification for local GGUF model files.

Performs header validation, size sanity checks, and optional SHA-256 checksum
verification. Also provides filesystem scanning and loopback-URL detection
utilities.
"""

from __future__ import annotations

import hashlib
import ipaddress
import logging
from pathlib import Path
from urllib.parse import urlparse

logger = logging.getLogger("toefl.model_pack_security")

_GGUF_MAGIC = b"GGUF"
_MAX_MODEL_BYTES = 20 * 1024 * 1024 * 1024  # 20 GB
_MIN_MODEL_BYTES = 50 * 1024 * 1024  # 50 MB (scan threshold)
_MODEL_EXTENSIONS = {".gguf", ".bin", ".safetensors"}


def verify_gguf_file(path: Path, expected_checksum: str | None = None) -> dict:
    errors: list[str] = []
    file_size = 0
    header_info: dict = {}

    try:
        file_size = path.stat().st_size
    except OSError as exc:
        return {
            "valid": False,
            "errors": [f"cannot_stat: {exc}"],
            "file_size": 0,
            "header_info": {},
        }

    if file_size == 0:
        errors.append("file_is_empty")

    if file_size > _MAX_MODEL_BYTES:
        errors.append(f"file_too_large: {file_size} > {_MAX_MODEL_BYTES}")

    try:
        with open(path, "rb") as f:
            magic = f.read(4)
    except OSError as exc:
        errors.append(f"cannot_read: {exc}")
        return {
            "valid": False,
            "errors": errors,
            "file_size": file_size,
            "header_info": {},
        }

    if magic != _GGUF_MAGIC:
        errors.append(
            f"invalid_magic: expected {_GGUF_MAGIC!r}, got {magic!r}"
        )
    else:
        header_info["magic"] = "GGUF"
        header_info["magic_valid"] = True

    if expected_checksum:
        try:
            sha = hashlib.sha256()
            with open(path, "rb") as f:
                for chunk in iter(lambda: f.read(64 * 1024), b""):
                    sha.update(chunk)
            actual = sha.hexdigest()
            if actual.lower() != expected_checksum.lower():
                errors.append(
                    f"checksum_mismatch: expected {expected_checksum[:16]}..., "
                    f"got {actual[:16]}..."
                )
            else:
                header_info["checksum_valid"] = True
        except OSError as exc:
            errors.append(f"checksum_read_error: {exc}")

    return {
        "valid": len(errors) == 0 and file_size > 0,
        "errors": errors,
        "file_size": file_size,
        "header_info": header_info,
    }


def scan_for_model_files(directory: Path) -> list[Path]:
    found: list[Path] = []
    if not directory.is_dir():
        return found

    for ext in _MODEL_EXTENSIONS:
        try:
            for candidate in directory.rglob(f"*{ext}"):
                try:
                    if candidate.stat().st_size >= _MIN_MODEL_BYTES:
                        found.append(candidate)
                except OSError:
                    pass
        except OSError:
            pass

    return sorted(set(found))


_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_LOOPBACK_NETS = (
    ipaddress.ip_network("127.0.0.0/8"),
    ipaddress.ip_network("::1/128"),
)


def is_loopback_url(url: str) -> bool:
    try:
        parsed = urlparse(url)
    except Exception:
        return False

    hostname = parsed.hostname
    if hostname is None:
        return False

    if hostname.lower() in _LOOPBACK_HOSTS:
        return True

    try:
        addr = ipaddress.ip_address(hostname)
        for net in _LOOPBACK_NETS:
            if addr in net:
                return True
    except ValueError:
        pass

    return False
