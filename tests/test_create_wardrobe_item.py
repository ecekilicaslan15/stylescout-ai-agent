"""Tests for POST /api/wardrobe/items."""

import json

import pytest

from wardrobe.json_wardrobe_repository import JsonWardrobeRepository

pytestmark = pytest.mark.usefixtures("isolated_api_wardrobe_service")

VALID_PAYLOAD = {
    "name": "User Linen Shirt",
    "category": "Tops",
    "color": "beige",
    "style": "casual",
    "event": "everyday",
    "image_url": "https://example.com/shirt.jpg",
}


class TestCreateWardrobeItem:
    def test_create_success_returns_serialized_item(
        self, api_client, isolated_api_wardrobe_service
    ):
        service, _path = isolated_api_wardrobe_service

        response = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)

        assert response.status_code == 201
        payload = response.json()
        assert payload["name"] == "User Linen Shirt"
        assert payload["category"] == "Tops"
        assert payload["color"] == "beige"
        assert payload["style"] == "casual"
        assert payload["event"] == "everyday"
        assert payload["user_id"] == "test-isolated-user"
        assert payload["image_url"] == "https://example.com/shirt.jpg"
        assert {"id", "created_at", "updated_at"} <= set(payload)

        stored = service.list_items()[0]
        assert stored["source"] == "wardrobe"
        assert stored["owned"] is True
        assert stored["category"] == "tops"

    def test_create_validation_failure_for_invalid_category(
        self, api_client, isolated_api_wardrobe_service
    ):
        response = api_client.post(
            "/api/wardrobe/items",
            json={**VALID_PAYLOAD, "category": "Not A Real Category"},
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_create_persists_and_survives_read_back(
        self, api_client, isolated_api_wardrobe_service
    ):
        _service, wardrobe_path = isolated_api_wardrobe_service

        response = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)
        assert response.status_code == 201

        saved = json.loads(wardrobe_path.read_text(encoding="utf-8"))
        assert saved["tops"][0]["name"] == "User Linen Shirt"
        assert saved["tops"][0]["source"] == "wardrobe"
        assert saved["tops"][0]["owned"] is True
        assert saved["tops"][0]["user_id"] == "test-isolated-user"

        reloaded = JsonWardrobeRepository(wardrobe_path, user_id="test-isolated-user").get_all()
        assert len(reloaded) == 1
        assert reloaded[0]["name"] == "User Linen Shirt"
        assert reloaded[0]["category"] == "tops"

    def test_duplicate_name_without_confirm_returns_warning_and_does_not_create(
        self, api_client, isolated_api_wardrobe_service
    ):
        service, _path = isolated_api_wardrobe_service

        first = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)
        assert first.status_code == 201

        duplicate = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)
        assert duplicate.status_code == 409
        body = duplicate.json()
        assert body == {
            "error": "duplicate_name",
            "message": "An item named 'User Linen Shirt' already exists in Tops. Add it anyway?",
            "existing_item_id": first.json()["id"],
        }
        assert len(service.list_items()) == 1

    def test_duplicate_name_with_confirm_creates_item(
        self, api_client, isolated_api_wardrobe_service
    ):
        service, _path = isolated_api_wardrobe_service

        first = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)
        assert first.status_code == 201

        warned = api_client.post("/api/wardrobe/items", json=VALID_PAYLOAD)
        assert warned.status_code == 409

        confirmed = api_client.post(
            "/api/wardrobe/items",
            json={**VALID_PAYLOAD, "confirm_duplicate": True},
        )
        assert confirmed.status_code == 201
        assert confirmed.json()["name"] == "User Linen Shirt"
        assert confirmed.json()["id"] != first.json()["id"]
        assert len(service.list_items()) == 2
