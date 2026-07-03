"""데스크톱 앱 진입점 (Phase 5).

책임: 사용자 데이터 디렉터리 준비 → 중복 실행 확인 → 서버 시작(동적 포트,
in-process 스레드) → health check 대기 → 네이티브 웹뷰 창 → 종료 시 서버 정리.
비즈니스 로직(채점/DB/평가)은 전혀 포함하지 않는다 — 전부 app.* 모듈에 위임한다.
"""

from __future__ import annotations

import signal
import subprocess
import sys

from app.paths import config_dir, logs_dir
from app.version import APP_DISPLAY_NAME, APP_VERSION
from desktop.server_manager import start_server_thread
from desktop.single_instance import SingleInstanceLock


def _show_fatal_dialog(message: str) -> None:
    """치명적 오류를 사용자에게 보여준다. macOS 네이티브 다이얼로그를 우선 쓰고,
    실패하면(비-macOS, headless 등) stderr로만 출력한다."""
    print(f"[FATAL] {message}", file=sys.stderr)
    try:
        escaped = message.replace('"', '\\"')
        subprocess.run(
            ["osascript", "-e", f'display dialog "{escaped}" buttons {{"확인"}} default button "확인"'],
            timeout=15, check=False,
        )
    except (OSError, subprocess.SubprocessError):
        pass


def main() -> int:
    print(f"{APP_DISPLAY_NAME} v{APP_VERSION} 시작 중...", file=sys.stderr)
    lock = SingleInstanceLock(config_dir() / "app.lock")
    existing = lock.check_existing()
    if existing is not None:
        _show_fatal_dialog(f"{APP_DISPLAY_NAME}이(가) 이미 실행 중입니다.\n실행 중인 창을 확인해주세요.")
        return 0  # 중복 실행은 오류가 아니라 정상적인 안내 후 종료

    try:
        managed = start_server_thread("app.main:app")
    except RuntimeError as exc:
        _show_fatal_dialog(f"서버를 시작하지 못했습니다.\n{exc}\n로그: {logs_dir()}")
        return 1

    lock.acquire(managed.port)

    # SIGTERM/SIGINT로 프로세스가 종료될 때도(예: 창을 닫지 않고 강제 종료 신호를
    # 받는 경우) 서버와 lock을 정리한다. 창 닫기(closing 이벤트)가 주 경로이고,
    # 이 핸들러는 그 경로를 타지 않는 종료(예: kill, 터미널 Ctrl+C)에 대한
    # 보조 안전망이다. 두 경로 모두 결국 이 프로세스 자체가 종료되므로,
    # in-process 스레드 구조상 별도 자식 프로세스가 남는 고아 프로세스 문제는
    # 애초에 발생하지 않는다 — 이 핸들러는 lock 파일 정리를 앞당길 뿐이다.
    def _handle_termination_signal(signum: int, _frame: object) -> None:
        managed.shutdown()
        lock.release()
        sys.exit(0)

    signal.signal(signal.SIGTERM, _handle_termination_signal)
    signal.signal(signal.SIGINT, _handle_termination_signal)

    try:
        import webview  # 지연 import — 서버만 검증하는 테스트에서 pywebview 의존성을 피하기 위함

        def _on_closing() -> None:
            managed.shutdown()

        window = webview.create_window(
            APP_DISPLAY_NAME,
            f"http://127.0.0.1:{managed.port}",
            width=1400, height=920, min_size=(1000, 700), text_select=True,
        )
        window.events.closing += _on_closing
        webview.start(debug=False)
    finally:
        managed.shutdown()
        lock.release()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
