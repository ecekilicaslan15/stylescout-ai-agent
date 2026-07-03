from wardrobe.wardrobe_manager import get_all_wardrobe_items, load_wardrobe


DISLIKE_PHRASES = [
    "i hate",
    "i don't like",
    "i dont like",
    "i dislike",
    "don't like",
    "dislike",
]

# Simple clothing keywords for rule-based dislike detection
CLOTHING_KEYWORDS = [
    "loafers",
    "heels",
    "sneakers",
    "blazer",
    "shirt",
    "trousers",
    "jeans",
    "boots",
    "sandals",
    "dress",
    "skirt",
    "jacket",
    "coat",
    "sweater",
    "hoodie",
    "shorts",
]


def detect_disliked_items(text: str) -> list[str]:
    """
    Finds clothing the user dislikes and maps keywords to wardrobe item names.
    """
    has_dislike_phrase = any(phrase in text for phrase in DISLIKE_PHRASES)
    if not has_dislike_phrase:
        return []

    matched_keywords = [
        keyword for keyword in CLOTHING_KEYWORDS if keyword in text
    ]
    if not matched_keywords:
        return []

    wardrobe_items = get_all_wardrobe_items(load_wardrobe())
    disliked_names = []

    for keyword in matched_keywords:
        matched_in_wardrobe = False

        for item in wardrobe_items:
            item_name = item.get("name", "")
            if keyword in item_name.lower() and item_name not in disliked_names:
                disliked_names.append(item_name)
                matched_in_wardrobe = True

        # Save the keyword too if it is not in the wardrobe yet (e.g. "heels")
        if not matched_in_wardrobe:
            fallback_name = keyword.title()
            if fallback_name not in disliked_names:
                disliked_names.append(fallback_name)

    return disliked_names
