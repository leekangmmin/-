#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
APP_NAME="토플첨삭기 by이강민.app"
APP_PATH="$PROJECT_DIR/$APP_NAME"
STAGING_DIR="$PROJECT_DIR/dist_macos/staging"
DIST_DIR="$PROJECT_DIR/dist_macos"
DMG_PATH="$DIST_DIR/TOEFLScorer-macOS.dmg"

if [ ! -d "$APP_PATH" ]; then
  echo "앱 번들을 찾을 수 없습니다: $APP_PATH"
  exit 1
fi

rm -rf "$STAGING_DIR"
mkdir -p "$STAGING_DIR"
mkdir -p "$DIST_DIR"

cp -R "$APP_PATH" "$STAGING_DIR/$APP_NAME"
cp "$PROJECT_DIR/실행.command" "$STAGING_DIR/실행.command"
ln -s /Applications "$STAGING_DIR/Applications"

if [ -f "$DMG_PATH" ]; then
  rm -f "$DMG_PATH"
fi

hdiutil create \
  -volname "TOEFL Scorer Installer" \
  -srcfolder "$STAGING_DIR" \
  -ov \
  -format UDZO \
  "$DMG_PATH"

echo "완료: $DMG_PATH"
