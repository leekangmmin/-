$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

# 1) Build TOEFLScorer.exe first
powershell -ExecutionPolicy Bypass -File windows/build_windows.ps1

$candidates = @(
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles(x86)\Inno Setup 6\ISCC.exe"
)

$iscc = $null
foreach ($p in $candidates) {
    if (Test-Path $p) {
        $iscc = $p
        break
    }
}

if (-not $iscc) {
    throw "Inno Setup 6(ISCC.exe)를 찾지 못했습니다. https://jrsoftware.org/isdl.php 에서 설치해 주세요."
}

& $iscc "windows\installer\TOEFLScorer.iss"

Write-Host "완료: dist_windows\installer\TOEFLScorer-Setup.exe"
