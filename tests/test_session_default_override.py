"""Tests for ALLOW_DEFAULT_OVERRIDE gating on the legacy default session cookie."""

import os
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app
from api.session import (
    ALLOW_DEFAULT_OVERRIDE_ENV,
    LEGACY_USER_ID,
    allow_default_override,
    is_valid_session_id,
)

MARKER_ITEM = {
    "name": "MARKER_DEFAULT_ONLY",
    "color": "purple",
    "style": "casual",
    "event": "everyday",
}


@pytest.fixture
def wardrobe_path(monkeypatch) -> Path:
    path = Path(os.environ["WARDROBE_JSON_PATH"])
    return path


@pytest.fixture
def seed_default_only_marker(wardrobe_path):
    from wardrobe.json_wardrobe_repository import JsonWardrobeRepository

    repository = JsonWardrobeRepository(wardrobe_path, user_id=LEGACY_USER_ID)
    repository.add_item("tops", MARKER_ITEM)
    return repository


class TestAllowDefaultOverrideEnv:
    def test_unset_or_false_rejects_default_literal(self, monkeypatch):
        monkeypatch.delenv(ALLOW_DEFAULT_OVERRIDE_ENV, raising=False)
        assert allow_default_override() is False
        assert is_valid_session_id(LEGACY_USER_ID) is False

        monkeypatch.setenv(ALLOW_DEFAULT_OVERRIDE_ENV, "false")
        assert allow_default_override() is False
        assert is_valid_session_id(LEGACY_USER_ID) is False

    def test_true_accepts_default_literal(self, monkeypatch):
        monkeypatch.setenv(ALLOW_DEFAULT_OVERRIDE_ENV, "true")
        assert allow_default_override() is True
        assert is_valid_session_id(LEGACY_USER_ID) is True


class TestDefaultSessionOverrideGate:
    def test_default_cookie_rejected_when_override_disabled(
        self,
        monkeypatch,
        seed_default_only_marker,
    ):
        monkeypatch.setenv(ALLOW_DEFAULT_OVERRIDE_ENV, "false")

        client = TestClient(app)
        client.cookies.set("stylescout_session", LEGACY_USER_ID)
        response = client.get("/api/wardrobe/items")

        assert response.status_code == 200
        issued = response.cookies.get("stylescout_session")
        assert issued is not None
        assert issued.startswith("sess_")
        names = {item["name"] for item in response.json()}
        assert MARKER_ITEM["name"] not in names

    def test_default_cookie_grants_default_user_when_override_enabled(
        self,
        monkeypatch,
        seed_default_only_marker,
    ):
        monkeypatch.setenv(ALLOW_DEFAULT_OVERRIDE_ENV, "true")

        client = TestClient(app)
        client.cookies.set("stylescout_session", LEGACY_USER_ID)
        response = client.get("/api/wardrobe/items")

        assert response.status_code == 200
        assert response.cookies.get("stylescout_session") is None
        names = {item["name"] for item in response.json()}
        assert MARKER_ITEM["name"] in names
