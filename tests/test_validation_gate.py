"""Tests for the full outfit validation gate (SCOUT-002 sub-task B)."""

from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient

from api.main import app
from models.plan import Plan
from models.styling_mode import StylingMode
from services.outfit_validator import FALLBACK_REASON, OutfitValidator

from tests.conftest import CONTEXT_TOP


client = TestClient(app)

POPULATED_WARDROBE = {
    "tops": [CONTEXT_TOP],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}

CASUAL_PLAN = Plan(intent="outfit_request", event="daily", style="casual")
EMPTY_MEMORY = {"favorite_colors": [], "preferred_styles": [], "disliked_items": []}


def _corrupted_duplicate_slot_outfit() -> dict:
    top = {**CONTEXT_TOP, "source": "wardrobe", "owned": True}
    duplicate = {**CONTEXT_TOP, "name": "Duplicate Top", "source": "wardrobe", "owned": True}
    return {
        "event": "daily",
        "style": "casual",
        "items": [top, duplicate],
        "reason": "test outfit",
    }


class TestValidationGateFlow:
    def test_duplicate_slot_is_repaired_without_fallback(self):
        outfit = _corrupted_duplicate_slot_outfit()
        calls: list[StylingMode] = []

        def fake_regenerate(_plan, _memory, _wardrobe, mode):
            calls.append(mode)
            return {"items": [], "reason": "fallback"}

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.MY_WARDROBE,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=fake_regenerate,
        )

        assert len(final["items"]) == 1
        assert "Adjusted after a validation issue" in final["reason"]
        assert calls == []

    def test_validate_rejects_three_suggested_without_compose(self):
        """Gate entry validate() — raw dict, no generate_outfit / StylistAgent."""
        outfit = {
            "items": [
                {"name": "S1", "category": "bottom", "source": "suggested", "owned": False},
                {"name": "S2", "category": "shoes", "source": "suggested", "owned": False},
                {"name": "S3", "category": "outerwear", "source": "suggested", "owned": False},
            ],
            "reason": "test",
        }

        with pytest.raises(RuntimeError, match="max is 2"):
            OutfitValidator.validate(outfit, POPULATED_WARDROBE, StylingMode.WARDROBE_PLUS_AI)

    def test_validate_and_finalize_trims_three_suggested_through_gate_entry(self):
        """Full gate path repairs a raw 3-suggested outfit to ≤2 without compose."""
        outfit = {
            "items": [
                {"name": "S1", "category": "bottom", "source": "suggested", "owned": False},
                {"name": "S2", "category": "shoes", "source": "suggested", "owned": False},
                {"name": "S3", "category": "outerwear", "source": "suggested", "owned": False},
            ],
            "reason": "test",
        }
        regenerate_calls: list[StylingMode] = []

        def fake_regenerate(_plan, _memory, _wardrobe, mode):
            regenerate_calls.append(mode)
            return {"items": [], "reason": "should not run"}

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=fake_regenerate,
        )

        suggested = [item for item in final["items"] if item["source"] == "suggested"]
        assert len(suggested) <= 2
        assert "Adjusted after a validation issue" in final["reason"]
        assert regenerate_calls == []

    def test_repair_still_invalid_falls_back_without_compose(self):
        """Repair output is re-checked; schema still broken → MY_WARDROBE fallback."""
        outfit = {
            "items": [{"name": "", "category": "tops", "source": "suggested", "owned": False}],
            "reason": "broken",
        }
        fallback_outfit = {
            "items": [{**CONTEXT_TOP, "source": "wardrobe", "owned": True}],
            "reason": "fallback composer",
        }
        regenerate_calls: list[StylingMode] = []

        def fake_regenerate(_plan, _memory, _wardrobe, mode):
            regenerate_calls.append(mode)
            return fallback_outfit

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=fake_regenerate,
        )

        assert final["reason"] == FALLBACK_REASON
        assert regenerate_calls == [StylingMode.MY_WARDROBE]
        assert all(item["source"] == "wardrobe" for item in final["items"])

    def test_coherence_requires_missing_slots_for_unfilled_frontend_slots(self):
        outfit = {
            "items": [{**CONTEXT_TOP, "source": "wardrobe", "owned": True}],
            "reason": "partial",
        }

        errors = OutfitValidator.collect_errors(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.MY_WARDROBE,
        )
        assert any("missing required slot" in error for error in errors)

        documented = OutfitValidator._document_missing_slots(dict(outfit))
        assert "Outerwear" in documented["missing_slots"]
        assert "Bottoms" in documented["missing_slots"]
        assert "Shoes" in documented["missing_slots"]

        assert (
            OutfitValidator.collect_errors(
                documented,
                POPULATED_WARDROBE,
                StylingMode.MY_WARDROBE,
            )
            == []
        )


class TestValidationGateApiWiring:
    @patch("api.main.run_fashion_agent")
    @patch("api.main.update_wardrobe_from_input", return_value=None)
    @patch("api.main.update_memory_from_input")
    @patch("api.main.OutfitValidator.validate_and_finalize")
    def test_post_outfits_invokes_gate_once(
        self,
        mock_finalize,
        _mock_memory,
        _mock_wardrobe,
        mock_run,
    ):
        raw_outfit = {
            "event": "daily",
            "style": "casual",
            "items": [
                {
                    **CONTEXT_TOP,
                    "id": "itm_context_top",
                    "source": "wardrobe",
                    "owned": True,
                }
            ],
            "reason": "Built from your wardrobe.",
        }
        mock_run.return_value = {
            "plan": CASUAL_PLAN,
            "memory": EMPTY_MEMORY,
            "outfit": raw_outfit,
            "message": None,
            "stylist_notes": None,
        }
        mock_finalize.side_effect = lambda outfit, *_args, **_kwargs: {
            **outfit,
            "missing_slots": ["Outerwear", "Bottoms", "Shoes"],
        }

        response = client.post(
            "/api/outfits",
            json={"prompt": "casual outfit", "mode": "my_wardrobe"},
        )

        assert response.status_code == 200
        mock_finalize.assert_called_once()
        payload = response.json()
        assert payload["outfit"]["missing_slots"] == ["Outerwear", "Bottoms", "Shoes"]
