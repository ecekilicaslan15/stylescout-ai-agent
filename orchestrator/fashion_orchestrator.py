from agents.inline_edit_agent import InlineEditAgent
from agents.planner import plan_user_request
from agents.stylist_agent import StylistAgent
from context.context_builder import ContextBuilder
from memory.memory_manager import load_memory, update_memory_from_plan
from models.agent_response import AgentResponse
from models.plan import plan_to_dict
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from services.preference_service import load_preferences
from services.wardrobe_matching_service import WardrobeMatchingService
from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.wardrobe_repository import WardrobeRepository

# Ordered agent sequence per intent. Multiple agents run left-to-right.
INTENT_AGENT_SEQUENCE: dict[str, list[str]] = {
    "outfit_request": ["stylist_agent"],
    "outfit_request_with_memory_update": ["stylist_agent"],
    "inline_edit": ["inline_edit_agent"],
}

MEMORY_SAVED_MESSAGE = "Got it. I saved this preference to your style memory."
SEWING_STUB_MESSAGE = (
    "SewingAgent is not connected yet. "
    "Alteration and sewing help will be available in a future release."
)
TREND_STUB_MESSAGE = (
    "TrendAgent is not connected yet. "
    "Trend recommendations will be available in a future release."
)
SHOPPING_NO_ITEM_MESSAGE = "Provide an item to generate marketplace search links."


class FashionOrchestrator:
    """Routes user requests to the correct agent(s) based on plan intent."""

    def __init__(self, wardrobe_repository: WardrobeRepository | None = None) -> None:
        self._wardrobe_repository = wardrobe_repository or create_wardrobe_repository()
        wardrobe_matching = WardrobeMatchingService(wardrobe_repository=self._wardrobe_repository)
        agents = [
            StylistAgent(wardrobe_repository=self._wardrobe_repository),
            InlineEditAgent(wardrobe_matching=wardrobe_matching),
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

    def run(self, user_input: str, mode: StylingMode = DEFAULT_STYLING_MODE) -> dict:
        plan = plan_user_request(user_input, mode=mode)
        plan_dict = plan_to_dict(plan)
        intent = plan_dict.get("intent", "outfit_request")
        memory = load_memory()
        wardrobe = self._wardrobe_repository.get_all()
        preferences = load_preferences(self._wardrobe_repository.user_id)

        context_builder = ContextBuilder()
        context = context_builder.build(
            user_input=user_input,
            plan=plan,
            memory=memory,
            preferences=preferences,
            current_outfit=[],
            selected_item=None,
            wardrobe=wardrobe,
            conversation_history=[],
            wardrobe_repository=self._wardrobe_repository,
            mode=mode,
        )
        outfit = None
        message = None
        stylist_notes = None

        if intent in {"memory_update", "outfit_request_with_memory_update"}:
            memory = update_memory_from_plan(plan)
            context.memory = memory
            if intent == "memory_update":
                return {
                    "plan": plan,
                    "memory": memory,
                    "outfit": None,
                    "message": MEMORY_SAVED_MESSAGE,
                    "stylist_notes": None,
                }

        if intent == "sewing_request":
            return {
                "plan": plan,
                "memory": memory,
                "outfit": None,
                "message": SEWING_STUB_MESSAGE,
                "stylist_notes": None,
            }

        if intent == "trend_request":
            return {
                "plan": plan,
                "memory": memory,
                "outfit": None,
                "message": TREND_STUB_MESSAGE,
                "stylist_notes": None,
            }

        if intent == "shopping_request":
            return {
                "plan": plan,
                "memory": memory,
                "outfit": None,
                "message": SHOPPING_NO_ITEM_MESSAGE,
                "stylist_notes": None,
            }

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
        wardrobe = self._wardrobe_repository.get_all()
        preferences = load_preferences(self._wardrobe_repository.user_id)

        context_builder = ContextBuilder()
        context = context_builder.build(
            user_input=instruction,
            plan=plan_dict,
            memory=memory,
            preferences=preferences,
            current_outfit=self._outfit_items(current_outfit),
            selected_item=target_item,
            wardrobe=wardrobe,
            conversation_history=[],
            wardrobe_repository=self._wardrobe_repository,
        )

        response: AgentResponse = self.registry["inline_edit_agent"].run(
            instruction,
            plan_dict,
            context,
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


def run_fashion_agent(
    user_input: str,
    mode: StylingMode = DEFAULT_STYLING_MODE,
    *,
    wardrobe_repository: WardrobeRepository | None = None,
) -> dict:
    """Public entry point used by the Streamlit app."""
    if wardrobe_repository is not None:
        return FashionOrchestrator(wardrobe_repository=wardrobe_repository).run(
            user_input,
            mode=mode,
        )
    return _orchestrator.run(user_input, mode=mode)


def run_fashion_agent_response(
    user_input: str,
    mode: StylingMode = DEFAULT_STYLING_MODE,
) -> AgentResponse:
    """Run the fashion pipeline and return a unified AgentResponse for the UI."""
    try:
        result = _orchestrator.run(user_input, mode=mode)
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
    *,
    wardrobe_repository: WardrobeRepository | None = None,
) -> dict:
    """Public entry point for single-item inline edits from the UI."""
    if wardrobe_repository is not None:
        orchestrator = FashionOrchestrator(wardrobe_repository=wardrobe_repository)
        return orchestrator.run_inline_edit(current_outfit, target_item, instruction)
    return _orchestrator.run_inline_edit(current_outfit, target_item, instruction)
