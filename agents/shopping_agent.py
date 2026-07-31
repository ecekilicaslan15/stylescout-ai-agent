from agents.base_agent import BaseAgent
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from services.shopping_service import ShoppingService


def _extract_item(context: AgentContext | dict | None) -> dict | None:
    if isinstance(context, AgentContext):
        return context.selected_item
    if isinstance(context, dict):
        return context.get("item") or context.get("target_item")
    return None


class ShoppingAgent(BaseAgent):
    name = "shopping_agent"
    description = "Generates marketplace search deep-links for suggested items."

    def __init__(self, shopping_service: ShoppingService | None = None) -> None:
        self._shopping_service = shopping_service or ShoppingService()

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "shopping_request"

    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        item = _extract_item(context)
        if not item:
            return AgentResponse(
                success=True,
                agent_name=self.name,
                message="Provide an item to generate marketplace search links.",
                data={},
            )

        try:
            spec = self._shopping_service.build_search_spec(item)
        except ValueError as exc:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message=str(exc),
                data={},
                error="invalid_item",
            )

        links = self._shopping_service.build_deep_links(spec)
        primary = links.get("vinted") or next(iter(links.values()), None)

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message="Generated marketplace search links for this item.",
            data={
                "search_spec": spec.model_dump(),
                "shopping_links": links,
                "shopping_link": primary,
            },
        )
