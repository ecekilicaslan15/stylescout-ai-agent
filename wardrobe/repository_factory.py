"""Factory for creating wardrobe repository implementations."""

from __future__ import annotations

import os

from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.sqlite_wardrobe_repository import SqliteWardrobeRepository
from wardrobe.wardrobe_repository import WardrobeRepository

WARDROBE_BACKEND_ENV = "WARDROBE_BACKEND"
SUPPORTED_BACKENDS = frozenset({"json", "sqlite"})


def create_wardrobe_repository(
    backend: str | None = None,
    user_id: str = "default",
) -> WardrobeRepository:
    """Create a wardrobe repository from explicit config or environment."""
    selected_backend = backend or os.getenv(WARDROBE_BACKEND_ENV) or "json"
    selected_backend = selected_backend.strip().lower()

    if selected_backend not in SUPPORTED_BACKENDS:
        supported = ", ".join(sorted(SUPPORTED_BACKENDS))
        raise ValueError(
            f"Unsupported wardrobe backend: {selected_backend!r}. "
            f"Supported backends: {supported}"
        )

    if selected_backend == "json":
        return JsonWardrobeRepository()

    return SqliteWardrobeRepository(user_id=user_id)
