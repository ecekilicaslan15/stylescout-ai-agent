"""Post-generation outfit validation by styling mode."""

from models.styling_mode import StylingMode

CATEGORY_NORMALIZATION = {
    "tops": "top",
    "top": "top",
    "bottoms": "bottom",
    "bottom": "bottom",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessories": "accessory",
    "accessory": "accessory",
}


def _normalize_category(category: str | None) -> str | None:
    if not category:
        return None

    return CATEGORY_NORMALIZATION.get(category.strip().lower())


def wardrobe_item_key(item: dict) -> tuple:
    """Stable wardrobe identity: repository id when present, else (category, name)."""
    item_id = item.get("id")
    if item_id is not None:
        return ("id", item_id)
    category = _normalize_category(item.get("category")) or (item.get("category") or "")
    name = (item.get("name") or "").strip().lower()
    return ("name", category, name)


def build_wardrobe_identity_set(wardrobe: dict) -> set[tuple]:
    keys: set[tuple] = set()
    for category_items in wardrobe.values():
        for item in category_items:
            keys.add(wardrobe_item_key(item))
    return keys


class OutfitValidator:
    @staticmethod
    def validate(outfit: dict, wardrobe: dict, mode: StylingMode) -> None:
        if mode == StylingMode.MY_WARDROBE:
            OutfitValidator._validate_my_wardrobe(outfit, wardrobe)
        elif mode == StylingMode.WARDROBE_PLUS_AI:
            OutfitValidator._validate_wardrobe_plus_ai(outfit, wardrobe)
        elif mode == StylingMode.AI_INSPIRATION:
            OutfitValidator._validate_ai_inspiration(outfit, wardrobe)

    @staticmethod
    def _validate_my_wardrobe(outfit: dict, wardrobe: dict) -> None:
        items = outfit.get("items") or []
        wardrobe_identities = build_wardrobe_identity_set(wardrobe)
        if not items or not wardrobe_identities:
            return

        for item in items:
            if item.get("source") != "wardrobe" or item.get("owned") is not True:
                raise RuntimeError(
                    f"my_wardrobe outfit item {item.get('name')!r} has invalid provenance"
                )
            if wardrobe_item_key(item) not in wardrobe_identities:
                raise RuntimeError(
                    f"my_wardrobe outfit item {item.get('name')!r} is not in the wardrobe snapshot"
                )

    @staticmethod
    def _validate_wardrobe_plus_ai(_outfit: dict, _wardrobe: dict) -> None:
        pass

    @staticmethod
    def _validate_ai_inspiration(_outfit: dict, _wardrobe: dict) -> None:
        pass
