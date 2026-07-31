"""Application-facing wardrobe operations backed by a repository."""

from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.seed import seed_user_wardrobe_if_empty
from wardrobe.wardrobe_repository import WardrobeRepository


class WardrobeService:
    """Thin service wrapper over WardrobeRepository for product-level access."""

    def __init__(
        self,
        repository: WardrobeRepository | None = None,
        *,
        user_id: str = "default",
        auto_seed: bool = True,
    ) -> None:
        self._repository = repository or create_wardrobe_repository(user_id=user_id)
        self._user_id = getattr(self._repository, "user_id", user_id)
        if auto_seed:
            seed_user_wardrobe_if_empty(self._repository)

    @property
    def user_id(self) -> str:
        return self._user_id

    def list_items(self) -> list[dict]:
        return self._repository.get_all()

    def get_items_by_category(self) -> dict[str, list[dict]]:
        return self._repository.get_by_category()

    def add_item(self, category: str, item: dict, *, allow_duplicate: bool = False) -> bool:
        return self._repository.add_item(category, item, allow_duplicate=allow_duplicate)

    def get_item_by_id(self, item_id: str) -> dict | None:
        return self._repository.get_item_by_id(item_id)

    def update_item(self, item_id: str, item: dict, *, allow_duplicate: bool = False) -> bool:
        return self._repository.update_item(item_id, item, allow_duplicate=allow_duplicate)

    def delete_item(self, item_id: str) -> bool:
        return self._repository.delete_item(item_id)
