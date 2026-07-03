#!/bin/zsh
# 내부 테스트용 DMG 생성 스크립트.
#
# 중요: 서명·공증되지 않은 앱을 DMG로 만들었다고 외부 배포 가능하다고
# 주장하지 않는다. 이 DMG는 내부 테스트 전달용이며, 받는 사람은 Gatekeeper
# 경고를 우회해야 실행할 수 있다 (external distribution prohibited).
#
# DMG에는 .app과 Applications 심볼릭 링크만 포함한다 — README/테스트/로그/
# 소스/키/.env는 포함하지 않는다 (마스터 스펙 25장).
set -euo pipefail

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
DIST_DIR="$PROJECT_DIR/dist"

APP_PATH=$(find "$DIST_DIR" -maxdepth 1 -name "*.app" | head -1)
if [ -z "$APP_PATH" ] || [ ! -d "$APP_PATH" ]; then
  echo "[ERROR] dist/에서 .app을 찾을 수 없습니다. 먼저 ./scripts/build_macos.sh를 실행하세요."
  exit 1
fi

VERSION=$("$PROJECT_DIR/.build-venv/bin/python" -c "from app.version import APP_VERSION; print(APP_VERSION)" 2>/dev/null \
  || "$PROJECT_DIR/.venv/bin/python" -c "from app.version import APP_VERSION; print(APP_VERSION)")
DMG_NAME="TOEFL-Writing-macOS-${VERSION}.dmg"
DMG_PATH="$DIST_DIR/$DMG_NAME"

STAGING=$(mktemp -d)
trap 'rm -rf "$STAGING"' EXIT

echo "==> DMG 스테이징 구성 (.app + Applications 링크만)"
cp -R "$APP_PATH" "$STAGING/"
ln -s /Applications "$STAGING/Applications"

echo "==> DMG 생성"
rm -f "$DMG_PATH"
hdiutil create -volname "TOEFL Writing $VERSION" \
  -srcfolder "$STAGING" \
  -ov -format UDZO \
  "$DMG_PATH"

echo ""
echo "[OK] $DMG_PATH"
ls -lh "$DMG_PATH"
echo ""
echo "상태: 내부 테스트용 DMG / unsigned 또는 ad-hoc signed / external distribution prohibited"
echo "      받는 사람은 Gatekeeper 경고를 우회해야 실행 가능합니다 (정식 배포 불가)."
