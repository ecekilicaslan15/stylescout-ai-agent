"""Tests for OutfitValidator post-generation checks."""

import pytest

from models.styling_mode import StylingMode
from services.outfit_validator import OutfitValidator, wardrobe_item_key

from tests.conftest import CONTEXT_TOP


EMPTY_WARDROBE = {
    "tops": [],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}

POPULATED_WARDROBE = {
    "tops": [CONTEXT_TOP],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}


def _valid_my_wardrobe_outfit() -> dict:
    item = {**CONTEXT_TOP, "source": "wardrobe", "owned": True}
    return {"items": [item], "reason": "test"}


class TestOutfitValidator:
    def test_my_wardrobe_valid_outfit_passes(self):
        outfit = _valid_my_wardrobe_outfit()
        OutfitValidator.validate(outfit, POPULATED_WARDROBE, StylingMode.MY_WARDROBE)

    def test_my_wardrobe_rejects_invalid_provenance(self):
        outfit = {
            "items": [{**CONTEXT_TOP, "source": "suggested", "owned": False}],
            "reason": "test",
        }

        with pytest.raises(RuntimeError, match="has invalid provenance"):
            OutfitValidator.validate(outfit, POPULATED_WARDROBE, StylingMode.MY_WARDROBE)

    def test_my_wardrobe_rejects_item_not_in_wardrobe_snapshot(self):
        foreign_item = {
            "name": "Other Top",
            "category": "tops",
            "source": "wardrobe",
            "owned": True,
        }
        outfit = {"items": [foreign_item], "reason": "test"}

        with pytest.raises(RuntimeError, match="is not in the wardrobe snapshot"):
            OutfitValidator.validate(outfit, POPULATED_WARDROBE, StylingMode.MY_WARDROBE)

    def test_my_wardrobe_skips_validation_when_outfit_empty(self):
        outfit = {"items": [], "reason": "test"}
        OutfitValidator.validate(outfit, POPULATED_WARDROBE, StylingMode.MY_WARDROBE)

    def test_my_wardrobe_skips_validation_when_wardrobe_empty(self):
        outfit = _valid_my_wardrobe_outfit()
        OutfitValidator.validate(outfit, EMPTY_WARDROBE, StylingMode.MY_WARDROBE)

    def test_other_modes_do_not_raise(self):
        outfit = {
            "items": [{"name": "Catalogue Top", "source": "suggested", "owned": False}],
            "reason": "test",
        }

        OutfitValidator.validate(outfit, EMPTY_WARDROBE, StylingMode.WARDROBE_PLUS_AI)
        OutfitValidator.validate(outfit, EMPTY_WARDROBE, StylingMode.AI_INSPIRATION)

    def test_wardrobe_item_key_prefers_repository_id(self):
        item = {"id": 42, "name": "Ignored", "category": "tops"}
        assert wardrobe_item_key(item) == ("id", 42)
