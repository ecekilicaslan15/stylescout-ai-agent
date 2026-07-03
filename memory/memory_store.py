import json
import re
from pathlib import Path

from agents.detectors.color_detector import detect_colors
from agents.detectors.dislike_detector import detect_disliked_items


MEMORY_PATH = Path("memory/memory_store.json")

DEFAULT_MEMORY = {
    "favorite_colors": [],
    "preferred_styles": [],
    "disliked_items": [],
}

COLOR_PHRASES = [
    "i like",
    "i love",
    "my favorite color is",
    "favorite color is",
]

STYLE_PHRASES = [
    "i like",
    "i love",
    "i prefer",
    "my preferred style is",
    "preferred style is",
]

DISLIKE_PHRASES = [
    "i hate",
    "i don't like",
    "i dont like",
    "i dislike",
    "don't like",
    "dislike",
]

STYLES = [
    "streetwear",
    "elegant",
    "classy",
    "minimal",
    "comfortable",
    "comfy",
    "casual",
    "sporty",
]


def _empty_memory() -> dict:
    return {
        "favorite_colors": [],
        "preferred_styles": [],
        "disliked_items": [],
    }


def _normalize_memory(data: dict) -> dict:
    """Support older nested JSON files during migration."""
    if "user_profile" in data:
        profile = data["user_profile"]
        return {
            "favorite_colors": list(profile.get("favorite_colors", [])),
            "preferred_styles": list(profile.get("preferred_styles", [])),
            "disliked_items": list(profile.get("disliked_items", [])),
        }

    memory = _empty_memory()
    for key in memory:
        memory[key] = list(data.get(key, []))
    return memory


def load_memory() -> dict:
    """Load memory from JSON. Create the file with defaults if it does not exist."""
    if not MEMORY_PATH.exists():
        save_memory(_empty_memory())
        return _empty_memory()

    with open(MEMORY_PATH, "r", encoding="utf-8") as file:
        data = json.load(file)

    memory = _normalize_memory(data)

    # Persist migrated flat structure if the file still used the old format.
    if "user_profile" in data:
        save_memory(memory)

    return memory


def save_memory(memory: dict) -> None:
    """Save memory to JSON."""
    MEMORY_PATH.parent.mkdir(parents=True, exist_ok=True)

    payload = {
        "favorite_colors": list(memory.get("favorite_colors", [])),
        "preferred_styles": list(memory.get("preferred_styles", [])),
        "disliked_items": list(memory.get("disliked_items", [])),
    }

    with open(MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(payload, file, indent=4, ensure_ascii=False)


def add_to_memory(category: str, value: str) -> dict:
    """Add a value to a memory category without creating duplicates."""
    memory = load_memory()

    if category not in memory:
        raise ValueError(f"Unknown memory category: {category}")

    cleaned_value = value.strip()
    if not cleaned_value:
        return memory

    if category in ("favorite_colors", "preferred_styles"):
        cleaned_value = cleaned_value.lower()

    existing_values = [item.lower() for item in memory[category]]
    if cleaned_value.lower() not in existing_values:
        memory[category].append(cleaned_value)
        save_memory(memory)

    return memory


def _contains_phrase(text: str, phrases: list[str]) -> bool:
    return any(phrase in text for phrase in phrases)


def _detect_preferred_styles(text: str) -> list[str]:
    found_styles = []

    for style in STYLES:
        if style in text:
            normalized_style = "comfortable" if style == "comfy" else style
            if style == "classy":
                normalized_style = "elegant"
            if normalized_style not in found_styles:
                found_styles.append(normalized_style)

    return found_styles


def _detect_disliked_phrase_items(text: str) -> list[str]:
    """Extract disliked clothing names from natural-language phrases."""
    found_items = []

    for phrase in DISLIKE_PHRASES:
        pattern = rf"{re.escape(phrase)}\s+([a-zA-Z\s]+)"
        matches = re.findall(pattern, text)

        for match in matches:
            item = match.strip(" .,!?:;")
            if item and item not in found_items:
                found_items.append(item.title())

    if found_items:
        return found_items

    return detect_disliked_items(text)


def update_memory_from_input(user_input: str) -> dict:
    """
    Parse simple preference phrases from user input and update memory.

    Examples:
    - "I like black" -> favorite_colors
    - "I prefer casual" -> preferred_styles
    - "I hate loafers" -> disliked_items
    """
    text = user_input.lower().strip()
    if not text:
        return load_memory()

    if _contains_phrase(text, COLOR_PHRASES):
        for color in detect_colors(text):
            add_to_memory("favorite_colors", color)

    if _contains_phrase(text, STYLE_PHRASES):
        for style in _detect_preferred_styles(text):
            add_to_memory("preferred_styles", style)

    if _contains_phrase(text, DISLIKE_PHRASES):
        for item in _detect_disliked_phrase_items(text):
            add_to_memory("disliked_items", item)

    return load_memory()
