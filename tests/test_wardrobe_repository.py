"""Tests for the wardrobe repository abstraction."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.stylist_agent import StylistAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from models.plan import Plan, plan_to_dict
from orchestrator.fashion_orchestrator import FashionOrchestrator
from wardrobe.json_wardrobe_repository import DEFAULT_JSON_PATH, JsonWardrobeRepository

from tests.conftest import CONTEXT_BOTTOM, CONTEXT_SHOES, CONTEXT_TOP


@pytest.fixture
def temp_repository(tmp_path) -> JsonWardrobeRepository:
    wardrobe_path = tmp_path / "wardrobe.json"
    wardrobe_path.write_text(
        json.dumps(
            {
                "tops": [
                    {
                        "name": "Repo White Shirt",
                        "category": "tops",
                        "color": "white",
                        "style": "casual",
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
    return JsonWardrobeRepository(wardrobe_path)


class TestJsonWardrobeRepository:
    def test_get_all_reads_from_json_file(self, temp_repository: JsonWardrobeRepository):
        items = temp_repository.get_all()
        assert len(items) == 1
        assert items[0]["name"] == "Repo White Shirt"

    def test_find_by_category(self, temp_repository: JsonWardrobeRepository):
        tops = temp_repository.find_by_category("tops")
        assert len(tops) == 1
        assert temp_repository.find_by_category("bottoms") == []

    def test_find_by_color(self, temp_repository: JsonWardrobeRepository):
        matches = temp_repository.find_by_color("white")
        assert len(matches) == 1
        assert matches[0]["name"] == "Repo White Shirt"

    def test_add_item_persists_to_json_file(self, tmp_path):
        repository = JsonWardrobeRepository(tmp_path / "wardrobe.json")
        added = repository.add_item(
            "shoes",
            {"name": "Repo Sneakers", "color": "white", "style": "casual"},
        )

        assert added is True
        saved = json.loads((tmp_path / "wardrobe.json").read_text(encoding="utf-8"))
        assert saved["shoes"][0]["name"] == "Repo Sneakers"

    def test_refuses_to_write_production_seed_during_pytest(self, monkeypatch):
        monkeypatch.delenv("WARDROBE_JSON_PATH", raising=False)
        repository = JsonWardrobeRepository(DEFAULT_JSON_PATH)

        with pytest.raises(RuntimeError, match="production seed wardrobe.json"):
            repository.add_item(
                "tops",
                {"name": "Must Not Persist", "color": "white", "style": "casual"},
            )

    def test_update_item_refuses_production_seed_during_pytest(self, monkeypatch):
        monkeypatch.delenv("WARDROBE_JSON_PATH", raising=False)
        repository = JsonWardrobeRepository(DEFAULT_JSON_PATH)
        item_id = repository.get_all()[0]["id"]

        with pytest.raises(RuntimeError, match="production seed wardrobe.json"):
            repository.update_item(item_id, {"color": "hotpink"})

    def test_duplicate_name_allowed_across_different_users(self, tmp_path):
        wardrobe_path = tmp_path / "wardrobe.json"
        wardrobe_path.write_text(
            json.dumps(
                {
                    "tops": [
                        {
                            "name": "Shared Shirt Name",
                            "category": "tops",
                            "color": "white",
                            "style": "casual",
                            "id": "itm_user_a",
                            "user_id": "user_a",
                        },
                        {
                            "name": "Shared Shirt Name",
                            "category": "tops",
                            "color": "blue",
                            "style": "casual",
                            "id": "itm_user_b",
                            "user_id": "user_b",
                        },
                    ],
                    "bottoms": [],
                    "shoes": [],
                    "outerwear": [],
                    "accessories": [],
                }
            ),
            encoding="utf-8",
        )

        user_a_repo = JsonWardrobeRepository(wardrobe_path, user_id="user_a")
        updated = user_a_repo.update_item("itm_user_a", {"color": "hotpink"})

        assert updated is True
        saved = json.loads(wardrobe_path.read_text(encoding="utf-8"))
        user_a_item = next(item for item in saved["tops"] if item["id"] == "itm_user_a")
        user_b_item = next(item for item in saved["tops"] if item["id"] == "itm_user_b")
        assert user_a_item["color"] == "hotpink"
        assert user_b_item["color"] == "blue"

    def test_duplicate_name_blocked_within_same_user(self, tmp_path):
        wardrobe_path = tmp_path / "wardrobe.json"
        wardrobe_path.write_text(
            json.dumps(
                {
                    "tops": [
                        {
                            "name": "White Shirt",
                            "category": "tops",
                            "color": "white",
                            "style": "casual",
                            "id": "itm_one",
                            "user_id": "user_a",
                        },
                        {
                            "name": "Blue Shirt",
                            "category": "tops",
                            "color": "blue",
                            "style": "casual",
                            "id": "itm_two",
                            "user_id": "user_a",
                        },
                    ],
                    "bottoms": [],
                    "shoes": [],
                    "outerwear": [],
                    "accessories": [],
                }
            ),
            encoding="utf-8",
        )

        repository = JsonWardrobeRepository(wardrobe_path, user_id="user_a")
        blocked = repository.update_item("itm_two", {"name": "White Shirt"})

        assert blocked is False

    def test_delete_item_refuses_production_seed_during_pytest(self, monkeypatch):
        monkeypatch.delenv("WARDROBE_JSON_PATH", raising=False)
        repository = JsonWardrobeRepository(DEFAULT_JSON_PATH)
        item_id = repository.get_all()[0]["id"]

        with pytest.raises(RuntimeError, match="production seed wardrobe.json"):
            repository.delete_item(item_id)


class TestAgentsUseRepository:
    def test_stylist_agent_uses_repository_fallback_not_json_file(
        self,
        casual_plan: Plan,
        casual_plan_dict: dict,
    ):
        mock_repository = MagicMock()
        mock_repository.get_by_category.return_value = {
            "tops": [CONTEXT_TOP],
            "bottoms": [CONTEXT_BOTTOM],
            "shoes": [CONTEXT_SHOES],
            "outerwear": [],
            "accessories": [],
        }

        agent = StylistAgent(
            rag_service=MagicMock(retrieve=lambda *args, **kwargs: []),
            wardrobe_repository=mock_repository,
        )
        response = agent.run("casual outfit", casual_plan_dict, context=None)

        mock_repository.get_by_category.assert_called_once()
        item_names = {item["name"] for item in response.data["outfit"]["items"]}
        assert "Context Casual Top" in item_names

    def test_stylist_agent_does_not_call_repository_when_context_has_wardrobe(
        self,
        casual_plan_dict: dict,
        agent_context: AgentContext,
    ):
        mock_repository = MagicMock()
        agent_context.wardrobe_repository = mock_repository

        agent = StylistAgent(
            rag_service=MagicMock(retrieve=lambda *args, **kwargs: []),
            wardrobe_repository=mock_repository,
        )
        agent.run("casual outfit", casual_plan_dict, agent_context)

        mock_repository.get_by_category.assert_not_called()
        mock_repository.get_all.assert_not_called()

    def test_orchestrator_loads_wardrobe_through_repository(self):
        mock_repository = MagicMock()
        mock_repository.get_all.return_value = [CONTEXT_TOP]

        stylist_response = AgentResponse(
            success=True,
            agent_name="stylist_agent",
            message="ok",
            data={"outfit": {"items": [CONTEXT_TOP]}},
        )

        with patch(
            "orchestrator.fashion_orchestrator.plan_user_request",
            return_value=Plan(intent="outfit_request"),
        ):
            with patch(
                "orchestrator.fashion_orchestrator.load_memory",
                return_value={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            ):
                with patch.object(StylistAgent, "run", return_value=stylist_response):
                    FashionOrchestrator(wardrobe_repository=mock_repository).run("casual outfit")

        mock_repository.get_all.assert_called_once()
