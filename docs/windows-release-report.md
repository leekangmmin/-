# Windows Release Report

상태: Phase 9 Mac 환경 감사 기준. 실제 Windows 머신 빌드는 아직 이 세션에서 실행되지 않았다.

## 현재 확인한 것

- Windows launcher가 공용 desktop lifecycle을 재사용하도록 수정했다.
- 서버는 `desktop.server_manager`를 통해 `127.0.0.1` 동적 포트에 바인딩한다.
- 중복 실행 방지는 `desktop.single_instance.SingleInstanceLock`을 사용한다.
- 고정 포트 `8000` Windows 런처 경로를 제거했다.
- `windows/build_windows.ps1`은 `windows/app_launcher.py`를 PyInstaller onefile/windowed로 빌드한다.
- `app` 소스 폴더 전체를 data로 넣는 옵션을 제거하고 `static`만 data로 포함하도록 정리했다.

## 이 환경에서 실행한 검증

- macOS `.venv` 기준 전체 테스트 통과.
- eval harness 통과.
- local AI rule validation 통과.
- PowerShell (`pwsh`/`powershell`)이 이 Mac 환경에 없어 `.\windows\build_windows.ps1`은 실행하지 못했다.

## Windows에서 반드시 확인할 항목

- `.\windows\build_windows.ps1`
- `dist_windows\TOEFLScorer.exe` 실행
- console 없는 실행 여부
- localhost-only bind
- dynamic port
- 종료 후 orphan process 없음
- evaluate/history/dashboard/PDF/backup/restore/draft/Build a Sentence/local AI status
- API 키 없이 core 기능
- cloud AI disabled by default
- admin API disabled by default
- artifact security scan

## 현재 결론

Windows release path는 개선됐지만, 실제 Windows 빌드와 smoke test 전에는 Windows 배포 완료라고 말할 수 없다.
