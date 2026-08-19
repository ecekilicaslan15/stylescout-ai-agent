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

    def test_wardrobe_plus_ai_rejects_more_than_two_suggested(self):
        outfit = {
            "items": [
                {"name": "S1", "category": "bottom", "source": "suggested", "owned": False},
                {"name": "S2", "category": "shoes", "source": "suggested", "owned": False},
                {"name": "S3", "category": "outerwear", "source": "suggested", "owned": False},
            ],
            "reason": "test",
        }

        errors = OutfitValidator.collect_errors(
            outfit,
            EMPTY_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
        )
        assert any("max is 2" in error for error in errors)

    def test_ai_inspiration_requires_provenance_fields(self):
        outfit = OutfitValidator._document_missing_slots(
            {
                "items": [{"name": "Catalogue Top", "category": "top"}],
                "reason": "test",
            }
        )

        errors = OutfitValidator.collect_errors(
            outfit,
            EMPTY_WARDROBE,
            StylingMode.AI_INSPIRATION,
        )
        assert any(
            "missing owned flag" in error or "invalid source" in error for error in errors
        )

    def test_wardrobe_item_key_prefers_repository_id(self):
        item = {"id": 42, "name": "Ignored", "category": "tops"}
        assert wardrobe_item_key(item) == ("id", 42)
