"""desktop/ 패키지(server_manager, single_instance) 테스트.

pywebview는 실제 네이티브 창을 여는 GUI 의존성이라 headless 테스트 환경에서
검증할 수 없다 — desktop/launcher.py의 webview 호출부는 여기서 다루지 않는다.
서버 lifecycle과 중복 실행 감지 로직은 GUI 없이 전부 검증 가능하다.
"""

from __future__ import annotations

import os
import time

import pytest

from desktop.server_manager import ManagedServer, pick_free_port, start_server_thread
from desktop.single_instance import SingleInstanceLock, _health_responds, _pid_alive


@pytest.fixture(autouse=True)
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TOEFL_DATA_DIR", str(tmp_path / "data"))


class TestPickFreePort:
    def test_returns_distinct_available_ports(self):
        ports = {pick_free_port() for _ in range(5)}
        assert len(ports) == 5  # 매번 다른 포트를 받는다(동시 바인딩이 없으므로)
        assert all(1024 < p < 65536 for p in ports)


class TestServerLifecycle:
    def test_server_starts_binds_loopback_and_responds_healthy(self):
        managed = start_server_thread("app.main:app")
        try:
            assert managed.wait_until_healthy(max_wait_seconds=1.0) is True
            import urllib.request

            with urllib.request.urlopen(f"http://127.0.0.1:{managed.port}/api/health", timeout=2) as resp:
                assert resp.status == 200
        finally:
            managed.shutdown()

    def test_shutdown_stops_thread(self):
        managed = start_server_thread("app.main:app")
        managed.wait_until_healthy()
        managed.shutdown(timeout=5.0)
        assert not managed.thread.is_alive()

    def test_only_binds_loopback_not_all_interfaces(self):
        """0.0.0.0 바인딩 금지 확인 — 실제로 127.0.0.1이 아닌 다른 인터페이스에서
        접근 불가능한지 직접 검증하기는 어려우므로, 최소한 실제로 사용한 host 값이
        127.0.0.1임을 서버 설정에서 확인한다."""
        from desktop.server_manager import HOST

        assert HOST == "127.0.0.1"


class TestWindowsLauncher:
    def test_windows_launcher_reuses_shared_desktop_lifecycle(self):
        import desktop.launcher
        import windows.app_launcher

        assert windows.app_launcher.main is desktop.launcher.main


class TestSingleInstanceLock:
    def test_no_existing_lock_returns_none(self, tmp_path):
        lock = SingleInstanceLock(tmp_path / "app.lock")
        assert lock.check_existing() is None

    def test_stale_lock_with_dead_pid_is_ignored_and_cleaned(self, tmp_path):
        lock_path = tmp_path / "app.lock"
        # 존재할 가능성이 극히 낮은 PID(테스트 환경에서 죽은 프로세스로 취급됨)
        dead_pid = 999999
        import json
        lock_path.write_text(json.dumps({"pid": dead_pid, "port": 59999}), encoding="utf-8")

        lock = SingleInstanceLock(lock_path)
        assert lock.check_existing() is None
        assert not lock_path.exists()  # stale lock은 정리됨

    def test_alive_pid_but_unresponsive_port_is_treated_as_stale(self, tmp_path):
        lock_path = tmp_path / "app.lock"
        import json
        # 현재 프로세스 PID는 살아있지만, 59998 포트는 아무도 안 듣고 있음
        lock_path.write_text(json.dumps({"pid": os.getpid(), "port": 59998}), encoding="utf-8")

        lock = SingleInstanceLock(lock_path)
        assert lock.check_existing() is None

    def test_acquire_and_release(self, tmp_path):
        lock_path = tmp_path / "app.lock"
        lock = SingleInstanceLock(lock_path)
        lock.acquire(port=12345)
        assert lock_path.exists()
        lock.release()
        assert not lock_path.exists()

    def test_real_running_server_detected_as_existing_instance(self, tmp_path):
        lock_path = tmp_path / "app.lock"
        managed = start_server_thread("app.main:app")
        try:
            managed.wait_until_healthy()
            lock = SingleInstanceLock(lock_path)
            lock.acquire(port=managed.port)

            second_check = SingleInstanceLock(lock_path)
            existing = second_check.check_existing()
            assert existing is not None
            assert existing.port == managed.port
            assert existing.pid == os.getpid()
        finally:
            managed.shutdown()

    def test_context_manager_releases_on_exit(self, tmp_path):
        lock_path = tmp_path / "app.lock"
        with SingleInstanceLock(lock_path) as lock:
            lock.acquire(port=1)
            assert lock_path.exists()
        assert not lock_path.exists()


class TestPidAliveHelper:
    def test_current_process_is_alive(self):
        assert _pid_alive(os.getpid()) is True

    def test_very_unlikely_pid_is_dead(self):
        assert _pid_alive(999999) is False
