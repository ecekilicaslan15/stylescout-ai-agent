"""Tests for anonymous session persistence and saved outfits."""

import json

import pytest
from fastapi.testclient import TestClient
from pathlib import Path

from api.main import app, get_saved_outfits_service, get_wardrobe_service
from api.session import LEGACY_USER_ID, generate_session_id, get_session_user_id
from services.saved_outfits_service import SavedOutfitsService
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.saved_outfit_repository import JsonSavedOutfitRepository
from wardrobe.seed import load_sample_template, seed_user_wardrobe_if_empty
from wardrobe.wardrobe_service import WardrobeService

SAMPLE_OUTFIT = {
    "event": "daily",
    "style": "casual",
    "reason": "Saved for later.",
    "items": [
        {
            "name": "White Elegant Shirt",
            "category": "Tops",
            "color": "white",
            "style": "elegant",
        }
    ],
}


@pytest.fixture
def session_client_factory(tmp_path):
    """Build isolated TestClient instances with distinct session cookies."""

    def _make_client(session_id: str) -> tuple[TestClient, JsonWardrobeRepository, SavedOutfitsService]:
        wardrobe_path = tmp_path / f"wardrobe-{session_id}.json"
        saved_path = tmp_path / f"saved-{session_id}.json"
        wardrobe_path.write_text(
            json.dumps(
                {
                    "tops": [],
                    "bottoms": [],
                    "shoes": [],
                    "outerwear": [],
                    "accessories": [],
                }
            ),
            encoding="utf-8",
        )

        repository = JsonWardrobeRepository(wardrobe_path, user_id=session_id)
        wardrobe_service = WardrobeService(repository=repository, auto_seed=True)
        saved_service = SavedOutfitsService(repository=JsonSavedOutfitRepository(saved_path))

        client = TestClient(app)
        client.cookies.set("stylescout_session", session_id)
        app.dependency_overrides[get_session_user_id] = lambda session_id=session_id: session_id
        app.dependency_overrides[get_wardrobe_service] = lambda wardrobe_service=wardrobe_service: wardrobe_service
        app.dependency_overrides[get_saved_outfits_service] = lambda saved_service=saved_service: saved_service
        return client, repository, saved_service

    yield _make_client
    app.dependency_overrides.clear()


class TestSavedOutfits:
    def test_save_outfit_read_back_in_history(self, session_client_factory):
        session_id = generate_session_id()
        client, _repository, _saved = session_client_factory(session_id)

        save_response = client.post("/api/outfits/save", json={"outfit": SAMPLE_OUTFIT})
        assert save_response.status_code == 201
        saved = save_response.json()
        assert saved["item_count"] == 1
        assert saved["user_id"] == session_id

        history_response = client.get("/api/outfits/history")
        assert history_response.status_code == 200
        history = history_response.json()
        assert len(history) == 1
        assert history[0]["id"] == saved["id"]
        assert history[0]["outfit"]["reason"] == "Saved for later."


class TestSeedIdempotency:
    def test_repeated_seed_calls_do_not_duplicate_items(self, tmp_path):
        wardrobe_path = tmp_path / "wardrobe.json"
        wardrobe_path.write_text(
            json.dumps(
                {
                    "tops": [],
                    "bottoms": [],
                    "shoes": [],
                    "outerwear": [],
                    "accessories": [],
                }
            ),
            encoding="utf-8",
        )
        session_id = generate_session_id()
        repository = JsonWardrobeRepository(wardrobe_path, user_id=session_id)

        counts = []
        for _ in range(3):
            seed_user_wardrobe_if_empty(repository)
            counts.append(len(repository.get_all()))

        template_count = len(load_sample_template())
        assert template_count > 0
        assert counts == [template_count, template_count, template_count]

    def test_seed_idempotency_via_api_requests(self, session_client_factory):
        session_id = generate_session_id()
        client, repository, _saved = session_client_factory(session_id)

        counts = []
        for _ in range(3):
            response = client.get("/api/wardrobe/items")
            assert response.status_code == 200
            counts.append(len(response.json()))

        assert counts[0] > 0
        assert counts == [counts[0], counts[0], counts[0]]
        assert len(repository.get_all()) == counts[0]


class TestSessionIsolation:
    def test_two_sessions_do_not_share_wardrobe_or_saved_outfits(self, tmp_path):
        session_a = generate_session_id()
        session_b = generate_session_id()

        def build_repo(session_id: str) -> JsonWardrobeRepository:
            path = tmp_path / f"wardrobe-{session_id}.json"
            path.write_text(
                json.dumps(
                    {
                        "tops": [],
                        "bottoms": [],
                        "shoes": [],
                        "outerwear": [],
                        "accessories": [],
                    }
                ),
                encoding="utf-8",
            )
            repository = JsonWardrobeRepository(path, user_id=session_id)
            seed_user_wardrobe_if_empty(repository)
            return repository

        repo_a = build_repo(session_a)
        repo_b = build_repo(session_b)

        repo_a.add_item(
            "tops",
            {
                "name": "Session A Shirt",
                "color": "white",
                "style": "casual",
                "event": "everyday",
            },
        )

        names_a = {item["name"] for item in repo_a.get_all()}
        names_b = {item["name"] for item in repo_b.get_all()}
        assert "Session A Shirt" in names_a
        assert "Session A Shirt" not in names_b

        saved_path_a = tmp_path / "saved-a.json"
        saved_path_b = tmp_path / "saved-b.json"
        saved_a = JsonSavedOutfitRepository(saved_path_a)
        saved_b = JsonSavedOutfitRepository(saved_path_b)
        saved_a.save(session_a, {**SAMPLE_OUTFIT, "reason": "Session A only"})

        assert len(saved_a.list_for_user(session_a)) == 1
        assert saved_b.list_for_user(session_b) == []
        assert saved_b.list_for_user(session_a) == []

        ids_a = {item["id"] for item in repo_a.get_all()}
        ids_b = {item["id"] for item in repo_b.get_all()}
        assert ids_a.isdisjoint(ids_b)


class TestLegacyDefaultUser:
    def test_default_user_data_unchanged_by_session_tests(self):
        production_path = Path(__file__).resolve().parent.parent / "wardrobe" / "wardrobe.json"
        before = JsonWardrobeRepository(production_path, user_id=LEGACY_USER_ID).get_all()
        before_ids = {item["id"] for item in before}

        assert before_ids

        after = JsonWardrobeRepository(production_path, user_id=LEGACY_USER_ID).get_all()
        after_ids = {item["id"] for item in after}

        assert before_ids == after_ids

    def test_cookieless_request_gets_session_and_does_not_crash(self):
        client = TestClient(app)
        response = client.get("/api/wardrobe/items")

        assert response.status_code == 200
        assert "stylescout_session" in response.cookies
        assert response.cookies["stylescout_session"].startswith("sess_")
