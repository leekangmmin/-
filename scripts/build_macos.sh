#!/bin/zsh
# macOS 내부 알파 .app 빌드 스크립트 (PyInstaller one-dir).
#
# 사용자 기존 개발 venv에 의존하지 않는다 — 매 실행마다 전용 build venv를
# 새로 만든다 (.build-venv, 프로젝트 개발용 .venv와 분리).
#
# 이 스크립트는 unsigned internal alpha .app만 생성한다. codesign/공증은
# Apple Developer 인증서가 있을 때 별도로 수행한다 (docs/macos-build.md 참고).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJECT_DIR"

BUILD_VENV="$PROJECT_DIR/.build-venv"
DIST_DIR="$PROJECT_DIR/dist"
BUILD_DIR="$PROJECT_DIR/build"

echo "==> [1/9] clean build directory"
rm -rf "$BUILD_DIR" "$DIST_DIR"

echo "==> [2/9] build venv 확인 또는 생성"
if [ ! -x "$BUILD_VENV/bin/python" ]; then
  python3.11 -m venv "$BUILD_VENV"
fi
PY="$BUILD_VENV/bin/python"

echo "==> [3/9] 의존성 설치"
"$PY" -m pip install --upgrade pip >/dev/null
"$PY" -m pip install -r "$PROJECT_DIR/requirements.txt" pyinstaller >/dev/null

echo "==> [4/9] compile (py_compile)"
"$PY" -m py_compile app/*.py desktop/*.py scripts/*.py

echo "==> [5/9] tests"
"$PY" -m pip install pytest >/dev/null
"$PY" -m pytest tests/ -q

echo "==> [6/9] harness (품질 회귀 게이트)"
PYTHONPATH="$PROJECT_DIR" "$PY" -m tests.eval_harness

echo "==> [7/9] PyInstaller 빌드"
"$PY" -m PyInstaller packaging/toefl-writing-macos.spec --clean --noconfirm --distpath "$DIST_DIR" --workpath "$BUILD_DIR"

APP_PATH=$("$PY" -c "from app.version import APP_BUNDLE_NAME; print(APP_BUNDLE_NAME)")
APP_BUNDLE="$DIST_DIR/${APP_PATH}.app"

if [ ! -d "$APP_BUNDLE" ]; then
  echo "[ERROR] 빌드 산출물이 없습니다: $APP_BUNDLE"
  exit 1
fi

echo "==> [8/9] package smoke test (health check)"
"$PY" "$PROJECT_DIR/scripts/packaged_app_smoke_test.py" "$APP_BUNDLE"

echo "==> [9/9] artifact summary"
echo "빌드 산출물: $APP_BUNDLE"
du -sh "$APP_BUNDLE"
find "$APP_BUNDLE" -maxdepth 3 -type d | sort
echo ""
echo "상태: package build complete / unsigned internal alpha / codesign pending / notarization pending / external distribution prohibited"
