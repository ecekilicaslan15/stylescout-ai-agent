from pathlib import Path

from context.runtime_helpers import resolve_memory, resolve_plan, resolve_wardrobe
from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.wardrobe_manager import load_wardrobe
from wardrobe.wardrobe_repository import WardrobeRepository

from agents.base_agent import BaseAgent
from memory.memory_manager import load_memory
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from models.plan import Plan
from services.rag_service import RagService
from services.stylist_notes_builder import build_knowledge_query, build_stylist_notes

KNOWLEDGE_DIR = Path(__file__).resolve().parent.parent / "knowledge"


DEFAULT_ITEMS = [
    {"name": "Black Blazer", "category": "outerwear",
        "color": "black", "style": "elegant", "event": "office"},
    {"name": "White Shirt", "category": "top", "color": "white",
        "style": "minimal", "event": "office"},
    {"name": "Beige Trousers", "category": "bottom",
        "color": "beige", "style": "elegant", "event": "office"},
    {"name": "Black Loafers", "category": "shoes",
        "color": "black", "style": "elegant", "event": "office"},
    {"name": "Blue Jeans", "category": "bottom",
        "color": "blue", "style": "casual", "event": "daily"},
    {"name": "White Sneakers", "category": "shoes",
        "color": "white", "style": "casual", "event": "daily"},
]

OUTFIT_CATEGORIES = ["top", "bottom", "shoes", "outerwear", "accessory"]

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

OUTFIT_TO_WARDROBE_KEY = {
    "top": "tops",
    "bottom": "bottoms",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessory": "accessories",
}


def _normalize_category(category: str | None) -> str | None:
    if not category:
        return None

    return CATEGORY_NORMALIZATION.get(category.strip().lower())


def _is_disliked(item_name: str, disliked_items: list[str]) -> bool:
    item_name_lower = item_name.lower()

    for disliked in disliked_items:
        disliked_lower = disliked.lower()
        if disliked_lower in item_name_lower or item_name_lower in disliked_lower:
            return True

    return False


def _score_item(
    item: dict,
    plan,
    favorite_colors: list[str],
    preferred_styles: list[str],
) -> int:
    score = 0

    if item.get("event") == plan.event:
        score += 5

    if item.get("style") == plan.style:
        score += 2

    if item.get("style") in preferred_styles:
        score += 2

    preferred_colors = plan.colors if plan.colors else favorite_colors

    if item.get("color") in preferred_colors:
        score += 2

    if item.get("color") in favorite_colors:
        score += 2

    return score


def _get_category_items(wardrobe: dict, outfit_category: str) -> tuple[list[dict], bool]:
    wardrobe_key = OUTFIT_TO_WARDROBE_KEY[outfit_category]
    wardrobe_items = list(wardrobe.get(wardrobe_key, []))

    if wardrobe_items:
        return wardrobe_items, False

    default_items = [
        item
        for item in DEFAULT_ITEMS
        if _normalize_category(item.get("category")) == outfit_category
    ]

    return default_items, True


def _select_best_item(
    items: list[dict],
    outfit_category: str,
    plan,
    favorite_colors: list[str],
    preferred_styles: list[str],
    disliked_items: list[str],
    use_default_rules: bool,
) -> dict | None:
    best_item = None
    best_score = -1

    for item in items:
        item_name = item.get("name", "")

        if _is_disliked(item_name, disliked_items):
            continue

        category = _normalize_category(item.get("category"))
        if category != outfit_category:
            continue

        if use_default_rules and item.get("event") != plan.event:
            continue

        score = _score_item(item, plan, favorite_colors, preferred_styles)

        if best_item is None or score > best_score:
            best_score = score
            best_item = item

    if use_default_rules and best_score <= 0:
        return None

    return best_item


def generate_outfit(plan, memory: dict, wardrobe: dict | None = None) -> dict:
    if wardrobe is None:
        wardrobe = load_wardrobe()

    favorite_colors = memory.get("favorite_colors", [])
    preferred_styles = memory.get("preferred_styles", [])
    disliked_items = memory.get("disliked_items", [])

    selected_items = []
    used_wardrobe = False
    used_defaults = False

    for category in OUTFIT_CATEGORIES:
        items_pool, use_default_rules = _get_category_items(wardrobe, category)

        if not items_pool:
            continue

        if use_default_rules:
            used_defaults = True
        else:
            used_wardrobe = True

        best_item = _select_best_item(
            items=items_pool,
            outfit_category=category,
            plan=plan,
            favorite_colors=favorite_colors,
            preferred_styles=preferred_styles,
            disliked_items=disliked_items,
            use_default_rules=use_default_rules,
        )

        if best_item:
            selected_items.append(best_item)

    if used_wardrobe and used_defaults:
        reason = (
            "This outfit combines your saved wardrobe pieces with default suggestions "
            "for categories you have not added yet, using event, style, saved memory, "
            "and color preferences."
        )
    elif used_wardrobe:
        reason = (
            "This outfit was built from your saved wardrobe by picking the best item "
            "from each category based on event, style, saved memory, and color preferences."
        )
    else:
        reason = (
            "This outfit was built from the default wardrobe using event, style, "
            "saved memory, and color preferences."
        )

    outfit = {
        "event": plan.event,
        "style": plan.style,
        "city": plan.city,
        "date": plan.date,
        "items": selected_items,
        "reason": reason,
    }

    if not selected_items:
        outfit["reason"] = (
            "No matching items were found for this request. "
            "Try adjusting your request or adding more clothes to your wardrobe."
        )

    return outfit


class StylistAgent(BaseAgent):
    name = "stylist_agent"
    description = "Builds outfit recommendations from wardrobe items and style memory."

    _HANDLED_INTENTS = {"outfit_request", "outfit_request_with_memory_update"}

    def __init__(
        self,
        rag_service: RagService | None = None,
        wardrobe_repository: WardrobeRepository | None = None,
    ) -> None:
        self._rag_service = rag_service or RagService(KNOWLEDGE_DIR)
        self._wardrobe_repository = wardrobe_repository or create_wardrobe_repository()

    def can_handle(self, plan: dict) -> bool:
        intent = plan.get("intent", "outfit_request")

        if intent in self._HANDLED_INTENTS:
            return True

        return intent not in {
            "memory_update",
            "inline_edit",
            "sewing_request",
            "trend_request",
            "shopping_request",
        }

    def run(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None = None,
    ) -> AgentResponse:
        memory, wardrobe, plan_obj, query_input = self._resolve_runtime(
            user_input, plan, context
        )

        outfit = generate_outfit(
            plan=plan_obj,
            memory=memory,
            wardrobe=wardrobe,
        )

        stylist_notes = self._retrieve_stylist_notes(query_input, plan_obj)

        response_data = {"outfit": outfit}
        if stylist_notes:
            response_data["stylist_notes"] = stylist_notes

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message="Outfit generated successfully.",
            data=response_data,
        )

    def _resolve_runtime(
        self,
        user_input: str,
        plan: dict,
        context: AgentContext | dict | None,
    ) -> tuple[dict, dict, Plan, str]:
        """Resolve memory, wardrobe, plan, and query text without affecting outfit scoring."""
        if isinstance(context, AgentContext):
            repository = context.wardrobe_repository or self._wardrobe_repository
            memory = resolve_memory(context.memory)
            wardrobe = resolve_wardrobe(context.wardrobe, repository)
            plan_obj = resolve_plan(plan, context)
            query_input = context.user_input or user_input
        elif isinstance(context, dict):
            repository = context.get("wardrobe_repository") or self._wardrobe_repository
            memory = resolve_memory(context.get("memory"))
            wardrobe = resolve_wardrobe(context.get("wardrobe"), repository)
            plan_obj = resolve_plan(plan, context)
            query_input = user_input
        else:
            memory = load_memory()
            wardrobe = resolve_wardrobe(None, self._wardrobe_repository)
            plan_obj = resolve_plan(plan, context)
            query_input = user_input

        return memory, wardrobe, plan_obj, query_input

    def _retrieve_stylist_notes(self, user_input: str, plan_obj: Plan) -> str:
        """Retrieve fashion knowledge after outfit generation and format stylist notes."""
        knowledge_query = build_knowledge_query(user_input, plan_obj)
        chunks = self._rag_service.retrieve(knowledge_query, top_k=3)
        return build_stylist_notes(chunks)
