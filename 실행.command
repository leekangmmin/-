

#!/bin/zsh
set -e

# Gatekeeper 격리 해제 및 실행 권한 자동 부여
xattr -dr com.apple.quarantine "$0" 2>/dev/null
chmod +x "$0" 2>/dev/null
xattr -dr com.apple.quarantine "./토플첨삭기 by이강민.app" 2>/dev/null
chmod -R +x "./토플첨삭기 by이강민.app/Contents/MacOS/" 2>/dev/null

PROJECT_DIR="$(cd "$(dirname "$0")" && pwd)"
APP_RUN="$PROJECT_DIR/토플첨삭기 by이강민.app/Contents/MacOS/run"

# Python 3.11+ 감지 및 .venv 자동 생성/설치
PY311_BIN=""
if [ -x "$PROJECT_DIR/.venv/bin/python" ]; then
  PY311_BIN="$PROJECT_DIR/.venv/bin/python"
elif command -v python3.11 >/dev/null 2>&1; then
  PY311_BIN="$(command -v python3.11)"
elif command -v python3 >/dev/null 2>&1 && [[ "$(python3 --version 2>&1)" == "Python 3.11"* ]]; then
  PY311_BIN="$(command -v python3)"
fi

if [ -z "$PY311_BIN" ]; then
  osascript -e 'display dialog "Python 3.11 이상이 필요합니다.\nhttps://www.python.org/downloads/ 에서 설치 후 다시 실행하세요." buttons {"확인"} default button "확인"'
  exit 1
fi

# .venv 없으면 자동 생성 및 requirements 설치
if [ ! -x "$PROJECT_DIR/.venv/bin/python" ]; then
  echo "가상환경(.venv) 자동 생성 중..."
  "$PY311_BIN" -m venv "$PROJECT_DIR/.venv"
  "$PROJECT_DIR/.venv/bin/python" -m pip install --upgrade pip
  "$PROJECT_DIR/.venv/bin/python" -m pip install -r "$PROJECT_DIR/requirements.txt"
fi

if [ ! -x "$APP_RUN" ]; then
  echo "앱 실행 파일을 찾을 수 없습니다: $APP_RUN"
  read -k 1 "?아무 키나 누르면 종료합니다..."
  echo
  exit 1
fi

cd "$PROJECT_DIR"
"$APP_RUN"
