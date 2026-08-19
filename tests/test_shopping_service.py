"""Tests for ShoppingService deep-link generation."""

from unittest.mock import MagicMock, patch
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from agents.stylist_agent import MAX_HYBRID_SUGGESTED_ITEMS
from api.main import _attach_shopping_links, app, serialize_fashion_agent_result
from api.session import LEGACY_USER_ID
from models.plan import Plan
from models.search_spec import SearchSpec
from models.styling_mode import StylingMode
from services.shopping_service import ShoppingService, VintedDeepLinkProvider, build_search_query
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService

legacy_client = TestClient(app)
legacy_client.cookies.set("stylescout_session", LEGACY_USER_ID)


class TestSearchSpecDeepLinks:
    @pytest.mark.parametrize(
        ("item", "expected_fragments"),
        [
            (
                {
                    "name": "White Linen Shirt",
                    "category": "Tops",
                    "color": "white",
                    "style": "casual",
                },
                ["white", "casual", "top", "White Linen Shirt"],
            ),
            (
                {
                    "name": "Black Heels",
                    "category": "Shoes",
                    "color": "black",
                    "style": "elegant",
                },
                ["black", "elegant", "shoes", "Black Heels"],
            ),
            (
                {
                    "name": "Camel Coat",
                    "category": "outerwear",
                    "color": "camel",
                    "style": "elegant",
                },
                ["camel", "elegant", "jacket", "Camel Coat"],
            ),
        ],
    )
    def test_search_spec_produces_vinted_catalog_url(self, item, expected_fragments):
        service = ShoppingService()
        spec = service.build_search_spec(item)
        url = service.build_deep_links(spec)["vinted"]

        parsed = urlparse(url)
        assert parsed.scheme == "https"
        assert parsed.netloc == "www.vinted.com"
        assert parsed.path == "/catalog"

        query = parse_qs(parsed.query)["search_text"][0]
        for fragment in expected_fragments:
            assert fragment.lower() in query.lower()

    def test_build_search_query_is_deterministic(self):
        spec = SearchSpec(
            name="Navy Blazer",
            category="outerwear",
            color="navy",
            style="elegant",
        )
        assert build_search_query(spec) == "navy elegant jacket Navy Blazer"


class TestShoppingService:
    def test_primary_shopping_link_uses_vinted_provider(self):
        service = ShoppingService(providers=[VintedDeepLinkProvider()])
        item = {
            "name": "Silk Scarf",
            "category": "accessory",
            "color": "beige",
            "style": "elegant",
            "source": "suggested",
            "owned": False,
        }
        link = service.primary_shopping_link(item)
        assert link.startswith("https://www.vinted.com/catalog?search_text=")


class TestShoppingServiceDelegation:
    def test_builds_search_spec_and_deep_links_for_item(self):
        service = ShoppingService()
        item = {
            "name": "White Sneakers",
            "category": "shoes",
            "color": "white",
            "style": "casual",
            "source": "suggested",
            "owned": False,
        }

        spec = service.build_search_spec(item)
        links = service.build_deep_links(spec)
        primary = links.get("vinted") or next(iter(links.values()), None)

        assert spec.name == "White Sneakers"
        assert "vinted" in links
        assert primary.startswith("https://www.vinted.com/catalog")


class TestOutfitShoppingLinksApi:
    def test_mode_one_response_has_no_shopping_link_fields(self):
        response = legacy_client.post(
            "/api/outfits",
            json={"prompt": "casual outfit for today", "mode": "my_wardrobe"},
        )
        assert response.status_code == 200
        items = response.json()["outfit"]["items"]
        assert items
        for item in items:
            assert "shopping_link" not in item
            assert item.get("source") == "wardrobe"
            assert item.get("owned") is True

    def test_mode_two_suggested_items_receive_shopping_links(self):
        items = [
            {
                "name": "White Elegant Shirt",
                "category": "Tops",
                "color": "white",
                "style": "elegant",
                "source": "wardrobe",
                "owned": True,
            },
            {
                "name": "Black Heels",
                "category": "Shoes",
                "color": "black",
                "style": "elegant",
                "source": "suggested",
                "owned": False,
            },
            {
                "name": "Silk Scarf",
                "category": "Accessories",
                "color": "beige",
                "style": "elegant",
                "source": "suggested",
                "owned": False,
            },
        ]
        attached = _attach_shopping_links(items, StylingMode.WARDROBE_PLUS_AI)
        suggested = [item for item in attached if item.get("source") == "suggested"]
        owned = [item for item in attached if item.get("source") == "wardrobe"]

        assert len(suggested) <= MAX_HYBRID_SUGGESTED_ITEMS
        assert len(suggested) == 2
        for item in suggested:
            assert item.get("owned") is False
            assert item.get("shopping_link", "").startswith(
                "https://www.vinted.com/catalog?search_text="
            )
            query = parse_qs(urlparse(item["shopping_link"]).query)["search_text"][0]
            assert item["color"].lower() in query.lower()
            assert item["style"].lower() in query.lower()
        for item in owned:
            assert "shopping_link" not in item

    @patch("api.main.run_fashion_agent")
    @patch("api.main.update_wardrobe_from_input", return_value=None)
    @patch("api.main.update_memory_from_input")
    def test_mode_two_api_attaches_one_link_per_suggested_item(
        self,
        _mock_memory,
        _mock_wardrobe,
        mock_run_fashion_agent,
    ):
        mock_run_fashion_agent.return_value = {
            "plan": Plan(intent="outfit_request", event="daily", style="elegant"),
            "outfit": {
                "items": [
                    {
                        "name": "White Elegant Shirt",
                        "category": "top",
                        "color": "white",
                        "style": "elegant",
                        "source": "wardrobe",
                        "owned": True,
                    },
                    {
                        "name": "Black Heels",
                        "category": "shoes",
                        "color": "black",
                        "style": "elegant",
                        "source": "suggested",
                        "owned": False,
                    },
                ],
                "reason": "Mixed outfit",
            },
            "message": None,
            "memory": {},
            "stylist_notes": None,
        }

        response = legacy_client.post(
            "/api/outfits",
            json={"prompt": "elegant dinner outfit", "mode": "wardrobe_plus_ai"},
        )
        assert response.status_code == 200
        items = response.json()["outfit"]["items"]
        suggested = [item for item in items if item.get("source") == "suggested"]
        assert len(suggested) == 1
        assert suggested[0]["shopping_link"].startswith("https://www.vinted.com/catalog")

    def test_attach_shopping_links_skips_mode_one(self):
        items = [
            {
                "name": "Suggested Top",
                "category": "Tops",
                "color": "white",
                "style": "casual",
                "source": "suggested",
                "owned": False,
            }
        ]
        attached = _attach_shopping_links(items, StylingMode.MY_WARDROBE)
        assert "shopping_link" not in attached[0]

    def test_serialize_fashion_agent_result_adds_links_for_mode_three(self):
        mock_repo = MagicMock(spec=JsonWardrobeRepository)
        mock_repo.get_all.return_value = []
        service = WardrobeService(repository=mock_repo, auto_seed=False)
        result = {
            "plan": None,
            "outfit": {
                "items": [
                    {
                        "id": "itm_suggested_blazer",
                        "name": "Black Blazer",
                        "category": "outerwear",
                        "color": "black",
                        "style": "elegant",
                        "source": "suggested",
                        "owned": False,
                    }
                ],
                "reason": "Inspired look.",
            },
            "message": "Done",
            "memory": {},
            "stylist_notes": None,
        }
        payload = serialize_fashion_agent_result(
            result,
            wardrobe_update=None,
            service=service,
            mode=StylingMode.AI_INSPIRATION,
        )
        item = payload["outfit"]["items"][0]
        assert item["shopping_link"].startswith("https://www.vinted.com/catalog")
