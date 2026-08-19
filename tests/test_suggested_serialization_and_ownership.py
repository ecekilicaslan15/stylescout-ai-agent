"""API tests for suggested-item serialization (Bug A) and inspiration ownership (Bug B).

Prior mode tests called generate_outfit() directly and never hit POST /api/outfits
with an empty wardrobe — the serialization crash lived only on the API path.
"""

import pytest
from fastapi.testclient import TestClient

from agents.stylist_agent import generate_outfit, resolve_inspiration_ownership
from api.main import app, serialize_outfit_item
from models.plan import Plan
from models.styling_mode import StylingMode
from wardrobe.item_metadata import synthetic_suggested_item_id
from wardrobe.normalization import build_wardrobe_identity_set, item_matches_wardrobe_identity


@pytest.fixture
def api_client():
    return TestClient(app)


EMPTY_WARDROBE = {
    "tops": [],
    "bottoms": [],
    "shoes": [],
    "outerwear": [],
    "accessories": [],
}


class TestSuggestedItemSerialization:
    def test_synthetic_id_for_unowned_catalogue_item(self):
        item = {
            "name": "Blue Jeans",
            "category": "bottom",
            "color": "blue",
            "style": "casual",
            "source": "suggested",
            "owned": False,
        }
        wardrobe_by_category = {key: [] for key in EMPTY_WARDROBE}
        serialized = serialize_outfit_item(item, wardrobe_by_category)

        assert serialized["id"].startswith("sug_")
        assert serialized["source"] == "suggested"
        assert serialized["owned"] is False

    def test_synthetic_id_is_stable_for_same_catalogue_piece(self):
        item = {"name": "White Sneakers", "category": "shoes", "color": "white", "style": "casual"}
        first = synthetic_suggested_item_id(item)
        second = synthetic_suggested_item_id(item)
        assert first == second
        assert first.startswith("sug_")

    @pytest.mark.parametrize("mode", ["wardrobe_plus_ai", "ai_inspiration"])
    def test_empty_wardrobe_post_outfits_returns_200(
        self,
        isolated_api_wardrobe_service,
        api_client: TestClient,
        mode: str,
    ):
        response = api_client.post(
            "/api/outfits",
            json={"prompt": "casual outfit for today", "mode": mode},
        )

        assert response.status_code == 200
        payload = response.json()
        items = payload["outfit"]["items"]
        assert items
        for item in items:
            assert "id" in item
            assert item["name"]
            assert item["source"] in {"wardrobe", "suggested"}
            assert isinstance(item["owned"], bool)
            if item["source"] == "suggested":
                assert item["id"].startswith("sug_")


class TestInspirationOwnershipWithPersistedIds:
    def test_resolve_ownership_matches_by_name_when_wardrobe_has_persisted_id(self):
        wardrobe = {
            "tops": [],
            "bottoms": [
                {
                    "id": "itm_98d4adca",
                    "name": "Blue Jeans",
                    "category": "bottoms",
                    "color": "blue",
                    "style": "casual",
                }
            ],
            "shoes": [
                {
                    "id": "itm_abc12345",
                    "name": "White Sneakers",
                    "category": "shoes",
                    "color": "white",
                    "style": "casual",
                }
            ],
            "outerwear": [],
            "accessories": [],
        }
        catalogue_jeans = {
            "name": "Blue Jeans",
            "category": "bottom",
            "color": "blue",
            "style": "casual",
        }
        identity_set = build_wardrobe_identity_set(wardrobe)

        assert item_matches_wardrobe_identity(catalogue_jeans, identity_set)
        resolved = resolve_inspiration_ownership(catalogue_jeans, wardrobe)
        assert resolved["source"] == "wardrobe"
        assert resolved["owned"] is True

    def test_ai_inspiration_api_marks_persisted_wardrobe_match_owned(
        self,
        isolated_api_wardrobe_service,
        api_client: TestClient,
    ):
        service, _ = isolated_api_wardrobe_service
        service.add_item(
            "bottoms",
            {"name": "Blue Jeans", "color": "blue", "style": "casual", "event": "daily"},
        )
        service.add_item(
            "shoes",
            {"name": "White Sneakers", "color": "white", "style": "casual", "event": "daily"},
        )

        response = api_client.post(
            "/api/outfits",
            json={"prompt": "casual outfit for daily wear", "mode": "ai_inspiration"},
        )

        assert response.status_code == 200
        items = response.json()["outfit"]["items"]
        by_name = {item["name"]: item for item in items}

        assert by_name["Blue Jeans"]["source"] == "wardrobe"
        assert by_name["Blue Jeans"]["owned"] is True
        assert by_name["Blue Jeans"]["id"].startswith("itm_")

        assert by_name["White Sneakers"]["source"] == "wardrobe"
        assert by_name["White Sneakers"]["owned"] is True
        assert by_name["White Sneakers"]["id"].startswith("itm_")

    def test_generate_outfit_ownership_with_persisted_ids(self):
        """Unit-level regression: prior test wardrobe lacked ids and masked Bug B."""
        wardrobe = {
            "tops": [],
            "bottoms": [
                {
                    "id": "itm_test_jeans",
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
        plan = Plan(intent="outfit_request", event="daily", style="casual")
        outfit = generate_outfit(
            plan=plan,
            memory={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            wardrobe=wardrobe,
            mode=StylingMode.AI_INSPIRATION,
        )
        jeans = next(item for item in outfit["items"] if item["name"] == "Blue Jeans")
        assert jeans["source"] == "wardrobe"
        assert jeans["owned"] is True
