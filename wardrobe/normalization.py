"""Shared wardrobe field normalization used by repository implementations."""

from wardrobe.constants import CATEGORIES

DEFAULT_COLOR = "neutral"


def normalize_color(color: str) -> str:
    """Normalize gray/grey spelling for consistent comparisons."""
    return "grey" if color == "gray" else color


def clean_item_name(name: str) -> str:
    """Strip whitespace from an item name."""
    return name.strip()


def normalize_style(style: str) -> str:
    """Normalize style text with a casual default."""
    return style.strip().lower() or "casual"


def validate_category(category: str) -> None:
    """Raise when a wardrobe category is not supported."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown wardrobe category: {category}")


def normalize_stored_color(color: str) -> str:
    """Normalize a color value for persistence or lookup."""
    cleaned = color.strip().lower()
    if not cleaned:
        return ""
    return normalize_color(cleaned)


def resolve_stored_color(color: str | None, *, default: str = DEFAULT_COLOR) -> str:
    """Resolve a color for storage, using a default when missing."""
    if not color or not color.strip():
        return default
    return normalize_stored_color(color)
