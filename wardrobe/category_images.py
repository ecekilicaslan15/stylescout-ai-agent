"""Neutral category silhouette placeholders for wardrobe item cards."""

CATEGORY_IMAGES: dict[str, str] = {
    "tops": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=520&q=80",
    "bottoms": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=520&q=80",
    "shoes": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=520&q=80",
    "outerwear": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=520&q=80",
    "accessories": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=520&q=80",
}


def category_image_url(category_key: str) -> str:
    """Return the deterministic placeholder for a stored category key."""
    return CATEGORY_IMAGES.get(category_key, CATEGORY_IMAGES["tops"])


def resolve_item_image_url(item: dict, category_key: str) -> str:
    """Return the card image for a wardrobe item.

    Uses the item's own ``image_url`` when present and not flagged unverified.
    Falls back to a category silhouette when the URL is missing or flagged bad.
    """
    if item.get("image_verified") is False:
        return category_image_url(category_key)
    if item.get("image_url"):
        return item["image_url"]
    return category_image_url(category_key)
