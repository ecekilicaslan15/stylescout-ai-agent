def detect_date(text: str) -> str | None:
    """Detect when the outfit is needed (today or tomorrow)."""
    if "tomorrow" in text:
        return "tomorrow"
    if "today" in text:
        return "today"

    return None
