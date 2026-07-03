"""
Planner factory for StyleScout.

This module is the single entry point for the orchestrator. It selects
which planner implementation to use and exposes a stable function
(``plan_user_request``) so callers never import concrete planner classes.
"""

from models.plan import Plan
from agents.planners.llm_planner import LLMPlanner
from agents.planners.rule_based_planner import RuleBasedPlanner

# ---------------------------------------------------------------------------
# Configuration: flip this flag when LLMPlanner is ready for production.
# ---------------------------------------------------------------------------
USE_LLM = False

if USE_LLM:
    planner = LLMPlanner()
else:
    planner = RuleBasedPlanner()


def plan_user_request(user_input: str) -> Plan:
    """
    Public planner entry point used by the orchestrator.

    Delegates to whichever implementation was selected above. The orchestrator
    and UI depend on this function—not on RuleBasedPlanner or LLMPlanner
    directly—so switching planners requires changing only USE_LLM here.
    """
    return planner.plan(user_input)
