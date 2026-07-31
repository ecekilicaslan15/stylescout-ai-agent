from agents.base_agent import BaseAgent
from agents.detectors.color_detector import detect_colors
from agents.inline_edit_config import InlineEditCriteria
from context.runtime_helpers import resolve_memory, resolve_wardrobe
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.wardrobe_repository import WardrobeRepository

OUTFIT_TO_WARDROBE_KEY = {
    "top": "tops",
    "bottom": "bottoms",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessory": "accessories",
}

CATEGORY_NORMALIZATION = {
    "tops": "top",
    "top": "top",
    "bottoms": "bottom",
    "bottom": "bottom",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessories": "accessory",
    "accessory": "accessory",
}

WEATHER_STYLE_BONUS = {
    "warm": {"casual": 3, "comfortable": 3, "sporty": 2, "elegant": -1, "formal": -2},
    "cold": {"elegant": 2, "classic": 2, "formal": 2, "casual": 0, "sporty": -1},
}

STYLE_SCORES = {
    "elegant": {
        "elegant": 10,
        "formal": 8,
        "classic": 7,
        "minimal": 6,
        "casual": 2,
        "sporty": 1,
        "streetwear": 1,
        "comfortable": 3,
    },
    "casual": {
        "casual": 10,
        "comfortable": 8,
        "sporty": 7,
        "streetwear": 6,
        "minimal": 4,
        "elegant": 2,
        "formal": 1,
        "classic": 3,
    },
}


def _normalize_category(category: str | None) -> str | None:
    if not category:
        return None
    return CATEGORY_NORMALIZATION.get(category.strip().lower())


def _normalize_color(color: str | None) -> str:
    if not color:
        return ""
    normalized = color.strip().lower()
    return "gray" if normalized == "grey" else normalized


class WardrobeAgent(BaseAgent):
    name = "wardrobe_agent"
    description = "Searches the user's wardrobe for items by category and style."

    def __init__(self, wardrobe_repository: WardrobeRepository | None = None) -> None:
        self._wardrobe_repository = wardrobe_repository or create_wardrobe_repository()

    def can_handle(self, plan: dict) -> bool:
        return plan.get("intent") == "wardrobe_search"

    def find_replacement(
        self,
        target_item: dict,
        target_style: str,
        memory: dict | None = None,
        instruction: str = "",
        wardrobe: list | dict | None = None,
        wardrobe_repository: WardrobeRepository | None = None,
        edit_criteria: InlineEditCriteria | None = None,
    ) -> AgentResponse:
        """Find the best wardrobe replacement for a single outfit item."""
        return self.run(
            user_input=instruction,
            plan={"intent": "wardrobe_search"},
            context={
                "action": "find_replacement",
                "target_item": target_item,
                "target_style": target_style,
                "memory": memory or {},
                "instruction": instruction,
                "wardrobe": wardrobe,
                "wardrobe_repository": wardrobe_repository,
                "edit_criteria": edit_criteria,
            },
        )

    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        if not isinstance(context, dict):
            context = {}

        action = context.get("action")
        target_item = context.get("target_item")
        target_style = context.get("target_style")
        memory = resolve_memory(context.get("memory"))
        instruction = context.get("instruction") or user_input
        edit_criteria = context.get("edit_criteria")
        repository = context.get("wardrobe_repository") or self._wardrobe_repository
        wardrobe = resolve_wardrobe(context.get("wardrobe"), repository)

        if action != "find_replacement":
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message="Unsupported wardrobe action.",
                data={},
                error=f"Unknown action: {action}",
            )

        if not target_item or not target_style:
            return AgentResponse(
                success=False,
                agent_name=self.name,
                message="Wardrobe search requires a target item and style.",
                data={},
                error="Missing target_item or target_style.",
            )

        category_items = self._get_category_items(wardrobe, target_item)
        outfit_category = _normalize_category(target_item.get("category"))

        if not category_items:
            return AgentResponse(
                success=True,
                agent_name=self.name,
                message=(
                    f"No wardrobe items found in the '{outfit_category}' category. "
                    "Add more pieces to your wardrobe first."
                ),
                data={
                    "replacement_item": None,
                    "match_type": None,
                    "explanation": "Category is empty in wardrobe.",
                    "target_item": target_item,
                    "target_style": target_style,
                },
            )

        disliked_items = memory.get("disliked_items", [])
        favorite_colors = memory.get("favorite_colors", [])
        if edit_criteria and edit_criteria.instruction_colors:
            instruction_colors = list(edit_criteria.instruction_colors)
        else:
            instruction_colors = detect_colors(instruction.lower())
        weather_hint = edit_criteria.weather_hint if edit_criteria else None

        best_item, match_type, explanation = self._find_best_replacement(
            category_items=category_items,
            target_item=target_item,
            target_style=target_style,
            disliked_items=disliked_items,
            favorite_colors=favorite_colors,
            instruction_colors=instruction_colors,
            weather_hint=weather_hint,
        )

        if best_item is None:
            return AgentResponse(
                success=True,
                agent_name=self.name,
                message=explanation,
                data={
                    "replacement_item": None,
                    "match_type": None,
                    "explanation": explanation,
                    "target_item": target_item,
                    "target_style": target_style,
                },
            )

        normalized = dict(best_item)
        normalized["category"] = outfit_category or target_item.get("category")

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message=explanation,
            data={
                "replacement_item": normalized,
                "match_type": match_type,
                "explanation": explanation,
                "target_item": target_item,
                "target_style": target_style,
            },
        )

    def _get_category_items(self, wardrobe: dict, target_item: dict) -> list[dict]:
        outfit_category = _normalize_category(target_item.get("category"))
        if not outfit_category:
            return []

        wardrobe_key = OUTFIT_TO_WARDROBE_KEY.get(outfit_category)
        if not wardrobe_key:
            return []

        return list(wardrobe.get(wardrobe_key, []))

    def _is_disliked(self, item_name: str, disliked_items: list[str]) -> bool:
        item_lower = item_name.strip().lower()
        for disliked in disliked_items:
            disliked_lower = disliked.strip().lower()
            if disliked_lower in item_lower or item_lower in disliked_lower:
                return True
        return False

    def _score_item(
        self,
        item: dict,
        target_item: dict,
        target_style: str,
        favorite_colors: list[str],
        instruction_colors: list[str],
        weather_hint: str | None = None,
    ) -> int:
        item_style = item.get("style", "casual")
        style_score = STYLE_SCORES.get(target_style, {}).get(item_style, 3)

        if weather_hint:
            style_score += WEATHER_STYLE_BONUS.get(weather_hint, {}).get(item_style, 0)

        color_bonus = 0
        item_color = _normalize_color(item.get("color"))
        target_color = _normalize_color(target_item.get("color"))

        if instruction_colors and item_color in instruction_colors:
            color_bonus = 4
        elif target_color and item_color == target_color:
            color_bonus = 2
        elif item_color in [_normalize_color(c) for c in favorite_colors]:
            color_bonus = 1

        return style_score + color_bonus

    def _find_best_replacement(
        self,
        category_items: list[dict],
        target_item: dict,
        target_style: str,
        disliked_items: list[str],
        favorite_colors: list[str],
        instruction_colors: list[str],
        weather_hint: str | None = None,
    ) -> tuple[dict | None, str | None, str]:
        target_name = target_item.get("name", "").strip().lower()
        candidates: list[tuple[int, dict]] = []

        for item in category_items:
            item_name = item.get("name", "").strip()
            if item_name.lower() == target_name:
                continue
            if self._is_disliked(item_name, disliked_items):
                continue

            score = self._score_item(
                item,
                target_item,
                target_style,
                favorite_colors,
                instruction_colors,
                weather_hint=weather_hint,
            )
            candidates.append((score, item))

        if not candidates:
            return (
                None,
                None,
                (
                    "No suitable replacement was found. Other items in this category "
                    "may be disliked or unavailable."
                ),
            )

        candidates.sort(key=lambda pair: pair[0], reverse=True)
        best_score, best_item = candidates[0]
        item_style = best_item.get("style", "")

        if item_style == target_style:
            match_type = "exact"
            explanation = (
                f"Found an exact {target_style} match in your wardrobe."
            )
        else:
            match_type = "closest"
            explanation = (
                f"No exact {target_style} match was available. "
                f"Selected the closest alternative ({best_item.get('name')}, "
                f"{item_style or 'unknown'} style)."
            )

        if best_score <= 0:
            return (
                None,
                None,
                (
                    f"No good {target_style} alternative exists in this category. "
                    "Try adding more wardrobe items."
                ),
            )

        return best_item, match_type, explanation
