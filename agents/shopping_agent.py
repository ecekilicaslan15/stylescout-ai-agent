from agents.base_agent import BaseAgent
from models.agent_response import AgentResponse


class ShoppingAgent(BaseAgent):
    name = "shopping_agent"
    description = "Placeholder for shopping suggestions and product discovery."

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "shopping_request"

    def run(
        self,
        user_input: str,
        plan: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        return AgentResponse(
            success=True,
            agent_name=self.name,
            message=(
                "ShoppingAgent is not connected yet. "
                "Shopping suggestions will be available in a future release."
            ),
            data={},
        )
