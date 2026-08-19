"""Tests for styling mode contract: planner policy flags and orchestrator plumbing."""

from unittest.mock import MagicMock, patch

import pytest

from agents.planner import plan_user_request
from agents.planners.rule_based_planner import RuleBasedPlanner
from models.plan import Plan
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from orchestrator.fashion_orchestrator import FashionOrchestrator
from agents.stylist_agent import StylistAgent


class TestModePlannerPolicy:
    @pytest.mark.parametrize(
        ("mode", "allow_external", "wardrobe_optional"),
        [
            (StylingMode.MY_WARDROBE, False, False),
            (StylingMode.WARDROBE_PLUS_AI, True, False),
            (StylingMode.AI_INSPIRATION, True, True),
        ],
    )
    def test_rule_based_planner_sets_mode_policy(
        self,
        mode: StylingMode,
        allow_external: bool,
        wardrobe_optional: bool,
    ):
        plan = RuleBasedPlanner().plan("casual outfit for today", mode=mode)

        assert plan.allow_external is allow_external
        assert plan.wardrobe_optional is wardrobe_optional

    def test_plan_user_request_applies_mode(self):
        plan = plan_user_request("office outfit", mode=StylingMode.MY_WARDROBE)

        assert plan.allow_external is False
        assert plan.wardrobe_optional is False

    def test_default_mode_is_my_wardrobe(self):
        plan = plan_user_request("casual outfit")

        assert DEFAULT_STYLING_MODE == StylingMode.MY_WARDROBE
        assert plan.allow_external is False
        assert plan.wardrobe_optional is False


class TestModeOrchestratorPlumbing:
    def test_orchestrator_passes_mode_to_planner(self):
        mock_repository = MagicMock()
        mock_repository.get_all.return_value = []

        with patch(
            "orchestrator.fashion_orchestrator.plan_user_request",
            return_value=Plan(intent="outfit_request").apply_styling_mode(
                StylingMode.MY_WARDROBE
            ),
        ) as mock_plan:
            with patch(
                "orchestrator.fashion_orchestrator.load_memory",
                return_value={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            ):
                with patch.object(StylistAgent, "run") as stylist_run:
                    stylist_run.return_value = MagicMock(
                        success=True,
                        data={"outfit": {"items": []}},
                        message="ok",
                    )
                    FashionOrchestrator(wardrobe_repository=mock_repository).run(
                        "casual outfit",
                        mode=StylingMode.MY_WARDROBE,
                    )

        mock_plan.assert_called_once_with("casual outfit", mode=StylingMode.MY_WARDROBE)

    def test_plan_on_context_reflects_mode_policy(self):
        mock_repository = MagicMock()
        mock_repository.get_all.return_value = []
        captured: dict = {}

        def stylist_run(_self, _user_input, _plan_dict, context):
            captured["plan"] = context.plan
            captured["mode"] = context.mode
            return MagicMock(
                success=True,
                data={"outfit": {"items": []}},
                message="ok",
            )

        with patch.object(StylistAgent, "run", stylist_run):
            with patch(
                "orchestrator.fashion_orchestrator.load_memory",
                return_value={"favorite_colors": [], "preferred_styles": [], "disliked_items": []},
            ):
                FashionOrchestrator(wardrobe_repository=mock_repository).run(
                    "casual outfit",
                    mode=StylingMode.AI_INSPIRATION,
                )

        assert captured["mode"] == StylingMode.AI_INSPIRATION
        assert captured["plan"].allow_external is True
        assert captured["plan"].wardrobe_optional is True
