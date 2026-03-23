@echo off
setlocal
cd /d %~dp0\..

REM 1. pyinstaller exe가 있으면 바로 실행
if exist dist_windows\TOEFLScorer.exe (
  start "TOEFLScorer" dist_windows\TOEFLScorer.exe
  exit /b
)

REM 2. .venv가 있으면 가상환경 python 사용
if exist .venv\Scripts\python.exe (
  .venv\Scripts\python.exe -m pip install -r requirements.txt >nul
  .venv\Scripts\python.exe windows\app_launcher.py
  exit /b
)

REM 3. 시스템 python으로 실행 (venv 없이)
where python >nul 2>nul
if %errorlevel%==0 (
  python -m pip install --user -r requirements.txt
  python windows\app_launcher.py
  exit /b
)
where py >nul 2>nul
if %errorlevel%==0 (
  py -m pip install --user -r requirements.txt
  py windows\app_launcher.py
  exit /b
)

echo Python이 설치되어 있지 않습니다. https://www.python.org/downloads/ 에서 설치 후 다시 실행해 주세요.
pause
