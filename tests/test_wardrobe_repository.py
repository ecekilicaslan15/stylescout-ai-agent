"""Tests for the wardrobe repository abstraction."""

import json
from unittest.mock import MagicMock, patch

import pytest

from agents.stylist_agent import StylistAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from models.plan import Plan, plan_to_dict
from orchestrator.fashion_orchestrator import FashionOrchestrator
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository

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
