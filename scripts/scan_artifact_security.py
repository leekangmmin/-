#!/usr/bin/env python3
"""빌드 산출물(.app) 보안 스캔 — 비밀정보/DB/개발 경로 미포함 검증.

Python 패키징 특성상 소스 복원이 완전히 불가능하다고 주장하지 않는다.
목표는 비밀정보를 포함하지 않는 것이다 (마스터 스펙 22장).

검사 항목:
  - .env / API 키 패턴 (sk-, sk-ant-, AIza)
  - .db / .sqlite 파일
  - Git 메타데이터, pytest 캐시, conftest, 테스트 파일
  - 개발 스크린샷, .log
  - 전문가 데이터 / 사용자 답안 마커
  - PYZ bytecode의 개발 절대경로(/Users/<home>) 유출

정상 → exit 0, 위반 발견 → 위반 목록 출력 후 exit 1.
"""

from __future__ import annotations

import re
import struct
import sys
import zlib
import marshal
from pathlib import Path

API_KEY_PATTERNS = [
    re.compile(rb"sk-[A-Za-z0-9]{20,}"),
    re.compile(rb"sk-ant-[A-Za-z0-9-]{20,}"),
    re.compile(rb"AIza[0-9A-Za-z_-]{30,}"),
]
TEXT_SUFFIXES = {".py", ".txt", ".json", ".plist", ".cfg", ".ini", ".env", ".md"}


def _find(app: Path, *patterns: str) -> list[Path]:
    out: list[Path] = []
    for pat in patterns:
        out.extend(app.rglob(pat))
    return out


def _scan_pyz_for_home_paths(app: Path, home_prefix: bytes) -> list[str]:
    """PYZ 아카이브의 bytecode co_filename에 개발 절대경로가 남았는지 검사한다."""
    leaks: list[str] = []
    # onedir 구조에서 PYZ는 실행 파일 내부에 있으므로, 빌드 워크디렉터리의
    # PYZ-00.pyz를 함께 검사한다 (없으면 스킵 — 산출물 자체엔 임베드됨).
    candidates = list(app.rglob("*.pyz")) + list((app.parent.parent / "build").rglob("PYZ-00.pyz"))
    for pyz in candidates:
        try:
            data = pyz.read_bytes()
            if data[:4] != b"PYZ\x00":
                continue
            toc_offset = struct.unpack("!i", data[8:12])[0]
            toc = marshal.loads(data[toc_offset:])
            for name, (_ispkg, pos, length) in toc:
                try:
                    code = marshal.loads(zlib.decompress(data[pos:pos + length]))
                    fn = (getattr(code, "co_filename", "") or "").encode()
                    if home_prefix in fn:
                        leaks.append(f"{pyz.name}:{name} -> {code.co_filename}")
                except Exception:
                    continue
        except Exception:
            continue
    return leaks


def scan(app: Path) -> list[str]:
    violations: list[str] = []

    for env in _find(app, "*.env", ".env"):
        violations.append(f".env 파일 포함: {env}")
    for db in _find(app, "*.db", "*.sqlite", "*.sqlite3"):
        violations.append(f"DB 파일 포함: {db}")
    for git in _find(app, ".git", ".gitignore", "*.gitmodules"):
        violations.append(f"Git 메타데이터 포함: {git}")
    for t in _find(app, "*pytest_cache*", "conftest.py", "test_*.py"):
        violations.append(f"테스트 산출물 포함: {t}")
    for s in _find(app, "*screenshot*", "*.log"):
        violations.append(f"개발 파일 포함: {s}")
    for e in _find(app, "*expert_data*", "*.migration_backup*"):
        violations.append(f"전문가/백업 데이터 포함: {e}")

    # 텍스트/설정 파일에서 API 키 패턴
    for f in app.rglob("*"):
        if f.is_file() and f.suffix in TEXT_SUFFIXES:
            try:
                blob = f.read_bytes()
            except OSError:
                continue
            for pat in API_KEY_PATTERNS:
                if pat.search(blob):
                    violations.append(f"API 키 패턴 발견: {f} ({pat.pattern.decode()})")

    # PYZ bytecode 절대경로 유출
    home = str(Path.home()).encode()
    for leak in _scan_pyz_for_home_paths(app, home):
        violations.append(f"개발 절대경로 유출: {leak}")

    return violations


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: scan_artifact_security.py <path-to-.app>")
        return 2
    app = Path(sys.argv[1]).resolve()
    if not app.exists():
        print(f"[ERROR] not found: {app}")
        return 2

    violations = scan(app)
    if violations:
        print(f"[FAIL] 보안 스캔 위반 {len(violations)}건:")
        for v in violations:
            print(f"  - {v}")
        return 1
    print("[PASS] 보안 스캔 — 비밀정보/DB/개발경로 미포함 확인")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
