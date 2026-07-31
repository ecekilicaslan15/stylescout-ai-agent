"""Shared metadata helpers for persisted wardrobe items."""

import uuid
from datetime import datetime, timezone


def utc_timestamp() -> str:
    """Return an ISO-8601 UTC timestamp with Z suffix."""
    return (
        datetime.now(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def build_unique_item_id() -> str:
    """Generate a one-off id for confirmed duplicate wardrobe items."""
    return f"itm_{uuid.uuid4().hex[:8]}"


def default_create_metadata(
    *,
    user_id: str = "default",
    source: str = "wardrobe",
    owned: bool = True,
    now: str | None = None,
) -> dict:
    """Return default ownership and timestamp fields for a new item."""
    timestamp = now or utc_timestamp()
    return {
        "id": build_unique_item_id(),
        "user_id": user_id,
        "source": source,
        "owned": owned,
        "created_at": timestamp,
        "updated_at": timestamp,
    }


def read_item_id(item: dict) -> str:
    """Return the persisted wardrobe item id or raise when missing."""
    item_id = item.get("id")
    if not item_id:
        raise ValueError("Wardrobe item is missing a persisted id.")
    return str(item_id)
