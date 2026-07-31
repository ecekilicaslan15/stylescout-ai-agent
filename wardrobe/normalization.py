"""Shared wardrobe field normalization used by repository implementations."""

from wardrobe.constants import CATEGORY_ALIASES, DISPLAY_LABELS

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


def normalize_stored_category(category: str) -> str:
    """Map any accepted category alias to the canonical storage key."""
    key = category.strip().lower()
    canonical = CATEGORY_ALIASES.get(key)
    if canonical is None:
        raise ValueError(f"Unknown wardrobe category: {category}")
    return canonical


def to_display_category(stored_category: str) -> str:
    """Convert a canonical storage key to the wardrobe grid display label."""
    canonical = normalize_stored_category(stored_category)
    return DISPLAY_LABELS[canonical]


def validate_category(category: str) -> None:
    """Raise when a wardrobe category is not supported."""
    normalize_stored_category(category)


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
