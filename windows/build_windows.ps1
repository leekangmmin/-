$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

$pythonCmd = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
  $pythonCmd = "py"
} elseif (Get-Command python -ErrorAction SilentlyContinue) {
  $pythonCmd = "python"
} else {
  throw "Python 실행 파일을 찾지 못했습니다. Python 설치 후 다시 시도하세요."
}

if (-not (Test-Path ".venv\Scripts\python.exe")) {
  & $pythonCmd -m venv .venv
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
