"""Shared fixtures for AgentContext architecture tests."""

import pytest

from models.agent_context import AgentContext
from models.plan import Plan, plan_to_dict

# Unique names make it obvious whether context or disk data was used.
CONTEXT_TOP = {
    "name": "Context Casual Top",
    "category": "tops",
    "color": "white",
    "style": "casual",
}
CONTEXT_BOTTOM = {
    "name": "Context Jeans",
    "category": "bottoms",
    "color": "blue",
    "style": "casual",
}
CONTEXT_SHOES = {
    "name": "Context Sneakers",
    "category": "shoes",
    "color": "white",
    "style": "casual",
}
DISK_TOP = {
    "name": "Disk Only Top",
    "category": "tops",
    "color": "black",
    "style": "casual",
}
DISK_BOTTOM = {
    "name": "Disk Only Jeans",
    "category": "bottoms",
    "color": "black",
    "style": "casual",
}
DISK_SHOES = {
    "name": "Disk Only Sneakers",
    "category": "shoes",
    "color": "black",
    "style": "casual",
}


@pytest.fixture
def casual_plan() -> Plan:
    return Plan(intent="outfit_request", event="daily", style="casual")


@pytest.fixture
def casual_plan_dict(casual_plan: Plan) -> dict:
    return plan_to_dict(casual_plan)


@pytest.fixture
def context_wardrobe_list() -> list[dict]:
    return [CONTEXT_TOP, CONTEXT_BOTTOM, CONTEXT_SHOES]


@pytest.fixture
def disk_wardrobe_dict() -> dict:
    return {
        "tops": [DISK_TOP],
        "bottoms": [DISK_BOTTOM],
        "shoes": [DISK_SHOES],
        "outerwear": [],
        "accessories": [],
    }


@pytest.fixture
def context_memory() -> dict:
    return {
        "favorite_colors": ["white"],
        "preferred_styles": ["casual"],
        "disliked_items": ["Disk Only Top"],
    }


@pytest.fixture
def agent_context(
    casual_plan: Plan,
    context_wardrobe_list: list[dict],
    context_memory: dict,
) -> AgentContext:
    return AgentContext(
        user_input="casual outfit for daily wear",
        plan=casual_plan,
        memory=context_memory,
        wardrobe=context_wardrobe_list,
    )
