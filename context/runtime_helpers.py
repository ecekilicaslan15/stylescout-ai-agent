"""Shared helpers for resolving runtime data from AgentContext."""

from memory.memory_manager import load_memory
from models.agent_context import AgentContext
from models.plan import Plan, plan_from_dict
from wardrobe.constants import CATEGORIES
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.wardrobe_manager import load_wardrobe
from wardrobe.wardrobe_repository import WardrobeRepository


def resolve_wardrobe(
    wardrobe: list | dict | None,
    repository: WardrobeRepository | None = None,
) -> dict:
    """Convert context wardrobe to a categorized dict; use repository as fallback."""
    if wardrobe is None:
        if repository is not None:
            return repository.get_by_category()
        return load_wardrobe()
    if isinstance(wardrobe, dict):
        return wardrobe
    if isinstance(wardrobe, list):
        grouped = {category: [] for category in CATEGORIES}
        for item in wardrobe:
            category = item.get("category")
            if category in grouped:
                grouped[category].append(item)
        return grouped
    if repository is not None:
        return repository.get_by_category()
    return load_wardrobe()


def resolve_memory(memory: dict | None) -> dict:
    """Return context memory when present; otherwise load from disk."""
    if memory:
        return memory
    return load_memory()


def resolve_plan(plan, context: AgentContext | dict | None) -> Plan:
    """Prefer plan from AgentContext; fall back to the plan argument."""
    if isinstance(context, AgentContext) and context.plan is not None:
        plan_obj = context.plan
    else:
        plan_obj = plan

    if isinstance(plan_obj, Plan):
        return plan_obj
    return plan_from_dict(plan_obj)


def default_wardrobe_repository() -> JsonWardrobeRepository:
    """Return the shared JSON repository used by backward-compatible helpers."""
    from wardrobe.wardrobe_manager import _get_default_repository

    return _get_default_repository()
