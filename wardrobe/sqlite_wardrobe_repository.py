"""SQLite implementation of WardrobeRepository."""

from __future__ import annotations

from pathlib import Path

from wardrobe.constants import CATEGORIES
from wardrobe.database import DEFAULT_DB_PATH, init_wardrobe_db, wardrobe_connection
from wardrobe.normalization import (
    clean_item_name,
    normalize_stored_color,
    normalize_style,
    resolve_stored_color,
    validate_category,
)
from wardrobe.wardrobe_repository import WardrobeRepository

DEFAULT_USER_ID = "default"


def _row_to_item(row) -> dict:
    """Convert a database row to the dict shape expected by agents."""
    item = {
        "id": row["id"],
        "name": row["name"],
        "category": row["category"],
        "color": row["color"],
        "style": row["style"],
    }
    if row["event"]:
        item["event"] = row["event"]
    if row["image_url"]:
        item["image_url"] = row["image_url"]
    return item


class SqliteWardrobeRepository(WardrobeRepository):
    """Load and save wardrobe data in SQLite, scoped by user_id."""

    def __init__(
        self,
        db_path: Path | str | None = None,
        user_id: str = DEFAULT_USER_ID,
    ) -> None:
        self._db_path = Path(db_path) if db_path is not None else DEFAULT_DB_PATH
        self._user_id = user_id
        self._initialize_database()

    @property
    def user_id(self) -> str:
        return self._user_id

    def _initialize_database(self) -> None:
        with wardrobe_connection(self._db_path) as connection:
            init_wardrobe_db(connection)

    def get_all(self) -> list[dict]:
        with wardrobe_connection(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, name, category, color, style, event, image_url
                FROM wardrobe_items
                WHERE user_id = ?
                ORDER BY category, name
                """,
                (self._user_id,),
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def get_by_category(self) -> dict[str, list[dict]]:
        grouped = {category: [] for category in CATEGORIES}
        for item in self.get_all():
            category = item.get("category")
            if category in grouped:
                grouped[category].append(item)
        return grouped

    def find_by_category(self, category: str) -> list[dict]:
        with wardrobe_connection(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, name, category, color, style, event, image_url
                FROM wardrobe_items
                WHERE user_id = ? AND category = ?
                ORDER BY name
                """,
                (self._user_id, category),
            ).fetchall()
        return [_row_to_item(row) for row in rows]

    def get_item_by_id(self, item_id: int) -> dict | None:
        with wardrobe_connection(self._db_path) as connection:
            row = connection.execute(
                """
                SELECT id, name, category, color, style, event, image_url
                FROM wardrobe_items
                WHERE id = ? AND user_id = ?
                """,
                (item_id, self._user_id),
            ).fetchone()
        if row is None:
            return None
        return _row_to_item(row)

    def find_by_color(self, color: str) -> list[dict]:
        normalized = normalize_stored_color(color)
        with wardrobe_connection(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, name, category, color, style, event, image_url
                FROM wardrobe_items
                WHERE user_id = ?
                ORDER BY category, name
                """,
                (self._user_id,),
            ).fetchall()

        matches: list[dict] = []
        for row in rows:
            item_color = normalize_stored_color(row["color"])
            if item_color == normalized:
                matches.append(_row_to_item(row))
        return matches

    def add_item(self, category: str, item: dict) -> bool:
        validate_category(category)

        name = clean_item_name(item.get("name", ""))
        if not name:
            return False

        color = resolve_stored_color(item.get("color"))
        style = normalize_style(item.get("style", "casual"))
        event = item.get("event")
        if isinstance(event, str):
            event = event.strip() or None

        image_url = item.get("image_url") or item.get("image_path")
        if isinstance(image_url, str):
            image_url = image_url.strip() or None
        else:
            image_url = None

        with wardrobe_connection(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO wardrobe_items (
                    user_id, name, category, color, style, event, image_url
                )
                VALUES (?, ?, ?, ?, ?, ?, ?)
                """,
                (self._user_id, name, category, color, style, event, image_url),
            )
        return True

    def update_item(self, item_id: int, item: dict) -> bool:
        """Update one item scoped by id and user_id. Refreshes updated_at."""
        fields: list[str] = []
        values: list[object] = []

        if "name" in item:
            name = clean_item_name(item.get("name", ""))
            if not name:
                return False
            fields.append("name = ?")
            values.append(name)

        if "category" in item:
            category = item.get("category")
            validate_category(category)
            fields.append("category = ?")
            values.append(category)

        if "color" in item:
            color = resolve_stored_color(item.get("color"))
            fields.append("color = ?")
            values.append(color)

        if "style" in item:
            style = normalize_style(item.get("style", "casual"))
            fields.append("style = ?")
            values.append(style)

        if "event" in item:
            event = item.get("event")
            if isinstance(event, str):
                event = event.strip() or None
            fields.append("event = ?")
            values.append(event)

        if "image_url" in item or "image_path" in item:
            image_url = item.get("image_url") or item.get("image_path")
            if isinstance(image_url, str):
                image_url = image_url.strip() or None
            else:
                image_url = None
            fields.append("image_url = ?")
            values.append(image_url)

        if not fields:
            return False

        fields.append("updated_at = datetime('now')")
        values.extend([item_id, self._user_id])

        with wardrobe_connection(self._db_path) as connection:
            cursor = connection.execute(
                f"""
                UPDATE wardrobe_items
                SET {", ".join(fields)}
                WHERE id = ? AND user_id = ?
                """,
                tuple(values),
            )
            return cursor.rowcount > 0

    def delete_item(self, item_id: int) -> bool:
        """Delete one item scoped by id and user_id."""
        with wardrobe_connection(self._db_path) as connection:
            cursor = connection.execute(
                """
                DELETE FROM wardrobe_items
                WHERE id = ? AND user_id = ?
                """,
                (item_id, self._user_id),
            )
            return cursor.rowcount > 0
