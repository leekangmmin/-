"""app/paths.py 리소스/사용자 데이터 경로 추상화 테스트.

conftest.py가 세션 전체에 TOEFL_DATA_DIR을 임시 디렉터리로 고정해두므로,
이 테스트들은 실제 OS 사용자 데이터 경로를 건드리지 않는다.
"""

from __future__ import annotations

import importlib
import os
from pathlib import Path

import pytest

import app.paths as paths_module


@pytest.fixture()
def isolated_data_dir(tmp_path, monkeypatch):
    monkeypatch.setenv("TOEFL_DATA_DIR", str(tmp_path / "custom_data"))
    return tmp_path / "custom_data"


class TestUserDataDirOverride:
    def test_env_override_is_used_and_created(self, isolated_data_dir):
        result = paths_module.user_data_dir()
        assert result == isolated_data_dir
        assert result.exists()

    def test_subdirs_created_under_override(self, isolated_data_dir):
        assert paths_module.databases_dir() == isolated_data_dir / "databases"
        assert paths_module.databases_dir().exists()
        assert paths_module.exports_dir() == isolated_data_dir / "exports"
        assert paths_module.backups_dir() == isolated_data_dir / "backups"
        assert paths_module.logs_dir() == isolated_data_dir / "logs"
        assert paths_module.config_dir() == isolated_data_dir / "config"
        assert paths_module.migrations_dir() == isolated_data_dir / "migrations"

    def test_no_override_falls_back_to_platformdirs(self, monkeypatch):
        monkeypatch.delenv("TOEFL_DATA_DIR", raising=False)
        result = paths_module.user_data_dir()
        assert "TOEFL Writing" in str(result)


class TestResourcePath:
    def test_source_mode_resolves_to_project_root(self):
        result = paths_module.resource_path("static", "index.html")
        assert result.exists()

    def test_is_frozen_false_in_source_mode(self):
        assert paths_module.is_frozen() is False

    def test_frozen_mode_uses_meipass(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.setattr(sys, "_MEIPASS", "/fake/bundle/root", raising=False)
        result = paths_module.resource_path("static")
        assert str(result) == "/fake/bundle/root/static"
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)

    def test_frozen_onedir_without_meipass_uses_executable_dir(self, monkeypatch):
        import sys

        monkeypatch.setattr(sys, "frozen", True, raising=False)
        monkeypatch.delattr(sys, "_MEIPASS", raising=False)
        monkeypatch.setattr(sys, "executable", "/fake/onedir/App.app/Contents/MacOS/App", raising=False)
        result = paths_module.resource_path("static")
        assert str(result) == "/fake/onedir/App.app/Contents/MacOS/static"


class TestSpecialPathCharacters:
    def test_korean_path_supported(self, tmp_path, monkeypatch):
        korean_dir = tmp_path / "토플 채점기 데이터"
        monkeypatch.setenv("TOEFL_DATA_DIR", str(korean_dir))
        result = paths_module.user_data_dir()
        assert result == korean_dir
        assert result.exists()

    def test_space_in_path_supported(self, tmp_path, monkeypatch):
        space_dir = tmp_path / "Application Support" / "TOEFL Writing"
        monkeypatch.setenv("TOEFL_DATA_DIR", str(space_dir))
        result = paths_module.user_data_dir()
        assert result.exists()
        assert (paths_module.databases_dir()).exists()


class TestLegacyProjectDataDir:
    def test_points_to_project_root_data(self):
        result = paths_module.legacy_project_data_dir()
        assert result.name == "data"
        assert result.parent == paths_module._SOURCE_ROOT
