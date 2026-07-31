"""Tests for PATCH and DELETE /api/wardrobe/items/{item_id}."""

import json

import pytest

from wardrobe.json_wardrobe_repository import JsonWardrobeRepository

pytestmark = pytest.mark.usefixtures("isolated_api_wardrobe_service")

CREATE_PAYLOAD = {
    "name": "User Linen Shirt",
    "category": "Tops",
    "color": "beige",
    "style": "casual",
    "event": "everyday",
}


class TestUpdateWardrobeItem:
    def test_edit_success_returns_serialized_item(
        self, api_client, isolated_api_wardrobe_service
    ):
        service, _path = isolated_api_wardrobe_service

        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        assert created.status_code == 201
        item_id = created.json()["id"]

        response = api_client.patch(
            f"/api/wardrobe/items/{item_id}",
            json={"name": "Renamed Linen Shirt", "color": "white"},
        )

        assert response.status_code == 200
        payload = response.json()
        assert payload["id"] == item_id
        assert payload["name"] == "Renamed Linen Shirt"
        assert payload["color"] == "white"
        assert payload["category"] == "Tops"

        stored = service.get_item_by_id(item_id)
        assert stored is not None
        assert stored["name"] == "Renamed Linen Shirt"
        assert stored["color"] == "white"

    def test_edit_validation_failure_for_invalid_category(
        self, api_client, isolated_api_wardrobe_service
    ):
        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        item_id = created.json()["id"]

        response = api_client.patch(
            f"/api/wardrobe/items/{item_id}",
            json={"category": "Not A Real Category"},
        )

        assert response.status_code == 422
        assert "detail" in response.json()

    def test_edit_persists_and_survives_read_back(
        self, api_client, isolated_api_wardrobe_service
    ):
        _service, wardrobe_path = isolated_api_wardrobe_service

        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        item_id = created.json()["id"]

        response = api_client.patch(
            f"/api/wardrobe/items/{item_id}",
            json={"style": "elegant", "event": "office"},
        )
        assert response.status_code == 200

        saved = json.loads(wardrobe_path.read_text(encoding="utf-8"))
        assert saved["tops"][0]["style"] == "elegant"
        assert saved["tops"][0]["event"] == "office"

        reloaded = JsonWardrobeRepository(wardrobe_path, user_id="test-isolated-user").get_item_by_id(item_id)
        assert reloaded is not None
        assert reloaded["style"] == "elegant"

    def test_edit_unknown_item_returns_404(self, api_client):
        response = api_client.patch(
            "/api/wardrobe/items/itm_doesnotexist",
            json={"name": "Ghost Shirt"},
        )
        assert response.status_code == 404


class TestDeleteWardrobeItem:
    def test_delete_success_removes_item(self, api_client, isolated_api_wardrobe_service):
        service, _path = isolated_api_wardrobe_service

        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        item_id = created.json()["id"]
        assert len(service.list_items()) == 1

        response = api_client.delete(f"/api/wardrobe/items/{item_id}")

        assert response.status_code == 204
        assert response.content == b""
        assert service.get_item_by_id(item_id) is None
        assert api_client.get("/api/wardrobe/items").json() == []

    def test_delete_unknown_item_returns_404(self, api_client):
        response = api_client.delete("/api/wardrobe/items/itm_doesnotexist")
        assert response.status_code == 404

    def test_delete_persists_after_reload(self, api_client, isolated_api_wardrobe_service):
        _service, wardrobe_path = isolated_api_wardrobe_service

        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        item_id = created.json()["id"]

        delete = api_client.delete(f"/api/wardrobe/items/{item_id}")
        assert delete.status_code == 204

        saved = json.loads(wardrobe_path.read_text(encoding="utf-8"))
        assert saved["tops"] == []

        reloaded = JsonWardrobeRepository(wardrobe_path, user_id="test-isolated-user").get_all()
        assert reloaded == []


class TestEditDuplicateNameFlow:
    def test_edit_duplicate_name_without_confirm_returns_409(
        self, api_client, isolated_api_wardrobe_service
    ):
        service, _path = isolated_api_wardrobe_service

        first = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        second = api_client.post(
            "/api/wardrobe/items",
            json={**CREATE_PAYLOAD, "name": "Other Shirt", "color": "white"},
        )
        second_id = second.json()["id"]

        response = api_client.patch(
            f"/api/wardrobe/items/{second_id}",
            json={"name": CREATE_PAYLOAD["name"]},
        )

        assert response.status_code == 409
        body = response.json()
        assert body["error"] == "duplicate_name"
        assert body["existing_item_id"] == first.json()["id"]
        assert service.get_item_by_id(second_id)["name"] == "Other Shirt"

    def test_edit_duplicate_name_with_confirm_succeeds(
        self, api_client, isolated_api_wardrobe_service
    ):
        first = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        second = api_client.post(
            "/api/wardrobe/items",
            json={**CREATE_PAYLOAD, "name": "Other Shirt", "color": "white"},
        )
        second_id = second.json()["id"]

        warned = api_client.patch(
            f"/api/wardrobe/items/{second_id}",
            json={"name": CREATE_PAYLOAD["name"]},
        )
        assert warned.status_code == 409

        confirmed = api_client.patch(
            f"/api/wardrobe/items/{second_id}",
            json={"name": CREATE_PAYLOAD["name"], "confirm_duplicate": True},
        )
        assert confirmed.status_code == 200
        assert confirmed.json()["name"] == CREATE_PAYLOAD["name"]
        assert confirmed.json()["id"] == second_id
        assert confirmed.json()["id"] != first.json()["id"]


class TestRenamePreservesItemId:
    def test_rename_preserves_item_id(self, api_client, isolated_api_wardrobe_service):
        created = api_client.post("/api/wardrobe/items", json=CREATE_PAYLOAD)
        assert created.status_code == 201
        original_id = created.json()["id"]

        renamed = api_client.patch(
            f"/api/wardrobe/items/{original_id}",
            json={"name": "Renamed Linen Shirt"},
        )
        assert renamed.status_code == 200
        assert renamed.json()["id"] == original_id
        assert renamed.json()["name"] == "Renamed Linen Shirt"

        listed = api_client.get("/api/wardrobe/items").json()
        match = next(item for item in listed if item["id"] == original_id)
        assert match["name"] == "Renamed Linen Shirt"


class TestPersistedSeedItemIds:
    def test_edit_seed_item_by_persisted_id(self, api_client, isolated_api_wardrobe_service):
        _service, wardrobe_path = isolated_api_wardrobe_service
        seed_id = "itm_seed_white_shirt"
        wardrobe_path.write_text(
            json.dumps(
                {
                    "tops": [
                        {
                            "id": seed_id,
                            "name": "Seed White Shirt",
                            "category": "tops",
                            "color": "white",
                            "style": "casual",
                            "user_id": "test-isolated-user",
                            "source": "wardrobe",
                            "owned": True,
                            "created_at": "2026-07-27T00:00:00Z",
                            "updated_at": "2026-07-27T00:00:00Z",
                        }
                    ],
                    "bottoms": [],
                    "shoes": [],
                    "outerwear": [],
                    "accessories": [],
                }
            ),
            encoding="utf-8",
        )

        response = api_client.patch(
            f"/api/wardrobe/items/{seed_id}",
            json={"color": "black", "name": "Seed Black Shirt"},
        )

        assert response.status_code == 200
        assert response.json()["id"] == seed_id
        assert response.json()["name"] == "Seed Black Shirt"
        assert response.json()["color"] == "black"
