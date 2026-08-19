"""Tests for wardrobe_plus_ai hybrid styling mode."""

from unittest.mock import MagicMock

import pytest

from agents.stylist_agent import (
    DEFAULT_ITEM_NAMES,
    MAX_HYBRID_SUGGESTED_ITEMS,
    StylistAgent,
    generate_outfit,
)
from models.agent_context import AgentContext
from models.plan import Plan
from models.styling_mode import StylingMode

from tests.conftest import CONTEXT_BOTTOM, CONTEXT_SHOES, CONTEXT_TOP


@pytest.fixture
def casual_plan() -> Plan:
    return Plan(intent="outfit_request", event="daily", style="casual")


@pytest.fixture
def empty_memory() -> dict:
    return {
        "favorite_colors": [],
        "preferred_styles": [],
        "disliked_items": [],
    }


@pytest.fixture
def stylist_agent() -> StylistAgent:
    return StylistAgent(rag_service=MagicMock(retrieve=lambda *args, **kwargs: []))


EMPTY_WARDROBE = {
    "tops": [],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}


class TestWardrobePlusAiMode:
    def test_prefers_wardrobe_items_over_defaults(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP, CONTEXT_BOTTOM, CONTEXT_SHOES],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        items = response.data["outfit"]["items"]

        assert all(item["source"] == "wardrobe" for item in items)
        assert all(item["owned"] is True for item in items)
        assert {item["name"] for item in items}.isdisjoint(DEFAULT_ITEM_NAMES)

    def test_fills_missing_categories_with_suggested_items(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        items = response.data["outfit"]["items"]

        assert items[0]["name"] == CONTEXT_TOP["name"]
        assert items[0]["source"] == "wardrobe"
        assert any(item["source"] == "suggested" for item in items[1:])

    def test_suggested_count_never_exceeds_two(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        items = response.data["outfit"]["items"]
        suggested = [item for item in items if item["source"] == "suggested"]

        assert len(suggested) <= MAX_HYBRID_SUGGESTED_ITEMS
        assert len(items) <= 1 + MAX_HYBRID_SUGGESTED_ITEMS

    def test_empty_wardrobe_returns_at_most_two_suggested_items(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=EMPTY_WARDROBE,
            mode=StylingMode.WARDROBE_PLUS_AI,
        )
        items = outfit["items"]
        suggested = [item for item in items if item["source"] == "suggested"]

        assert len(items) <= MAX_HYBRID_SUGGESTED_ITEMS
        assert len(suggested) == len(items)
        assert all(item["owned"] is False for item in suggested)

    def test_provenance_on_mixed_outfit(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        items = response.data["outfit"]["items"]

        for item in items:
            if item["name"] == CONTEXT_TOP["name"]:
                assert item["source"] == "wardrobe"
                assert item["owned"] is True
            else:
                assert item["source"] == "suggested"
                assert item["owned"] is False

    def test_mixed_outfit_reason(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        reason = response.data["outfit"]["reason"].lower()

        assert "wardrobe" in reason
        assert "suggested" in reason
