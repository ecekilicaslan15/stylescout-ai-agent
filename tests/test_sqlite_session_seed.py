"""SQLite session user seeding (sess_* wardrobe clone on first access)."""

from api.session import generate_session_id
from wardrobe.seed import load_sample_template
from wardrobe.sqlite_wardrobe_repository import SqliteWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService


class TestSqliteSessionSeed:
    def test_new_sess_user_gets_template_wardrobe_on_first_service_access(self, tmp_path):
        db_path = tmp_path / "session_seed.db"
        session_id = generate_session_id()
        template_len = len(load_sample_template())
        assert template_len > 0

        service = WardrobeService(
            repository=SqliteWardrobeRepository(db_path=db_path, user_id=session_id),
        )
        items = service.list_items()

        assert len(items) == template_len
        assert {item["name"] for item in items} == {row["name"] for row in load_sample_template()}
