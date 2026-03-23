from __future__ import annotations

import threading
import time
import urllib.error
import urllib.request
import webbrowser
import tkinter as tk
from tkinter import messagebox

import uvicorn
import webview

HOST = "127.0.0.1"
PORT = 8000
BASE_URL = f"http://{HOST}:{PORT}"
HEALTH_URL = f"{BASE_URL}/api/health"


def health_ok(timeout: float = 1.0) -> bool:
    try:
        with urllib.request.urlopen(HEALTH_URL, timeout=timeout) as response:
            return response.status == 200
    except (urllib.error.URLError, TimeoutError, ConnectionError):
        return False


def wait_for_server(max_wait_seconds: float = 15.0) -> bool:
    deadline = time.time() + max_wait_seconds
    while time.time() < deadline:
        if health_ok(timeout=0.8):
            return True
        time.sleep(0.2)
    return False


def build_server() -> uvicorn.Server:
    config = uvicorn.Config(
        "app.main:app",
        host=HOST,
        port=PORT,
        log_level="warning",
    )
    return uvicorn.Server(config)


def main() -> int:
    server = build_server()
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()

    if not wait_for_server():
        messagebox.showerror("TOEFL 채점기", "서버 시작에 실패했습니다. 로그를 확인해 주세요.")
        return 1

    try:
        webview.create_window(
            "TOEFL 채점기",
            BASE_URL,
            width=1360,
            height=900,
            min_size=(1024, 700),
            text_select=True,
        )
        webview.start(debug=False)
    except Exception:
        # If webview runtime is unavailable, fall back to browser mode.
        webbrowser.open(BASE_URL)

        root = tk.Tk()
        root.title("TOEFL 채점기")
        root.geometry("440x190")
        root.resizable(False, False)

        title = tk.Label(root, text="TOEFL 채점기 실행 중", font=("Segoe UI", 13, "bold"))
        title.pack(pady=(18, 10))

        info = tk.Label(
            root,
            text="데스크톱 웹뷰 실행에 실패하여 브라우저 모드로 열었습니다.\n창을 닫으면 서버도 함께 종료됩니다.",
            justify="center",
        )
        info.pack(pady=(0, 10))

        button_frame = tk.Frame(root)
        button_frame.pack(pady=8)

        open_btn = tk.Button(button_frame, text="브라우저 열기", width=14, command=lambda: webbrowser.open(BASE_URL))
        open_btn.grid(row=0, column=0, padx=6)

        def on_exit() -> None:
            server.should_exit = True
            root.destroy()

        exit_btn = tk.Button(button_frame, text="종료", width=14, command=on_exit)
        exit_btn.grid(row=0, column=1, padx=6)

        root.protocol("WM_DELETE_WINDOW", on_exit)
        root.mainloop()

    server.should_exit = True
    thread.join(timeout=5)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
