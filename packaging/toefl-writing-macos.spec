# -*- mode: python ; coding: utf-8 -*-
"""PyInstaller one-dir spec — macOS 내부 알파.

빌드: `scripts/build_macos.sh` (권장) 또는
  .venv/bin/pyinstaller packaging/toefl-writing-macos.spec --clean --noconfirm
프로젝트 루트에서 실행해야 한다 (상대경로 기준).

포함: static(UI), app/*, desktop/* 비즈니스 로직 + 런처, 라이선스.
제외: .env, 실제 DB, 전문가 원본 데이터, 테스트, 개발 로그, Git 메타데이터
  (Analysis.datas에 명시적으로 나열한 항목만 포함되므로 별도 제외 처리가
  필요 없다 — "포함 안 한 것 = 제외됨"이 기본 동작이다).
"""

import sys
from pathlib import Path

PROJECT_ROOT = Path(SPECPATH).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT))

from app.version import APP_BUNDLE_NAME, APP_DISPLAY_NAME, APP_VERSION, BUNDLE_IDENTIFIER  # noqa: E402

block_cipher = None

# static/ 전체가 아니라 앱이 실제로 서빙하는 파일만 명시적으로 나열한다.
# static/logo.png, screenshot_*.png는 README.md에서 GitHub raw URL로만
# 참조되는 0바이트 placeholder이며 앱 UI 어디에서도 로드하지 않으므로
# 패키징 산출물에 포함하지 않는다 (섹션 17 "무분별한 전체 폴더 포함을 피하라").
_STATIC_RUNTIME_FILES = ["index.html", "app.js", "styles.css"]
datas = [
    (str(PROJECT_ROOT / "static" / name), "static")
    for name in _STATIC_RUNTIME_FILES
    if (PROJECT_ROOT / "static" / name).exists()
]
license_path = PROJECT_ROOT / "LICENSE"
if license_path.exists():
    datas.append((str(license_path), "."))

hiddenimports = [
    "uvicorn.logging",
    "uvicorn.loops",
    "uvicorn.loops.auto",
    "uvicorn.protocols",
    "uvicorn.protocols.http",
    "uvicorn.protocols.http.auto",
    "uvicorn.protocols.websockets",
    "uvicorn.protocols.websockets.auto",
    "uvicorn.lifespan",
    "uvicorn.lifespan.on",
    "webview.platforms.cocoa",
]

a = Analysis(
    [str(PROJECT_ROOT / "packaging" / "entry_point.py")],
    pathex=[str(PROJECT_ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[str(PROJECT_ROOT / "packaging" / "hooks")],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["tests", "scripts"],
    noarchive=False,
    cipher=block_cipher,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name=APP_BUNDLE_NAME,
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name=APP_BUNDLE_NAME,
)

app = BUNDLE(
    coll,
    name=f"{APP_BUNDLE_NAME}.app",
    icon=None,  # 아이콘(.icns) 미준비 — 향후 packaging/resources/app.icns로 교체
    bundle_identifier=BUNDLE_IDENTIFIER,
    info_plist={
        "CFBundleName": APP_BUNDLE_NAME,
        "CFBundleDisplayName": APP_DISPLAY_NAME,
        "CFBundleShortVersionString": APP_VERSION,
        "CFBundleVersion": APP_VERSION,
        "LSMinimumSystemVersion": "12.0",
        "NSHighResolutionCapable": True,
        "NSHumanReadableCopyright": "© 2026 leekangmin",
        # 이 앱은 loopback(127.0.0.1) 전용 서버만 열고 외부 네트워크를
        # 사용하지 않는다 (Cloud AI 활성화 시에만 아웃바운드 HTTPS 호출).
        "com.leekangmin.toeflwriting.offline-core": True,
    },
)
