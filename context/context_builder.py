from models.agent_context import AgentContext
from wardrobe.wardrobe_repository import WardrobeRepository


class ContextBuilder:
    """Builds AgentContext instances for agent runtime execution."""

    def build(
        self,
        user_input: str,
        plan=None,
        memory=None,
        current_outfit=None,
        selected_item=None,
        wardrobe=None,
        conversation_history=None,
        wardrobe_repository: WardrobeRepository | None = None,
    ) -> AgentContext:
        return AgentContext(
            user_input=user_input,
            plan=plan,
            memory=memory if memory is not None else {},
            current_outfit=current_outfit if current_outfit is not None else [],
            selected_item=selected_item,
            wardrobe=wardrobe if wardrobe is not None else [],
            conversation_history=conversation_history if conversation_history is not None else [],
            wardrobe_repository=wardrobe_repository,
        )
