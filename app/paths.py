"""리소스 경로 / 사용자 데이터 경로 추상화 (Phase 5).

PyInstaller로 패키징된 앱은 `sys._MEIPASS`(onefile) 또는 실행 파일 옆
디렉터리(onedir)에서 번들 리소스를 찾아야 하고, 현재 작업 디렉터리나 소스
트리 경로에 의존하면 안 된다. 이 모듈이 모든 리소스/데이터 경로 조회의
단일 진입점이다 — 다른 코드에서 `os.getcwd()`나 `Path(__file__).../data`를
직접 조합하지 않는다.

경로 우선순위(사용자 데이터):
1. `TOEFL_DATA_DIR` 환경변수 — 테스트/개발 환경에서 명시적으로 override
2. OS 기본 사용자 데이터 경로(`platformdirs`) — 프로덕션 기본값

패키지 리소스(정적 파일, 폰트, 자체 문항 등)는 항상 읽기 전용으로 취급하고,
쓰기는 전부 사용자 데이터 디렉터리 아래에서만 수행한다.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

import platformdirs

APP_NAME = "TOEFL Writing"

# 소스 체크아웃 루트 (dev/pytest 모드의 리소스 탐색 기준점, 데이터 저장에는 쓰지 않음)
_SOURCE_ROOT = Path(__file__).resolve().parent.parent


def is_frozen() -> bool:
    """PyInstaller로 패키징된 실행 파일에서 실행 중인지 확인한다."""
    return bool(getattr(sys, "frozen", False))


def _bundle_root() -> Path:
    """번들된 리소스가 위치한 루트를 반환한다.

    - PyInstaller onefile: `sys._MEIPASS`(임시 압축 해제 디렉터리)
    - PyInstaller onedir: 실행 파일이 위치한 디렉터리
    - 소스/개발/pytest 모드: 프로젝트 체크아웃 루트
    """
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    if is_frozen():
        return Path(sys.executable).resolve().parent
    return _SOURCE_ROOT


def resource_path(*parts: str) -> Path:
    """읽기 전용 번들 리소스(static/templates/font/자체 문항/설정/라이선스 등) 경로.

    반환된 경로에 쓰기를 시도하지 마라 — 패키징된 앱에서는 읽기 전용이거나
    코드 서명이 깨질 수 있는 위치다. 사용자 데이터는 항상 user_data_dir() 계열을 써라.
    """
    return _bundle_root().joinpath(*parts)


def _env_override() -> Path | None:
    raw = os.environ.get("TOEFL_DATA_DIR", "").strip()
    if not raw:
        return None
    return Path(raw).expanduser()


def user_data_dir() -> Path:
    """사용자 데이터 최상위 디렉터리. 앱 패키지 내부나 프로젝트 루트가 아니다.

    우선순위: TOEFL_DATA_DIR 환경변수 > OS 표준 사용자 데이터 경로
    (macOS: ~/Library/Application Support/TOEFL Writing).
    """
    override = _env_override()
    if override is not None:
        override.mkdir(parents=True, exist_ok=True)
        return override
    path = Path(platformdirs.user_data_dir(APP_NAME, appauthor=False))
    path.mkdir(parents=True, exist_ok=True)
    return path


def _subdir(name: str) -> Path:
    path = user_data_dir() / name
    path.mkdir(parents=True, exist_ok=True)
    return path


def databases_dir() -> Path:
    return _subdir("databases")


def exports_dir() -> Path:
    return _subdir("exports")


def backups_dir() -> Path:
    return _subdir("backups")


def logs_dir() -> Path:
    return _subdir("logs")


def config_dir() -> Path:
    return _subdir("config")


def migrations_dir() -> Path:
    return _subdir("migrations")


def models_dir() -> Path:
    return _subdir("models")


def legacy_project_data_dir() -> Path:
    """Phase 4까지 쓰이던 프로젝트 루트 `data/` 디렉터리 — migration의 원본 위치.

    소스 체크아웃 기준이며, PyInstaller 패키지 안에는 존재하지 않는다
    (패키지에는 사용자 DB를 절대 포함하지 않으므로).
    """
    return _SOURCE_ROOT / "data"
