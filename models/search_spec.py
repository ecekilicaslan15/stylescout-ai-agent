"""Structured search intent for marketplace deep-links (no live inventory)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field

_OUTFIT_CATEGORY_ALIASES = {
    "tops": "top",
    "top": "top",
    "bottoms": "bottom",
    "bottom": "bottom",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessories": "accessory",
    "accessory": "accessory",
    "Tops": "top",
    "Bottoms": "bottom",
    "Shoes": "shoes",
    "Outerwear": "outerwear",
    "Accessories": "accessory",
}


def _normalize_outfit_slot(category: str) -> str | None:
    cleaned = category.strip()
    return _OUTFIT_CATEGORY_ALIASES.get(cleaned.lower()) or _OUTFIT_CATEGORY_ALIASES.get(
        cleaned
    )


class SearchSpec(BaseModel):
    """Provider-agnostic search intent derived from a suggested outfit item."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    color: str = Field(min_length=1)
    style: str = Field(min_length=1)
    max_price: float | None = None
    size: str | None = None


def build_search_spec(item: dict, preferences: dict | None = None) -> SearchSpec:
    """Build a SearchSpec from an outfit/serializer item dict."""
    name = (item.get("name") or "").strip()
    if not name:
        raise ValueError("Item name is required to build a search spec.")

    raw_category = item.get("category") or item.get("source_category") or ""
    slot = _normalize_outfit_slot(str(raw_category))
    category = slot or str(raw_category).strip().lower()

    color = (item.get("color") or "neutral").strip().lower()
    style = (item.get("style") or "casual").strip().lower()

    max_price = None
    size = None
    if preferences:
        raw_price = preferences.get("max_price")
        if raw_price is not None:
            max_price = float(raw_price)
        raw_size = preferences.get("size")
        if raw_size:
            cleaned_size = str(raw_size).strip()
            size = cleaned_size or None

    return SearchSpec(
        name=name,
        category=category,
        color=color,
        style=style,
        max_price=max_price,
        size=size,
    )
