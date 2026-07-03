def detect_style(text: str) -> str:
    """Detect the preferred style from user input."""
    if "elegant" in text or "classy" in text:
        return "elegant"
    if "minimal" in text:
        return "minimal"
    if "comfortable" in text or "comfy" in text:
        return "comfortable"
    if "casual" in text:
        return "casual"
    if "sporty" in text:
        return "sporty"

    return "casual"
