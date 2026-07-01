import json
from pathlib import Path


MEMORY_PATH = Path("memory/memory_store.json")


def load_memory() -> dict:
    """
    Loads user memory from a JSON file.
    """

    if not MEMORY_PATH.exists():
        return {
            "user_profile": {
                "favorite_colors": [],
                "disliked_items": [],
                "preferred_styles": [],
                "preferred_fit": ""
            }
        }

    with open(MEMORY_PATH, "r", encoding="utf-8") as file:
        return json.load(file)


def save_memory(memory: dict) -> None:
    """
    Saves user memory to a JSON file.
    """

    with open(MEMORY_PATH, "w", encoding="utf-8") as file:
        json.dump(memory, file, indent=4, ensure_ascii=False)


def update_memory_from_plan(plan) -> dict:
    """
    Updates memory using information found in the user's plan.
    For MVP, we only store colors and style preferences.
    """

    memory = load_memory()
    profile = memory["user_profile"]

    for color in plan.colors:
        if color not in profile["favorite_colors"]:
            profile["favorite_colors"].append(color)

    if plan.style and plan.style not in profile["preferred_styles"]:
        profile["preferred_styles"].append(plan.style)

    save_memory(memory)

    return memory
