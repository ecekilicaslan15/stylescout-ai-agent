"""Tests for the minimal StyleScout API."""

from unittest.mock import ANY, patch

import pytest
from fastapi.testclient import TestClient

from api.main import (
    app,
    serialize_fashion_agent_result,
    serialize_inline_edit_result,
    serialize_wardrobe_item,
    to_agent_item,
)
from api.session import LEGACY_USER_ID
from models.plan import Plan
from models.styling_mode import StylingMode
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService


client = TestClient(app)
legacy_client = TestClient(app)
legacy_client.cookies.set("stylescout_session", LEGACY_USER_ID)


class TestHealthEndpoint:
    def test_health_returns_ok(self):
        response = client.get("/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}

    def test_api_health_returns_ok(self):
        response = client.get("/api/health")

        assert response.status_code == 200
        assert response.json() == {"status": "ok", "version": "0.1.0"}


class TestWardrobeItemsEndpoint:
    def test_list_wardrobe_items_returns_array(self):
        response = legacy_client.get("/api/wardrobe/items")

        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        assert len(items) > 0

    def test_items_match_frontend_shape(self):
        item = legacy_client.get("/api/wardrobe/items").json()[0]

        assert {"id", "user_id", "name", "category", "color", "style", "event", "image_url", "created_at", "updated_at"} <= set(item)
        assert item["category"] in {"Tops", "Bottoms", "Shoes", "Outerwear", "Accessories"}

    def test_seeded_display_categories_are_non_empty(self):
        items = legacy_client.get("/api/wardrobe/items").json()
        counts = {label: 0 for label in ("Tops", "Bottoms", "Shoes", "Outerwear", "Accessories")}

        for item in items:
            counts[item["category"]] += 1

        assert sum(counts.values()) == len(items)
        assert all(count > 0 for count in counts.values())

    def test_category_labels_match_filter_vocabulary(self):
        labels = legacy_client.get("/api/wardrobe/category-labels").json()

        assert labels[0] == "All"
        assert labels[1:] == ["Tops", "Bottoms", "Shoes", "Outerwear", "Accessories"]

    def test_filter_all_returns_full_wardrobe(self):
        items = legacy_client.get("/api/wardrobe/items").json()
        expected = len(JsonWardrobeRepository(user_id=LEGACY_USER_ID).get_all())

        assert len(items) == expected

    def test_filter_tops_returns_seeded_count(self):
        items = legacy_client.get("/api/wardrobe/items").json()
        tops = [item for item in items if item["category"] == "Tops"]

        assert len(tops) == 5
        assert all(item["category"] == "Tops" for item in tops)


class TestOutfitsEndpoint:
    def test_create_outfit_requires_prompt(self):
        response = client.post("/api/outfits", json={"prompt": "   "})

        assert response.status_code == 400

    @patch("api.main.run_fashion_agent")
    @patch("api.main.update_wardrobe_from_input", return_value=None)
    @patch("api.main.update_memory_from_input")
    def test_create_outfit_returns_serialized_result(
        self,
        mock_update_memory,
        mock_update_wardrobe,
        mock_run_fashion_agent,
    ):
        mock_run_fashion_agent.return_value = {
            "plan": Plan(intent="outfit_request", event="daily", style="casual"),
            "memory": {
                "favorite_colors": ["black"],
                "preferred_styles": ["casual"],
                "disliked_items": [],
            },
            "outfit": {
                "event": "daily",
                "style": "casual",
                "city": None,
                "date": None,
                "reason": "Built from your wardrobe.",
                "items": [
                    {
                        "name": "White Elegant Shirt",
                        "category": "top",
                        "color": "white",
                        "style": "elegant",
                    }
                ],
            },
            "message": None,
            "stylist_notes": "Linen breathes well in warm weather.",
        }

        response = client.post(
            "/api/outfits",
            json={"prompt": "What should I wear today?"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["outfit"]["reason"] == "Built from your wardrobe."
        assert payload["outfit"]["items"][0]["category"] == "Tops"
        assert payload["stylist_notes"] == "Linen breathes well in warm weather."
        assert payload["plan"]["intent"] == "outfit_request"
        mock_run_fashion_agent.assert_called_once_with(
            "What should I wear today?",
            mode=StylingMode.WARDROBE_PLUS_AI,
            wardrobe_repository=ANY,
        )

    def test_create_outfit_integration(self):
        response = legacy_client.post(
            "/api/outfits",
            json={"prompt": "I need a casual outfit for today"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["outfit"] is not None
        assert isinstance(payload["outfit"]["items"], list)


class TestOutfitModePlumbing:
    @patch("api.main.run_fashion_agent")
    @patch("api.main.update_wardrobe_from_input", return_value=None)
    @patch("api.main.update_memory_from_input")
    def test_missing_mode_defaults_to_wardrobe_plus_ai(
        self,
        mock_update_memory,
        mock_update_wardrobe,
        mock_run_fashion_agent,
    ):
        mock_run_fashion_agent.return_value = {
            "plan": Plan(intent="outfit_request"),
            "memory": {},
            "outfit": None,
            "message": "Done",
            "stylist_notes": None,
        }

        response = client.post("/api/outfits", json={"prompt": "casual outfit"})

        assert response.status_code == 200
        mock_run_fashion_agent.assert_called_once_with(
            "casual outfit",
            mode=StylingMode.WARDROBE_PLUS_AI,
            wardrobe_repository=ANY,
        )

    @pytest.mark.parametrize(
        "mode",
        [
            StylingMode.MY_WARDROBE,
            StylingMode.WARDROBE_PLUS_AI,
            StylingMode.AI_INSPIRATION,
        ],
    )
    @patch("api.main.run_fashion_agent")
    @patch("api.main.update_wardrobe_from_input", return_value=None)
    @patch("api.main.update_memory_from_input")
    def test_valid_modes_are_accepted(
        self,
        mock_update_memory,
        mock_update_wardrobe,
        mock_run_fashion_agent,
        mode: StylingMode,
    ):
        mock_run_fashion_agent.return_value = {
            "plan": Plan(intent="outfit_request"),
            "memory": {},
            "outfit": None,
            "message": "Done",
            "stylist_notes": None,
        }

        response = client.post(
            "/api/outfits",
            json={"prompt": "casual outfit", "mode": mode.value},
        )

        assert response.status_code == 200
        mock_run_fashion_agent.assert_called_once_with(
            "casual outfit",
            mode=mode,
            wardrobe_repository=ANY,
        )

    def test_invalid_mode_is_rejected(self):
        response = client.post(
            "/api/outfits",
            json={"prompt": "casual outfit", "mode": "invalid_mode"},
        )

        assert response.status_code == 422


class TestInlineEditEndpoint:
    def test_inline_edit_requires_instruction(self):
        response = client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": {"items": [{"name": "White Shirt", "category": "Tops", "color": "white", "style": "casual"}]},
                "target_item": {"name": "White Shirt", "category": "Tops", "color": "white", "style": "casual"},
                "instruction": "   ",
            },
        )

        assert response.status_code == 400

    @patch("api.main.run_inline_edit")
    def test_inline_edit_returns_serialized_item(self, mock_run_inline_edit):
        mock_run_inline_edit.return_value = {
            "success": True,
            "message": "Updated Casual White T-Shirt to White Elegant Shirt.",
            "updated_item": {
                "name": "White Elegant Shirt",
                "category": "top",
                "color": "white",
                "style": "elegant",
            },
            "original_item": {
                "name": "Casual White T-Shirt",
                "category": "top",
                "color": "white",
                "style": "casual",
            },
            "instruction": "make it more elegant",
            "error": None,
        }

        response = client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": {
                    "items": [
                        {
                            "name": "Casual White T-Shirt",
                            "category": "Tops",
                            "color": "white",
                            "style": "casual",
                            "source_category": "top",
                        }
                    ]
                },
                "target_item": {
                    "name": "Casual White T-Shirt",
                    "category": "Tops",
                    "color": "white",
                    "style": "casual",
                    "source_category": "top",
                },
                "instruction": "make it more elegant",
            },
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["success"] is True
        assert payload["updated_item"]["category"] == "Tops"
        assert payload["updated_item"]["name"] == "White Elegant Shirt"
        mock_run_inline_edit.assert_called_once()

    def test_to_agent_item_maps_display_category(self):
        agent_item = to_agent_item(
            {
                "name": "Black Blazer",
                "category": "Outerwear",
                "color": "black",
                "style": "elegant",
            }
        )

        assert agent_item["category"] == "outerwear"

    def test_inline_edit_integration(self):
        outfit_response = legacy_client.post(
            "/api/outfits",
            json={"prompt": "casual outfit for today"},
        ).json()
        target = outfit_response["outfit"]["items"][0]

        edit_response = client.post(
            "/api/outfits/inline-edit",
            json={
                "current_outfit": outfit_response["outfit"],
                "target_item": target,
                "instruction": "make it more elegant",
            },
        )

        assert edit_response.status_code == 200
        payload = edit_response.json()
        assert payload["success"] is True
        assert payload["updated_item"] is not None
        assert payload["updated_item"]["category"] == target["category"]


class TestWardrobeSerializer:
    def test_serializes_repository_item_with_display_category(self):
        payload = serialize_wardrobe_item(
            {
                "id": "itm_test_white_shirt",
                "name": "White Elegant Shirt",
                "category": "tops",
                "color": "white",
                "style": "elegant",
            }
        )

        assert payload["name"] == "White Elegant Shirt"
        assert payload["category"] == "Tops"
        assert payload["color"] == "white"
        assert payload["event"] == "everyday"
        assert payload["image_url"]

    def test_serialize_fashion_agent_result_includes_plan_dict(self):
        service = WardrobeService(user_id=LEGACY_USER_ID, auto_seed=False)
        payload = serialize_fashion_agent_result(
            {
                "plan": Plan(intent="outfit_request", event="daily", style="casual"),
                "memory": {"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
                "outfit": None,
                "message": "Done",
                "stylist_notes": None,
            },
            wardrobe_update=None,
            service=service,
        )

        assert payload["plan"]["intent"] == "outfit_request"
        assert payload["message"] == "Done"

    def test_serialize_inline_edit_result_shapes_items(self):
        service = WardrobeService(user_id=LEGACY_USER_ID, auto_seed=False)
        payload = serialize_inline_edit_result(
            {
                "success": True,
                "message": "Updated item.",
                "updated_item": {
                    "name": "White Elegant Shirt",
                    "category": "top",
                    "color": "white",
                    "style": "elegant",
                },
                "original_item": {
                    "name": "Casual White T-Shirt",
                    "category": "top",
                    "color": "white",
                    "style": "casual",
                },
                "instruction": "make it more elegant",
                "error": None,
            },
            service=service,
        )

        assert payload["updated_item"]["category"] == "Tops"
