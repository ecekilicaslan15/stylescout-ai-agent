from agents.base_agent import BaseAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse


class SewingAgent(BaseAgent):
    name = "sewing_agent"
    description = "Placeholder for sewing, alterations, and DIY guidance."

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "sewing_request"

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
                "SewingAgent is not connected yet. "
                "Alteration and sewing help will be available in a future release."
            ),
            data={},
        )
