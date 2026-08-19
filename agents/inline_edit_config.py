"""Configurable keyword rules for InlineEditAgent (no LLM)."""

from __future__ import annotations

from dataclasses import dataclass

from agents.detectors.color_detector import detect_colors

# Maps a target wardrobe style to trigger phrases (lowercase substring match).
STYLE_KEYWORD_GROUPS: dict[str, tuple[str, ...]] = {
    "elegant": (
        "elegant",
        "formal",
        "dressy",
        "fancy",
        "smart",
        "resmi",
        "chic",
        "polished",
    ),
    "casual": (
        "casual",
        "comfortable",
        "comfort",
        "comfy",
        "relaxed",
        "rahat",
        "informal",
        "günlük",
        "everyday",
        "laid-back",
        "cozy",
    ),
}

# Formality hints that override or reinforce style detection.
FORMALITY_KEYWORDS: dict[str, str] = {
    "formal": "elegant",
    "informal": "casual",
    "business": "elegant",
    "office": "elegant",
    "weekend": "casual",
}

# Weather hints adjust wardrobe scoring (not a standalone style).
WEATHER_KEYWORDS: dict[str, tuple[str, ...]] = {
    "warm": ("warm", "hot", "summer", "sıcak", "yaz", "heat"),
    "cold": ("cold", "cool", "winter", "soğuk", "kış", "chilly", "freezing"),
}


@dataclass(frozen=True)
class InlineEditCriteria:
    """Parsed instruction criteria for wardrobe replacement."""

    target_style: str
    instruction_colors: tuple[str, ...]
    weather_hint: str | None = None
    formality_hint: str | None = None
    matched_category: str | None = None


def _contains_keyword(text: str, keyword: str) -> bool:
    return keyword in text


def parse_inline_edit_instruction(instruction: str) -> InlineEditCriteria | None:
    """Return parsed criteria when at least one known keyword category matches."""
    text = instruction.strip().lower()
    if not text:
        return None

    target_style: str | None = None
    matched_category: str | None = None
    formality_hint: str | None = None
    weather_hint: str | None = None

    for hint, style in sorted(FORMALITY_KEYWORDS.items(), key=lambda item: len(item[0]), reverse=True):
        if _contains_keyword(text, hint):
            target_style = style
            formality_hint = hint
            matched_category = "formality"
            break

    if target_style is None:
        for style, keywords in STYLE_KEYWORD_GROUPS.items():
            matched = [
                keyword
                for keyword in sorted(keywords, key=len, reverse=True)
                if _contains_keyword(text, keyword)
            ]
            if matched:
                target_style = style
                if any(k in text for k in ("comfort", "comfortable", "comfy", "relaxed", "rahat", "cozy")):
                    matched_category = "comfort"
                else:
                    matched_category = "style"
                break

    for weather, keywords in WEATHER_KEYWORDS.items():
        if any(_contains_keyword(text, keyword) for keyword in keywords):
            weather_hint = weather
            if matched_category is None:
                matched_category = "weather"
            break

    instruction_colors = tuple(detect_colors(text))
    if instruction_colors and target_style is None and weather_hint is None:
        # Color-only preference still counts as a recognized edit intent.
        target_style = "casual"
        matched_category = "color"

    if target_style is None and weather_hint is not None:
        # Weather-only: default to casual for warm, elegant layering tone for cold.
        target_style = "casual" if weather_hint == "warm" else "elegant"
        matched_category = "weather"

    if target_style is None:
        return None

    return InlineEditCriteria(
        target_style=target_style,
        instruction_colors=instruction_colors,
        weather_hint=weather_hint,
        formality_hint=formality_hint,
        matched_category=matched_category,
    )
