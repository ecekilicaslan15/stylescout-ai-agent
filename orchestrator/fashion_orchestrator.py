from dataclasses import asdict

from agents.planner import plan_user_request
from agents.trend_agent import get_trends
from agents.stylist_agent import create_outfit


def run_fashion_agent(user_input: str) -> dict:
    plan = plan_user_request(user_input)
    trends = get_trends(plan)
    outfit = create_outfit(plan, trends)

    return {
        "plan": asdict(plan),
        "trends": trends,
        "outfit": outfit
    }
