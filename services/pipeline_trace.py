"""Single source for pipeline trace labels shown in the UI."""

_TRACE_LABELS_LLM = {
    "wardrobe": "WARDROBE SERVICE",
    "memory": "MEMORY SERVICE",
    "composer": "STYLIST AGENT (LLM)",
    "composer_footer": "From your stylist agent (LLM)",
    "inline_edit": "INLINE EDIT AGENT",
}

_TRACE_LABELS_RULE = {
    "wardrobe": "WARDROBE SERVICE",
    "memory": "MEMORY SERVICE",
    "composer": "RULE-BASED COMPOSER",
    "composer_footer": "From the rule-based composer",
    "inline_edit": "INLINE EDIT AGENT",
}


def labels_for_planner_path(*, used_llm: bool) -> dict:
    """Map whether LLMPlanner actually produced the Plan to UI trace copy."""
    labels = _TRACE_LABELS_LLM if used_llm else _TRACE_LABELS_RULE
    return {**labels, "use_llm": used_llm}


def get_pipeline_trace_labels() -> dict:
    """Return UI trace labels for the execution path that actually ran.

    Uses the last ``plan_user_request`` outcome when one exists (so a
    USE_LLM=true request that fell back to RuleBasedPlanner is labeled
    rule-based). Before any plan call, falls back to the USE_LLM env flag.
    """
    from agents.planner import (
        last_plan_used_llm,
        llm_plan_error_count,
        llm_rate_limited_count,
        use_llm_enabled,
    )

    recorded = last_plan_used_llm()
    used_llm = use_llm_enabled() if recorded is None else recorded
    return {
        **labels_for_planner_path(used_llm=used_llm),
        "llm_plan_error_count": llm_plan_error_count(),
        "llm_rate_limited_count": llm_rate_limited_count(),
    }
