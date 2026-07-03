"""프로젝트 루트 `data/`(Phase 4까지 사용)에서 OS 사용자 데이터 경로로 안전하게
이관하는 최초 실행 migration (Phase 5, 마스터 스펙 10장).

안전 원칙:
- 원본 DB는 **절대 삭제하지 않는다**
- 이관 실패 시 원본을 그대로 두고, 사용자 데이터 경로에는 아무것도 남기지 않는다
  (부분 테이블만 복사하고 완료 처리하지 않는다)
- 이관 전 대상 위치에 이미 DB가 있으면 건드리지 않는다(사용자가 이미 새 경로로
  실행한 적이 있다는 뜻일 수 있음 — 덮어쓰지 않는다)
- 이관 완료는 레코드 수 비교로 검증한 뒤에만 완료 마커를 남긴다
- 중복 migration을 방지하되, 실패한 시도는 다음 실행 시 재시도할 수 있어야 한다
"""

from __future__ import annotations

import shutil
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path

from app.paths import databases_dir, legacy_project_data_dir, migrations_dir

MIGRATION_MARKER_NAME = "legacy_data_migration_v1.complete"

_DB_FILENAMES = ["submissions.db", "shadow_assessments.db", "expert_data.db"]


@dataclass
class SingleDbMigrationResult:
    filename: str
    attempted: bool
    succeeded: bool
    source_row_count: int | None = None
    dest_row_count: int | None = None
    error: str | None = None


@dataclass
class MigrationReport:
    already_completed: bool
    performed: bool
    results: list[SingleDbMigrationResult] = field(default_factory=list)
    backup_dir: str | None = None


def _table_row_counts(db_path: Path) -> dict[str, int]:
    counts: dict[str, int] = {}
    conn = sqlite3.connect(db_path)
    try:
        conn.row_factory = sqlite3.Row
        tables = [
            r["name"] for r in conn.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        ]
        for table in tables:
            counts[table] = conn.execute(f"SELECT COUNT(*) AS c FROM '{table}'").fetchone()["c"]  # noqa: S608 — table명은 sqlite_master에서만 가져옴
    finally:
        conn.close()
    return counts


def _migrate_single_db(filename: str, source_dir: Path, dest_dir: Path) -> SingleDbMigrationResult:
    source_path = source_dir / filename
    dest_path = dest_dir / filename

    if not source_path.exists():
        return SingleDbMigrationResult(filename=filename, attempted=False, succeeded=False)

    if dest_path.exists():
        # 대상에 이미 파일이 있으면 덮어쓰지 않는다 — 이미 이관됐거나 사용자가
        # 새 경로에서 이미 실제로 앱을 써서 데이터가 쌓였을 수 있다.
        return SingleDbMigrationResult(
            filename=filename, attempted=True, succeeded=False,
            error="destination_already_exists_not_overwritten",
        )

    try:
        source_counts = _table_row_counts(source_path)
    except sqlite3.DatabaseError as exc:
        return SingleDbMigrationResult(filename=filename, attempted=True, succeeded=False, error=f"source_unreadable: {exc}")

    tmp_dest_path = dest_path.with_suffix(dest_path.suffix + ".migrating")
    try:
        # sqlite3 backup API로 일관된 스냅샷 복사 (파일 단순 copy보다 안전 — WAL 모드에서도 정합성 보장)
        src_conn = sqlite3.connect(source_path)
        dest_conn = sqlite3.connect(tmp_dest_path)
        try:
            src_conn.backup(dest_conn)
        finally:
            dest_conn.close()
            src_conn.close()

        dest_counts = _table_row_counts(tmp_dest_path)

        if dest_counts != source_counts:
            tmp_dest_path.unlink(missing_ok=True)
            return SingleDbMigrationResult(
                filename=filename, attempted=True, succeeded=False,
                source_row_count=sum(source_counts.values()), dest_row_count=sum(dest_counts.values()),
                error="record_count_mismatch_after_copy",
            )

        tmp_dest_path.rename(dest_path)
        return SingleDbMigrationResult(
            filename=filename, attempted=True, succeeded=True,
            source_row_count=sum(source_counts.values()), dest_row_count=sum(dest_counts.values()),
        )
    except Exception as exc:  # noqa: BLE001 — 실패를 리포트에 담아 원본을 보존한 채 반환
        tmp_dest_path.unlink(missing_ok=True)
        return SingleDbMigrationResult(filename=filename, attempted=True, succeeded=False, error=str(exc))


def migrate_legacy_data_if_needed() -> MigrationReport:
    """최초 실행 시 프로젝트 루트 data/의 DB를 사용자 데이터 경로로 안전하게 복사한다.

    이미 완료 마커가 있으면 아무 작업도 하지 않는다. 마커는 (이관 대상이 하나도
    없었거나) 존재했던 모든 DB가 성공적으로 이관됐을 때만 기록한다 — 부분 성공
    상태로 마커를 남기지 않아, 다음 실행에서 실패한 DB만 다시 시도할 수 있다.
    """
    marker_path = migrations_dir() / MIGRATION_MARKER_NAME
    if marker_path.exists():
        return MigrationReport(already_completed=True, performed=False)

    source_dir = legacy_project_data_dir()
    dest_dir = databases_dir()

    if not source_dir.exists():
        # 이관할 레거시 데이터 자체가 없다 (신규 설치) — 완료로 표시하고 끝낸다.
        marker_path.write_text("no_legacy_data_found\n", encoding="utf-8")
        return MigrationReport(already_completed=False, performed=True, results=[])

    backup_dir = source_dir / f".migration_backup_v1"
    backup_dir.mkdir(parents=True, exist_ok=True)
    for filename in _DB_FILENAMES:
        src = source_dir / filename
        if src.exists():
            shutil.copy2(src, backup_dir / filename)

    results = [_migrate_single_db(f, source_dir, dest_dir) for f in _DB_FILENAMES]

    attempted = [r for r in results if r.attempted]
    all_attempted_succeeded = all(r.succeeded for r in attempted)

    if all_attempted_succeeded:
        marker_path.write_text(
            "migrated:" + ",".join(r.filename for r in attempted if r.succeeded) + "\n",
            encoding="utf-8",
        )

    return MigrationReport(
        already_completed=False, performed=True, results=results, backup_dir=str(backup_dir),
    )
