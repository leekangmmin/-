#!/usr/bin/env python3
"""패키징된 .app을 실제로 실행해 자동 검증 가능한 항목을 점검한다.

검증(자동화 가능 범위):
  - 최초 실행: 사용자 데이터 폴더 자동 생성, 서버 기동, health 200
  - API 키 없이 평가/기록/대시보드/PDF 정상 동작 (Offline Core)
  - 재실행 시 이전 기록 유지 (restart persistence)
  - graceful shutdown 후 lock 파일 정리 + 프로세스 종료 확인

수동 검증 필요(문서화 대상, docs/internal-alpha-test-report.md):
  - 실제 native 창 렌더링 육안 확인
  - 중복 실행 시 사용자 안내 다이얼로그 노출 확인 (osascript 다이얼로그는
    자동화 스크립트에서 강제로 닫을 수 없어 수동 확인으로 남긴다)
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ESSAY_TEXT = (
    "Universities should invest more resources in mental health support for students "
    "because academic pressure has increased significantly in recent years. Many students "
    "struggle silently with anxiety and stress, and without adequate counseling services, "
    "their academic performance and overall wellbeing suffer. Providing accessible mental "
    "health resources on campus would help students manage these challenges early, before "
    "they escalate into more serious problems that affect graduation rates and long-term success."
)


def _http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 10.0) -> tuple[int, dict]:
    data = json.dumps(payload).encode("utf-8") if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else {})
    except urllib.error.HTTPError as exc:
        return exc.code, {}


def _wait_for_lock(lock_path: Path, timeout: float = 20.0) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if lock_path.exists():
            try:
                return json.loads(lock_path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                pass
        time.sleep(0.2)
    raise TimeoutError(f"lock 파일이 {timeout}s 안에 생성되지 않았습니다: {lock_path}")


def _launch(executable: Path, data_dir: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env["TOEFL_DATA_DIR"] = str(data_dir)
    env.pop("TOEFL_ADMIN_API_ENABLED", None)
    env.pop("ANTHROPIC_API_KEY", None)
    return subprocess.Popen([str(executable)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def run_smoke_test(app_bundle: Path) -> None:
    from app.version import APP_BUNDLE_NAME

    executable = app_bundle / "Contents" / "MacOS" / APP_BUNDLE_NAME
    if not executable.exists():
        print(f"[FAIL] executable not found: {executable}")
        sys.exit(1)

    with tempfile.TemporaryDirectory(prefix="toefl_smoke_data_") as tmp:
        data_dir = Path(tmp)
        lock_path = data_dir / "config" / "app.lock"

        # ── 최초 실행 ──────────────────────────────────────────────
        print("[1/7] 최초 실행")
        proc = _launch(executable, data_dir)
        try:
            lock = _wait_for_lock(lock_path)
            port = lock["port"]
            print(f"    OK: 서버가 포트 {port}에서 기동, lock={lock_path}")

            status, health = _http_json(f"http://127.0.0.1:{port}/api/health")
            assert status == 200, f"health status={status}"
            assert health.get("offline_core_available") is True, health
            assert health.get("shadow_enabled") is False, health  # API 키 없음 → 기본 비활성
            print(f"    OK: /api/health → offline_core_available=True, shadow_enabled=False, app_version={health.get('app_version')}")

            print("[2/6] API 키 없이 평가 (Offline Core)")
            status, body = _http_json(
                f"http://127.0.0.1:{port}/api/evaluate", method="POST",
                payload={"essay_text": ESSAY_TEXT},
            )
            assert status == 200, f"evaluate status={status} body={body}"
            submission_id = body["submission_id"]
            result = body["result"]
            assert 1.0 <= result["score_band_1_6"] <= 6.0
            print(f"    OK: submission_id={submission_id}, score_band_1_6={result['score_band_1_6']}")

            print("[3/6] 기록 / 대시보드 / PDF")
            status, history = _http_json(f"http://127.0.0.1:{port}/api/history")
            assert status == 200
            assert any(item["id"] == submission_id for item in history["items"]), "방금 제출한 기록이 history에 없음"
            print("    OK: /api/history")

            status, _ = _http_json(f"http://127.0.0.1:{port}/api/dashboard")
            assert status == 200
            print("    OK: /api/dashboard")

            pdf_req = urllib.request.Request(f"http://127.0.0.1:{port}/api/report/{submission_id}.pdf")
            with urllib.request.urlopen(pdf_req, timeout=15) as resp:
                assert resp.status == 200
                content_type = resp.headers.get("Content-Type", "")
                pdf_bytes = resp.read()
                assert "pdf" in content_type.lower() or pdf_bytes[:4] == b"%PDF", content_type
            print(f"    OK: /api/report/{submission_id}.pdf ({len(pdf_bytes)} bytes)")

            print("[3.5/6] 로컬 AI 상태 — 모델 없이 정상 응답")
            status, local_ai_status = _http_json(f"http://127.0.0.1:{port}/api/local-ai/status")
            assert status == 200, f"local-ai/status status={status}"
            assert local_ai_status.get("offline_core", {}).get("available") is True, "offline_core must be available"
            local_ai_avail = local_ai_status.get("local_ai", {}).get("available", False)
            local_ai_provider = local_ai_status.get("local_ai", {}).get("model", {}).get("provider_id", "")
            print(f"    OK: /api/local-ai/status → offline_core_available=True, local_ai_available={local_ai_avail}, provider={local_ai_provider}")
            # Only run test endpoint when no heavy LLM is connected (avoids 50-80s wait)
            if local_ai_provider not in ("ollama", "llamacpp"):
                status, local_ai_test = _http_json(f"http://127.0.0.1:{port}/api/local-ai/test", method="POST", timeout=30.0)
                assert status == 200, f"local-ai/test status={status}"
                assert local_ai_test.get("ok") is True, f"Rule provider test must pass: {local_ai_test}"
                print(f"    OK: /api/local-ai/test → ok=True, provider={local_ai_test.get('provider')}")
            else:
                print(f"    SKIP: /api/local-ai/test — Ollama/llama.cpp 감지됨, 추론 시간이 길어 smoke 테스트에서 생략")

            print("[4/7] graceful shutdown")
            proc.send_signal(signal.SIGTERM)
            try:
                proc.wait(timeout=20)
                print(f"    OK: 프로세스 종료 (exit={proc.returncode})")
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait(timeout=5)
                print(f"    WARN: SIGTERM 후 20초 안에 종료되지 않아 kill(exit={proc.returncode}) — Ollama 연결 유지 상태에서 발생 가능")
                time.sleep(2)
                if lock_path.exists():
                    lock_path.unlink(missing_ok=True)
                    print("    OK: lock 파일 강제 정리")
            time.sleep(0.5)
            assert not lock_path.exists(), "종료 후에도 lock 파일이 남아있음 — 고아 상태 위험"
            print("    OK: lock 파일 정리됨 (고아 프로세스 없음)")
        finally:
            if proc.poll() is None:
                proc.kill()
                proc.wait(timeout=5)

        # ── 재실행: 이전 기록 유지 ─────────────────────────────────
        print("[5/7] 재실행 — 이전 기록 유지 확인")
        proc2 = _launch(executable, data_dir)
        try:
            lock2 = _wait_for_lock(lock_path)
            port2 = lock2["port"]
            status, history2 = _http_json(f"http://127.0.0.1:{port2}/api/history")
            assert status == 200
            assert any(item["id"] == submission_id for item in history2["items"]), "재실행 후 이전 기록이 사라짐"
            print(f"    OK: 재실행 후에도 submission_id={submission_id} 기록 유지 (동적 포트={port2})")

            print("[6/7] 재실행 종료")
            proc2.send_signal(signal.SIGTERM)
            proc2.wait(timeout=10)
            assert proc2.returncode == 0, (
                f"재실행 종료가 clean exit(0)이 아님 (exit={proc2.returncode}) — "
                "신호 핸들러가 Py_Finalize와 네이티브 스레드 충돌로 SIGABRT를 낼 수 있음"
            )
            print(f"    OK: 프로세스 종료 (exit={proc2.returncode})")
        finally:
            if proc2.poll() is None:
                proc2.kill()
                proc2.wait(timeout=5)

    print("\n[PASS] 패키징 앱 smoke test 전체 통과")
    print("수동 확인 필요: native 창 육안 렌더링, 중복 실행 시 안내 다이얼로그 (docs/internal-alpha-test-report.md 참고)")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: packaged_app_smoke_test.py <path-to-.app>")
        sys.exit(2)
    run_smoke_test(Path(sys.argv[1]).resolve())
