#!/bin/zsh
# macOS 내부 릴리스 후보(.app) 빌드 스크립트 (PyInstaller one-dir).
#
# 사용자 기존 개발 venv에 의존하지 않는다 — 매 실행마다 전용 build venv를
# 새로 만든다 (.build-venv, 프로젝트 개발용 .venv와 분리).
#
# 이 스크립트는 unsigned/ad-hoc signed internal release candidate .app을
# 생성한다. Developer ID codesign/공증은 인증서가 있을 때 별도로 수행한다
# (scripts/sign_and_notarize.sh, docs/signing-and-notarization.md 참고).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BUILD_VENV="$PROJECT_DIR/.build-venv"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"

echo "==> [1/14] clean build directory"
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "==> [2/14] build venv 확인 또는 생성"
if [ ! -x "$BUILD_VENV/bin/python" ]; then
  python3.11 -m venv "$BUILD_VENV"
fi
PY="$BUILD_VENV/bin/python"

echo "==> [3/14] 의존성 설치"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$PROJECT_DIR/requirements.txt" pyinstaller pytest >/dev/null

echo "==> [4/14] compile (py_compile)"
"$PY" -m py_compile app/*.py desktop/*.py scripts/*.py

echo "==> [5/14] tests"
"$PY" -m pytest tests/ -q

echo "==> [6/14] harness (품질 회귀 게이트)"
PYTHONPATH="$PROJECT_DIR" "$PY" -m tests.eval_harness

echo "==> [7/14] 앱 아이콘 확인 또는 생성"
if [ ! -f "$PROJECT_DIR/packaging/resources/app.icns" ]; then
  echo "    아이콘이 없어 생성합니다..."
  "$PY" "$PROJECT_DIR/scripts/generate_app_icon.py"
else
  echo "    packaging/resources/app.icns 존재"
fi

echo "==> [8/14] PyInstaller 빌드"
"$PY" -m PyInstaller packaging/toefl-writing-macos.spec --clean --noconfirm --distpath "$DIST_DIR" --workpath "$BUILD_DIR"

APP_PATH=$("$PY" -c "from app.version import APP_BUNDLE_NAME; print(APP_BUNDLE_NAME)")
APP_BUNDLE="$DIST_DIR/${APP_PATH}.app"

if [ ! -d "$APP_BUNDLE" ]; then
  echo "[ERROR] 빌드 산출물이 없습니다: $APP_BUNDLE"
  exit 1
fi

echo "==> [9/14] Info.plist 검증"
"$PY" "$PROJECT_DIR/scripts/verify_info_plist.py" "$APP_BUNDLE"

echo "==> [10/14] ad-hoc 서명 (Developer ID 인증서 없음 — 로컬 실행용)"
codesign --force --deep --sign - "$APP_BUNDLE" 2>/dev/null && echo "    ad-hoc 서명 완료" || echo "    [WARN] ad-hoc 서명 실패 (codesign 미사용 환경)"

echo "==> [11/14] artifact security scan"
"$PY" "$PROJECT_DIR/scripts/scan_artifact_security.py" "$APP_BUNDLE"

echo "==> [12/14] packaged app smoke test"
"$PY" "$PROJECT_DIR/scripts/packaged_app_smoke_test.py" "$APP_BUNDLE"

echo "==> [13/14] update migration test (구버전 데이터 보존)"
"$PY" "$PROJECT_DIR/scripts/update_migration_test.py" "$APP_BUNDLE"

echo "==> [14/14] release manifest + checksum + zip"
"$PY" "$PROJECT_DIR/scripts/make_release_manifest.py" "$APP_BUNDLE" --signing-status "ad-hoc signed (Developer ID pending)"

echo ""
echo "빌드 산출물: $APP_BUNDLE"
du -sh "$APP_BUNDLE"
echo ""
echo "상태: internal release candidate / ad-hoc signed / Developer ID signing pending / notarization pending / external distribution prohibited"
