"""Idempotent per-user wardrobe seeding from the default sample template."""

from __future__ import annotations

import json
from pathlib import Path

from wardrobe.constants import CATEGORIES
from wardrobe.item_metadata import build_unique_item_id, utc_timestamp
from wardrobe.wardrobe_repository import WardrobeRepository

SAMPLE_WARDROBE_PATH = Path(__file__).resolve().parent / "wardrobe.json"
LEGACY_USER_ID = "default"


def load_sample_template() -> list[dict]:
    """Return default-user items from wardrobe.json (the live sample set)."""
    with SAMPLE_WARDROBE_PATH.open(encoding="utf-8") as file:
        sample_data = json.load(file)

    template: list[dict] = []
    for category in CATEGORIES:
        for item in sample_data.get(category, []):
            row = dict(item)
            row_user_id = row.get("user_id", LEGACY_USER_ID)
            if row_user_id != LEGACY_USER_ID:
                continue
            row["category"] = category
            template.append(row)
    return template


def _clone_template_item(item: dict, user_id: str, now: str) -> dict:
    """Copy one template row for a new user with fresh ids and timestamps."""
    cloned = {
        "name": item.get("name", ""),
        "category": item.get("category"),
        "color": item.get("color", "neutral"),
        "style": item.get("style", "casual"),
        "user_id": user_id,
        "source": item.get("source", "wardrobe"),
        "owned": bool(item.get("owned", True)),
        "id": build_unique_item_id(),
        "created_at": now,
        "updated_at": now,
    }
    event = item.get("event")
    if isinstance(event, str) and event.strip():
        cloned["event"] = event.strip()
    image_url = item.get("image_url")
    if isinstance(image_url, str) and image_url.strip():
        cloned["image_url"] = image_url.strip()
    return cloned


def seed_user_wardrobe_if_empty(repository: WardrobeRepository) -> int:
    """Seed sample wardrobe for user_id when they have zero items (idempotent).

    Returns the number of items inserted (0 when already seeded or legacy default).
    """
    user_id = getattr(repository, "user_id", LEGACY_USER_ID)
    if user_id == LEGACY_USER_ID:
        return 0

    if repository.get_all():
        return 0

    template = load_sample_template()
    if not template:
        return 0

    now = utc_timestamp()
    inserted = 0
    for item in template:
        payload = _clone_template_item(item, user_id, now)
        category = payload.pop("category")
        if repository.add_item(category, payload, allow_duplicate=True):
            inserted += 1
    return inserted
