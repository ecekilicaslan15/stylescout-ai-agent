from agents.inline_edit_agent import InlineEditAgent
from agents.memory_agent import MemoryAgent
from agents.planner import plan_user_request
from agents.sewing_agent import SewingAgent
from agents.shopping_agent import ShoppingAgent
from agents.stylist_agent import StylistAgent
from agents.trend_agent import TrendAgent
from agents.wardrobe_agent import WardrobeAgent
from context.context_builder import ContextBuilder
from memory.memory_manager import load_memory
from models.agent_response import AgentResponse
from models.plan import plan_to_dict
from wardrobe.wardrobe_manager import get_all_wardrobe_items, load_wardrobe

# Ordered agent sequence per intent. Multiple agents run left-to-right.
INTENT_AGENT_SEQUENCE: dict[str, list[str]] = {
    "memory_update": ["memory_agent"],
    "outfit_request": ["stylist_agent"],
    "outfit_request_with_memory_update": ["memory_agent", "stylist_agent"],
    "inline_edit": ["inline_edit_agent"],
    "sewing_request": ["sewing_agent"],
    "trend_request": ["trend_agent"],
    "shopping_request": ["shopping_agent"],
}


class FashionOrchestrator:
    """Routes user requests to the correct agent(s) based on plan intent."""

    def __init__(self) -> None:
        wardrobe_agent = WardrobeAgent()
        agents = [
            MemoryAgent(),
            StylistAgent(),
            InlineEditAgent(wardrobe_agent=wardrobe_agent),
            wardrobe_agent,
            SewingAgent(),
            TrendAgent(),
            ShoppingAgent(),
        ]
        self.agents = agents
        self.registry = {agent.name: agent for agent in agents}

    @staticmethod
    def _outfit_items(current_outfit) -> list:
        if isinstance(current_outfit, dict):
            return list(current_outfit.get("items", []))
        if isinstance(current_outfit, list):
            return list(current_outfit)
        return []

    def _resolve_agent_names(self, plan_dict: dict) -> list[str]:
        intent = plan_dict.get("intent", "outfit_request")

        if intent in INTENT_AGENT_SEQUENCE:
            return INTENT_AGENT_SEQUENCE[intent]

        matching = [agent.name for agent in self.agents if agent.can_handle(plan_dict)]
        if matching:
            return matching

        return ["stylist_agent"]

    def run(self, user_input: str) -> dict:
        plan = plan_user_request(user_input)
        plan_dict = plan_to_dict(plan)
        memory = load_memory()
        wardrobe = get_all_wardrobe_items(load_wardrobe())

        context_builder = ContextBuilder()
        context = context_builder.build(
            user_input=user_input,
            plan=plan,
            memory=memory,
            current_outfit=[],
            selected_item=None,
            wardrobe=wardrobe,
            conversation_history=[],
        )
        print("AgentContext:", context)

        outfit = None
        message = None
        stylist_notes = None

        for agent_name in self._resolve_agent_names(plan_dict):
            agent = self.registry[agent_name]
            response: AgentResponse = agent.run(user_input, plan_dict, context)

            if not response.success:
                if response.message:
                    message = response.message
                elif response.error:
                    message = response.error
                continue

            if "memory" in response.data:
                memory = response.data["memory"]
                context.memory = memory

            if "outfit" in response.data:
                outfit = response.data["outfit"]

            if response.data.get("stylist_notes"):
                stylist_notes = response.data["stylist_notes"]

            if response.message:
                message = response.message

        return {
            "plan": plan,
            "memory": memory,
            "outfit": outfit,
            "message": message,
            "stylist_notes": stylist_notes,
        }

    def run_inline_edit(
        self,
        current_outfit: dict,
        target_item: dict,
        instruction: str,
    ) -> dict:
        """Run a single-item inline edit without regenerating the full outfit."""
        plan_dict = {"intent": "inline_edit"}
        memory = load_memory()
        wardrobe = get_all_wardrobe_items(load_wardrobe())

        context_builder = ContextBuilder()
        context = context_builder.build(
            user_input=instruction,
            plan=plan_dict,
            memory=memory,
            current_outfit=self._outfit_items(current_outfit),
            selected_item=target_item,
            wardrobe=wardrobe,
            conversation_history=[],
        )
        print("AgentContext:", context)

        agent_context = {
            "current_outfit": current_outfit,
            "target_item": target_item,
            "instruction": instruction,
            "memory": memory,
        }

        response: AgentResponse = self.registry["inline_edit_agent"].run(
            instruction,
            plan_dict,
            agent_context,
        )

        return {
            "success": response.success,
            "message": response.message,
            "updated_item": response.data.get("updated_item"),
            "original_item": response.data.get("original_item"),
            "instruction": response.data.get("instruction"),
            "error": response.error,
        }


_orchestrator = FashionOrchestrator()


def run_fashion_agent(user_input: str) -> dict:
    """Public entry point used by the Streamlit app."""
    return _orchestrator.run(user_input)


def run_fashion_agent_response(user_input: str) -> AgentResponse:
    """Run the fashion pipeline and return a unified AgentResponse for the UI."""
    try:
        result = _orchestrator.run(user_input)
        message = result.get("message") or ""
        outfit = result.get("outfit")

        if outfit and not message:
            message = "Outfit generated successfully."
        elif not message:
            message = "Request processed successfully."

        return AgentResponse(
            success=True,
            agent_name="fashion_orchestrator",
            message=message,
            data={
                "plan": result["plan"],
                "memory": result["memory"],
                "outfit": outfit,
            },
        )
    except Exception as exc:
        return AgentResponse(
            success=False,
            agent_name="fashion_orchestrator",
            message="Failed to process your request.",
            data={},
            error=str(exc),
        )


def run_inline_edit(
    current_outfit: dict,
    target_item: dict,
    instruction: str,
) -> dict:
    """Public entry point for single-item inline edits from the UI."""
    return _orchestrator.run_inline_edit(current_outfit, target_item, instruction)
