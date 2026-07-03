#!/usr/bin/env python3
"""Info.plist 검증 — 버전/식별자/아이콘이 app.version 단일 출처와 일치하는지 확인.

usage: verify_info_plist.py <path-to-.app>
"""

from __future__ import annotations

import plistlib
import sys
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: verify_info_plist.py <path-to-.app>")
        return 2
    app = Path(sys.argv[1]).resolve()
    plist_path = app / "Contents" / "Info.plist"
    if not plist_path.exists():
        print(f"[ERROR] Info.plist not found: {plist_path}")
        return 1

    from app.version import APP_VERSION, BUNDLE_IDENTIFIER

    with open(plist_path, "rb") as f:
        plist = plistlib.load(f)

    errors: list[str] = []
    checks = {
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "CFBundleIdentifier": BUNDLE_IDENTIFIER,
    }
    for key, expected in checks.items():
        actual = plist.get(key)
        if actual != expected:
            errors.append(f"{key}: 기대 {expected!r}, 실제 {actual!r}")

    # 아이콘 참조가 있으면 실제 파일이 번들에 존재해야 한다
    icon_name = plist.get("CFBundleIconFile")
    if icon_name:
        icon_file = icon_name if icon_name.endswith(".icns") else f"{icon_name}.icns"
        if not (app / "Contents" / "Resources" / icon_file).exists():
            errors.append(f"CFBundleIconFile={icon_name} 이지만 Resources/{icon_file} 없음")
    else:
        errors.append("CFBundleIconFile 미설정 (앱 아이콘 없음)")

    if not plist.get("NSHighResolutionCapable"):
        errors.append("NSHighResolutionCapable 미설정")

    if errors:
        print(f"[FAIL] Info.plist 검증 {len(errors)}건:")
        for e in errors:
            print(f"  - {e}")
        return 1

    print(f"[PASS] Info.plist — version={APP_VERSION}, id={BUNDLE_IDENTIFIER}, icon={icon_name}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
