import json
import re
from pathlib import Path


WARDROBE_PATH = Path("wardrobe/wardrobe.json")

CATEGORIES = ["tops", "bottoms", "shoes", "outerwear", "accessories"]

DEFAULT_WARDROBE = {category: [] for category in CATEGORIES}

ADD_PHRASES = [
    "i have a",
    "i have an",
    "i have",
    "add",
    "i bought a",
    "i bought an",
    "i bought",
    "i got a",
    "i got an",
    "i got",
]

ITEM_KEYWORDS = {
    "tops": ["t-shirt", "blouse", "shirt", "top"],
    "bottoms": ["trousers", "jeans", "pants", "skirt"],
    "shoes": ["sneakers", "loafers", "boots", "heels"],
    "outerwear": ["jacket", "coat", "blazer", "hoodie"],
    "accessories": ["scarf", "belt", "bag", "hat"],
}

COLORS = [
    "black",
    "white",
    "blue",
    "red",
    "pink",
    "green",
    "beige",
    "brown",
    "grey",
    "gray",
]

STYLES = ["casual", "formal", "elegant", "sporty", "streetwear", "classic"]

DISPLAY_NAMES = {
    "t-shirt": "T-Shirt",
    "blouse": "Blouse",
    "shirt": "Shirt",
    "top": "Top",
    "trousers": "Trousers",
    "jeans": "Jeans",
    "pants": "Pants",
    "skirt": "Skirt",
    "sneakers": "Sneakers",
    "loafers": "Loafers",
    "boots": "Boots",
    "heels": "Heels",
    "jacket": "Jacket",
    "coat": "Coat",
    "blazer": "Blazer",
    "hoodie": "Hoodie",
    "scarf": "Scarf",
    "belt": "Belt",
    "bag": "Bag",
    "hat": "Hat",
}


def load_wardrobe() -> dict:
    """Load wardrobe from JSON. Create the file with defaults if it does not exist."""
    if not WARDROBE_PATH.exists():
        save_wardrobe(DEFAULT_WARDROBE)
        return {category: [] for category in CATEGORIES}

    with open(WARDROBE_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    wardrobe = {category: list(data.get(category, [])) for category in CATEGORIES}
    return wardrobe


def save_wardrobe(wardrobe: dict) -> None:
    """Save wardrobe to JSON."""
    WARDROBE_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {category: list(wardrobe.get(category, [])) for category in CATEGORIES}

    with open(WARDROBE_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)


def get_all_wardrobe_items(wardrobe: dict | None = None) -> list[dict]:
    """Return all wardrobe items as a flat list."""
    wardrobe = wardrobe or load_wardrobe()
    items = []

    for category in CATEGORIES:
        for item in wardrobe.get(category, []):
            items.append(item)

    return items


def is_wardrobe_empty(wardrobe: dict | None = None) -> bool:
    """Return True when every wardrobe category is empty."""
    wardrobe = wardrobe or load_wardrobe()
    return all(not wardrobe.get(category) for category in CATEGORIES)


def _normalize_color(color: str) -> str:
    return "grey" if color == "gray" else color


def _item_exists(wardrobe: dict, category: str, item: dict) -> bool:
    item_name = item.get("name", "").strip().lower()
    if not item_name:
        return False

    for existing in wardrobe.get(category, []):
        if existing.get("name", "").strip().lower() == item_name:
            return True

    return False


def add_item_to_wardrobe(category: str, item: dict) -> bool:
    """Add an item to a wardrobe category. Returns False for duplicates."""
    if category not in CATEGORIES:
        raise ValueError(f"Unknown wardrobe category: {category}")

    wardrobe = load_wardrobe()

    cleaned_item = {
        "name": item.get("name", "").strip(),
        "category": category,
        "color": _normalize_color(item.get("color", "").strip().lower()),
        "style": item.get("style", "casual").strip().lower() or "casual",
    }

    if not cleaned_item["name"]:
        return False

    if _item_exists(wardrobe, category, cleaned_item):
        return False

    wardrobe[category].append(cleaned_item)
    save_wardrobe(wardrobe)
    return True


def _contains_add_phrase(text: str) -> bool:
    return any(phrase in text for phrase in ADD_PHRASES)


def _detect_category_and_keyword(text: str) -> tuple[str | None, str | None]:
    for category, keywords in ITEM_KEYWORDS.items():
        for keyword in sorted(keywords, key=len, reverse=True):
            if re.search(rf"\b{re.escape(keyword)}\b", text):
                return category, keyword

    return None, None


def _detect_color(text: str) -> str | None:
    for color in COLORS:
        if re.search(rf"\b{re.escape(color)}\b", text):
            return _normalize_color(color)

    return None


def _detect_style(text: str) -> str:
    for style in STYLES:
        if re.search(rf"\b{re.escape(style)}\b", text):
            return style

    return "casual"


def _build_item_name(color: str | None, keyword: str) -> str:
    display_name = DISPLAY_NAMES.get(keyword, keyword.title())

    if color:
        return f"{color.title()} {display_name}"

    return display_name


def detect_wardrobe_item_from_input(user_input: str) -> dict | None:
    """
    Detect a wardrobe item from simple natural-language phrases.

    Examples:
    - "I have a white shirt"
    - "add black sneakers"
    - "I bought blue jeans"
    """
    text = user_input.lower().strip()
    if not text or not _contains_add_phrase(text):
        return None

    category, keyword = _detect_category_and_keyword(text)
    if not category or not keyword:
        return None

    color = _detect_color(text)
    style = _detect_style(text)
    name = _build_item_name(color, keyword)

    return {
        "name": name,
        "category": category,
        "color": color or "neutral",
        "style": style,
    }


def update_wardrobe_from_input(user_input: str) -> dict | None:
    """
    Detect and save a wardrobe item from user input.

    Returns a result dict when an item was detected, otherwise None.
    """
    item = detect_wardrobe_item_from_input(user_input)
    if not item:
        return None

    added = add_item_to_wardrobe(item["category"], item)

    return {
        "added": added,
        "item": item,
        "duplicate": not added,
    }
