from agents.base_agent import BaseAgent
from memory.memory_manager import update_memory_from_plan
from models.agent_response import AgentResponse
from models.plan import plan_from_dict


class MemoryAgent(BaseAgent):
    name = "memory_agent"
    description = "Saves style preferences, favorite colors, and disliked items."

    _HANDLED_INTENTS = {"memory_update", "outfit_request_with_memory_update"}

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") in self._HANDLED_INTENTS

    def run(
        self,
        user_input: str,
        plan: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        memory = update_memory_from_plan(plan_from_dict(plan))

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message="Got it. I saved this preference to your style memory.",
            data={"memory": memory},
        )
