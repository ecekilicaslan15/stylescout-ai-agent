"""SQLite schema and connection helpers for wardrobe persistence."""

from __future__ import annotations

import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

DEFAULT_DB_PATH = Path(__file__).resolve().parent / "wardrobe.db"


def get_db_path() -> Path:
    """Return the configured SQLite path, defaulting to the local dev location."""
    configured = os.getenv("DB_PATH")
    if configured:
        return Path(configured)
    return DEFAULT_DB_PATH

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
    source TEXT NOT NULL DEFAULT 'wardrobe',
    owned INTEGER NOT NULL DEFAULT 1,
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


def _ensure_wardrobe_item_columns(connection: sqlite3.Connection) -> None:
    """Add columns introduced after the initial schema (idempotent)."""
    columns = {
        row["name"]
        for row in connection.execute("PRAGMA table_info(wardrobe_items)").fetchall()
    }
    if "source" not in columns:
        connection.execute(
            "ALTER TABLE wardrobe_items ADD COLUMN source TEXT NOT NULL DEFAULT 'wardrobe'"
        )
    if "owned" not in columns:
        connection.execute(
            "ALTER TABLE wardrobe_items ADD COLUMN owned INTEGER NOT NULL DEFAULT 1"
        )


SAVED_OUTFITS_TABLE_SQL = """
CREATE TABLE IF NOT EXISTS saved_outfits (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    outfit_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
"""

SAVED_OUTFITS_INDEX_SQL = """
CREATE INDEX IF NOT EXISTS idx_saved_outfits_user_id
    ON saved_outfits (user_id);
CREATE INDEX IF NOT EXISTS idx_saved_outfits_user_created
    ON saved_outfits (user_id, created_at DESC);
"""


def init_saved_outfits_db(connection: sqlite3.Connection) -> None:
    """Create saved outfit tables and indexes if they do not exist."""
    connection.executescript(SAVED_OUTFITS_TABLE_SQL + SAVED_OUTFITS_INDEX_SQL)


def init_wardrobe_db(connection: sqlite3.Connection) -> None:
    """Create wardrobe tables and indexes if they do not exist."""
    connection.executescript(WARDROBE_ITEMS_TABLE_SQL + WARDROBE_ITEMS_INDEX_SQL)
    _ensure_wardrobe_item_columns(connection)
    init_saved_outfits_db(connection)


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
