"""Tests for my_wardrobe mode enforcement in StylistAgent."""

from unittest.mock import MagicMock

import pytest

from agents.stylist_agent import (
    DEFAULT_ITEM_NAMES,
    StylistAgent,
    generate_outfit,
    wardrobe_item_key,
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


def _wardrobe_identities(items: list[dict]) -> set[tuple]:
    return {wardrobe_item_key(item) for item in items}


class TestMyWardrobeMode:
    def test_never_returns_default_items(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.MY_WARDROBE,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        item_names = {item["name"] for item in response.data["outfit"]["items"]}

        assert item_names.isdisjoint(DEFAULT_ITEM_NAMES)

    def test_every_item_exists_in_wardrobe_snapshot(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        wardrobe_items = [CONTEXT_TOP, CONTEXT_BOTTOM, CONTEXT_SHOES]
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.MY_WARDROBE,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=wardrobe_items,
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        allowed = _wardrobe_identities(wardrobe_items)

        for item in response.data["outfit"]["items"]:
            assert wardrobe_item_key(item) in allowed

    def test_missing_category_is_omitted_not_filled_with_fake_item(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.MY_WARDROBE,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        items = response.data["outfit"]["items"]

        assert len(items) == 1
        assert items[0]["name"] == CONTEXT_TOP["name"]
        assert {item["name"] for item in items}.isdisjoint(DEFAULT_ITEM_NAMES)

    def test_empty_wardrobe_returns_clear_result_without_crashing(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=StylingMode.MY_WARDROBE,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        outfit = response.data["outfit"]

        assert outfit["items"] == []
        assert "wardrobe" in outfit["reason"].lower()

    def test_empty_wardrobe_via_generate_outfit(
        self,
        casual_plan: Plan,
        empty_memory: dict,
    ):
        outfit = generate_outfit(
            plan=casual_plan,
            memory=empty_memory,
            wardrobe={
                "tops": [],
                "bottoms": [],
                "shoes": [],
                "outerwear": [],
                "accessories": [],
            },
            mode=StylingMode.MY_WARDROBE,
        )

        assert outfit["items"] == []
        assert "wardrobe" in outfit["reason"].lower()


class TestUnfinishedModesBaseline:
    @pytest.mark.parametrize(
        "mode",
        [StylingMode.WARDROBE_PLUS_AI, StylingMode.AI_INSPIRATION],
    )
    def test_unfinished_modes_still_use_default_fallback(
        self,
        stylist_agent: StylistAgent,
        casual_plan: Plan,
        empty_memory: dict,
        mode: StylingMode,
    ):
        context = AgentContext(
            user_input="casual outfit",
            mode=mode,
            plan=casual_plan,
            memory=empty_memory,
            wardrobe=[CONTEXT_TOP],
        )

        response = stylist_agent.run("casual outfit", {"intent": "outfit_request"}, context)
        item_names = {item["name"] for item in response.data["outfit"]["items"]}

        assert CONTEXT_TOP["name"] in item_names
        assert item_names & DEFAULT_ITEM_NAMES
