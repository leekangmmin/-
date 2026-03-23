#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
NATIVE_DIR="$PROJECT_DIR/NativeMacApp"
OUTPUT_DIR="$PROJECT_DIR/dist_macos/xcode"
ARCHIVE_PATH="$OUTPUT_DIR/ToeflNativeApp.xcarchive"
EXPORT_DIR="$OUTPUT_DIR/export"

mkdir -p "$OUTPUT_DIR"

if ! command -v xcodebuild >/dev/null 2>&1; then
  echo "xcodebuild를 찾을 수 없습니다. Xcode를 설치해 주세요."
  exit 1
fi

if ! command -v xcodegen >/dev/null 2>&1; then
  echo "xcodegen이 필요합니다. 설치 후 다시 실행해 주세요."
  echo "예: brew install xcodegen"
  exit 1
fi

cd "$NATIVE_DIR"
xcodegen generate --spec project.yml

xcodebuild \
  -project ToeflNativeApp.xcodeproj \
  -scheme ToeflNativeApp \
  -configuration Release \
  -archivePath "$ARCHIVE_PATH" \
  archive

xcodebuild \
  -exportArchive \
  -archivePath "$ARCHIVE_PATH" \
  -exportPath "$EXPORT_DIR" \
  -exportOptionsPlist "$NATIVE_DIR/exportOptions.plist"

echo "완료: $EXPORT_DIR"
