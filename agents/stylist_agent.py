import json
from pathlib import Path


WARDROBE_PATH = Path("data/wardrobe.json")


def load_wardrobe() -> list[dict]:
    """
    Loads wardrobe items from JSON file.
    """

    if not WARDROBE_PATH.exists():
        return []

    with open(WARDROBE_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def generate_outfit(plan, memory: dict) -> dict:
    """
    Generates an outfit recommendation using the plan, user memory,
    and wardrobe data.
    """

    wardrobe = load_wardrobe()
    profile = memory.get("user_profile", {})

    favorite_colors = profile.get("favorite_colors", [])
    disliked_items = profile.get("disliked_items", [])

    selected_items = []

    for item in wardrobe:
        matches_event = item.get("event") == plan.event
        matches_style = item.get("style") == plan.style
        matches_color = item.get("color") in plan.colors or item.get(
            "color") in favorite_colors

        if matches_event or matches_style or matches_color:
            if item.get("name") not in disliked_items:
                selected_items.append(item)

    outfit = {
        "event": plan.event,
        "style": plan.style,
        "city": plan.city,
        "date": plan.date,
        "items": selected_items[:4],
        "reason": "This outfit was selected based on your request, saved preferences, and available wardrobe items."
    }

    if not selected_items:
        outfit["reason"] = "No perfect wardrobe match was found, so try adding more items to your wardrobe."

    return outfit
