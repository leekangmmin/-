"""중복 실행 방지 (Phase 5, 마스터 스펙 8장).

단순 lock 파일 존재 여부만으로 판단하지 않는다 — PID가 재사용됐거나 앱이
비정상 종료돼 lock 파일만 남은 경우(stale lock)를 구분해야 영구적으로 실행을
막는 사고를 피할 수 있다. lock 파일에는 PID와 그 PID가 열었던 포트를 함께
저장하고, 두 조건(PID 생존 + 해당 포트에서 우리 앱의 /api/health 응답)이 모두
충족될 때만 "이미 실행 중"으로 판단한다.
"""

from __future__ import annotations

import json
import os
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunningInstance:
    pid: int
    port: int


def _pid_alive(pid: int) -> bool:
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True  # 존재는 하지만 다른 사용자 소유 — 살아있다고 취급
    return True


def _health_responds(port: int, timeout: float = 0.6) -> bool:
    try:
        with urllib.request.urlopen(f"http://127.0.0.1:{port}/api/health", timeout=timeout) as resp:
            return resp.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError, OSError):
        return False


class SingleInstanceLock:
    """lock 파일 기반 중복 실행 감지. 컨텍스트 매니저로 쓴다.

    stale lock(죽은 PID, 응답 없는 포트)은 자동으로 무시하고 새로 획득한다 —
    비정상 종료 후 앱이 영구적으로 막히지 않게 하기 위함이다.
    """

    def __init__(self, lock_path: Path):
        self.lock_path = lock_path
        self._acquired = False

    def check_existing(self) -> RunningInstance | None:
        """이미 실행 중인 정상 인스턴스가 있으면 정보를 반환하고, 없으면(또는
        stale이면) None을 반환한다. stale lock은 여기서 정리한다."""
        if not self.lock_path.exists():
            return None
        try:
            data = json.loads(self.lock_path.read_text(encoding="utf-8"))
            pid = int(data["pid"])
            port = int(data["port"])
        except (json.JSONDecodeError, KeyError, ValueError, OSError):
            self.lock_path.unlink(missing_ok=True)
            return None

        if _pid_alive(pid) and _health_responds(port):
            return RunningInstance(pid=pid, port=port)

        # stale lock — 정리하고 새로 시작할 수 있게 한다
        self.lock_path.unlink(missing_ok=True)
        return None

    def acquire(self, port: int) -> None:
        self.lock_path.parent.mkdir(parents=True, exist_ok=True)
        self.lock_path.write_text(
            json.dumps({"pid": os.getpid(), "port": port, "acquired_at": time.time()}),
            encoding="utf-8",
        )
        self._acquired = True

    def release(self) -> None:
        if self._acquired:
            self.lock_path.unlink(missing_ok=True)
            self._acquired = False

    def __enter__(self) -> "SingleInstanceLock":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.release()
