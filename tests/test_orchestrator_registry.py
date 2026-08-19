"""Orchestrator agent registry invariants (SCOUT-011)."""

from agents.inline_edit_agent import InlineEditAgent
from agents.stylist_agent import StylistAgent
from orchestrator.fashion_orchestrator import FashionOrchestrator


def test_orchestrator_registers_exactly_two_agents():
    orchestrator = FashionOrchestrator()
    agent_types = {type(agent) for agent in orchestrator.agents}

    assert len(orchestrator.agents) == 2
    assert agent_types == {StylistAgent, InlineEditAgent}
    assert set(orchestrator.registry) == {"stylist_agent", "inline_edit_agent"}
