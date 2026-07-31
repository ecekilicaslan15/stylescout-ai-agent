"""Tests for WardrobeService delegation."""

import os
from unittest.mock import MagicMock, patch

from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.repository_factory import WARDROBE_BACKEND_ENV
from wardrobe.sqlite_wardrobe_repository import SqliteWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService


class TestWardrobeService:
    def test_list_items_delegates_to_repository(self):
        repository = MagicMock()
        repository.get_all.return_value = [{"name": "Service Shirt", "category": "tops"}]

        items = WardrobeService(repository=repository, auto_seed=False).list_items()

        repository.get_all.assert_called_once_with()
        assert items[0]["name"] == "Service Shirt"

    def test_get_items_by_category_delegates_to_repository(self):
        repository = MagicMock()
        repository.get_by_category.return_value = {"tops": [{"name": "Service Shirt"}]}

        grouped = WardrobeService(repository=repository, auto_seed=False).get_items_by_category()

        repository.get_by_category.assert_called_once_with()
        assert grouped["tops"][0]["name"] == "Service Shirt"

    def test_add_item_delegates_to_repository(self):
        repository = MagicMock()
        repository.add_item.return_value = True
        payload = {"name": "Service Shirt", "color": "white", "style": "casual"}

        added = WardrobeService(repository=repository, auto_seed=False).add_item("tops", payload)

        repository.add_item.assert_called_once_with("tops", payload, allow_duplicate=False)
        assert added is True

    def test_defaults_to_factory_repository(self):
        with patch.dict(os.environ, {}, clear=True):
            service = WardrobeService()

        assert isinstance(service._repository, JsonWardrobeRepository)

    def test_respects_environment_backend(self, monkeypatch):
        monkeypatch.setenv(WARDROBE_BACKEND_ENV, "sqlite")

        service = WardrobeService()

        assert isinstance(service._repository, SqliteWardrobeRepository)
