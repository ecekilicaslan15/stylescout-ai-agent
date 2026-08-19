"""Shared fixtures for AgentContext architecture tests."""

import json
import shutil
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from api.main import app, get_saved_outfits_service, get_wardrobe_service
from api.session import get_session_user_id
from models.agent_context import AgentContext
from models.plan import Plan, plan_to_dict
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.wardrobe_service import WardrobeService

PROJECT_ROOT = Path(__file__).resolve().parent.parent
PRODUCTION_WARDROBE = PROJECT_ROOT / "wardrobe" / "wardrobe.json"


@pytest.fixture(autouse=True)
def isolate_json_storage(tmp_path, monkeypatch):
    """Route JSON persistence to per-test temp files (never production wardrobe.json)."""
    storage_dir = tmp_path / "api_json_storage"
    storage_dir.mkdir(exist_ok=True)
    wardrobe_tmp = storage_dir / "wardrobe.json"
    if PRODUCTION_WARDROBE.exists():
        shutil.copy(PRODUCTION_WARDROBE, wardrobe_tmp)
    else:
        wardrobe_tmp.write_text(
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

    saved_tmp = storage_dir / "saved_outfits.json"
    saved_tmp.write_text("[]", encoding="utf-8")
    monkeypatch.setenv("WARDROBE_JSON_PATH", str(wardrobe_tmp))
    monkeypatch.setenv("SAVED_OUTFITS_JSON_PATH", str(saved_tmp))
    monkeypatch.setenv("ALLOW_DEFAULT_OVERRIDE", "true")
    yield

# Unique names make it obvious whether context or disk data was used.
CONTEXT_TOP = {
    "name": "Context Casual Top",
    "category": "tops",
    "color": "white",
    "style": "casual",
}
CONTEXT_BOTTOM = {
    "name": "Context Jeans",
    "category": "bottoms",
    "color": "blue",
    "style": "casual",
}
CONTEXT_SHOES = {
    "name": "Context Sneakers",
    "category": "shoes",
    "color": "white",
    "style": "casual",
}
DISK_TOP = {
    "name": "Disk Only Top",
    "category": "tops",
    "color": "black",
    "style": "casual",
}
DISK_BOTTOM = {
    "name": "Disk Only Jeans",
    "category": "bottoms",
    "color": "black",
    "style": "casual",
}
DISK_SHOES = {
    "name": "Disk Only Sneakers",
    "category": "shoes",
    "color": "black",
    "style": "casual",
}


@pytest.fixture
def casual_plan() -> Plan:
    return Plan(intent="outfit_request", event="daily", style="casual")


@pytest.fixture
def casual_plan_dict(casual_plan: Plan) -> dict:
    return plan_to_dict(casual_plan)


@pytest.fixture
def context_wardrobe_list() -> list[dict]:
    return [CONTEXT_TOP, CONTEXT_BOTTOM, CONTEXT_SHOES]


@pytest.fixture
def disk_wardrobe_dict() -> dict:
    return {
        "tops": [DISK_TOP],
        "bottoms": [DISK_BOTTOM],
        "shoes": [DISK_SHOES],
        "outerwear": [],
        "accessories": [],
    }


@pytest.fixture
def context_memory() -> dict:
    return {
        "favorite_colors": ["white"],
        "preferred_styles": ["casual"],
        "disliked_items": ["Disk Only Top"],
    }


@pytest.fixture
def agent_context(
    casual_plan: Plan,
    context_wardrobe_list: list[dict],
    context_memory: dict,
) -> AgentContext:
    return AgentContext(
        user_input="casual outfit for daily wear",
        plan=casual_plan,
        memory=context_memory,
        wardrobe=context_wardrobe_list,
    )


@pytest.fixture
def temp_json_wardrobe_repository(tmp_path) -> JsonWardrobeRepository:
    """JSON repository backed by a disposable file (never the seed wardrobe)."""
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
    return JsonWardrobeRepository(wardrobe_path, user_id="test-isolated-user")


@pytest.fixture
def temp_saved_outfit_repository(tmp_path):
    from wardrobe.saved_outfit_repository import JsonSavedOutfitRepository

    return JsonSavedOutfitRepository(tmp_path / "saved_outfits.json")


@pytest.fixture
def isolated_api_wardrobe_service(temp_json_wardrobe_repository, temp_saved_outfit_repository):
    """Route API wardrobe access through temp JSON files for write-safe tests."""
    from api.session import get_session_user_id
    from services.saved_outfits_service import SavedOutfitsService

    test_user_id = temp_json_wardrobe_repository.user_id
    service = WardrobeService(repository=temp_json_wardrobe_repository, auto_seed=False)
    saved_service = SavedOutfitsService(repository=temp_saved_outfit_repository)

    app.dependency_overrides[get_session_user_id] = lambda: test_user_id
    app.dependency_overrides[get_wardrobe_service] = lambda: service
    app.dependency_overrides[get_saved_outfits_service] = lambda: saved_service
    yield service, temp_json_wardrobe_repository._path
    app.dependency_overrides.clear()


@pytest.fixture
def api_client():
    return TestClient(app)
