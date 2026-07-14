"""Abstract wardrobe persistence interface."""

from abc import ABC, abstractmethod


class WardrobeRepository(ABC):
    """Persistence contract for wardrobe data (JSON today, SQLite later)."""

    @abstractmethod
    def get_all(self) -> list[dict]:
        """Return every wardrobe item as a flat list."""

    @abstractmethod
    def get_by_category(self) -> dict[str, list[dict]]:
        """Return wardrobe items grouped by category key."""

    @abstractmethod
    def find_by_category(self, category: str) -> list[dict]:
        """Return items stored under a wardrobe category."""

    @abstractmethod
    def find_by_color(self, color: str) -> list[dict]:
        """Return items matching a color name."""

    @abstractmethod
    def add_item(self, category: str, item: dict) -> bool:
        """Add an item to a category. Returns False for duplicates."""
