"""Convert retrieved knowledge chunks into concise stylist-facing notes."""

from __future__ import annotations

from services.rag_service import RetrievedChunk
from models.styling_mode import StylingMode

# Plain sentences keyed by constraint ids from OutfitValidator.collect_satisfied_constraints.
CONSTRAINT_SENTENCES: dict[str, str] = {
    "schema_valid": "Each item has a name, category, color, and style.",
    "no_duplicate_slots": "No board slot appears more than once.",
    "required_slots_documented": "Every unfilled board slot is explicitly listed.",
    "my_wardrobe_provenance": "Every piece is from your wardrobe and marked as owned.",
    "wardrobe_plus_ai_provenance": "Each piece is marked as wardrobe-owned or suggested.",
    "wardrobe_plus_ai_suggested_cap": (
        "Suggested-piece count is within the Wardrobe + AI mode limit."
    ),
    "ai_inspiration_provenance": (
        "Ownership was resolved against your wardrobe for each piece."
    ),
}

CONSTRAINT_ORDER = [
    "schema_valid",
    "no_duplicate_slots",
    "required_slots_documented",
    "my_wardrobe_provenance",
    "wardrobe_plus_ai_provenance",
    "wardrobe_plus_ai_suggested_cap",
    "ai_inspiration_provenance",
]


def build_stylist_notes(chunks: list[RetrievedChunk], max_notes: int = 2) -> str:
    """Turn top retrieved chunks into short, readable stylist notes."""
    if not chunks:
        return ""

    notes: list[str] = []
    for chunk in chunks[:max_notes]:
        first_sentence = chunk.content.split(".")[0].strip()
        if not first_sentence:
            continue
        notes.append(f"{chunk.heading}: {first_sentence}.")

    return " ".join(notes)


def build_knowledge_query(user_input: str, plan) -> str:
    """Build a retrieval query from the user request and parsed plan."""
    parts = [user_input.strip(), plan.style, plan.event]

    if plan.city:
        parts.append(plan.city)
    if plan.date:
        parts.append(plan.date)
    if plan.colors:
        parts.extend(plan.colors)

    return " ".join(part for part in parts if part)


def build_outfit_explanation(
    *,
    satisfied_constraints: list[str],
    validation_outcome: str,
    mode: StylingMode,
    outfit: dict,
    reason: str | None = None,
) -> list[str]:
    """Turn gate satisfied-constraint ids into plain, check-backed sentences."""
    from services.outfit_validator import FALLBACK_REASON

    lines: list[str] = []
    cleaned_reason = (reason or "").strip()

    if validation_outcome == "fallback":
        lines.append(cleaned_reason or FALLBACK_REASON)
    elif validation_outcome == "repaired" and cleaned_reason:
        lines.append(cleaned_reason)

    for key in CONSTRAINT_ORDER:
        if key in satisfied_constraints and key in CONSTRAINT_SENTENCES:
            lines.append(CONSTRAINT_SENTENCES[key])

    missing_slots = [str(label) for label in (outfit.get("missing_slots") or []) if label]
    if missing_slots:
        joined = ", ".join(missing_slots)
        lines.append(f"No wardrobe item was available for: {joined}.")

    if validation_outcome == "validated" and not lines and not missing_slots:
        lines.append("Outfit passed the validation checks for the selected mode.")

    return lines
