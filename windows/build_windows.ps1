$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

if (-not (Get-Command py -ErrorAction SilentlyContinue)) {
    throw "Python launcher 'py'를 찾을 수 없습니다. Windows에서 Python 설치 후 다시 시도하세요."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
    py -m venv .venv
}

& .\.venv\Scripts\python.exe -m pip install --upgrade pip
& .\.venv\Scripts\python.exe -m pip install -r requirements.txt pyinstaller

$distDir = "dist_windows"
if (Test-Path $distDir) {
    Remove-Item -Recurse -Force $distDir
}

& .\.venv\Scripts\pyinstaller.exe `
  --noconfirm `
  --clean `
  --windowed `
  --onefile `
    --hidden-import webview `
  --name "TOEFLScorer" `
  --distpath $distDir `
  --paths "." `
  --add-data "app;app" `
  --add-data "static;static" `
  windows\app_launcher.py

Write-Host "완료: $distDir\TOEFLScorer.exe"
