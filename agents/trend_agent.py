from agents.base_agent import BaseAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse


class TrendAgent(BaseAgent):
    name = "trend_agent"
    description = "Placeholder for trend discovery and seasonal inspiration."

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "trend_request"

    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            success=True,
            agent_name=self.name,
            message=(
                "TrendAgent is not connected yet. "
                "Trend recommendations will be available in a future release."
            ),
            data={},
        )
