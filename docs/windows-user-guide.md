# Windows 사용자 가이드

상태: 스크립트와 런처 경로는 준비됨. 실제 Windows 빌드 smoke test는 Windows 머신에서 추가 확인 필요.

## 내부 알파 빌드 만들기

PowerShell에서 저장소 루트로 이동한 뒤 실행한다.

```powershell
.\windows\build_windows.ps1
```

성공하면 `dist_windows\TOEFLScorer.exe`가 생성된다.

## 실행

- 앱은 내부 FastAPI 서버를 `127.0.0.1` 동적 포트로 띄운다.
- 네트워크 외부 인터페이스에는 바인딩하지 않는다.
- 중복 실행 방지 lock을 사용한다.
- 창을 닫으면 서버도 종료된다.

## 알려진 경고

- 코드 서명 전에는 SmartScreen 경고가 뜰 수 있다.
- Windows 실제 smoke test 전에는 릴리스 완료로 표시하지 않는다.
- Inno Setup이 없으면 installer script는 실패한다.

## 확인해야 할 기능

evaluate, history, dashboard, PDF, backup/restore, draft autosave, Build a Sentence, `/api/local-ai/status`, API 키 없이 core 기능, artifact scan.
