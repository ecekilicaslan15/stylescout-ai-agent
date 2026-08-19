"""Tests for shopping preference profile (SCOUT-008/009 partial scope)."""

import os
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient

from api.main import app, get_session_user_id
from api.session import LEGACY_USER_ID
from models.search_spec import SearchSpec, build_search_spec
from services.preference_service import load_preferences, save_preferences
from services.shopping_service import ShoppingService, build_search_query


@pytest.fixture
def preferences_path(tmp_path, monkeypatch):
    path = tmp_path / "preferences.json"
    monkeypatch.setenv("PREFERENCES_JSON_PATH", str(path))
    return path


@pytest.fixture
def preferences_client(preferences_path):
    client = TestClient(app)
    client.cookies.set("stylescout_session", LEGACY_USER_ID)
    app.dependency_overrides[get_session_user_id] = lambda: LEGACY_USER_ID
    yield client
    app.dependency_overrides.pop(get_session_user_id, None)


SAMPLE_ITEM = {
    "name": "Black Heels",
    "category": "Shoes",
    "color": "black",
    "style": "elegant",
}


class TestPreferencePersistence:
    def test_preferences_persist_per_user_id(self, preferences_path):
        save_preferences("sess_user_a", {"max_price": 45.0, "size": "M"})
        save_preferences("sess_user_b", {"size": "L"})

        assert load_preferences("sess_user_a") == {"max_price": 45.0, "size": "M"}
        assert load_preferences("sess_user_b") == {"size": "L"}

        reloaded_path = preferences_path.read_text(encoding="utf-8")
        assert "sess_user_a" in reloaded_path

        fresh_load = load_preferences("sess_user_a")
        assert fresh_load == {"max_price": 45.0, "size": "M"}


class TestSearchSpecPreferences:
    def test_build_search_spec_without_preferences_unchanged(self):
        spec = build_search_spec(SAMPLE_ITEM)
        assert spec == SearchSpec(
            name="Black Heels",
            category="shoes",
            color="black",
            style="elegant",
            max_price=None,
            size=None,
        )
        assert spec.max_price is None
        assert spec.size is None
        assert build_search_query(spec) == "black elegant shoes Black Heels"

    def test_build_search_spec_with_preferences_adds_optional_fields(self):
        spec = build_search_spec(
            SAMPLE_ITEM,
            preferences={"max_price": 50.0, "size": "M"},
        )
        assert spec.max_price == 50.0
        assert spec.size == "M"
        query = build_search_query(spec)
        assert "size M" in query
        assert "under 50" in query

    def test_deep_link_differs_with_preferences(self):
        service = ShoppingService()
        base_link = service.primary_shopping_link(SAMPLE_ITEM)
        pref_link = service.primary_shopping_link(
            SAMPLE_ITEM,
            preferences={"max_price": 40.0, "size": "38"},
        )
        assert base_link != pref_link

        base_query = parse_qs(urlparse(base_link).query)["search_text"][0]
        pref_query = parse_qs(urlparse(pref_link).query)["search_text"][0]
        assert "size 38" in pref_query
        assert "under 40" in pref_query
        assert "size 38" not in base_query
        assert "under 40" not in base_query


class TestPreferencesApi:
    def test_get_preferences_returns_empty_by_default(self, preferences_client):
        response = preferences_client.get("/api/preferences")
        assert response.status_code == 200
        assert response.json() == {}

    def test_post_preferences_persists_for_session_user(self, preferences_client, preferences_path):
        response = preferences_client.post(
            "/api/preferences",
            json={"max_price": 55.0, "size": "S"},
        )
        assert response.status_code == 200
        assert response.json() == {"max_price": 55.0, "size": "S"}

        get_response = preferences_client.get("/api/preferences")
        assert get_response.status_code == 200
        assert get_response.json() == {"max_price": 55.0, "size": "S"}

        stored = load_preferences(LEGACY_USER_ID)
        assert stored == {"max_price": 55.0, "size": "S"}

    def test_invalid_max_price_returns_422_not_500(self, preferences_client):
        response = preferences_client.post(
            "/api/preferences",
            json={"max_price": -10.0},
        )
        assert response.status_code == 422
        assert response.status_code != 500

    def test_production_preferences_guard_during_pytest(self, monkeypatch):
        monkeypatch.delenv("PREFERENCES_JSON_PATH", raising=False)
        if "PYTEST_CURRENT_TEST" not in os.environ:
            monkeypatch.setenv("PYTEST_CURRENT_TEST", "guard-check")
        with pytest.raises(RuntimeError, match="Refusing to write to production preferences.json"):
            save_preferences("default", {"size": "M"})
