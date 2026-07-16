"""Application-facing wardrobe operations backed by a repository."""

from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.wardrobe_repository import WardrobeRepository


class WardrobeService:
    """Thin service wrapper over WardrobeRepository for product-level access."""

    def __init__(self, repository: WardrobeRepository | None = None) -> None:
        self._repository = repository or create_wardrobe_repository()

    def list_items(self) -> list[dict]:
        return self._repository.get_all()

    def get_items_by_category(self) -> dict[str, list[dict]]:
        return self._repository.get_by_category()

    def add_item(self, category: str, item: dict) -> bool:
        return self._repository.add_item(category, item)
