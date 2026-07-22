"""Canonical styling mode values for outfit generation."""

from enum import Enum


class StylingMode(str, Enum):
    MY_WARDROBE = "my_wardrobe"
    WARDROBE_PLUS_AI = "wardrobe_plus_ai"
    AI_INSPIRATION = "ai_inspiration"


DEFAULT_STYLING_MODE = StylingMode.MY_WARDROBE
