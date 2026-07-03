def detect_city(text: str) -> str | None:
    """Detect the city mentioned in user input."""
    if "istanbul" in text:
        return "Istanbul"
    if "izmir" in text:
        return "Izmir"
    if "ankara" in text:
        return "Ankara"

    return None
