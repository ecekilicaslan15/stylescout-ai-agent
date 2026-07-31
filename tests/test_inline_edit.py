"""Tests for free-text inline edit and expanded keyword matching."""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agents.inline_edit_agent import InlineEditAgent
from agents.inline_edit_config import parse_inline_edit_instruction
from api.main import (
    _merge_inline_edit_outfit,
    app,
    serialize_inline_edit_result,
)
from api.session import LEGACY_USER_ID
from models.agent_context import AgentContext
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService

legacy_client = TestClient(app)
legacy_client.cookies.set("stylescout_session", LEGACY_USER_ID)


TOPS = [
    {
        "id": "itm_casual_top",
        "name": "Casual White Tee",
        "category": "tops",
        "color": "white",
        "style": "casual",
        "source": "wardrobe",
        "owned": True,
    },
    {
        "id": "itm_elegant_top",
        "name": "Silk Blouse",
        "category": "tops",
        "color": "white",
        "style": "elegant",
        "source": "wardrobe",
        "owned": True,
    },
]

BOTTOMS = [
    {
        "id": "itm_casual_jeans",
        "name": "Relaxed Jeans",
        "category": "bottoms",
        "color": "blue",
        "style": "casual",
        "source": "wardrobe",
        "owned": True,
    },
    {
        "id": "itm_formal_trousers",
        "name": "Formal Trousers",
        "category": "bottoms",
        "color": "black",
        "style": "elegant",
        "source": "wardrobe",
        "owned": True,
    },
]

SHOES = [
    {
        "id": "itm_comfy_sneakers",
        "name": "Comfort Sneakers",
        "category": "shoes",
        "color": "white",
        "style": "casual",
        "source": "wardrobe",
        "owned": True,
    },
    {
        "id": "itm_heels",
        "name": "Black Heels",
        "category": "shoes",
        "color": "black",
        "style": "elegant",
        "source": "wardrobe",
        "owned": True,
    },
]


def _wardrobe_dict() -> dict:
    return {
        "tops": list(TOPS),
        "bottoms": list(BOTTOMS),
        "shoes": list(SHOES),
        "outerwear": [],
        "accessories": [],
    }


def _display_outfit() -> dict:
    return {
        "event": "daily",
        "style": "casual",
        "items": [
            {
                "id": "itm_elegant_top",
                "name": "Silk Blouse",
                "category": "Tops",
                "color": "white",
                "style": "elegant",
                "source": "wardrobe",
                "owned": True,
            },
            {
                "id": "itm_casual_jeans",
                "name": "Relaxed Jeans",
                "category": "Bottoms",
                "color": "blue",
                "style": "casual",
                "source": "wardrobe",
                "owned": True,
            },
            {
                "id": "itm_heels",
                "name": "Black Heels",
                "category": "Shoes",
                "color": "black",
                "style": "elegant",
                "source": "suggested",
                "owned": False,
            },
        ],
    }


class TestInlineEditKeywordParsing:
    def test_parses_comfort_keywords(self):
        criteria = parse_inline_edit_instruction("bunu daha rahat bir şeyle değiştir")
        assert criteria is not None
        assert criteria.target_style == "casual"
        assert criteria.matched_category == "comfort"

    def test_parses_formality_keywords(self):
        criteria = parse_inline_edit_instruction("this blazer is too formal, make it informal")
        assert criteria is not None
        assert criteria.target_style == "casual"
        assert criteria.formality_hint == "informal"

    def test_parses_weather_keywords(self):
        criteria = parse_inline_edit_instruction("something better for hot summer weather")
        assert criteria is not None
        assert criteria.weather_hint == "warm"

    def test_unrecognized_instruction_returns_none(self):
        assert parse_inline_edit_instruction("make it more purple unicorn sparkle") is None


class TestInlineEditAgentKeywords:
    def _run_edit(self, target_item: dict, instruction: str):
        context = AgentContext(
            user_input=instruction,
            plan={"intent": "inline_edit"},
            memory={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            current_outfit=[target_item],
            selected_item=target_item,
            wardrobe=_wardrobe_dict(),
        )
        return InlineEditAgent().run(instruction, {"intent": "inline_edit"}, context)

    def test_elegant_keyword_still_works(self):
        target = dict(TOPS[0])
        target["category"] = "top"
        response = self._run_edit(target, "make it more elegant")
        assert response.success is True
        assert response.data["updated_item"]["name"] == "Silk Blouse"

    def test_casual_keyword_still_works(self):
        target = dict(TOPS[1])
        target["category"] = "top"
        response = self._run_edit(target, "make it more casual")
        assert response.success is True
        assert response.data["updated_item"]["name"] == "Casual White Tee"

    def test_comfort_keyword_replaces_with_casual_piece(self):
        target = dict(SHOES[1])
        target["category"] = "shoes"
        response = self._run_edit(
            target,
            "replace with a comfortable shoe for walking",
        )
        assert response.success is True
        assert response.data["updated_item"]["name"] == "Comfort Sneakers"

    def test_formal_keyword_replaces_with_elegant_piece(self):
        target = dict(BOTTOMS[0])
        target["category"] = "bottom"
        response = self._run_edit(target, "I need something more formal for the office")
        assert response.success is True
        assert response.data["updated_item"]["name"] == "Formal Trousers"

    def test_unrecognized_instruction_is_not_success(self):
        target = dict(TOPS[0])
        target["category"] = "top"
        response = self._run_edit(target, "make it more purple unicorn sparkle")
        assert response.success is False
        assert response.error == "unrecognized_instruction"


class TestInlineEditApiStatus:
    def test_unrecognized_instruction_returns_422(self):
        outfit = _display_outfit()
        response = legacy_client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": outfit,
                "target_item": outfit["items"][0],
                "instruction": "make it more purple unicorn sparkle",
            },
        )
        assert response.status_code == 422
        assert "understand" in response.json()["detail"].lower()

    @patch("api.main.run_inline_edit")
    def test_agent_internal_error_returns_500(self, mock_run_inline_edit):
        mock_run_inline_edit.return_value = {
            "success": False,
            "message": "Inline edit requires a current outfit and target item.",
            "error": "missing_context",
            "updated_item": None,
            "original_item": None,
            "instruction": "make it casual",
        }
        outfit = _display_outfit()
        response = legacy_client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": outfit,
                "target_item": outfit["items"][0],
                "instruction": "make it casual",
            },
        )
        assert response.status_code == 400


class TestInlineEditOtherItemsUnchanged:
    def test_merge_keeps_non_target_items_identical(self):
        outfit = _display_outfit()
        target = outfit["items"][0]
        updated = {
            **target,
            "id": "itm_casual_top",
            "name": "Casual White Tee",
            "style": "casual",
        }
        wardrobe_by_category = {
            category: list(items)
            for category, items in _wardrobe_dict().items()
        }
        merged = _merge_inline_edit_outfit(outfit, target, updated, wardrobe_by_category)

        unchanged = [item for item in merged["items"] if item["id"] != updated["id"]]
        assert len(unchanged) == 2
        assert unchanged[0]["id"] == "itm_casual_jeans"
        assert unchanged[0]["source"] == "wardrobe"
        assert unchanged[0]["owned"] is True
        assert unchanged[1]["id"] == "itm_heels"
        assert unchanged[1]["source"] == "suggested"
        assert unchanged[1]["owned"] is False

    def test_api_response_outfit_leaves_other_items_unchanged(self):
        outfit = _display_outfit()
        target = outfit["items"][0]
        others_before = {
            item["id"]: item for item in outfit["items"] if item["id"] != target["id"]
        }

        mock_repo = MagicMock(spec=JsonWardrobeRepository)
        mock_repo.get_all.return_value = TOPS + BOTTOMS + SHOES
        mock_repo.user_id = LEGACY_USER_ID

        service = WardrobeService(repository=mock_repo, auto_seed=False)
        result = {
            "success": True,
            "message": "Updated Silk Blouse to Casual White Tee.",
            "updated_item": {
                "name": "Casual White Tee",
                "category": "top",
                "color": "white",
                "style": "casual",
            },
            "original_item": target,
            "instruction": "make it more casual",
        }

        payload = serialize_inline_edit_result(
            result,
            service,
            current_outfit=outfit,
            target_item=target,
        )

        assert payload["outfit"] is not None
        for item in payload["outfit"]["items"]:
            if item["id"] not in others_before:
                continue
            before = others_before[item["id"]]
            assert item["name"] == before["name"]
            assert item["source"] == before["source"]
            assert item["owned"] == before["owned"]

    def test_integration_other_items_unchanged(self):
        outfit_response = legacy_client.post(
            "/api/outfits",
            json={"prompt": "casual outfit for today", "mode": "my_wardrobe"},
        )
        assert outfit_response.status_code == 200
        outfit = outfit_response.json()["outfit"]
        assert outfit is not None
        assert len(outfit["items"]) >= 2

        target = outfit["items"][0]
        others_before = {
            item["id"]: {
                "id": item["id"],
                "name": item["name"],
                "source": item.get("source"),
                "owned": item.get("owned"),
            }
            for item in outfit["items"]
            if item.get("id") != target.get("id")
        }

        edit_response = legacy_client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": outfit,
                "target_item": target,
                "instruction": "make it more comfortable and casual",
            },
        )
        assert edit_response.status_code == 200
        edited_outfit = edit_response.json()["outfit"]
        assert edited_outfit is not None

        for item in edited_outfit["items"]:
            if item["id"] not in others_before:
                continue
            before = others_before[item["id"]]
            assert item["name"] == before["name"]
            assert item.get("source") == before["source"]
            assert item.get("owned") == before["owned"]
