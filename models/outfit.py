"""Pydantic schema models for outfit validation (SCOUT-002 gate, schema stage)."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field, ValidationError, field_validator


class OutfitItemModel(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    source: Literal["wardrobe", "suggested"] | None = None
    owned: bool | None = None
    color: str | None = None
    style: str | None = None
    event: str | None = None

    @field_validator("name", "category", mode="before")
    @classmethod
    def _strip_required_strings(cls, value: Any) -> Any:
        if isinstance(value, str):
            return value.strip()
        return value


class OutfitModel(BaseModel):
    items: list[OutfitItemModel] = Field(default_factory=list)
    event: str | None = None
    style: str | None = None
    city: str | None = None
    date: str | None = None
    reason: str | None = None
    missing_slots: list[str] = Field(default_factory=list)


def outfit_schema_errors(outfit: dict) -> list[str]:
    """Return human-readable schema errors; empty list means schema stage passed."""
    if not isinstance(outfit, dict):
        return ["outfit must be a mapping"]

    try:
        OutfitModel.model_validate(outfit)
    except ValidationError as exc:
        return [f"outfit schema invalid: {exc.errors()[0]['msg']}"]

    errors: list[str] = []
    for index, item in enumerate(outfit.get("items") or []):
        if not isinstance(item, dict):
            errors.append(f"outfit.items[{index}] must be a mapping")
            continue
        if not str(item.get("name") or "").strip():
            errors.append(f"outfit.items[{index}] missing name")
        if not str(item.get("category") or "").strip():
            errors.append(f"outfit.items[{index}] missing category")

    return errors
