"""JSON file implementation of WardrobeRepository."""

import json
from pathlib import Path

from wardrobe.constants import CATEGORIES, DEFAULT_WARDROBE
from wardrobe.wardrobe_repository import WardrobeRepository

DEFAULT_PATH = Path("wardrobe/wardrobe.json")


def _normalize_color(color: str) -> str:
    return "grey" if color == "gray" else color


class JsonWardrobeRepository(WardrobeRepository):
    """Load and save wardrobe data from a JSON file."""

    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else DEFAULT_PATH

    def get_by_category(self) -> dict[str, list[dict]]:
        if not self._path.exists():
            self._save(DEFAULT_WARDROBE)
            return {category: [] for category in CATEGORIES}

        with open(self._path, "r", encoding="utf-8") as file:
            data = json.load(file)

        return {category: list(data.get(category, [])) for category in CATEGORIES}

    def get_all(self) -> list[dict]:
        items: list[dict] = []
        for category in CATEGORIES:
            items.extend(self.get_by_category().get(category, []))
        return items

    def find_by_category(self, category: str) -> list[dict]:
        return list(self.get_by_category().get(category, []))

    def find_by_color(self, color: str) -> list[dict]:
        normalized = _normalize_color(color.strip().lower())
        matches: list[dict] = []

        for item in self.get_all():
            item_color = _normalize_color(item.get("color", "").strip().lower())
            if item_color == normalized:
                matches.append(item)

        return matches

    def add_item(self, category: str, item: dict) -> bool:
        if category not in CATEGORIES:
            raise ValueError(f"Unknown wardrobe category: {category}")

        wardrobe = self.get_by_category()
        cleaned_item = {
            "name": item.get("name", "").strip(),
            "category": category,
            "color": _normalize_color(item.get("color", "").strip().lower()),
            "style": item.get("style", "casual").strip().lower() or "casual",
        }

        if not cleaned_item["name"]:
            return False

        if self._item_exists(wardrobe, category, cleaned_item):
            return False

        wardrobe[category].append(cleaned_item)
        self._save(wardrobe)
        return True

    def _save(self, wardrobe: dict) -> None:
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {category: list(wardrobe.get(category, [])) for category in CATEGORIES}

        with open(self._path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _item_exists(wardrobe: dict, category: str, item: dict) -> bool:
        item_name = item.get("name", "").strip().lower()
        if not item_name:
            return False

        for existing in wardrobe.get(category, []):
            if existing.get("name", "").strip().lower() == item_name:
                return True

        return False
