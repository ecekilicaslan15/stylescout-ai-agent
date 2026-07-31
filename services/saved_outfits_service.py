"""Application-facing saved outfit history."""

from wardrobe.repository_factory import create_wardrobe_repository
from wardrobe.saved_outfit_repository import SavedOutfitRepository, create_saved_outfit_repository


class SavedOutfitsService:
    def __init__(self, repository: SavedOutfitRepository | None = None) -> None:
        self._repository = repository or create_saved_outfit_repository()

    def save_outfit(self, user_id: str, outfit: dict) -> dict:
        return self._repository.save(user_id, outfit)

    def list_outfits(self, user_id: str) -> list[dict]:
        return self._repository.list_for_user(user_id)


def create_user_wardrobe_repository(user_id: str):
    """Build a wardrobe repository scoped to one session user."""
    return create_wardrobe_repository(user_id=user_id)
