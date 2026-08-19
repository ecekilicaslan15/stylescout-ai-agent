from pathlib import Path

from context.runtime_helpers import resolve_memory, resolve_plan, resolve_wardrobe
from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.wardrobe_manager import load_wardrobe
from wardrobe.wardrobe_repository import WardrobeRepository

from agents.base_agent import BaseAgent
from memory.memory_manager import load_memory
from models.agent_context import AgentContext
from models.agent_response import AgentResponse
from models.plan import Plan, plan_from_dict
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
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
MAX_HYBRID_SUGGESTED_ITEMS = 2

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

# DEFAULT_ITEMS catalogue names — used by inspiration/suggested fallbacks.
DEFAULT_ITEM_NAMES = frozenset(item["name"] for item in DEFAULT_ITEMS)


def wardrobe_item_key(item: dict) -> tuple:
    """Stable wardrobe identity: repository id when present, else (category, name)."""
    item_id = item.get("id")
    if item_id is not None:
        return ("id", item_id)
    category = _normalize_category(item.get("category")) or (item.get("category") or "")
    name = (item.get("name") or "").strip().lower()
    return ("name", category, name)


def _build_wardrobe_identity_set(wardrobe: dict) -> set[tuple]:
    keys: set[tuple] = set()
    for category_items in wardrobe.values():
        for item in category_items:
            keys.add(wardrobe_item_key(item))
    return keys


def resolve_inspiration_ownership(item: dict, wardrobe: dict) -> dict:
    """Post-generation ownership resolver for ai_inspiration mode.

    Separated so sub-task B (full validation gate) can invoke it independently.
    """
    if wardrobe_item_key(item) in _build_wardrobe_identity_set(wardrobe):
        return _with_provenance(item, source="wardrobe", owned=True)
    return _with_provenance(item, source="suggested", owned=False)


def _mode_from_plan(plan: Plan) -> StylingMode:
    if plan.wardrobe_optional:
        return StylingMode.AI_INSPIRATION
    if plan.allow_external:
        return StylingMode.WARDROBE_PLUS_AI
    return StylingMode.MY_WARDROBE


def _coerce_plan(plan) -> Plan:
    if isinstance(plan, Plan):
        return plan
    return plan_from_dict(plan)


def _with_provenance(item: dict, *, source: str, owned: bool) -> dict:
    annotated = dict(item)
    annotated["source"] = source
    annotated["owned"] = owned
    return annotated


def _wardrobe_pool(wardrobe: dict, outfit_category: str) -> list[dict]:
    wardrobe_key = OUTFIT_TO_WARDROBE_KEY[outfit_category]
    return list(wardrobe.get(wardrobe_key, []))


def _default_pool(outfit_category: str) -> list[dict]:
    return [
        item
        for item in DEFAULT_ITEMS
        if _normalize_category(item.get("category")) == outfit_category
    ]


def _build_outfit_reason(
    mode: StylingMode,
    wardrobe_count: int,
    suggested_count: int,
) -> str:
    if wardrobe_count == 0 and suggested_count == 0:
        if mode == StylingMode.MY_WARDROBE:
            return (
                "No items in your wardrobe matched this request. "
                "Add pieces to your wardrobe or try a different prompt."
            )
        if mode == StylingMode.WARDROBE_PLUS_AI:
            return (
                "No wardrobe or suggested items matched this request. "
                "Try adjusting your prompt or adding pieces to your wardrobe."
            )
        if mode == StylingMode.AI_INSPIRATION:
            return (
                "No inspiration items matched this request. "
                "Try adjusting your prompt or style preferences."
            )
        return (
            "No matching items were found for this request. "
            "Try adjusting your request or adding more clothes to your wardrobe."
        )

    if mode == StylingMode.AI_INSPIRATION:
        if wardrobe_count == 0:
            return "Generated as an inspiration outfit from your style preferences."
        if suggested_count == 0:
            return (
                "Generated as inspiration — every piece matches something you already own."
            )
        return "Generated as inspiration — some pieces match items you already own."

    if suggested_count == 0:
        return (
            "This outfit was built from your saved wardrobe by picking the best item "
            "from each category based on event, style, saved memory, and color preferences."
        )

    if wardrobe_count == 0:
        return (
            "Suggested items to complete your look — add more to your wardrobe "
            "to personalize future outfits."
        )

    return (
        "This outfit combines pieces from your wardrobe with suggested items "
        "for missing categories."
    )


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


def _pick_wardrobe_item(
    wardrobe: dict,
    outfit_category: str,
    plan,
    favorite_colors: list[str],
    preferred_styles: list[str],
    disliked_items: list[str],
) -> dict | None:
    items_pool = _wardrobe_pool(wardrobe, outfit_category)
    if not items_pool:
        return None

    return _select_best_item(
        items=items_pool,
        outfit_category=outfit_category,
        plan=plan,
        favorite_colors=favorite_colors,
        preferred_styles=preferred_styles,
        disliked_items=disliked_items,
        use_default_rules=False,
    )


def _pick_suggested_item(
    outfit_category: str,
    plan,
    favorite_colors: list[str],
    preferred_styles: list[str],
    disliked_items: list[str],
) -> dict | None:
    items_pool = _default_pool(outfit_category)
    if not items_pool:
        return None

    return _select_best_item(
        items=items_pool,
        outfit_category=outfit_category,
        plan=plan,
        favorite_colors=favorite_colors,
        preferred_styles=preferred_styles,
        disliked_items=disliked_items,
        use_default_rules=True,
    )


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


def generate_outfit(
    plan,
    memory: dict,
    wardrobe: dict | None = None,
    mode: StylingMode | None = None,
) -> dict:
    plan_obj = _coerce_plan(plan)
    if mode is not None:
        plan_obj.apply_styling_mode(mode)

    if wardrobe is None:
        wardrobe = load_wardrobe()

    effective_mode = _mode_from_plan(plan_obj)
    allow_external = plan_obj.allow_external
    wardrobe_optional = plan_obj.wardrobe_optional

    favorite_colors = memory.get("favorite_colors", [])
    preferred_styles = memory.get("preferred_styles", [])
    disliked_items = memory.get("disliked_items", [])

    wardrobe_identities = _build_wardrobe_identity_set(wardrobe)
    selected_items: list[dict] = []
    wardrobe_count = 0
    suggested_count = 0

    if wardrobe_optional:
        for category in OUTFIT_CATEGORIES:
            inspiration_item = _pick_suggested_item(
                category,
                plan_obj,
                favorite_colors,
                preferred_styles,
                disliked_items,
            )
            if not inspiration_item:
                continue

            annotated = resolve_inspiration_ownership(inspiration_item, wardrobe)
            selected_items.append(annotated)
            if annotated["owned"]:
                wardrobe_count += 1
            else:
                suggested_count += 1
    elif allow_external:
        for category in OUTFIT_CATEGORIES:
            wardrobe_item = _pick_wardrobe_item(
                wardrobe,
                category,
                plan_obj,
                favorite_colors,
                preferred_styles,
                disliked_items,
            )
            if wardrobe_item:
                selected_items.append(
                    _with_provenance(wardrobe_item, source="wardrobe", owned=True)
                )
                wardrobe_count += 1
                continue

            if suggested_count >= MAX_HYBRID_SUGGESTED_ITEMS:
                continue

            suggested_item = _pick_suggested_item(
                category,
                plan_obj,
                favorite_colors,
                preferred_styles,
                disliked_items,
            )
            if suggested_item:
                selected_items.append(
                    _with_provenance(suggested_item, source="suggested", owned=False)
                )
                suggested_count += 1
    else:
        for category in OUTFIT_CATEGORIES:
            wardrobe_item = _pick_wardrobe_item(
                wardrobe,
                category,
                plan_obj,
                favorite_colors,
                preferred_styles,
                disliked_items,
            )
            if not wardrobe_item:
                continue

            selected_items.append(
                _with_provenance(wardrobe_item, source="wardrobe", owned=True)
            )
            wardrobe_count += 1

    reason = _build_outfit_reason(effective_mode, wardrobe_count, suggested_count)

    outfit = {
        "event": plan_obj.event,
        "style": plan_obj.style,
        "city": plan_obj.city,
        "date": plan_obj.date,
        "items": selected_items,
        "reason": reason,
    }

    if not wardrobe_optional and not allow_external and selected_items and wardrobe_identities:
        for item in selected_items:
            if item.get("source") != "wardrobe" or item.get("owned") is not True:
                raise RuntimeError(
                    f"my_wardrobe outfit item {item.get('name')!r} has invalid provenance"
                )
            if wardrobe_item_key(item) not in wardrobe_identities:
                raise RuntimeError(
                    f"my_wardrobe outfit item {item.get('name')!r} is not in the wardrobe snapshot"
                )

    # Validated in api/main.py via OutfitValidator after generation (SCOUT-002 sub-task B).
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
        memory, wardrobe, plan_obj, query_input, mode = self._resolve_runtime(
            user_input, plan, context
        )

        plan_obj.apply_styling_mode(mode)

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
    ) -> tuple[dict, dict, Plan, str, StylingMode]:
        """Resolve memory, wardrobe, plan, mode, and query text for outfit generation."""
        mode = DEFAULT_STYLING_MODE
        if isinstance(context, AgentContext):
            repository = context.wardrobe_repository or self._wardrobe_repository
            memory = resolve_memory(context.memory)
            wardrobe = resolve_wardrobe(context.wardrobe, repository)
            plan_obj = resolve_plan(plan, context)
            query_input = context.user_input or user_input
            mode = context.mode
        elif isinstance(context, dict):
            repository = context.get("wardrobe_repository") or self._wardrobe_repository
            memory = resolve_memory(context.get("memory"))
            wardrobe = resolve_wardrobe(context.get("wardrobe"), repository)
            plan_obj = resolve_plan(plan, context)
            query_input = user_input
            mode = context.get("mode", DEFAULT_STYLING_MODE)
        else:
            memory = load_memory()
            wardrobe = resolve_wardrobe(None, self._wardrobe_repository)
            plan_obj = resolve_plan(plan, context)
            query_input = user_input

        return memory, wardrobe, plan_obj, query_input, mode

    def _retrieve_stylist_notes(self, user_input: str, plan_obj: Plan) -> str:
        """Retrieve fashion knowledge after outfit generation and format stylist notes."""
        knowledge_query = build_knowledge_query(user_input, plan_obj)
        chunks = self._rag_service.retrieve(knowledge_query, top_k=3)
        return build_stylist_notes(chunks)
