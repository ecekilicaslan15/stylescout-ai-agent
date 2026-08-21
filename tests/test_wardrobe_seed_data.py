"""Validation for wardrobe/wardrobe.json seed baseline."""

import json
from pathlib import Path

import pytest

from scripts.export_wardrobe_to_seed import (
    SEED_REQUIRED_FIELDS,
    _visual_identity_key,
    merge_local_into_seed,
    service_item_to_seed_row,
)
from wardrobe.constants import CATEGORIES
from wardrobe.seed import SAMPLE_WARDROBE_PATH

PROJECT_ROOT = Path(__file__).resolve().parent.parent


def _load_seed() -> dict:
    with SAMPLE_WARDROBE_PATH.open(encoding="utf-8") as handle:
        return json.load(handle)


class TestWardrobeSeedFile:
    def test_seed_file_is_valid_json_with_category_keys(self):
        data = _load_seed()
        assert isinstance(data, dict)
        for category in CATEGORIES:
            assert category in data
            assert isinstance(data[category], list)

    def test_every_entry_has_required_seed_fields(self):
        data = _load_seed()
        for category in CATEGORIES:
            for item in data[category]:
                for field in SEED_REQUIRED_FIELDS:
                    assert field in item, f"{category} item missing {field!r}: {item.get('name')}"
                assert item["user_id"] == "default"
                assert str(item["id"]).startswith("itm_")

    def test_no_duplicate_ids_in_seed(self):
        data = _load_seed()
        seen: set[str] = set()
        for category in CATEGORIES:
            for item in data[category]:
                item_id = str(item["id"])
                assert item_id not in seen, f"duplicate id {item_id!r} in seed"
                seen.add(item_id)


class TestExportWardrobeMergeHelpers:
    def test_merge_skips_duplicate_id_and_visual_identity(self):
        seed = {category: [] for category in CATEGORIES}
        existing = service_item_to_seed_row(
            {
                "name": "Blue Jeans",
                "category": "bottoms",
                "color": "blue",
                "style": "casual",
                "id": "itm_abc12345",
                "user_id": "default",
            }
        )
        seed["bottoms"].append(existing)

        same_visual_new_id = {
            "name": "Blue Jeans",
            "category": "bottoms",
            "color": "blue",
            "style": "casual",
            "id": "itm_deadbeef",
            "user_id": "default",
        }
        added = merge_local_into_seed(seed, [same_visual_new_id, existing])
        assert added == 0
        assert len(seed["bottoms"]) == 1

    def test_merge_appends_new_local_row(self):
        seed = {category: [] for category in CATEGORIES}
        new_item = {
            "name": "Export Test Top",
            "category": "tops",
            "color": "green",
            "style": "casual",
            "id": "itm_newitem01",
            "user_id": "default",
            "source": "wardrobe",
            "owned": True,
            "created_at": "2026-08-21T00:00:00Z",
            "updated_at": "2026-08-21T00:00:00Z",
        }
        added = merge_local_into_seed(seed, [new_item])
        assert added == 1
        assert seed["tops"][0]["name"] == "Export Test Top"
        assert _visual_identity_key(seed["tops"][0]) == ("tops", "export test top", "green")
