from agents.base_agent import BaseAgent
from agents.inline_edit_config import InlineEditCriteria, parse_inline_edit_instruction
from context.runtime_helpers import resolve_memory
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from services.wardrobe_matching_service import WardrobeMatchingService


def _resolve_inline_edit_fields(
    context: AgentContext | dict | None,
    user_input: str,
) -> dict:
    """Extract inline-edit fields from AgentContext or a legacy dict."""
    if isinstance(context, AgentContext):
        return {
            "current_outfit": context.current_outfit,
            "target_item": context.selected_item,
            "instruction": context.user_input or user_input,
            "memory": resolve_memory(context.memory),
            "wardrobe": context.wardrobe,
            "wardrobe_repository": context.wardrobe_repository,
        }

    context = context or {}
    return {
        "current_outfit": context.get("current_outfit"),
        "target_item": context.get("target_item"),
        "instruction": context.get("instruction") or user_input,
        "memory": resolve_memory(context.get("memory")),
        "wardrobe": context.get("wardrobe"),
        "wardrobe_repository": context.get("wardrobe_repository"),
    }


class InlineEditAgent(BaseAgent):
    name = "inline_edit_agent"
    description = "Edits a single outfit item based on a short instruction."

    def __init__(self, wardrobe_matching: WardrobeMatchingService | None = None) -> None:
        self._wardrobe_matching = wardrobe_matching or WardrobeMatchingService()

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "inline_edit"

    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        fields = _resolve_inline_edit_fields(context, user_input)
        current_outfit = fields["current_outfit"]
        target_item = fields["target_item"]
        instruction = fields["instruction"]
        memory = fields["memory"]

        if current_outfit is None or target_item is None:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message="Inline edit requires a current outfit and target item.",
                data={},
                error="missing_context",
            )

        instruction = instruction.strip()
        original_name = target_item.get("name", "this item")

        if not instruction:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message="Please describe how you want to update this item.",
                data={
                    "updated_item": target_item,
                    "original_item": target_item,
                    "instruction": instruction,
                },
                error="empty_instruction",
            )

        criteria = parse_inline_edit_instruction(instruction)
        if criteria is None:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message=(
                    "Could not understand that edit. Try mentioning comfort, formality, "
                    "color, weather, or words like 'elegant' or 'casual'."
                ),
                data={
                    "updated_item": target_item,
                    "original_item": target_item,
                    "instruction": instruction,
                },
                error="unrecognized_instruction",
            )

        wardrobe_response = self._wardrobe_matching.find_replacement(
            target_item=target_item,
            target_style=criteria.target_style,
            memory=memory,
            instruction=instruction,
            wardrobe=fields["wardrobe"],
            wardrobe_repository=fields.get("wardrobe_repository"),
            edit_criteria=criteria,
        )

        replacement = wardrobe_response.data.get("replacement_item")
        match_type = wardrobe_response.data.get("match_type")
        explanation = wardrobe_response.data.get("explanation") or wardrobe_response.message

        if replacement is None:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message=f"Could not replace {original_name}. {explanation}",
                data={
                    "updated_item": target_item,
                    "original_item": target_item,
                    "instruction": instruction,
                },
                error="no_replacement",
            )

        replacement_name = replacement.get("name", "another item")
        if match_type == "exact":
            message = f"Updated {original_name} to {replacement_name}."
        else:
            message = (
                f"Updated {original_name} to {replacement_name}. "
                f"{explanation}"
            )

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message=message,
            data={
                "updated_item": replacement,
                "original_item": target_item,
                "instruction": instruction,
                "match_type": match_type,
                "criteria": criteria,
            },
        )
