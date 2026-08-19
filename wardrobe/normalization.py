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


def wardrobe_name_identity_key(item: dict) -> tuple[str, str, str]:
    """Normalized name+category identity for wardrobe matching (canonical storage keys)."""
    category = normalize_stored_category(item.get("category") or "")
    name = clean_item_name(item.get("name") or "").lower()
    return ("name", category, name)


def wardrobe_item_key(item: dict) -> tuple:
    """Primary lookup key: repository id when present, else normalized name identity."""
    item_id = item.get("id")
    if item_id is not None:
        return ("id", str(item_id))
    return wardrobe_name_identity_key(item)


def wardrobe_identity_keys(item: dict) -> frozenset[tuple]:
    """All identity keys for an item — id plus normalized name (when category is known)."""
    keys: set[tuple] = set()
    item_id = item.get("id")
    if item_id is not None:
        keys.add(("id", str(item_id)))
    try:
        keys.add(wardrobe_name_identity_key(item))
    except ValueError:
        pass
    return frozenset(keys)


def build_wardrobe_identity_set(wardrobe: dict) -> set[tuple]:
    """Build a set of identity keys for every item in a grouped wardrobe snapshot."""
    keys: set[tuple] = set()
    for category_items in wardrobe.values():
        for item in category_items:
            keys.update(wardrobe_identity_keys(item))
    return keys


def item_matches_wardrobe_identity(item: dict, identity_set: set[tuple]) -> bool:
    """Return True when any identity key for item appears in the wardrobe identity set."""
    return bool(wardrobe_identity_keys(item) & identity_set)


def find_matching_wardrobe_item(item: dict, wardrobe: dict) -> dict | None:
    """Return the first wardrobe row that identity-matches item, or None."""
    item_keys = wardrobe_identity_keys(item)
    if not item_keys:
        return None
    for category_items in wardrobe.values():
        for candidate in category_items:
            if item_keys & wardrobe_identity_keys(candidate):
                return candidate
    return None
