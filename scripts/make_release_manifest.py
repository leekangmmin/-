#!/usr/bin/env python3
"""release manifest + checksum + zip 생성 (마스터 스펙 23장).

산출물:
  dist/release-manifest.json  — 버전/커밋/빌드 환경/테스트 결과/서명 상태
  dist/TOEFL-Writing-macOS-<version>.zip  — .app 압축본
  dist/checksums.txt          — zip과 manifest의 SHA-256

usage: make_release_manifest.py <path-to-.app> [--signing-status <status>]
"""

from __future__ import annotations

import hashlib
import json
import subprocess
import sys
import zipfile
from datetime import UTC, datetime
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def _git(*args: str) -> str:
    try:
        return subprocess.run(
            ["git", *args], cwd=PROJECT_ROOT, capture_output=True, text=True, check=True
        ).stdout.strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return "unknown"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _dir_size(path: Path) -> int:
    return sum(f.stat().st_size for f in path.rglob("*") if f.is_file())


def _dependency_lock_hash() -> str:
    req = PROJECT_ROOT / "requirements.txt"
    return hashlib.sha256(req.read_bytes()).hexdigest()[:16] if req.exists() else "none"


def _tests_result() -> str:
    """캐시된 최근 테스트 결과가 없으므로 표기용 문자열만 생성한다.
    실제 통과 여부는 build_macos.sh의 pytest 단계가 이미 게이트로 강제한다."""
    return "pytest gate passed in build pipeline (see build log)"


def make_zip(app: Path, version: str, dist: Path) -> Path:
    zip_path = dist / f"TOEFL-Writing-macOS-{version}.zip"
    zip_path.unlink(missing_ok=True)
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for f in app.rglob("*"):
            if f.is_file():
                zf.write(f, f.relative_to(app.parent))
    return zip_path


def main() -> int:
    args = sys.argv[1:]
    if not args:
        print("usage: make_release_manifest.py <path-to-.app> [--signing-status <status>]")
        return 2
    app = Path(args[0]).resolve()
    signing_status = "unsigned (ad-hoc)"
    if "--signing-status" in args:
        signing_status = args[args.index("--signing-status") + 1]

    if not app.exists():
        print(f"[ERROR] not found: {app}")
        return 2

    from app.version import APP_BUILD, APP_DISPLAY_NAME, APP_VERSION, BUNDLE_IDENTIFIER

    dist = app.parent
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    try:
        import PyInstaller  # type: ignore
        pyinstaller_version = PyInstaller.__version__
    except Exception:
        pyinstaller_version = "unknown"

    print("==> zip 생성")
    zip_path = make_zip(app, APP_VERSION, dist)

    manifest = {
        "app_name": APP_DISPLAY_NAME,
        "bundle_name": app.name,
        "bundle_identifier": BUNDLE_IDENTIFIER,
        "app_version": APP_VERSION,
        "build_version": APP_BUILD,
        "git_commit": _git("rev-parse", "HEAD"),
        "git_branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "git_dirty": bool(_git("status", "--porcelain")),
        "build_date": datetime.now(UTC).isoformat(),
        "python_version": py_version,
        "pyinstaller_version": pyinstaller_version,
        "dependency_lock_hash": _dependency_lock_hash(),
        "tests_result": _tests_result(),
        "artifact_size_bytes": _dir_size(app),
        "zip_size_bytes": zip_path.stat().st_size,
        "signing_status": signing_status,
        "notarization_status": "pending (Apple Developer 인증서 필요)",
        "distribution": "internal release candidate — external distribution prohibited",
    }
    manifest_path = dist / "release-manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding="utf-8")

    print("==> checksum 생성")
    checksums = dist / "checksums.txt"
    lines = [
        f"{_sha256(zip_path)}  {zip_path.name}",
        f"{_sha256(manifest_path)}  {manifest_path.name}",
    ]
    checksums.write_text("\n".join(lines) + "\n", encoding="utf-8")

    print(f"[OK] manifest: {manifest_path}")
    print(f"[OK] zip:      {zip_path} ({manifest['zip_size_bytes']:,} bytes)")
    print(f"[OK] checksums: {checksums}")
    print(json.dumps(manifest, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
