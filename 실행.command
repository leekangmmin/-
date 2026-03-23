#!/bin/zsh
set -e

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_RUN="$PROJECT_DIR/토플첨삭기 by이강민.app/Contents/MacOS/run"

if [ ! -x "$APP_RUN" ]; then
  echo "앱 실행 파일을 찾을 수 없습니다: $APP_RUN"
  read -k 1 "?아무 키나 누르면 종료합니다..."
  echo
  exit 1
fi

cd "$PROJECT_DIR"
"$APP_RUN"
