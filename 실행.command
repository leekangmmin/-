
#!/bin/zsh
set -e

# Gatekeeper 격리 해제 및 실행 권한 자동 부여
xattr -dr com.apple.quarantine "$0" 2>/dev/null
chmod +x "$0" 2>/dev/null
xattr -dr com.apple.quarantine "./토플첨삭기 by이강민.app" 2>/dev/null
chmod -R +x "./토플첨삭기 by이강민.app/Contents/MacOS/" 2>/dev/null

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
