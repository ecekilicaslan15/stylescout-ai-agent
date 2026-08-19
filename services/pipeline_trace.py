"""Single source for pipeline trace labels shown in the UI."""

from agents.planner import USE_LLM

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


def get_pipeline_trace_labels() -> dict[str, str]:
    """Return UI trace labels for the active execution path."""
    labels = _TRACE_LABELS_LLM if USE_LLM else _TRACE_LABELS_RULE
    return {**labels, "use_llm": USE_LLM}
