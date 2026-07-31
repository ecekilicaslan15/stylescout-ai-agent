"""JSON file implementation of WardrobeRepository."""

import json
import os
from pathlib import Path

from wardrobe.constants import CATEGORIES, DEFAULT_WARDROBE
from wardrobe.item_metadata import (
    build_unique_item_id,
    default_create_metadata,
    read_item_id,
    utc_timestamp,
)
from wardrobe.normalization import (
    clean_item_name,
    normalize_stored_category,
    normalize_stored_color,
    normalize_style,
    validate_category,
)
from wardrobe.wardrobe_repository import WardrobeRepository

DEFAULT_JSON_PATH = Path(__file__).resolve().parent / "wardrobe.json"
WARDROBE_JSON_PATH_ENV = "WARDROBE_JSON_PATH"


def _resolve_json_path() -> Path:
    configured = os.getenv(WARDROBE_JSON_PATH_ENV)
    if configured:
        return Path(configured)
    return DEFAULT_JSON_PATH


def _is_pytest_run() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _guard_production_seed_writes(path: Path) -> None:
    if path.resolve() == DEFAULT_JSON_PATH.resolve() and _is_pytest_run():
        raise RuntimeError(
            "Refusing to write to the production seed wardrobe.json during tests. "
            "Use JsonWardrobeRepository(tmp_path / 'wardrobe.json') or the "
            "isolated_api_wardrobe_service fixture instead."
        )


class JsonWardrobeRepository(WardrobeRepository):
    """Load and save wardrobe data from a JSON file."""

    def __init__(
        self,
        path: Path | str | None = None,
        user_id: str = "default",
    ) -> None:
        self._path = Path(path) if path is not None else _resolve_json_path()
        self._user_id = user_id

    @property
    def user_id(self) -> str:
        return self._user_id

    def _item_belongs_to_user(self, item: dict) -> bool:
        row_user_id = item.get("user_id", "default")
        return row_user_id == self._user_id

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
            for item in self.get_by_category().get(category, []):
                row = dict(item)
                if not self._item_belongs_to_user(row):
                    continue
                raw_category = row.get("category") or category
                row["category"] = normalize_stored_category(raw_category)
                items.append(row)
        return items

    def find_by_category(self, category: str) -> list[dict]:
        category = normalize_stored_category(category)
        return list(self.get_by_category().get(category, []))

    def find_by_color(self, color: str) -> list[dict]:
        normalized = normalize_stored_color(color)
        matches: list[dict] = []

        for item in self.get_all():
            item_color = normalize_stored_color(item.get("color", ""))
            if item_color == normalized:
                matches.append(item)

        return matches

    def add_item(self, category: str, item: dict, *, allow_duplicate: bool = False) -> bool:
        category = normalize_stored_category(category)
        validate_category(category)

        wardrobe = self.get_by_category()
        name = clean_item_name(item.get("name", ""))
        if not name:
            return False

        now = item.get("created_at") or utc_timestamp()
        cleaned_item = {
            "name": name,
            "category": category,
            "color": normalize_stored_color(item.get("color", "")),
            "style": normalize_style(item.get("style", "casual")),
            **default_create_metadata(
                user_id=self._user_id,
                source=item.get("source", "wardrobe"),
                owned=bool(item.get("owned", True)),
                now=now,
            ),
        }

        event = item.get("event")
        if isinstance(event, str) and event.strip():
            cleaned_item["event"] = event.strip()

        image_url = item.get("image_url")
        if isinstance(image_url, str) and image_url.strip():
            cleaned_item["image_url"] = image_url.strip()

        if not cleaned_item["color"]:
            return False

        duplicate_exists = self._item_exists(wardrobe, category, cleaned_item)
        if duplicate_exists and not allow_duplicate:
            return False
        if duplicate_exists and allow_duplicate:
            cleaned_item["id"] = build_unique_item_id()
            cleaned_item["created_at"] = now
            cleaned_item["updated_at"] = now

        wardrobe[category].append(cleaned_item)
        self._save(wardrobe)
        return True

    def get_item_by_id(self, item_id: str) -> dict | None:
        for category in CATEGORIES:
            for item in self.get_by_category().get(category, []):
                row = dict(item)
                if not self._item_belongs_to_user(row):
                    continue
                row["category"] = normalize_stored_category(row.get("category") or category)
                stored_id = row.get("id")
                if stored_id is None or str(stored_id) != item_id:
                    continue
                return row
        return None

    def update_item(self, item_id: str, item: dict, *, allow_duplicate: bool = False) -> bool:
        wardrobe = self.get_by_category()
        located = self._locate_item(wardrobe, item_id)
        if located is None:
            return False

        old_category, index, existing = located
        merged = dict(existing)

        if "name" in item:
            name = clean_item_name(item.get("name", ""))
            if not name:
                return False
            merged["name"] = name

        if "category" in item:
            category = normalize_stored_category(item.get("category"))
            validate_category(category)
            merged["category"] = category

        if "color" in item:
            color = normalize_stored_color(item.get("color", ""))
            if not color:
                return False
            merged["color"] = color

        if "style" in item:
            merged["style"] = normalize_style(item.get("style", "casual"))

        if "event" in item:
            event = item.get("event")
            if isinstance(event, str):
                event = event.strip() or None
            if event:
                merged["event"] = event
            else:
                merged.pop("event", None)

        if "image_url" in item or "image_path" in item:
            image_url = item.get("image_url") or item.get("image_path")
            if isinstance(image_url, str) and image_url.strip():
                merged["image_url"] = image_url.strip()
            else:
                merged.pop("image_url", None)

        new_category = normalize_stored_category(merged.get("category", old_category))
        validate_category(new_category)
        merged["category"] = new_category

        target_name = clean_item_name(merged.get("name", "")).lower()
        if not target_name:
            return False

        for idx, other in enumerate(wardrobe.get(new_category, [])):
            if new_category == old_category and idx == index:
                continue
            if clean_item_name(other.get("name", "")).lower() == target_name:
                if not allow_duplicate:
                    return False

        merged["updated_at"] = utc_timestamp()
        wardrobe[old_category].pop(index)
        wardrobe[new_category].append(merged)
        self._save(wardrobe)
        return True

    def delete_item(self, item_id: str) -> bool:
        wardrobe = self.get_by_category()
        located = self._locate_item(wardrobe, item_id)
        if located is None:
            return False

        category, index, _existing = located
        wardrobe[category].pop(index)
        self._save(wardrobe)
        return True

    def _locate_item(
        self, wardrobe: dict, item_id: str
    ) -> tuple[str, int, dict] | None:
        for category in CATEGORIES:
            for index, item in enumerate(wardrobe.get(category, [])):
                row = dict(item)
                if not self._item_belongs_to_user(row):
                    continue
                row["category"] = normalize_stored_category(row.get("category") or category)
                stored_id = row.get("id")
                if stored_id is None or str(stored_id) != item_id:
                    continue
                return category, index, item
        return None

    def _save(self, wardrobe: dict) -> None:
        _guard_production_seed_writes(self._path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        payload = {category: list(wardrobe.get(category, [])) for category in CATEGORIES}

        with open(self._path, "w", encoding="utf-8") as file:
            json.dump(payload, file, indent=4, ensure_ascii=False)

    @staticmethod
    def _item_exists(wardrobe: dict, category: str, item: dict) -> bool:
        item_name = clean_item_name(item.get("name", "")).lower()
        if not item_name:
            return False

        for existing in wardrobe.get(category, []):
            if clean_item_name(existing.get("name", "")).lower() == item_name:
                return True

        return False
