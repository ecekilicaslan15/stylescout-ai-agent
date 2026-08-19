"""Shopping preference profile (partial SCOUT-008 scope)."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field, field_validator


class PreferenceProfile(BaseModel):
    """User-declared shopping filters; all fields optional and skippable."""

    model_config = ConfigDict(extra="forbid")

    max_price: float | None = Field(default=None, gt=0)
    size: str | None = None

    @field_validator("size")
    @classmethod
    def validate_size(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("size cannot be empty.")
        return cleaned
