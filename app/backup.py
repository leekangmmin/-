"""사용자 데이터 백업·복원 (Phase 6).

백업 대상은 사용자 기록이 모두 담긴 submissions.db 하나다(제출 기록,
Build a Sentence 기록, 작성 중 답안, 사용자 설정 전부 이 DB에 있다).
shadow_assessments.db / expert_data.db는 연구·개발용 데이터라 사용자 백업에
포함하지 않는다. API 키는 app_settings 테이블에 있으므로 백업 zip 생성 시
제거한 사본을 담는다 — 백업 파일이 다른 기기·사람에게 전달될 수 있기 때문.

백업 파일 형식: zip 안에
  - submissions.db  (sqlite3 .backup() API로 만든 일관된 스냅샷, API 키 제거본)
  - metadata.json   (앱 버전/스키마 버전/생성 시각/레코드 수)

복원 안전 절차:
  1. zip 구조·metadata 검증 (schema version 확인)
  2. 스냅샷 DB의 무결성(integrity_check)과 필수 테이블 확인
  3. 현재 DB를 pre_restore 안전 백업으로 자동 보존
  4. 교체 후 레코드 수 검증 — 실패 시 안전 백업에서 자동 롤백
"""

from __future__ import annotations

import json
import shutil
import sqlite3
import zipfile
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from app.db import DB_PATH, count_user_records, init_db
from app.paths import backups_dir
from app.version import APP_VERSION, DB_SCHEMA_VERSION

BACKUP_FORMAT_VERSION = "1"
_REQUIRED_TABLES = {"submissions", "app_settings", "bas_attempts", "drafts"}
# 백업 사본에서 제거할 민감 설정 키 (로컬 AI 연결용 API 키)
_SENSITIVE_SETTING_KEYS = ("openai_api_key", "anthropic_api_key", "gemini_api_key")


def _snapshot_db(source: Path, dest: Path) -> None:
    """sqlite3 backup API로 일관된 스냅샷을 만든다 (raw copy 금지 — WAL/락 안전)."""
    src = sqlite3.connect(source)
    try:
        dst = sqlite3.connect(dest)
        try:
            src.backup(dst)
        finally:
            dst.close()
    finally:
        src.close()


def _strip_sensitive_settings(db_path: Path) -> None:
    conn = sqlite3.connect(db_path)
    try:
        for key in _SENSITIVE_SETTING_KEYS:
            conn.execute("DELETE FROM app_settings WHERE key = ?", (key,))
        conn.commit()
        # DELETE만으로는 freed page에 키 바이트가 남을 수 있다 — VACUUM으로
        # 파일을 재작성해 삭제된 데이터를 물리적으로 제거한다.
        conn.execute("VACUUM")
    finally:
        conn.close()


def _read_sensitive_settings(db_path: Path) -> dict[str, str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute(
            f"SELECT key, value FROM app_settings WHERE key IN ({','.join('?' * len(_SENSITIVE_SETTING_KEYS))})",
            _SENSITIVE_SETTING_KEYS,
        ).fetchall()
        return {k: v for k, v in rows}
    finally:
        conn.close()


def _write_sensitive_settings(db_path: Path, values: dict[str, str]) -> None:
    if not values:
        return
    conn = sqlite3.connect(db_path)
    try:
        for key, value in values.items():
            conn.execute(
                "INSERT INTO app_settings (key, value) VALUES (?, ?) "
                "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
                (key, value),
            )
        conn.commit()
    finally:
        conn.close()


def _table_names(db_path: Path) -> set[str]:
    conn = sqlite3.connect(db_path)
    try:
        rows = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
        return {r[0] for r in rows}
    finally:
        conn.close()


def _integrity_ok(db_path: Path) -> bool:
    try:
        conn = sqlite3.connect(db_path)
        try:
            result = conn.execute("PRAGMA integrity_check").fetchone()
            return bool(result and result[0] == "ok")
        finally:
            conn.close()
    except sqlite3.Error:
        return False


def create_backup() -> dict[str, Any]:
    """백업 zip을 backups_dir에 생성하고 메타데이터를 반환한다."""
    init_db()
    created_at = datetime.now(UTC)
    counts = count_user_records()

    stamp = created_at.strftime("%Y%m%d-%H%M%S")
    backup_path = backups_dir() / f"toefl-writing-backup-{stamp}.zip"

    tmp_db = backups_dir() / f".backup-snapshot-{stamp}.db"
    try:
        _snapshot_db(DB_PATH, tmp_db)
        _strip_sensitive_settings(tmp_db)

        metadata = {
            "backup_format_version": BACKUP_FORMAT_VERSION,
            "app_version": APP_VERSION,
            "db_schema_version": DB_SCHEMA_VERSION,
            "created_at": created_at.isoformat(),
            "record_counts": counts,
            "included": ["submissions.db"],
            "excluded": ["shadow_assessments.db", "expert_data.db", "API 키"],
        }
        with zipfile.ZipFile(backup_path, "w", zipfile.ZIP_DEFLATED) as zf:
            zf.write(tmp_db, "submissions.db")
            zf.writestr("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2))
    finally:
        tmp_db.unlink(missing_ok=True)

    return {
        "filename": backup_path.name,
        "path": str(backup_path),
        "size_bytes": backup_path.stat().st_size,
        **{k: v for k, v in metadata.items() if k != "included"},
    }


def list_backups() -> list[dict[str, Any]]:
    """backups_dir의 백업 zip 목록(최신순). metadata를 읽을 수 없는 파일은 표시만 한다."""
    items: list[dict[str, Any]] = []
    for path in sorted(backups_dir().glob("toefl-writing-backup-*.zip"), reverse=True):
        entry: dict[str, Any] = {
            "filename": path.name,
            "size_bytes": path.stat().st_size,
            "readable": False,
        }
        try:
            with zipfile.ZipFile(path) as zf:
                metadata = json.loads(zf.read("metadata.json"))
            entry.update(
                readable=True,
                created_at=metadata.get("created_at"),
                app_version=metadata.get("app_version"),
                db_schema_version=metadata.get("db_schema_version"),
                record_counts=metadata.get("record_counts"),
            )
        except (zipfile.BadZipFile, KeyError, json.JSONDecodeError, OSError):
            pass
        items.append(entry)
    return items


class RestoreError(Exception):
    """복원 검증 실패 — 기존 데이터는 변경되지 않은 상태."""


def inspect_backup(filename: str) -> dict[str, Any]:
    """복원 전 미리보기: metadata와 현재 데이터 레코드 수를 함께 반환한다."""
    path = _resolve_backup_path(filename)
    try:
        with zipfile.ZipFile(path) as zf:
            names = set(zf.namelist())
            if "metadata.json" not in names or "submissions.db" not in names:
                raise RestoreError("백업 파일 구조가 올바르지 않습니다 (metadata.json/submissions.db 누락)")
            metadata = json.loads(zf.read("metadata.json"))
    except zipfile.BadZipFile:
        raise RestoreError("백업 파일이 손상되었거나 올바른 zip 형식이 아닙니다")
    except json.JSONDecodeError:
        raise RestoreError("백업 metadata를 읽을 수 없습니다 (손상된 파일)")
    if metadata.get("db_schema_version") != DB_SCHEMA_VERSION:
        raise RestoreError(
            f"데이터 스키마 버전이 다릅니다 (백업: {metadata.get('db_schema_version')}, "
            f"현재 앱: {DB_SCHEMA_VERSION}). 이 백업은 복원할 수 없습니다."
        )
    return {
        "backup": metadata,
        "current_record_counts": count_user_records(),
    }


def _resolve_backup_path(filename: str) -> Path:
    """경로 조작(../) 방지 — backups_dir 안의 파일명만 허용한다."""
    name = Path(filename).name
    path = backups_dir() / name
    if not path.exists():
        raise RestoreError(f"백업 파일을 찾을 수 없습니다: {name}")
    return path


def restore_backup(filename: str) -> dict[str, Any]:
    """백업에서 복원한다. 실패 시 기존 데이터로 자동 롤백한다."""
    init_db()
    path = _resolve_backup_path(filename)
    preview = inspect_backup(filename)  # 구조/스키마 검증 포함

    stamp = datetime.now(UTC).strftime("%Y%m%d-%H%M%S")
    extracted = backups_dir() / f".restore-incoming-{stamp}.db"
    safety = backups_dir() / f"pre-restore-safety-{stamp}.db"

    try:
        with zipfile.ZipFile(path) as zf, zf.open("submissions.db") as src, open(extracted, "wb") as dst:
            shutil.copyfileobj(src, dst)

        if not _integrity_ok(extracted):
            raise RestoreError("백업 안의 DB가 손상되어 있습니다 (integrity check 실패)")
        missing = _REQUIRED_TABLES - _table_names(extracted)
        if missing:
            raise RestoreError(f"백업 DB에 필수 테이블이 없습니다: {', '.join(sorted(missing))}")

        # 현재 데이터를 안전 백업으로 보존 (복원 실패 시 롤백 지점)
        _snapshot_db(DB_PATH, safety)

        # 백업에는 API 키가 제거돼 있으므로(생성 시 strip), 복원으로 이 기기의
        # 키가 소실되지 않게 현재 키를 읽어뒀다가 복원 후 다시 넣는다.
        current_keys = _read_sensitive_settings(DB_PATH)

        try:
            _snapshot_db(extracted, DB_PATH)
            _write_sensitive_settings(DB_PATH, current_keys)
            restored_counts = count_user_records()
            expected = preview["backup"].get("record_counts") or {}
            for table in ("submissions", "bas_attempts"):
                if table in expected and restored_counts.get(table) != expected[table]:
                    raise RestoreError(
                        f"복원 후 레코드 수 불일치 ({table}: 기대 {expected[table]}, 실제 {restored_counts.get(table)})"
                    )
        except Exception:
            _snapshot_db(safety, DB_PATH)  # 롤백
            raise

        return {
            "restored_from": path.name,
            "record_counts": restored_counts,
            "safety_backup": safety.name,
        }
    finally:
        extracted.unlink(missing_ok=True)
