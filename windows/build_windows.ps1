# Windows 실행 파일(.exe) 빌드 — PyInstaller onefile.
#
# 실제 Windows 머신 또는 GitHub Actions windows-latest 러너에서 실행한다.
# macOS/Linux에서는 실행할 수 없다(Windows .exe는 Windows에서만 빌드 가능).
# 산출물: dist_windows\<AppName>.exe
$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
} else {
  throw "Python 실행 파일을 찾지 못했습니다. Python 3.11+ 설치 후 다시 시도하세요."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  & $pythonCmd -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller pytest

# 아이콘 확인/생성 (Pillow만 필요하므로 Windows에서도 생성 가능)
if (-not (Test-Path "packaging\resources\app.ico")) {
  & .\.venv\Scripts\python.exe scripts\generate_app_icon.py
}

# 앱 이름/버전을 단일 출처(app/version.py)에서 읽는다
$appName = & .\.venv\Scripts\python.exe -c "from app.version import APP_BUNDLE_NAME; print(APP_BUNDLE_NAME)"
$appVersion = & .\.venv\Scripts\python.exe -c "from app.version import APP_VERSION; print(APP_VERSION)"
Write-Host "Building $appName v$appVersion"

$distDir = "dist_windows"
if (Test-Path $distDir) { Remove-Item -Recurse -Force $distDir }
if (Test-Path "build") { Remove-Item -Recurse -Force "build" }

& .\.venv\Scripts\pyinstaller.exe `
  --noconfirm `
  --clean `
  --windowed `
  --onefile `
  --hidden-import webview `
  --name "$appName" `
  --icon "packaging\resources\app.ico" `
  --distpath $distDir `
  --paths "." `
  --add-data "static;static" `
  windows\app_launcher.py

Write-Host "완료: $distDir\$appName.exe"
