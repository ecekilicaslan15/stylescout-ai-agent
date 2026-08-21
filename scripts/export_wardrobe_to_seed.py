#!/usr/bin/env python3
"""One-off: merge local default-user wardrobe rows into wardrobe/wardrobe.json seed.

Uses WardrobeService + repository_factory (respects WARDROBE_BACKEND / DB_PATH /
WARDROBE_JSON_PATH from the environment). Does not import app startup or agents.

Seed target: wardrobe/seed.py SAMPLE_WARDROBE_PATH (same file as api/main.py
seed_wardrobe_if_empty() reads for SQLite bootstrap).
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from wardrobe.constants import CATEGORIES
from wardrobe.item_metadata import build_unique_item_id, utc_timestamp
from wardrobe.normalization import (
    clean_item_name,
    normalize_stored_category,
    normalize_stored_color,
    normalize_style,
)
from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.seed import LEGACY_USER_ID, SAMPLE_WARDROBE_PATH
from wardrobe.wardrobe_service import WardrobeService

# Fields present on every row in committed wardrobe/wardrobe.json (SCOUT-006 metadata).
SEED_REQUIRED_FIELDS = (
    "name",
    "category",
    "color",
    "style",
    "id",
    "user_id",
    "source",
    "owned",
    "created_at",
    "updated_at",
)


def _visual_identity_key(item: dict) -> tuple[str, str, str]:
    """Fallback dedup when ids differ across backends (e.g. SQLite INTEGER vs itm_*)."""
    category = normalize_stored_category(item.get("category") or "")
    name = clean_item_name(item.get("name") or "").lower()
    color = normalize_stored_color(item.get("color") or "neutral")
    return (category, name, color)


def _normalize_seed_id(item: dict) -> str:
    """Map WardrobeService item id to seed-file id string.

    JSON repository rows already use itm_* strings. SQLite uses INTEGER PRIMARY KEY
    autoincrement — those are exported as itm_<zero_padded_hex> so seed ids stay
    string-shaped and content-independent per SCOUT-006.
    """
    raw = item.get("id")
    if raw is None:
        return build_unique_item_id()
    text = str(raw).strip()
    if text.startswith("itm_"):
        return text
    if text.isdigit():
        return f"itm_{int(text):08x}"
    return f"itm_{text}"


def service_item_to_seed_row(item: dict) -> dict:
    """Serialize one WardrobeService list_items() row to wardrobe.json entry shape."""
    category = normalize_stored_category(item.get("category") or "")
    now = utc_timestamp()
    row: dict = {
        "name": clean_item_name(item.get("name") or ""),
        "category": category,
        "color": normalize_stored_color(item.get("color") or "neutral"),
        "style": normalize_style(item.get("style") or "casual"),
        "id": _normalize_seed_id(item),
        "user_id": LEGACY_USER_ID,
        "source": item.get("source") or "wardrobe",
        "owned": bool(item.get("owned", True)),
        "created_at": item.get("created_at") or now,
        "updated_at": item.get("updated_at") or now,
    }
    event = item.get("event")
    if isinstance(event, str) and event.strip():
        row["event"] = event.strip()
    image_url = item.get("image_url")
    if isinstance(image_url, str) and image_url.strip():
        row["image_url"] = image_url.strip()
    return row


def load_seed_file(path: Path) -> dict[str, list[dict]]:
    with path.open(encoding="utf-8") as handle:
        data = json.load(handle)
    grouped = {category: list(data.get(category, [])) for category in CATEGORIES}
    return grouped


def count_items(grouped: dict[str, list[dict]]) -> int:
    return sum(len(grouped.get(category, [])) for category in CATEGORIES)


def merge_local_into_seed(
    seed_data: dict[str, list[dict]],
    local_items: list[dict],
) -> int:
    """Append local rows not already in seed (by id, else category+name+color). Returns added count."""
    existing_ids: set[str] = set()
    existing_visual: set[tuple[str, str, str]] = set()
    for category in CATEGORIES:
        for row in seed_data.get(category, []):
            if row.get("id") is not None:
                existing_ids.add(str(row["id"]))
            existing_visual.add(_visual_identity_key(row))

    added = 0
    for item in local_items:
        if item.get("user_id", LEGACY_USER_ID) != LEGACY_USER_ID:
            continue
        row = service_item_to_seed_row(item)
        row_id = row["id"]
        visual = _visual_identity_key(row)
        if row_id in existing_ids or visual in existing_visual:
            continue
        category = row["category"]
        seed_data.setdefault(category, []).append(row)
        existing_ids.add(row_id)
        existing_visual.add(visual)
        added += 1
    return added


def main() -> None:
    seed_path = SAMPLE_WARDROBE_PATH
    seed_data = load_seed_file(seed_path)
    before = count_items(seed_data)

    repository = create_wardrobe_repository(user_id=LEGACY_USER_ID)
    service = WardrobeService(repository=repository, auto_seed=False)
    local_items = service.list_items()

    added = merge_local_into_seed(seed_data, local_items)
    after = count_items(seed_data)

    payload = {category: seed_data[category] for category in CATEGORIES}
    seed_path.write_text(
        json.dumps(payload, indent=4, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )

    print(f"Seed file: {seed_path}")
    print(f"Items before: {before}")
    print(f"Items added:  {added}")
    print(f"Items after:  {after}")


if __name__ == "__main__":
    main()
