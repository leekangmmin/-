"""서버 lifecycle: 동적 loopback 포트 선택, in-process 백그라운드 스레드 실행,
health check 대기, graceful shutdown (Phase 5, 마스터 스펙 6~7장).

subprocess로 별도 python/uvicorn 프로세스를 띄우지 않고, 같은 프로세스 안에서
백그라운드 스레드로 uvicorn을 돌린다. 이유: PyInstaller onedir/onefile로
패키징된 실행 파일은 일반 python 인터프리터가 아니므로, `sys.executable -m
uvicorn ...`으로 서브프로세스를 스폰하면 패키징된 실행 파일 자기 자신을 다시
실행하려 시도해 무한 부트스트랩에 빠질 위험이 있다. in-process 스레드 방식은
개발 모드와 패키징 모드에서 완전히 동일하게 동작하고, 별도 자식 프로세스가
없으므로 "종료 후 고아 프로세스" 문제 자체가 구조적으로 발생하지 않는다.
"""

from __future__ import annotations

import socket
import threading
import time
import urllib.error
import urllib.request

import uvicorn

HOST = "127.0.0.1"


def pick_free_port() -> int:
    """OS가 사용 가능한 loopback 포트를 임시로 할당하게 한다.

    바인드했다가 즉시 닫으므로 이론적으로 아주 짧은 race window가 있다 —
    닫힌 직후 다른 프로세스가 같은 포트를 채갈 가능성. 실무적으로 매우
    드물고, 서버 시작이 실패하면 호출부가 새 포트로 재시도해야 한다
    (start_server_thread의 retry 로직 참고).
    """
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind((HOST, 0))
        return s.getsockname()[1]


def _health_ok(port: int, timeout: float = 0.8) -> bool:
    try:
        with urllib.request.urlopen(f"http://{HOST}:{port}/api/health", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


class ManagedServer:
    def __init__(self, server: uvicorn.Server, thread: threading.Thread, port: int):
        self.server = server
        self.thread = thread
        self.port = port

    def wait_until_healthy(self, max_wait_seconds: float = 15.0) -> bool:
        deadline = time.time() + max_wait_seconds
        while time.time() < deadline:
            if not self.thread.is_alive():
                return False  # 서버 스레드가 시작 중 죽음 (예: 포트 충돌)
            if _health_ok(self.port):
                return True
            time.sleep(0.1)
        return False

    def shutdown(self, timeout: float = 5.0) -> None:
        """graceful shutdown 시도 후 timeout 내 끝나지 않으면 포기하고 반환한다.

        uvicorn.Server.should_exit=True는 진행 중인 요청이 끝나도록 유예를 준다
        (강제 kill이 아니다). 이 프로세스 자체가 곧 종료되므로, 스레드가 완전히
        멈추지 않아도 데몬 스레드는 프로세스 종료와 함께 정리된다.
        """
        self.server.should_exit = True
        self.thread.join(timeout=timeout)


def start_server_thread(app_import_path: str, max_port_attempts: int = 3) -> ManagedServer:
    """백그라운드 스레드에서 uvicorn 서버를 시작한다. 포트 충돌 시 새 포트로 재시도한다."""
    last_error: Exception | None = None
    for _attempt in range(max_port_attempts):
        port = pick_free_port()
        config = uvicorn.Config(
            app_import_path, host=HOST, port=port, log_level="warning",
            access_log=False,  # 요청 경로/상태만이라도 사용자 답안 원문과 섞여 로그에 남지 않게 최소화
        )
        server = uvicorn.Server(config)
        thread = threading.Thread(target=server.run, daemon=True, name="toefl-uvicorn")
        thread.start()

        managed = ManagedServer(server=server, thread=thread, port=port)
        if managed.wait_until_healthy():
            return managed

        # 실패 — 다음 포트로 재시도
        server.should_exit = True
        thread.join(timeout=2.0)
        last_error = RuntimeError(f"server failed to become healthy on port {port}")

    raise RuntimeError(f"서버 시작 {max_port_attempts}회 시도 모두 실패: {last_error}")
