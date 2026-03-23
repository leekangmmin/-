#!/bin/zsh
# FastAPI 서버를 pyinstaller로 독립 실행 파일로 빌드
# 실행: ./macos/build_standalone_server.command

set -e
cd "$(dirname "$0")/.."

# 1. pyinstaller 설치 (최초 1회)
pip install --upgrade pyinstaller

# 2. FastAPI 서버 바이너리 빌드
pyinstaller --onefile --name toefl_server app/main.py

# 3. 앱 번들에 바이너리 복사
cp dist/toefl_server "토플첨삭기 by이강민.app/Contents/MacOS/toefl_server"

echo "✅ FastAPI 서버 독립 실행 파일 빌드 및 앱 번들에 포함 완료!"
