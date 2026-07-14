"""Tests for AgentContext as the primary agent runtime data source."""

from unittest.mock import MagicMock, patch

import pytest

from agents.inline_edit_agent import InlineEditAgent
from agents.memory_agent import MemoryAgent
from agents.stylist_agent import StylistAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from models.plan import Plan, plan_to_dict
from orchestrator.fashion_orchestrator import FashionOrchestrator
from services.rag_service import RetrievedChunk
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository

from tests.conftest import (
    CONTEXT_BOTTOM,
    CONTEXT_SHOES,
    CONTEXT_TOP,
)


class TestStylistAgentContext:
    """StylistAgent should consume wardrobe and memory from AgentContext."""

    def test_uses_wardrobe_from_agent_context(
        self,
        casual_plan_dict: dict,
        agent_context: AgentContext,
        disk_wardrobe_dict: dict,
    ):
        mock_repository = MagicMock(spec=JsonWardrobeRepository)
        mock_repository.get_by_category.return_value = disk_wardrobe_dict
        agent_context.wardrobe_repository = mock_repository

        agent = StylistAgent(rag_service=MagicMock(retrieve=lambda *args, **kwargs: []))
        response = agent.run("casual outfit", casual_plan_dict, agent_context)

        mock_repository.get_by_category.assert_not_called()

        item_names = {item["name"] for item in response.data["outfit"]["items"]}
        assert "Context Casual Top" in item_names
        assert "Context Jeans" in item_names
        assert "Context Sneakers" in item_names
        assert "Disk Only Top" not in item_names

    def test_uses_memory_from_agent_context(
        self,
        casual_plan: Plan,
        casual_plan_dict: dict,
        context_wardrobe_list: list[dict],
    ):
        """Disliked items from context memory should filter wardrobe picks."""
        wardrobe_with_blocked_item = context_wardrobe_list + [
            {
                "name": "Blocked Top",
                "category": "tops",
                "color": "black",
                "style": "casual",
            }
        ]
        context = AgentContext(
            user_input="casual outfit",
            plan=casual_plan,
            memory={
                "favorite_colors": ["white"],
                "preferred_styles": ["casual"],
                "disliked_items": ["Blocked Top"],
            },
            wardrobe=wardrobe_with_blocked_item,
        )
        agent = StylistAgent(rag_service=MagicMock(retrieve=lambda *args, **kwargs: []))

        with patch("context.runtime_helpers.load_memory") as mock_load_memory:
            response = agent.run("casual outfit", casual_plan_dict, context)

        mock_load_memory.assert_not_called()

        top_names = [
            item["name"]
            for item in response.data["outfit"]["items"]
            if item.get("category") in {"tops", "top"}
        ]
        assert "Context Casual Top" in top_names
        assert "Blocked Top" not in top_names

    def test_repository_fallback_not_used_when_context_exists(
        self,
        casual_plan_dict: dict,
        agent_context: AgentContext,
    ):
        mock_repository = MagicMock(spec=JsonWardrobeRepository)
        agent_context.wardrobe_repository = mock_repository
        agent = StylistAgent(rag_service=MagicMock(retrieve=lambda *args, **kwargs: []))

        with patch("context.runtime_helpers.load_memory") as mock_load_memory:
            with patch("agents.stylist_agent.load_memory") as mock_agent_memory:
                agent.run("casual outfit", casual_plan_dict, agent_context)

        mock_repository.get_by_category.assert_not_called()
        mock_repository.get_all.assert_not_called()
        mock_load_memory.assert_not_called()
        mock_agent_memory.assert_not_called()

    def test_stylist_notes_still_returned_for_fashion_query(self, casual_plan: Plan):
        """RAG notes remain a separate post-outfit step."""
        chunks = [
            RetrievedChunk(
                heading="Linen",
                content="Linen is a lightweight, breathable natural fabric made from flax fibers.",
                source="fabrics.md",
                score=5.0,
            ),
            RetrievedChunk(
                heading="Cotton",
                content="Cotton is a soft, breathable natural fabric that is comfortable in warm weather.",
                source="fabrics.md",
                score=4.0,
            ),
        ]
        rag_mock = MagicMock()
        rag_mock.retrieve.return_value = chunks

        context = AgentContext(
            user_input="casual outfit for hot weather in Istanbul",
            plan=casual_plan,
            memory={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            wardrobe=[CONTEXT_TOP, CONTEXT_BOTTOM, CONTEXT_SHOES],
        )
        agent = StylistAgent(rag_service=rag_mock)
        plan_dict = plan_to_dict(casual_plan)

        mock_repository = MagicMock(spec=JsonWardrobeRepository)
        context.wardrobe_repository = mock_repository

        with patch("context.runtime_helpers.load_memory") as mock_load_memory:
            response = agent.run(
                "casual outfit for hot weather in Istanbul",
                plan_dict,
                context,
            )

        mock_repository.get_by_category.assert_not_called()
        mock_load_memory.assert_not_called()
        rag_mock.retrieve.assert_called_once()

        notes = response.data.get("stylist_notes", "")
        assert "Linen" in notes
        assert "Cotton" in notes
        assert "Context Casual Top" in {item["name"] for item in response.data["outfit"]["items"]}


class TestOrchestratorContextFlow:
    """Orchestrator should build AgentContext and propagate updates between agents."""

    def test_updated_memory_available_to_next_agent(self):
        updated_memory = {
            "favorite_colors": ["purple"],
            "preferred_styles": ["elegant"],
            "disliked_items": [],
        }
        stylist_memories: list[dict] = []
        call_order: list[str] = []

        def memory_run(self, user_input, plan, context=None):
            call_order.append("memory_agent")
            return AgentResponse(
                success=True,
                agent_name="memory_agent",
                message="saved",
                data={"memory": updated_memory},
            )

        def stylist_run(self, user_input, plan, context=None):
            call_order.append("stylist_agent")
            stylist_memories.append(dict(context.memory))
            return AgentResponse(
                success=True,
                agent_name="stylist_agent",
                message="ok",
                data={"outfit": {"items": [], "event": "daily", "style": "elegant"}},
            )

        mock_repository = MagicMock(spec=JsonWardrobeRepository)
        mock_repository.get_all.return_value = []

        with patch.object(MemoryAgent, "run", memory_run):
            with patch.object(StylistAgent, "run", stylist_run):
                with patch(
                    "orchestrator.fashion_orchestrator.plan_user_request",
                    return_value=Plan(
                        intent="outfit_request_with_memory_update",
                        style="elegant",
                        colors=["purple"],
                    ),
                ):
                    with patch(
                        "orchestrator.fashion_orchestrator.load_memory",
                        return_value={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
                    ):
                        result = FashionOrchestrator(
                            wardrobe_repository=mock_repository,
                        ).run("I love purple elegant outfits")

        mock_repository.get_all.assert_called_once()
        assert call_order == ["memory_agent", "stylist_agent"]
        assert stylist_memories[0]["favorite_colors"] == ["purple"]
        assert result["memory"]["favorite_colors"] == ["purple"]


class TestInlineEditAgentContext:
    """Inline edit should read outfit fields and wardrobe from AgentContext."""

    def test_inline_edit_with_agent_context_uses_context_wardrobe(self, disk_wardrobe_dict: dict):
        casual_top = {
            "name": "Inline Casual Tee",
            "category": "tops",
            "color": "white",
            "style": "casual",
        }
        elegant_top = {
            "name": "Inline Elegant Blouse",
            "category": "tops",
            "color": "white",
            "style": "elegant",
        }
        mock_repository = MagicMock(spec=JsonWardrobeRepository)
        mock_repository.get_by_category.return_value = disk_wardrobe_dict

        context = AgentContext(
            user_input="make it more elegant",
            plan={"intent": "inline_edit"},
            memory={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            current_outfit=[casual_top],
            selected_item=casual_top,
            wardrobe=[casual_top, elegant_top],
            wardrobe_repository=mock_repository,
        )
        agent = InlineEditAgent()

        with patch("context.runtime_helpers.load_memory") as mock_load_memory:
            response = agent.run("make it more elegant", {"intent": "inline_edit"}, context)

        mock_repository.get_by_category.assert_not_called()
        mock_load_memory.assert_not_called()

        assert response.success is True
        assert response.data["updated_item"]["name"] == "Inline Elegant Blouse"
        assert "Updated Inline Casual Tee to Inline Elegant Blouse" in response.message
