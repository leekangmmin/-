"""데스크톱 앱 진입점 (Phase 5).

책임: 사용자 데이터 디렉터리 준비 → 중복 실행 확인 → 서버 시작(동적 포트,
in-process 스레드) → health check 대기 → 네이티브 웹뷰 창 → 종료 시 서버 정리.
비즈니스 로직(채점/DB/평가)은 전혀 포함하지 않는다 — 전부 app.* 모듈에 위임한다.
"""

from __future__ import annotations

import os
import signal
import subprocess
import sys
import webbrowser

from app.paths import config_dir, logs_dir
from app.version import APP_DISPLAY_NAME, APP_VERSION
from desktop.server_manager import start_server_thread
from desktop.single_instance import SingleInstanceLock


def _show_fatal_dialog(message: str) -> None:
    """치명적 오류를 사용자에게 보여준다."""
    print(f"[FATAL] {message}", file=sys.stderr)
    if sys.platform == "darwin":
        try:
            escaped = message.replace('"', '\\"')
            result = subprocess.run(
                ["osascript", "-e", f'display dialog "{escaped}" buttons {{"확인"}} default button "확인"'],
                timeout=15, check=False,
            )
            if result.returncode == 0:
                return
        except (OSError, subprocess.SubprocessError):
            pass

    try:
        import tkinter as tk
        from tkinter import messagebox

        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(APP_DISPLAY_NAME, message)
        root.destroy()
    except Exception:
        pass


def _run_browser_fallback(url: str) -> None:
    """pywebview 런타임이 없을 때 브라우저로 열고 작은 종료 창을 유지한다."""
    webbrowser.open(url)
    try:
        import tkinter as tk

        root = tk.Tk()
        root.title(APP_DISPLAY_NAME)
        root.geometry("460x190")
        root.resizable(False, False)

        title = tk.Label(root, text=f"{APP_DISPLAY_NAME} 실행 중", font=("Segoe UI", 13, "bold"))
        title.pack(pady=(18, 10))

        info = tk.Label(
            root,
            text="데스크톱 웹뷰를 열 수 없어 브라우저 모드로 실행했습니다.\n이 창을 닫으면 앱 서버도 함께 종료됩니다.",
            justify="center",
        )
        info.pack(pady=(0, 10))

        button_frame = tk.Frame(root)
        button_frame.pack(pady=8)

        open_btn = tk.Button(button_frame, text="브라우저 열기", width=14, command=lambda: webbrowser.open(url))
        open_btn.grid(row=0, column=0, padx=6)

        exit_btn = tk.Button(button_frame, text="종료", width=14, command=root.destroy)
        exit_btn.grid(row=0, column=1, padx=6)

        root.protocol("WM_DELETE_WINDOW", root.destroy)
        root.mainloop()
    except Exception:
        print(f"[WARN] 브라우저 fallback 창을 열 수 없습니다. URL: {url}", file=sys.stderr)


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
    #
    # 정리(서버 종료·lock 해제)를 먼저 끝낸 뒤 os._exit(0)으로 즉시 종료한다.
    # sys.exit(0)은 SystemExit를 발생시켜 Python 정상 종료(Py_Finalize)를
    # 트리거하는데, 이때 pywebview의 네이티브 Cocoa 스레드가 아직 살아있으면
    # 인터프리터 파이널라이즈와 충돌해 SIGABRT(exit=-6)로 죽을 수 있다.
    # 필요한 정리를 이미 마쳤으므로, 파이널라이저를 건너뛰고 exit code 0으로
    # 곧장 나가는 os._exit(0)이 신호 핸들러에서 가장 안전한 종료 방식이다.
    def _handle_termination_signal(signum: int, _frame: object) -> None:
        try:
            managed.shutdown()
            lock.release()
        finally:
            os._exit(0)

    signal.signal(signal.SIGTERM, _handle_termination_signal)
    signal.signal(signal.SIGINT, _handle_termination_signal)

    try:
        url = f"http://127.0.0.1:{managed.port}"
        try:
            import webview  # 지연 import — 서버만 검증하는 테스트에서 pywebview 의존성을 피하기 위함

            def _on_closing() -> None:
                managed.shutdown()

            window = webview.create_window(
                APP_DISPLAY_NAME,
                url,
                width=1400, height=920, min_size=(1000, 700), text_select=True,
            )
            window.events.closing += _on_closing
            webview.start(debug=False)
        except Exception as exc:
            print(f"[WARN] pywebview 실행 실패, 브라우저 모드로 전환합니다: {exc}", file=sys.stderr)
            _run_browser_fallback(url)
    finally:
        managed.shutdown()
        lock.release()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
