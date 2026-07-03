# 데스크톱 앱 아키텍처 (Phase 5)

## 개요

```text
Desktop Launcher (desktop/launcher.py)
    ↓
사용자 데이터 디렉터리 준비 (app/paths.py, platformdirs)
    ↓
중복 실행 확인 (desktop/single_instance.py — lock 파일 + PID/health 이중 확인)
    ↓
사용 가능한 loopback 포트 선택 (desktop/server_manager.py, socket.bind(('127.0.0.1', 0)))
    ↓
FastAPI 서버를 in-process 백그라운드 스레드로 127.0.0.1:<동적포트>에서 시작
    ↓
health endpoint(GET /api/health) 확인 (최대 15초 대기, 무한 대기 아님)
    ↓
lock 파일 기록 (pid, port, acquired_at)
    ↓
SIGTERM/SIGINT 핸들러 등록 (보조 안전망)
    ↓
pywebview 네이티브 창 실행 (webview.create_window + webview.start)
    ↓
창 닫힘(closing 이벤트) 또는 종료 신호 → 서버 graceful shutdown → lock 해제
```

## 채택 기술: FastAPI + pywebview + PyInstaller one-dir

마스터 스펙 5장에 따라 기존 Python 중심 구조를 보존하는 기본 권장안(FastAPI +
pywebview + PyInstaller one-dir + platformdirs + SQLite)을 그대로 채택했다.
Electron/React로 전면 교체할 기술적 필요가 없었다 — pywebview는 macOS Cocoa
WebKit 백엔드로 정상 동작했고(`pyobjc-framework-Cocoa/WebKit` 이미 설치돼
있었음), 별도 blocker가 발견되지 않았다. 따라서 대체 기술 문서화(섹션 5의
"불가능한 이유" 절차)는 필요 없었다.

## `desktop/` 패키지 구성

```text
desktop/
├─ __init__.py       — 패키지 docstring (비즈니스 로직 금지 명시)
├─ launcher.py        — 진입점, 생명주기 오케스트레이션
├─ server_manager.py   — 동적 포트, in-process 서버 스레드, health check, shutdown
└─ single_instance.py — lock 파일 기반 중복 실행 감지/정리
```

비즈니스 로직(채점/DB/평가)은 전혀 포함하지 않는다 — 전부 `app.*` 모듈을
그대로 import해서 쓴다. `desktop/launcher.py`는 실행과 생명주기만 담당한다
(마스터 스펙 6장, 26장 요구사항).

## 서버 lifecycle 상세

### in-process 스레드 vs subprocess

`desktop/server_manager.py`는 `subprocess`로 별도 uvicorn 프로세스를 띄우지
않고, **같은 프로세스 안에서 백그라운드 스레드로 uvicorn을 실행**한다.

이유: PyInstaller로 얼린 실행 파일은 일반 `python` 인터프리터가 아니다.
`sys.executable -m uvicorn ...` 같은 방식으로 서브프로세스를 스폰하면 패키징된
실행 파일 자기 자신을 다시 실행하려 시도해 무한 부트스트랩에 빠질 위험이
있다. in-process 스레드 방식은 개발 모드와 패키징 모드에서 완전히 동일하게
동작하고, **별도 자식 프로세스가 없으므로 "종료 후 고아 프로세스" 문제가
구조적으로 발생하지 않는다** — 메인 프로세스가 죽으면 데몬 스레드도 함께
사라진다(마스터 스펙 1장 "앱 종료 후 백엔드 프로세스가 남지 않음" 요구사항을
아키텍처 수준에서 충족).

### 동적 포트

`pick_free_port()`는 `socket.bind(('127.0.0.1', 0))` 후 즉시 `getsockname()`으로
OS가 할당한 포트 번호를 읽고 소켓을 닫는다. 이론적으로 닫은 직후 다른
프로세스가 같은 포트를 채가는 짧은 race window가 있지만, `start_server_thread`가
최대 3회까지 새 포트로 재시도하도록 설계해 실무적으로 문제가 되지 않는다.
포트는 어떤 설정 파일에도 영구 하드코딩하지 않는다.

### health check

`GET /api/health`는 다음만 노출한다: `status`, `app_version`, `db_schema_version`,
`offline_core_available`, `shadow_enabled`(불리언만 — API 키 존재 여부·모델명
등 세부 정보는 노출하지 않는다). `ManagedServer.wait_until_healthy()`는 최대
15초까지만 대기하고(무한 대기 금지), 서버 스레드가 시작 중 죽으면 즉시
실패로 판단한다.

### graceful shutdown

- 창 닫기 → `window.events.closing` 콜백 → `managed.shutdown()`
- `uvicorn.Server.should_exit = True` 후 스레드 join(최대 5초 유예 — 진행 중인
  요청이 끝나도록 기다리되 무한정 대기하지 않음)
- SIGTERM/SIGINT 수신 시에도 동일한 정리 경로를 타도록 Phase 5에서 시그널
  핸들러를 추가했다(창을 닫지 않고 강제 종료 신호를 받는 경우에 대한 보조
  안전망 — `scripts/packaged_app_smoke_test.py`로 실제 패키징 앱에서 검증,
  두 번 모두 exit code 0으로 정상 종료 확인).

## 중복 실행 방지

`desktop/single_instance.py`의 `SingleInstanceLock`은:
- lock 파일(`config/app.lock`, JSON: `{pid, port, acquired_at}`)로 기존 인스턴스
  존재 여부를 판단한다.
- **PID 생존 여부 + 실제 health 응답 이중 확인**을 한다 — PID만 확인하면
  PID 재사용(다른 프로세스가 같은 PID를 새로 받은 경우) 오탐이 발생할 수
  있고, 포트 응답만 확인하면 다른 앱이 우연히 같은 포트를 쓰는 경우를
  구분 못한다. 두 조건을 모두 만족해야 "정말 실행 중"으로 판단한다.
- PID가 죽었거나 포트가 응답하지 않으면 stale lock으로 간주하고 자동
  정리한다(영구적으로 앱을 막는 lock 파일 문제 없음 — 마스터 스펙 8장 금지
  항목 회피).
- 두 번째 인스턴스는 새 서버/DB writer를 만들지 않고, macOS 네이티브
  다이얼로그(`osascript display dialog`)로 안내 후 종료한다(exit 0 — 중복
  실행은 오류가 아니라 정상적인 안내).

자동화 테스트: `tests/test_desktop_launcher.py`가 실제 서버를 띄운 상태에서
두 번째 `SingleInstanceLock` 인스턴스가 이를 올바르게 감지하는지 검증한다
(`test_real_running_server_detected_as_existing_instance`). 패키징된 `.app`
자체의 중복 실행도 수동으로 재현 검증했다(`docs/internal-alpha-test-report.md`
참고).

## 개발 모드와 패키징 모드 병존

기존 개발 흐름은 전혀 깨지지 않았다:
- 브라우저 기반 개발 서버: `.venv/bin/python -m uvicorn app.main:app --reload`
  (기존 방식 그대로 동작, `pytest`/harness 포함)
- 데스크톱 런처 개발 실행: `.venv/bin/python -m desktop.launcher`
- 패키징 앱 실행: `dist/TOEFL Writing.app`

세 경로 모두 동일한 `app.main:app`을 사용하므로 비즈니스 로직 중복이 없다.
