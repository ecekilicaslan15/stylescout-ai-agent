from agents.base_agent import BaseAgent
from agents.wardrobe_agent import WardrobeAgent
from models.agent_response import AgentResponse


def _detect_target_style(instruction: str) -> str | None:
    text = instruction.lower()
    if "elegant" in text:
        return "elegant"
    if "casual" in text:
        return "casual"
    return None


class InlineEditAgent(BaseAgent):
    name = "inline_edit_agent"
    description = "Edits a single outfit item based on a short instruction."

    def __init__(self, wardrobe_agent: WardrobeAgent | None = None) -> None:
        self._wardrobe_agent = wardrobe_agent or WardrobeAgent()

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "inline_edit"

    def run(
        self,
        user_input: str,
        plan: dict,
        context: dict | None = None,
    ) -> AgentResponse:
        context = context or {}
        current_outfit = context.get("current_outfit")
        target_item = context.get("target_item")
        instruction = context.get("instruction") or user_input
        memory = context.get("memory") or {}

        if current_outfit is None or target_item is None:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message="Inline edit requires a current outfit and target item.",
                data={},
                error="Missing current_outfit or target_item in context.",
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
                error="Empty instruction.",
            )

        target_style = _detect_target_style(instruction)
        if target_style is None:
            return AgentResponse(
                success=True,
                agent_name=self.name,
                message=(
                    f"Kept {original_name}. No style keyword found — "
                    "try words like 'elegant' or 'casual'."
                ),
                data={
                    "updated_item": target_item,
                    "original_item": target_item,
                    "instruction": instruction,
                },
            )

        wardrobe_response = self._wardrobe_agent.find_replacement(
            target_item=target_item,
            target_style=target_style,
            memory=memory,
            instruction=instruction,
        )

        replacement = wardrobe_response.data.get("replacement_item")
        match_type = wardrobe_response.data.get("match_type")
        explanation = wardrobe_response.data.get("explanation") or wardrobe_response.message

        if replacement is None:
            return AgentResponse(
                success=True,
                agent_name=self.name,
                message=f"Kept {original_name}. {explanation}",
                data={
                    "updated_item": target_item,
                    "original_item": target_item,
                    "instruction": instruction,
                },
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
            },
        )
