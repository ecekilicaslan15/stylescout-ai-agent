"""
Planner factory for StyleScout.

This module is the single entry point for the orchestrator. It selects
which planner implementation to use and exposes a stable function
(``plan_user_request``) so callers never import concrete planner classes.
"""

import logging
import os
import threading

from models.plan import Plan
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from agents.planners.llm_planner import LLMPlanError, LLMPlanner
from agents.planners.rule_based_planner import RuleBasedPlanner
from services.llm_client import LLMRateLimitError

_TRUTHY = frozenset({"1", "true", "yes", "on"})
_lock = threading.Lock()
_last_plan_used_llm: bool | None = None
_llm_plan_error_count = 0
_llm_rate_limited_count = 0
logger = logging.getLogger(__name__)


def use_llm_enabled() -> bool:
    """Return True when the USE_LLM env var is an explicit truthy value."""
    raw = (os.getenv("USE_LLM") or "false").strip().lower()
    return raw in _TRUTHY


# Import-time snapshot for callers that still read this name as a constant.
USE_LLM = use_llm_enabled()


def last_plan_used_llm() -> bool | None:
    """Whether the most recent plan_user_request used LLMPlanner. None if none yet."""
    return _last_plan_used_llm


def llm_plan_error_count() -> int:
    """How many times Gemini plan JSON was unparseable this process."""
    return _llm_plan_error_count


def llm_rate_limited_count() -> int:
    """How many requests fell back after an exhausted OpenRouter 429 retry."""
    return _llm_rate_limited_count


def reset_planner_observability() -> None:
    """Clear per-process planner path/counter (tests only)."""
    global _last_plan_used_llm, _llm_plan_error_count, _llm_rate_limited_count
    with _lock:
        _last_plan_used_llm = None
        _llm_plan_error_count = 0
        _llm_rate_limited_count = 0


def _record_plan_path(*, used_llm: bool) -> None:
    global _last_plan_used_llm
    with _lock:
        _last_plan_used_llm = used_llm


def _record_llm_plan_error() -> None:
    global _llm_plan_error_count, _last_plan_used_llm
    with _lock:
        _llm_plan_error_count += 1
        _last_plan_used_llm = False
        count = _llm_plan_error_count
    logger.info(
        "LLMPlanError: Gemini plan JSON unparseable; "
        "substituted RuleBasedPlanner (count=%s)",
        count,
    )


def _record_llm_rate_limit() -> None:
    global _llm_rate_limited_count, _last_plan_used_llm
    with _lock:
        _llm_rate_limited_count += 1
        _last_plan_used_llm = False
        count = _llm_rate_limited_count
    logger.info(
        "LLMRateLimitError: OpenRouter 429 after retry; "
        "substituted RuleBasedPlanner (count=%s)",
        count,
    )


def plan_user_request(
    user_input: str,
    mode: StylingMode = DEFAULT_STYLING_MODE,
) -> Plan:
    """
    Public planner entry point used by the orchestrator.

    Delegates to whichever implementation USE_LLM selects. Unparseable LLM
    JSON is not repaired here: LLMPlanner raises, and this factory falls
    through to RuleBasedPlanner so StylistAgent + OutfitValidator still run.
    """
    if use_llm_enabled():
        try:
            plan = LLMPlanner().plan(user_input, mode=mode)
            _record_plan_path(used_llm=True)
            return plan
        except LLMRateLimitError:
            _record_llm_rate_limit()
            return RuleBasedPlanner().plan(user_input, mode=mode)
        except LLMPlanError:
            _record_llm_plan_error()
            return RuleBasedPlanner().plan(user_input, mode=mode)
    _record_plan_path(used_llm=False)
    return RuleBasedPlanner().plan(user_input, mode=mode)
