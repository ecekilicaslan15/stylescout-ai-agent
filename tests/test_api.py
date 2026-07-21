"""Tests for the minimal StyleScout API."""

from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import (
    app,
    serialize_fashion_agent_result,
    serialize_inline_edit_result,
    serialize_wardrobe_item,
    to_agent_item,
)
from models.plan import Plan


client = TestClient(app)


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
        response = client.get("/api/wardrobe/items")

        assert response.status_code == 200
        items = response.json()
        assert isinstance(items, list)
        assert len(items) > 0

    def test_items_match_frontend_shape(self):
        item = client.get("/api/wardrobe/items").json()[0]

        assert {"id", "user_id", "name", "category", "color", "style", "event", "image_url", "created_at", "updated_at"} <= set(item)
        assert item["category"] in {"Tops", "Bottoms", "Shoes", "Outerwear", "Accessories"}


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
        mock_run_fashion_agent.assert_called_once_with("What should I wear today?")

    def test_create_outfit_integration(self):
        response = client.post(
            "/api/outfits",
            json={"prompt": "I need a casual outfit for today"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["outfit"] is not None
        assert isinstance(payload["outfit"]["items"], list)


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
        outfit_response = client.post(
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
        payload = serialize_fashion_agent_result(
            {
                "plan": Plan(intent="outfit_request", event="daily", style="casual"),
                "memory": {"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
                "outfit": None,
                "message": "Done",
                "stylist_notes": None,
            },
            wardrobe_update=None,
        )

        assert payload["plan"]["intent"] == "outfit_request"
        assert payload["message"] == "Done"

    def test_serialize_inline_edit_result_shapes_items(self):
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
            }
        )

        assert payload["updated_item"]["category"] == "Tops"
