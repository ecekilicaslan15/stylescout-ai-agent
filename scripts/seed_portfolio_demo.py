#!/usr/bin/env python3
"""Seed an isolated SQLite DB with ~15 fictional wardrobe items for portfolio demos.

Creates data/portfolio_demo.db (gitignored). No secrets, no .env writes.

Demo tenant: user_id ``default`` (use Cookie stylescout_session=default with
ALLOW_DEFAULT_OVERRIDE=true for local UI/screenshots only).

Usage:
  python scripts/seed_portfolio_demo.py
  WARDROBE_BACKEND=sqlite DB_PATH=data/portfolio_demo.db ALLOW_DEFAULT_OVERRIDE=true \\
    uvicorn api.main:app --host 127.0.0.1 --port 8000
"""

from __future__ import annotations

import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wardrobe.database import init_wardrobe_db, wardrobe_connection  # noqa: E402

DB_PATH = ROOT / "data" / "portfolio_demo.db"
DEMO_USER_ID = "default"

# Fictional catalog entries — varied categories, colors, seasons (via event).
PORTFOLIO_ITEMS: list[dict] = [
    {"name": "Ivory Linen Shirt", "category": "tops", "color": "white", "style": "casual", "event": "summer"},
    {"name": "Charcoal Merino Sweater", "category": "tops", "color": "grey", "style": "casual", "event": "winter"},
    {"name": "Rust Silk Blouse", "category": "tops", "color": "rust", "style": "elegant", "event": "spring"},
    {"name": "Indigo Straight Jeans", "category": "bottoms", "color": "blue", "style": "casual", "event": "all-season"},
    {"name": "Camel Wide-Leg Trousers", "category": "bottoms", "color": "camel", "style": "elegant", "event": "office"},
    {"name": "Black Tailored Trousers", "category": "bottoms", "color": "black", "style": "elegant", "event": "formal"},
    {"name": "White Leather Sneakers", "category": "shoes", "color": "white", "style": "casual", "event": "everyday"},
    {"name": "Tan Ankle Boots", "category": "shoes", "color": "tan", "style": "elegant", "event": "autumn"},
    {"name": "Navy Loafers", "category": "shoes", "color": "navy", "style": "elegant", "event": "office"},
    {"name": "Olive Trench Coat", "category": "outerwear", "color": "neutral", "style": "elegant", "event": "spring"},
    {"name": "Black Wool Blazer", "category": "outerwear", "color": "black", "style": "elegant", "event": "formal"},
    {"name": "Beige Quilted Jacket", "category": "outerwear", "color": "beige", "style": "casual", "event": "winter"},
    {"name": "Gold Hoop Earrings", "category": "accessories", "color": "gold", "style": "elegant", "event": "evening"},
    {"name": "Navy Crossbody Bag", "category": "accessories", "color": "navy", "style": "casual", "event": "everyday"},
    {"name": "Grey Wool Scarf", "category": "accessories", "color": "grey", "style": "casual", "event": "winter"},
]


def seed_database(db_path: Path) -> int:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    if db_path.exists():
        db_path.unlink()

    with wardrobe_connection(db_path) as connection:
        init_wardrobe_db(connection)
        for item in PORTFOLIO_ITEMS:
            connection.execute(
                """
                INSERT INTO wardrobe_items (
                    user_id, name, category, color, style, event,
                    image_url, source, owned
                )
                VALUES (?, ?, ?, ?, ?, ?, NULL, 'wardrobe', 1)
                """,
                (
                    DEMO_USER_ID,
                    item["name"],
                    item["category"],
                    item["color"],
                    item["style"],
                    item["event"],
                ),
            )
        count = connection.execute("SELECT COUNT(*) FROM wardrobe_items").fetchone()[0]
        connection.commit()
    return int(count)


def main() -> None:
    inserted = seed_database(DB_PATH)
    print(f"Seeded {inserted} items for user_id={DEMO_USER_ID!r} → {DB_PATH}")


if __name__ == "__main__":
    main()
