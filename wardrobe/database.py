"""SQLite schema and connection helpers for wardrobe persistence."""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "wardrobe.db"

WARDROBE_ITEMS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS wardrobe_items (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT NOT NULL,
    name TEXT NOT NULL,
    category TEXT NOT NULL,
    color TEXT NOT NULL,
    style TEXT NOT NULL DEFAULT 'casual',
    event TEXT,
    image_url TEXT,
    created_at TEXT NOT NULL DEFAULT (datetime('now')),
    updated_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

WARDROBE_ITEMS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_user_id
    ON wardrobe_items (user_id);
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_user_category
    ON wardrobe_items (user_id, category);
CREATE INDEX IF NOT EXISTS idx_wardrobe_items_user_color
    ON wardrobe_items (user_id, color);
"""


def init_wardrobe_db(connection: sqlite3.Connection) -> None:
    """Create wardrobe tables and indexes if they do not exist."""
    connection.executescript(WARDROBE_ITEMS_TABLE_SQL + WARDROBE_ITEMS_INDEX_SQL)


@contextmanager
def wardrobe_connection(db_path: Path | str) -> Iterator[sqlite3.Connection]:
    """Open a SQLite connection, commit on success, and always close it."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)

    connection = sqlite3.connect(path)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    except Exception:
        connection.rollback()
        raise
    finally:
        connection.close()
