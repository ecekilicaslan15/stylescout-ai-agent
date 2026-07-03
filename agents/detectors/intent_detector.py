OUTFIT_PHRASES = [
    "outfit",
    "wear",
    "dress",
    "look",
    "combination",
    "need something",
    "need a",
    "need an",
]

MEMORY_PHRASES = [
    "remember",
    "keep in mind",
    "save this",
    "note that",
    "i like",
    "i love",
    "my favorite",
    "i prefer",
    "i don't like",
    "i dont like",
    "i dislike",
    "i hate",
    "dislike",
]


def detect_intent(text: str) -> str:
    """Detect whether the user wants an outfit, a memory update, or both."""
    wants_outfit = any(phrase in text for phrase in OUTFIT_PHRASES)
    wants_memory = any(phrase in text for phrase in MEMORY_PHRASES)

    if wants_outfit and wants_memory:
        return "outfit_request_with_memory_update"
    if wants_memory:
        return "memory_update"
    if wants_outfit:
        return "outfit_request"

    return "outfit_request"
