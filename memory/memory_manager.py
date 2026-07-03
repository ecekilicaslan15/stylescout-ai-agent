"""
Backward-compatible wrapper around memory_store for the orchestrator.
"""

from memory.memory_store import add_to_memory, load_memory, save_memory


def update_memory_from_plan(plan) -> dict:
    """Update memory using fields extracted by the planner."""
    for color in plan.colors:
        add_to_memory("favorite_colors", color)

    if plan.style:
        add_to_memory("preferred_styles", plan.style)

    for item in plan.disliked_items:
        add_to_memory("disliked_items", item)

    return load_memory()
