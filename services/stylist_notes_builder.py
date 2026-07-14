"""Convert retrieved knowledge chunks into concise stylist-facing notes."""

from services.rag_service import RetrievedChunk


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
