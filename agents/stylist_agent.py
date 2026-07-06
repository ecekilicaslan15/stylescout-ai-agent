from wardrobe.wardrobe_manager import load_wardrobe

from agents.base_agent import BaseAgent
from memory.memory_manager import load_memory
from models.agent_response import AgentResponse
from models.plan import plan_from_dict

# Fallback items when the user's wardrobe is still empty.
DEFAULT_ITEMS = [
    {
        "name": "Black Blazer",
        "category": "outerwear",
        "color": "black",
        "style": "elegant",
        "event": "office",
    },
    {
        "name": "White Shirt",
        "category": "top",
        "color": "white",
        "style": "minimal",
        "event": "office",
    },
    {
        "name": "Beige Trousers",
        "category": "bottom",
        "color": "beige",
        "style": "elegant",
        "event": "office",
    },
    {
        "name": "Black Loafers",
        "category": "shoes",
        "color": "black",
        "style": "elegant",
        "event": "office",
    },
    {
        "name": "Blue Jeans",
        "category": "bottom",
        "color": "blue",
        "style": "casual",
        "event": "daily",
    },
    {
        "name": "White Sneakers",
        "category": "shoes",
        "color": "white",
        "style": "casual",
        "event": "daily",
    },
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
    """Map wardrobe and legacy category names to outfit slots."""
    if not category:
        return None

    return CATEGORY_NORMALIZATION.get(category.strip().lower())


def _is_disliked(item_name: str, disliked_items: list[str]) -> bool:
    """Return True if the item matches any disliked entry."""
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
    """Score a wardrobe item against the plan and saved memory."""
    score = 0

    # Event match remains the strongest signal.
    if item.get("event") == plan.event:
        score += 5

    # Current request style still matters.
    if item.get("style") == plan.style:
        score += 2

    # Saved style preferences from memory.
    if item.get("style") in preferred_styles:
        score += 2

    # Colors mentioned in the current request take priority.
    preferred_colors = plan.colors if plan.colors else favorite_colors
    if item.get("color") in preferred_colors:
        score += 2

    # Saved favorite colors from memory.
    if item.get("color") in favorite_colors:
        score += 2

    return score


def _get_category_items(wardrobe: dict, outfit_category: str) -> tuple[list[dict], bool]:
    """
    Return the item pool for one outfit slot.

    Uses wardrobe items when that category is populated; otherwise falls back
    to DEFAULT_ITEMS for that category only.
    """
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
    """Pick the highest-scoring item for a single outfit category."""
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


def generate_outfit(plan, memory: dict) -> dict:
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
            items_pool,
            category,
            plan,
            favorite_colors,
            preferred_styles,
            disliked_items,
            use_default_rules,
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
        if used_wardrobe and used_defaults:
            outfit["reason"] = (
                "No matching items were found for this request. "
                "Try adjusting your request or adding more clothes to your wardrobe."
            )
        elif used_wardrobe:
            outfit["reason"] = (
                "No matching items were found in your wardrobe. "
                "Try adding more clothes or adjusting your request."
            )
        else:
            outfit["reason"] = (
                "No matching default items were found for this event. "
                "Try adjusting your request or add clothes to your wardrobe."
            )

    return outfit


class StylistAgent(BaseAgent):
    name = "stylist_agent"
    description = "Builds outfit recommendations from wardrobe items and style memory."

    _HANDLED_INTENTS = {"outfit_request", "outfit_request_with_memory_update"}

    def can_handle(self, plan: dict) -> bool:
        intent = plan.get("intent", "outfit_request")
        if intent in self._HANDLED_INTENTS:
            return True
        # Default fallback for unrecognized intents.
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
        context: dict | None = None,
    ) -> AgentResponse:
        memory = (context or {}).get("memory")
        if memory is None:
            memory = load_memory()

        plan_obj = plan_from_dict(plan) if isinstance(plan, dict) else plan
        outfit = generate_outfit(plan_obj, memory)

        return AgentResponse(
            success=True,
            agent_name=self.name,
            message="",
            data={"outfit": outfit},
        )
