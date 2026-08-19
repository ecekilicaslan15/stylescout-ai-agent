"""Tests for grounded outfit explanations (SCOUT-013)."""

import re
from pathlib import Path

from models.plan import Plan
from models.styling_mode import StylingMode
from services.outfit_validator import FALLBACK_REASON, OutfitValidator

from tests.conftest import CONTEXT_TOP

POPULATED_WARDROBE = {
    "tops": [CONTEXT_TOP],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}

CASUAL_PLAN = Plan(intent="outfit_request", event="daily", style="elegant")
EMPTY_MEMORY = {"favorite_colors": [], "preferred_styles": [], "disliked_items": []}

ADJECTIVE_PATTERN = re.compile(
    r"\b(chic|versatile|stylish|trendy|fabulous|perfect|beautiful|gorgeous)\b",
    re.IGNORECASE,
)
SCORE_PATTERN = re.compile(r"\d")


def _assert_grounded_copy(lines: list[str]) -> None:
    joined = " ".join(lines)
    assert not SCORE_PATTERN.search(joined)
    assert not ADJECTIVE_PATTERN.search(joined)


class TestOutfitExplanation:
    def test_validated_outfit_lists_satisfied_constraints_without_adjectives_or_scores(self):
        outfit = {
            "items": [{**CONTEXT_TOP, "source": "wardrobe", "owned": True}],
            "reason": "Built from your wardrobe.",
        }

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.MY_WARDROBE,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=lambda *_args, **_kwargs: {"items": [], "reason": "unused"},
        )

        explanation = final.get("explanation") or []
        assert explanation
        assert any("Every piece is from your wardrobe" in line for line in explanation)
        assert any("No wardrobe item was available for" in line for line in explanation)
        assert "Outerwear" in " ".join(explanation)
        assert "Bottoms" in " ".join(explanation)
        assert "Shoes" in " ".join(explanation)
        _assert_grounded_copy(explanation)

    def test_fallback_outfit_states_reason_honestly(self):
        outfit = {
            "items": [{"name": "", "category": "tops", "source": "suggested", "owned": False}],
            "reason": "broken",
        }
        fallback_outfit = {
            "items": [{**CONTEXT_TOP, "source": "wardrobe", "owned": True}],
            "reason": "fallback composer",
        }

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=lambda *_args, **_kwargs: fallback_outfit,
        )

        explanation = final.get("explanation") or []
        assert explanation[0] == FALLBACK_REASON
        assert final.get("validation_outcome") == "fallback"
        _assert_grounded_copy(explanation)

    def test_partial_mode_one_names_missing_slots(self):
        outfit = {
            "items": [{**CONTEXT_TOP, "source": "wardrobe", "owned": True}],
            "reason": "partial wardrobe match",
        }

        final = OutfitValidator.validate_and_finalize(
            outfit,
            POPULATED_WARDROBE,
            StylingMode.MY_WARDROBE,
            plan=CASUAL_PLAN,
            memory=EMPTY_MEMORY,
            regenerate=lambda *_args, **_kwargs: {"items": [], "reason": "unused"},
        )

        missing_line = next(
            (line for line in final.get("explanation") or [] if "No wardrobe item was available for" in line),
            "",
        )
        assert "Outerwear" in missing_line
        assert "Bottoms" in missing_line
        assert "Shoes" in missing_line
        assert "Tops" not in missing_line

    def test_inline_edit_swap_module_clears_explanation_on_success(self):
        """Gate does not run on inline-edit; swap success must hide stale explanation panel."""
        source = (
            Path(__file__).resolve().parent.parent / "frontend" / "inline-edit-swap.js"
        ).read_text(encoding="utf-8")
        assert "clearExplanation" in source
        assert "if (typeof clearExplanation === \"function\") clearExplanation();" in source

    def test_mode_two_cap_constraint_only_when_count_verified(self):
        over_cap_outfit = {
            "items": [
                {
                    "name": "Suggested Bottom",
                    "category": "bottom",
                    "color": "black",
                    "style": "casual",
                    "source": "suggested",
                    "owned": False,
                },
                {
                    "name": "Suggested Shoes",
                    "category": "shoes",
                    "color": "black",
                    "style": "casual",
                    "source": "suggested",
                    "owned": False,
                },
                {
                    "name": "Suggested Jacket",
                    "category": "outerwear",
                    "color": "black",
                    "style": "casual",
                    "source": "suggested",
                    "owned": False,
                },
            ],
            "reason": "test",
        }

        satisfied = OutfitValidator.collect_satisfied_constraints(
            over_cap_outfit,
            POPULATED_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
        )
        assert "wardrobe_plus_ai_suggested_cap" not in satisfied

        within_cap_outfit = {
            "items": over_cap_outfit["items"][:2],
            "reason": "test",
        }
        satisfied_ok = OutfitValidator.collect_satisfied_constraints(
            within_cap_outfit,
            POPULATED_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
        )
        assert "wardrobe_plus_ai_suggested_cap" in satisfied_ok
