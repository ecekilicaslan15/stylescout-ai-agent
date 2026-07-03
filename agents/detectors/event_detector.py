def detect_event(text: str) -> str:
    """Detect the occasion from user input (office, wedding, party, daily)."""
    if "office" in text or "work" in text:
        return "office"
    if "wedding" in text:
        return "wedding"
    if "party" in text:
        return "party"
    if "daily" in text or "casual" in text or "today" in text:
        return "daily"

    return "daily"
