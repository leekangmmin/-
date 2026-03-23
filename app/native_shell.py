from __future__ import annotations

import atexit
import os
import signal
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

import webview  # type: ignore[import-not-found]


HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
HEALTH_URL = f"{BASE_URL}/api/health"
WINDOW_TITLE = "토플첨삭기 by이강민"


def health_ok(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def start_server(project_dir: Path, python_bin: Path, log_file: Path) -> subprocess.Popen[str]:
    command = [
        str(python_bin),
        "-m",
        "uvicorn",
        "app.main:app",
        "--host",
        HOST,
        "--port",
        str(PORT),
    ]

    log_handle = log_file.open("a", encoding="utf-8")
    process = subprocess.Popen(
        command,
        cwd=str(project_dir),
        stdout=log_handle,
        stderr=log_handle,
        text=True,
    )
    return process


def wait_for_server(max_wait_seconds: float = 12.0) -> bool:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if health_ok(timeout=0.8):
            return True
        time.sleep(0.2)
    return False


def terminate_process(process: subprocess.Popen[str]) -> None:
    if process.poll() is not None:
        return

    process.terminate()
    try:
        process.wait(timeout=4)
    except subprocess.TimeoutExpired:
        process.kill()


def main() -> int:
    project_dir = Path(__file__).resolve().parents[1]
    data_dir = project_dir / "data"
    data_dir.mkdir(parents=True, exist_ok=True)

    python_bin = Path(sys.executable)
    log_file = data_dir / "app.log"
    pid_file = data_dir / "app.pid"

    started_here = False
    process: subprocess.Popen[str] | None = None

    if not health_ok():
        process = start_server(project_dir=project_dir, python_bin=python_bin, log_file=log_file)
        started_here = True
        pid_file.write_text(str(process.pid), encoding="utf-8")

        if not wait_for_server():
            terminate_process(process)
            pid_file.unlink(missing_ok=True)
            return 1

    def cleanup() -> None:
        if started_here and process is not None:
            terminate_process(process)
            pid_file.unlink(missing_ok=True)

    atexit.register(cleanup)

    def _signal_handler(_sig: int, _frame: object) -> None:
        cleanup()
        raise SystemExit(0)

    signal.signal(signal.SIGINT, _signal_handler)
    signal.signal(signal.SIGTERM, _signal_handler)

    webview.create_window(
        WINDOW_TITLE,
        BASE_URL,
        width=1400,
        height=920,
        min_size=(1000, 700),
        text_select=True,
    )
    webview.start(debug=False)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
