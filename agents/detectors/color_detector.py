COLORS = ["black", "white", "beige", "navy", "blue", "gray", "pink", "red"]


def detect_colors(text: str) -> list[str]:
    """Detect color preferences mentioned in user input."""
    found_colors = []

    for color in COLORS:
        if color in text:
            found_colors.append(color)

    return found_colors
