"""LLMPlanner + USE_LLM env toggle tests. HTTP to OpenRouter is always mocked."""

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from agents.planner import (
    last_plan_used_llm,
    llm_plan_error_count,
    llm_rate_limited_count,
    plan_user_request,
    use_llm_enabled,
)
from agents.planners.llm_planner import LLMPlanError, LLMPlanner
from agents.planners.rule_based_planner import RuleBasedPlanner
from api.main import app
from models.plan import Plan
from models.styling_mode import StylingMode
from services.llm_client import LLM_MODEL, LLMRateLimitError
from services.outfit_validator import FALLBACK_REASON, OutfitValidator

from tests.conftest import CONTEXT_TOP


client = TestClient(app)

VALID_PLAN_JSON = json.dumps(
    {
        "intent": "outfit_request",
        "event": "office",
        "style": "elegant",
        "colors": ["black"],
        "disliked_items": [],
        "city": "Istanbul",
        "date": "today",
        "allow_external": True,
        "wardrobe_optional": True,
    }
)


def _openrouter_response(content: str, status_code: int = 200) -> MagicMock:
    mock = MagicMock()
    mock.status_code = status_code
    mock.text = content
    mock.json.return_value = {"choices": [{"message": {"content": content}}]}
    return mock


def _invalid_outfit() -> dict:
    return {
        "items": [{"name": "", "category": "tops", "source": "suggested", "owned": False}],
        "reason": "broken",
    }


def _fallback_outfit() -> dict:
    return {
        "items": [
            {
                **CONTEXT_TOP,
                "id": "itm_context_top",
                "source": "wardrobe",
                "owned": True,
            }
        ],
        "reason": "fallback composer",
    }


class TestUseLlmEnvToggle:
    def test_use_llm_defaults_false_when_unset(self, monkeypatch):
        monkeypatch.delenv("USE_LLM", raising=False)
        assert use_llm_enabled() is False

        with patch.object(LLMPlanner, "plan") as llm_plan:
            with patch.object(
                RuleBasedPlanner,
                "plan",
                return_value=Plan().apply_styling_mode(StylingMode.MY_WARDROBE),
            ) as rule_plan:
                plan_user_request("casual outfit")

        rule_plan.assert_called_once()
        llm_plan.assert_not_called()

    def test_use_llm_false_keeps_rule_based_planner(self, monkeypatch):
        monkeypatch.setenv("USE_LLM", "false")
        assert use_llm_enabled() is False

        with patch.object(LLMPlanner, "plan") as llm_plan:
            with patch.object(
                RuleBasedPlanner,
                "plan",
                return_value=Plan().apply_styling_mode(StylingMode.MY_WARDROBE),
            ) as rule_plan:
                plan_user_request("casual outfit")

        rule_plan.assert_called_once()
        llm_plan.assert_not_called()

    @pytest.mark.parametrize("value", ["true", "TRUE", "1", "yes", "on"])
    def test_use_llm_truthy_selects_llm_planner(self, monkeypatch, value: str):
        monkeypatch.setenv("USE_LLM", value)
        assert use_llm_enabled() is True

        llm_plan_result = Plan(event="office").apply_styling_mode(StylingMode.MY_WARDROBE)
        with patch.object(LLMPlanner, "plan", return_value=llm_plan_result) as llm_plan:
            with patch.object(RuleBasedPlanner, "plan") as rule_plan:
                plan = plan_user_request("office outfit", mode=StylingMode.MY_WARDROBE)

        llm_plan.assert_called_once_with("office outfit", mode=StylingMode.MY_WARDROBE)
        rule_plan.assert_not_called()
        assert plan.event == "office"


class TestLlmPlannerParsing:
    def test_valid_json_becomes_plan_and_mode_flags_are_forced(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(return_value=_openrouter_response(VALID_PLAN_JSON))

        with patch("services.llm_client.requests.post", mock_post):
            plan = LLMPlanner().plan("elegant office look", mode=StylingMode.MY_WARDROBE)

        mock_post.assert_called_once()
        payload = mock_post.call_args.kwargs["json"]
        assert payload["model"] == LLM_MODEL
        assert plan.event == "office"
        assert plan.style == "elegant"
        assert plan.colors == ["black"]
        assert plan.city == "Istanbul"
        assert plan.date == "today"
        assert plan.allow_external is False
        assert plan.wardrobe_optional is False

    def test_malformed_response_raises_and_does_not_keyword_mock(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        content = "sure, an office wedding elegant black outfit coming right up"
        mock_post = MagicMock(return_value=_openrouter_response(content))

        with patch("services.llm_client.requests.post", mock_post):
            with pytest.raises(LLMPlanError):
                LLMPlanner().plan("office wedding elegant black")


class TestLlmPlannerValidationGate:
    def test_mocked_valid_llm_response_reaches_validation(
        self,
        monkeypatch,
        isolated_api_wardrobe_service,
        api_client: TestClient,
    ):
        monkeypatch.setenv("USE_LLM", "true")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(return_value=_openrouter_response(VALID_PLAN_JSON))

        with patch("services.llm_client.requests.post", mock_post):
            with patch(
                "api.main.OutfitValidator.validate_and_finalize",
                wraps=OutfitValidator.validate_and_finalize,
            ) as mock_gate:
                response = api_client.post(
                    "/api/outfits",
                    json={"prompt": "elegant office look", "mode": "my_wardrobe"},
                )

        assert response.status_code == 200
        mock_post.assert_called_once()
        assert mock_post.call_args.kwargs["json"]["model"] == LLM_MODEL
        mock_gate.assert_called_once()
        plan = response.json()["plan"]
        assert plan["event"] == "office"
        assert plan["style"] == "elegant"
        assert plan["colors"] == ["black"]
        assert plan["allow_external"] is False
        assert plan["wardrobe_optional"] is False
        trace = response.json()["pipeline_trace"]
        assert trace["composer"] == "STYLIST AGENT (LLM)"
        assert trace["use_llm"] is True
        assert llm_plan_error_count() == 0

    def test_mocked_malformed_response_triggers_repair_then_fallback(
        self,
        monkeypatch,
        isolated_api_wardrobe_service,
        api_client: TestClient,
    ):
        monkeypatch.setenv("USE_LLM", "true")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(
            return_value=_openrouter_response("this is not a plan json object")
        )
        invalid_outfit = _invalid_outfit()
        fallback_outfit = _fallback_outfit()

        with patch("services.llm_client.requests.post", mock_post):
            with patch(
                "agents.stylist_agent.generate_outfit",
                side_effect=[invalid_outfit, fallback_outfit],
            ) as mock_compose:
                with patch.object(
                    OutfitValidator,
                    "_repair_outfit",
                    wraps=OutfitValidator._repair_outfit,
                ) as mock_repair:
                    response = api_client.post(
                        "/api/outfits",
                        json={
                            "prompt": "office wedding elegant black",
                            "mode": "wardrobe_plus_ai",
                        },
                    )

        assert response.status_code == 200
        mock_post.assert_called_once()
        assert mock_repair.call_count == 1
        assert mock_compose.call_count == 2
        assert mock_compose.call_args.kwargs["mode"] == StylingMode.MY_WARDROBE
        payload = response.json()
        assert payload["outfit"]["reason"] == FALLBACK_REASON
        assert payload["plan"]["event"] == "office"

    def test_plan_fallback_trace_labels_are_rule_based_not_llm(
        self,
        monkeypatch,
        isolated_api_wardrobe_service,
        api_client: TestClient,
    ):
        monkeypatch.setenv("USE_LLM", "true")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(
            return_value=_openrouter_response("this is not a plan json object")
        )

        with patch("services.llm_client.requests.post", mock_post):
            response = api_client.post(
                "/api/outfits",
                json={"prompt": "casual outfit for today", "mode": "my_wardrobe"},
            )

        assert response.status_code == 200
        assert last_plan_used_llm() is False
        assert llm_plan_error_count() == 1
        trace = response.json()["pipeline_trace"]
        assert trace["composer"] == "RULE-BASED COMPOSER"
        assert trace["use_llm"] is False
        assert "stylist agent" not in trace["composer"].lower()
        assert trace["llm_plan_error_count"] == 1

        labels = api_client.get("/api/pipeline/trace-labels").json()
        assert labels["composer"] == "RULE-BASED COMPOSER"
        assert labels["use_llm"] is False
        assert labels["llm_plan_error_count"] == 1
        assert llm_rate_limited_count() == 0
        assert labels["llm_rate_limited_count"] == 0


class TestLlmRateLimit:
    def test_429_then_success_is_not_a_quality_failure(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(
            side_effect=[
                _openrouter_response("rate limited", status_code=429),
                _openrouter_response(VALID_PLAN_JSON),
            ]
        )

        with patch("services.llm_client.time.sleep") as mock_sleep:
            with patch("services.llm_client.requests.post", mock_post):
                plan = LLMPlanner().plan("elegant office look", mode=StylingMode.MY_WARDROBE)

        mock_sleep.assert_called_once()
        assert mock_post.call_count == 2
        assert plan.event == "office"
        assert llm_plan_error_count() == 0
        assert llm_rate_limited_count() == 0

    def test_exhausted_429_is_not_counted_as_json_quality_failure(
        self,
        monkeypatch,
        isolated_api_wardrobe_service,
        api_client: TestClient,
    ):
        monkeypatch.setenv("USE_LLM", "true")
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(
            side_effect=[
                _openrouter_response("rate limited", status_code=429),
                _openrouter_response("still rate limited", status_code=429),
            ]
        )

        with patch("services.llm_client.time.sleep") as mock_sleep:
            with patch("services.llm_client.requests.post", mock_post):
                response = api_client.post(
                    "/api/outfits",
                    json={"prompt": "casual outfit for today", "mode": "my_wardrobe"},
                )

        assert response.status_code == 200
        mock_sleep.assert_called_once()
        assert mock_post.call_count == 2
        assert llm_rate_limited_count() == 1
        assert llm_plan_error_count() == 0
        trace = response.json()["pipeline_trace"]
        assert trace["composer"] == "RULE-BASED COMPOSER"
        assert trace["use_llm"] is False
        assert trace["llm_rate_limited_count"] == 1
        assert trace["llm_plan_error_count"] == 0
        assert last_plan_used_llm() is False

    def test_exhausted_429_raises_rate_limit_error_not_plan_error(self, monkeypatch):
        monkeypatch.setenv("OPENROUTER_API_KEY", "test-key")
        mock_post = MagicMock(
            return_value=_openrouter_response("rate limited", status_code=429)
        )

        with patch("services.llm_client.time.sleep"):
            with patch("services.llm_client.requests.post", mock_post):
                with pytest.raises(LLMRateLimitError):
                    LLMPlanner().plan("casual outfit")

        assert llm_plan_error_count() == 0
