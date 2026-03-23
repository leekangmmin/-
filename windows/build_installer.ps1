$ErrorActionPreference = "Stop"

Set-Location -Path (Join-Path $PSScriptRoot "..")

# 1) Build TOEFLScorer.exe first
$psHost = $null
if (Get-Command pwsh -ErrorAction SilentlyContinue) {
    $psHost = "pwsh"
} elseif (Get-Command powershell -ErrorAction SilentlyContinue) {
    $psHost = "powershell"
} else {
    throw "PowerShell 실행 파일(pwsh/powershell)을 찾지 못했습니다."
}

& $psHost -NoProfile -ExecutionPolicy Bypass -File (Join-Path $PSScriptRoot "build_windows.ps1")
if ($LASTEXITCODE -ne 0) {
    throw "windows/build_windows.ps1 실행에 실패했습니다."
}

$candidates = @(
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe"
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
