#!/usr/bin/env python3
"""패키징 앱 업데이트 데이터 보존 테스트.

실제 구버전 빌드 아티팩트가 없으므로 구버전(v0.5.0) 스키마를 그대로 모사한
fixture DB(drafts 테이블 없음, 기록 2건 + BAS 기록 + 설정)를 사용자 데이터
디렉터리에 미리 넣고, "업데이트된" 신버전 .app이 그 위에서:
  1. 기존 기록을 ID 그대로 보존하는지
  2. 새 테이블(drafts)을 안전하게 추가하는지
  3. 새 평가가 기존 기록과 공존하는지 (ID 충돌 없음)
  4. PDF가 구버전 기록에서도 생성되는지
  5. 재시작 후 구·신 기록이 모두 유지되는지
를 검증한다.

usage: update_migration_test.py <path-to-.app>
"""

from __future__ import annotations

import json
import os
import signal
import sqlite3
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

ESSAY = (
    "Universities should invest more resources in mental health support for students "
    "because academic pressure has increased significantly in recent years. Many students "
    "struggle silently with anxiety and stress, and without adequate counseling services "
    "their academic performance and overall wellbeing suffer considerably over time. "
    "Providing accessible mental health resources on campus would help students manage "
    "these challenges early, before they escalate into more serious problems that affect "
    "graduation rates and long-term career success for everyone involved in education."
)


def _build_v050_fixture(data_dir: Path) -> None:
    db_dir = data_dir / "databases"
    db_dir.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(db_dir / "submissions.db")
    conn.executescript(
        """
        CREATE TABLE submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, prompt_type TEXT NOT NULL,
            prompt_text TEXT NOT NULL, essay_text TEXT NOT NULL, result_json TEXT NOT NULL
        );
        CREATE TABLE app_settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE bas_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            created_at TEXT NOT NULL, item_id TEXT NOT NULL, item_version TEXT NOT NULL,
            rubric_version TEXT NOT NULL, engine_version TEXT NOT NULL,
            is_correct INTEGER NOT NULL, match_type TEXT NOT NULL,
            time_spent_ms INTEGER, attempt_number INTEGER NOT NULL
        );
        """
    )
    result = {"estimated_score_0_5": 3.5, "score_band_1_6": 4.5, "estimated_score_30": 24, "engine": None}
    for i in (1, 2):
        conn.execute(
            "INSERT INTO submissions (created_at, prompt_type, prompt_text, essay_text, result_json) "
            "VALUES (?, 'academic_discussion', 'old prompt', ?, ?)",
            (f"2026-06-0{i}T00:00:00+00:00", f"old essay {i}", json.dumps(result)),
        )
    conn.execute(
        "INSERT INTO bas_attempts (created_at, item_id, item_version, rubric_version, engine_version, "
        "is_correct, match_type, time_spent_ms, attempt_number) "
        "VALUES ('2026-06-01T00:00:00+00:00', 'bas-001', '1.0.0', 'bas-rubric-1.0.0', "
        "'build-a-sentence-1.0.0', 1, 'exact', 5000, 1)"
    )
    conn.execute("INSERT INTO app_settings (key, value) VALUES ('ai_provider', 'local')")
    conn.commit()
    conn.close()


def _http_json(url: str, method: str = "GET", payload: dict | None = None, timeout: float = 10.0):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        body = resp.read()
        return resp.status, (json.loads(body) if body else {})


def _launch(executable: Path, data_dir: Path) -> subprocess.Popen:
    env = dict(os.environ)
    env["TOEFL_DATA_DIR"] = str(data_dir)
    env["TOEFL_NO_WINDOW"] = "1"  # 헤드리스 — 창 없이 서버만 (CI 안정성)
    env.pop("ANTHROPIC_API_KEY", None)
    return subprocess.Popen([str(executable)], env=env, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)


def _wait_port(lock_path: Path, timeout: float = 20.0) -> int:
    deadline = time.time() + timeout
    while time.time() < deadline:
        if lock_path.exists():
            try:
                return json.loads(lock_path.read_text())["port"]
            except (json.JSONDecodeError, OSError, KeyError):
                pass
        time.sleep(0.2)
    raise TimeoutError(f"lock not created: {lock_path}")


def _stop(proc: subprocess.Popen) -> None:
    proc.send_signal(signal.SIGTERM)
    proc.wait(timeout=10)
    assert proc.returncode == 0, f"graceful shutdown 실패 (exit={proc.returncode})"


def run(app_bundle: Path) -> None:
    from app.version import APP_BUNDLE_NAME

    executable = app_bundle / "Contents" / "MacOS" / APP_BUNDLE_NAME
    assert executable.exists(), f"executable not found: {executable}"

    with tempfile.TemporaryDirectory(prefix="toefl_update_test_") as tmp:
        data_dir = Path(tmp)
        lock_path = data_dir / "config" / "app.lock"

        print("[1/5] 구버전(v0.5.0 스키마) 사용자 데이터 fixture 생성")
        _build_v050_fixture(data_dir)

        print("[2/5] 신버전 앱을 구버전 데이터 위에서 실행")
        proc = _launch(executable, data_dir)
        try:
            port = _wait_port(lock_path)
            base = f"http://127.0.0.1:{port}"

            _, history = _http_json(f"{base}/api/history")
            ids = {item["id"] for item in history["items"]}
            assert ids == {1, 2}, f"기존 기록 보존 실패: {ids}"
            assert all(item["is_legacy"] for item in history["items"])
            print(f"    OK: 기존 기록 2건 보존 (ID {sorted(ids)}), legacy 표시됨")

            status, _ = _http_json(f"{base}/api/draft", "PUT", {"essay_text": "draft on upgraded db"})
            assert status == 200
            print("    OK: 새 drafts 테이블이 구버전 DB에 안전하게 추가됨")

            print("[3/5] 새 평가 생성 — 기존 기록과 공존")
            _, body = _http_json(f"{base}/api/evaluate", "POST", {"essay_text": ESSAY})
            new_id = body["submission_id"]
            assert new_id == 3, f"ID 충돌/불연속: {new_id}"
            print(f"    OK: 새 평가 ID={new_id} (AUTOINCREMENT 이어짐)")

            print("[4/5] 구버전 기록 PDF 생성")
            req = urllib.request.Request(f"{base}/api/report/1.pdf")
            with urllib.request.urlopen(req, timeout=15) as resp:
                pdf = resp.read()
                assert resp.status == 200 and pdf[:4] == b"%PDF"
            print(f"    OK: legacy 기록 PDF {len(pdf)} bytes")

            _stop(proc)
        finally:
            if proc.poll() is None:
                proc.kill()

        print("[5/5] 재시작 — 구·신 기록 모두 유지")
        proc2 = _launch(executable, data_dir)
        try:
            port2 = _wait_port(lock_path)
            _, history2 = _http_json(f"http://127.0.0.1:{port2}/api/history")
            ids2 = {item["id"] for item in history2["items"]}
            assert ids2 == {1, 2, 3}, f"재시작 후 기록 유실: {ids2}"
            _, draft = _http_json(f"http://127.0.0.1:{port2}/api/draft")
            assert draft["draft"]["essay_text"] == "draft on upgraded db"
            print("    OK: 재시작 후 기록 3건 + draft 유지")
            _stop(proc2)
        finally:
            if proc2.poll() is None:
                proc2.kill()

    print("\n[PASS] 업데이트 데이터 보존 테스트 전체 통과")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: update_migration_test.py <path-to-.app>")
        sys.exit(2)
    run(Path(sys.argv[1]).resolve())
