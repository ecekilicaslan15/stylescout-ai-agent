"""Tests for wardrobe repository factory."""

import os
from unittest.mock import patch

import pytest

from wardrobe.json_wardrobe_repository import DEFAULT_JSON_PATH, JsonWardrobeRepository
from wardrobe.repository_factory import WARDROBE_BACKEND_ENV, create_wardrobe_repository
from wardrobe.sqlite_wardrobe_repository import SqliteWardrobeRepository


class TestRepositoryFactory:
    def test_defaults_to_json_repository(self):
        with patch.dict(os.environ, {}, clear=True):
            repository = create_wardrobe_repository()

        assert isinstance(repository, JsonWardrobeRepository)

    def test_explicit_json_backend(self):
        repository = create_wardrobe_repository(backend="json")
        assert isinstance(repository, JsonWardrobeRepository)

    def test_explicit_sqlite_backend(self):
        with patch.dict(os.environ, {}, clear=True):
            repository = create_wardrobe_repository(
                backend="sqlite",
                user_id="user-test",
            )

        assert isinstance(repository, SqliteWardrobeRepository)
        assert repository.user_id == "user-test"

    def test_environment_variable_selects_backend(self, tmp_path, monkeypatch):
        monkeypatch.setenv(WARDROBE_BACKEND_ENV, "sqlite")

        repository = create_wardrobe_repository(user_id="env-user")

        assert isinstance(repository, SqliteWardrobeRepository)
        assert repository.user_id == "env-user"

    def test_explicit_backend_overrides_environment(self, monkeypatch):
        monkeypatch.setenv(WARDROBE_BACKEND_ENV, "sqlite")

        repository = create_wardrobe_repository(backend="json")

        assert isinstance(repository, JsonWardrobeRepository)

    def test_invalid_backend_raises_clear_error(self):
        with pytest.raises(ValueError, match="Unsupported wardrobe backend: 'postgres'"):
            create_wardrobe_repository(backend="postgres")

    def test_json_default_path_is_file_relative(self):
        repository = JsonWardrobeRepository()
        assert repository._path == DEFAULT_JSON_PATH
        assert repository._path.name == "wardrobe.json"
        assert repository._path.parent.name == "wardrobe"
