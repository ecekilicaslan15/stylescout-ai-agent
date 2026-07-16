"""Tests for SQLite wardrobe persistence."""

import sqlite3
from unittest.mock import MagicMock, patch

import pytest

from wardrobe.constants import CATEGORIES
from wardrobe.database import init_wardrobe_db, wardrobe_connection
from wardrobe.sqlite_wardrobe_repository import SqliteWardrobeRepository


@pytest.fixture
def db_path(tmp_path):
    return tmp_path / "test_wardrobe.db"


@pytest.fixture
def repository(db_path) -> SqliteWardrobeRepository:
    return SqliteWardrobeRepository(db_path=db_path, user_id="user-a")


class TestWardrobeDatabase:
    def test_init_creates_wardrobe_items_table(self, db_path):
        with wardrobe_connection(db_path) as connection:
            init_wardrobe_db(connection)

        with wardrobe_connection(db_path) as connection:
            row = connection.execute(
                """
                SELECT name
                FROM sqlite_master
                WHERE type = 'table' AND name = 'wardrobe_items'
                """
            ).fetchone()

        assert row is not None
        assert row["name"] == "wardrobe_items"

    def test_repository_initializes_database_on_construction(self, db_path):
        SqliteWardrobeRepository(db_path=db_path)

        with wardrobe_connection(db_path) as connection:
            columns = connection.execute("PRAGMA table_info(wardrobe_items)").fetchall()
            column_names = {column["name"] for column in columns}

        assert column_names == {
            "id",
            "user_id",
            "name",
            "category",
            "color",
            "style",
            "event",
            "image_url",
            "created_at",
            "updated_at",
        }


class TestSqliteWardrobeRepository:
    def test_add_item_persists_item(self, repository: SqliteWardrobeRepository, db_path):
        added = repository.add_item(
            "tops",
            {
                "name": "SQLite White Shirt",
                "color": "white",
                "style": "casual",
                "event": "daily",
                "image_url": "/uploads/shirt.jpg",
            },
        )

        assert added is True
        items = repository.get_all()
        assert len(items) == 1
        assert items[0]["name"] == "SQLite White Shirt"
        assert items[0]["category"] == "tops"
        assert items[0]["color"] == "white"
        assert items[0]["style"] == "casual"
        assert items[0]["event"] == "daily"
        assert items[0]["image_url"] == "/uploads/shirt.jpg"
        assert isinstance(items[0]["id"], int)

    def test_add_item_allows_duplicate_name_in_same_category(
        self,
        repository: SqliteWardrobeRepository,
    ):
        payload = {"name": "White Shirt", "color": "white", "style": "casual"}

        assert repository.add_item("tops", payload) is True
        assert repository.add_item("tops", payload) is True

        items = repository.get_all()
        assert len(items) == 2
        assert all(item["name"] == "White Shirt" for item in items)
        assert items[0]["id"] != items[1]["id"]

    def test_get_by_category_groups_items(self, repository: SqliteWardrobeRepository):
        repository.add_item(
            "tops",
            {"name": "Blue Blouse", "color": "blue", "style": "elegant"},
        )
        repository.add_item(
            "shoes",
            {"name": "White Sneakers", "color": "white", "style": "casual"},
        )

        grouped = repository.get_by_category()

        assert len(grouped["tops"]) == 1
        assert len(grouped["shoes"]) == 1
        assert grouped["bottoms"] == []
        for category in CATEGORIES:
            assert category in grouped

    def test_find_by_category_filters_items(self, repository: SqliteWardrobeRepository):
        repository.add_item(
            "bottoms",
            {"name": "Blue Jeans", "color": "blue", "style": "casual"},
        )

        jeans = repository.find_by_category("bottoms")
        tops = repository.find_by_category("tops")

        assert len(jeans) == 1
        assert jeans[0]["name"] == "Blue Jeans"
        assert tops == []

    def test_find_by_color_normalizes_gray(self, repository: SqliteWardrobeRepository):
        repository.add_item(
            "outerwear",
            {"name": "Grey Cardigan", "color": "gray", "style": "casual"},
        )

        matches = repository.find_by_color("grey")

        assert len(matches) == 1
        assert matches[0]["name"] == "Grey Cardigan"

    def test_user_isolation(self, db_path):
        user_a = SqliteWardrobeRepository(db_path=db_path, user_id="user-a")
        user_b = SqliteWardrobeRepository(db_path=db_path, user_id="user-b")

        user_a.add_item(
            "tops",
            {"name": "User A Shirt", "color": "white", "style": "casual"},
        )
        user_b.add_item(
            "tops",
            {"name": "User B Shirt", "color": "black", "style": "elegant"},
        )

        user_a_items = user_a.get_all()
        user_b_items = user_b.get_all()

        assert [item["name"] for item in user_a_items] == ["User A Shirt"]
        assert [item["name"] for item in user_b_items] == ["User B Shirt"]

    def test_get_item_by_id_is_scoped_to_user(self, db_path):
        owner = SqliteWardrobeRepository(db_path=db_path, user_id="user-a")
        other = SqliteWardrobeRepository(db_path=db_path, user_id="user-b")

        owner.add_item(
            "tops",
            {"name": "Owned Shirt", "color": "white", "style": "casual"},
        )
        item_id = owner.get_all()[0]["id"]

        assert owner.get_item_by_id(item_id) is not None
        assert other.get_item_by_id(item_id) is None

    def test_update_item_refreshes_updated_at(self, repository: SqliteWardrobeRepository, db_path):
        repository.add_item(
            "tops",
            {"name": "Update Me", "color": "white", "style": "casual"},
        )
        item_id = repository.get_all()[0]["id"]

        with wardrobe_connection(db_path) as connection:
            before = connection.execute(
                "SELECT updated_at FROM wardrobe_items WHERE id = ? AND user_id = ?",
                (item_id, repository.user_id),
            ).fetchone()["updated_at"]

        assert repository.update_item(item_id, {"color": "black"}) is True

        with wardrobe_connection(db_path) as connection:
            after_row = connection.execute(
                "SELECT updated_at, color FROM wardrobe_items WHERE id = ? AND user_id = ?",
                (item_id, repository.user_id),
            ).fetchone()

        assert after_row["color"] == "black"
        assert after_row["updated_at"] >= before

    def test_user_cannot_update_or_delete_another_users_item(self, db_path):
        owner = SqliteWardrobeRepository(db_path=db_path, user_id="user-a")
        other = SqliteWardrobeRepository(db_path=db_path, user_id="user-b")

        owner.add_item(
            "tops",
            {"name": "Protected Shirt", "color": "white", "style": "casual"},
        )
        item_id = owner.get_all()[0]["id"]

        assert other.update_item(item_id, {"color": "black"}) is False
        assert other.delete_item(item_id) is False

        item = owner.get_item_by_id(item_id)
        assert item is not None
        assert item["color"] == "white"

        assert owner.delete_item(item_id) is True
        assert owner.get_item_by_id(item_id) is None

    def test_wardrobe_connection_commits_and_closes(self, db_path):
        mock_connection = MagicMock()

        with patch("wardrobe.database.sqlite3.connect", return_value=mock_connection):
            with wardrobe_connection(db_path):
                mock_connection.execute("SELECT 1")

        mock_connection.commit.assert_called_once()
        mock_connection.close.assert_called_once()

    def test_wardrobe_connection_rolls_back_on_error(self, db_path):
        mock_connection = MagicMock()
        mock_connection.execute.side_effect = sqlite3.Error("boom")

        with patch("wardrobe.database.sqlite3.connect", return_value=mock_connection):
            with pytest.raises(sqlite3.Error):
                with wardrobe_connection(db_path):
                    mock_connection.execute("SELECT 1")

        mock_connection.rollback.assert_called_once()
        mock_connection.close.assert_called_once()
