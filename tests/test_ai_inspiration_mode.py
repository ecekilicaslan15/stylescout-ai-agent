"""Tests for ai_inspiration wardrobe-independent styling mode."""

from unittest.mock import MagicMock

import pytest

from agents.stylist_agent import (
    MAX_HYBRID_SUGGESTED_ITEMS,
    StylistAgent,
    generate_outfit,
)
from models.agent_context import AgentContext
from models.plan import Plan
from models.styling_mode import StylingMode

from tests.conftest import CONTEXT_TOP


@pytest.fixture
def casual_plan() -> Plan:
    return Plan(intent="outfit_request", event="daily", style="casual")


@pytest.fixture
def office_plan() -> Plan:
    return Plan(intent="outfit_request", event="office", style="elegant")


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

POPULATED_WARDROBE = {
    "tops": [CONTEXT_TOP],
    "bottoms": [
        {
            "name": "Blue Jeans",
            "category": "bottoms",
            "color": "blue",
            "style": "casual",
        }
    ],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}


def _item_names(outfit: dict) -> list[str]:
    return [item["name"] for item in outfit["items"]]


class TestAiInspirationMode:
    def test_same_selection_with_empty_and_populated_wardrobe(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        empty_outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=EMPTY_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )
        populated_outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=POPULATED_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )

        assert _item_names(empty_outfit) == _item_names(populated_outfit)

    def test_wardrobe_items_do_not_affect_inspiration_selection(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.AI_INSPIRATION,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        item_names = {item["name"] for item in response.data["outfit"]["items"]}

        assert CONTEXT_TOP["name"] not in item_names

    def test_ownership_applied_after_generation(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=POPULATED_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )
        jeans = next(item for item in outfit["items"] if item["name"] == "Blue Jeans")

        assert jeans["source"] == "wardrobe"
        assert jeans["owned"] is True

    def test_unmatched_inspiration_items_are_suggested(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=EMPTY_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )

        assert outfit["items"]
        assert all(item["source"] == "suggested" for item in outfit["items"])
        assert all(item["owned"] is False for item in outfit["items"])

    def test_empty_wardrobe_returns_full_inspiration_outfit(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=EMPTY_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )

        assert len(outfit["items"]) >= 2
        assert "inspiration" in outfit["reason"].lower()

    def test_not_limited_to_two_suggested_items(
        self,
        office_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=office_plan,
            memory=empty_memory,
            wardrobe=EMPTY_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )

        assert len(outfit["items"]) > MAX_HYBRID_SUGGESTED_ITEMS

    def test_inspiration_reason_mentions_owned_pieces_when_applicable(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=POPULATED_WARDROBE,
            mode=StylingMode.AI_INSPIRATION,
        )

        assert "inspiration" in outfit["reason"].lower()
        assert "already own" in outfit["reason"].lower()
