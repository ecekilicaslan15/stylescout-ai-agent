"""Canonical wardrobe category vocabulary."""

# Storage keys — lowercase plural, used in JSON/SQLite and repositories.
CATEGORIES = ["tops", "bottoms", "shoes", "outerwear", "accessories"]

DEFAULT_WARDROBE = {category: [] for category in CATEGORIES}

# Accepted aliases mapped to storage keys (singular/plural, outfit slot names).
CATEGORY_ALIASES = {
    "top": "tops",
    "tops": "tops",
    "bottom": "bottoms",
    "bottoms": "bottoms",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessory": "accessories",
    "accessories": "accessories",
}

# Display labels returned by the API and used for wardrobe grid filters.
DISPLAY_LABELS = {
    "tops": "Tops",
    "bottoms": "Bottoms",
    "shoes": "Shoes",
    "outerwear": "Outerwear",
    "accessories": "Accessories",
}

# Ordered filter tabs for the wardrobe UI ("All" plus each display label).
FILTER_LABELS = ["All"] + [DISPLAY_LABELS[category] for category in CATEGORIES]
