"""Minimal StyleScout API for wardrobe data and outfit generation."""

from __future__ import annotations

import hashlib
import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

from memory.memory_store import update_memory_from_input
from models.plan import Plan, plan_to_dict
from orchestrator.fashion_orchestrator import run_fashion_agent, run_inline_edit
from wardrobe.constants import CATEGORIES
from wardrobe.database import get_db_path, init_wardrobe_db, wardrobe_connection
from wardrobe.repository_factory import WARDROBE_BACKEND_ENV
from wardrobe.wardrobe_manager import update_wardrobe_from_input
from wardrobe.wardrobe_service import WardrobeService

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
SAMPLE_WARDROBE_PATH = Path(__file__).resolve().parent.parent / "wardrobe" / "wardrobe.json"
DEFAULT_USER_ID_FOR_SEED = "default"

CATEGORY_LABELS = {
    "tops": "Tops",
    "bottoms": "Bottoms",
    "shoes": "Shoes",
    "outerwear": "Outerwear",
    "accessories": "Accessories",
}

OUTFIT_CATEGORY_KEYS = {
    "top": "tops",
    "tops": "tops",
    "bottom": "bottoms",
    "bottoms": "bottoms",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessory": "accessories",
    "accessories": "accessories",
}

DEFAULT_EVENT = "everyday"
DEFAULT_USER_ID = "default"

CATEGORY_IMAGES = {
    "tops": "https://images.unsplash.com/photo-1521572163474-6864f9cf17ab?w=520&q=80",
    "bottoms": "https://images.unsplash.com/photo-1594633312681-425c7b97ccd1?w=520&q=80",
    "shoes": "https://images.unsplash.com/photo-1549298916-b41d501d3772?w=520&q=80",
    "outerwear": "https://images.unsplash.com/photo-1551028719-00167b16eac5?w=520&q=80",
    "accessories": "https://images.unsplash.com/photo-1523381210434-271e8be1f52b?w=520&q=80",
}

DISPLAY_CATEGORY_TO_AGENT = {
    "Tops": "top",
    "Bottoms": "bottom",
    "Shoes": "shoes",
    "Outerwear": "outerwear",
    "Accessories": "accessory",
}


class OutfitRequest(BaseModel):
    prompt: str = Field(min_length=1)


class InlineEditRequest(BaseModel):
    current_outfit: dict
    target_item: dict
    instruction: str = Field(min_length=1)


@lru_cache
def get_wardrobe_service() -> WardrobeService:
    return WardrobeService()


def seed_wardrobe_if_empty() -> None:
    """Load sample wardrobe into SQLite when the table is empty (idempotent)."""
    backend = (os.getenv(WARDROBE_BACKEND_ENV) or "json").strip().lower()
    if backend != "sqlite":
        return

    db_path = get_db_path()
    with wardrobe_connection(db_path) as connection:
        init_wardrobe_db(connection)
        count = connection.execute("SELECT COUNT(*) FROM wardrobe_items").fetchone()[0]
        if count > 0:
            return

        with SAMPLE_WARDROBE_PATH.open(encoding="utf-8") as file:
            sample_data = json.load(file)

        for category in CATEGORIES:
            for item in sample_data.get(category, []):
                connection.execute(
                    """
                    INSERT INTO wardrobe_items (
                        user_id, name, category, color, style, event, image_url
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        DEFAULT_USER_ID_FOR_SEED,
                        item.get("name", ""),
                        category,
                        item.get("color", "neutral"),
                        item.get("style", "casual"),
                        item.get("event"),
                        item.get("image_url"),
                    ),
                )


@asynccontextmanager
async def lifespan(_app: FastAPI):
    seed_wardrobe_if_empty()
    yield


def serialize_wardrobe_item(item: dict) -> dict:
    """Map repository item dicts to the frontend wardrobe grid shape."""
    category_key = (item.get("category") or "").strip().lower()
    category_key = OUTFIT_CATEGORY_KEYS.get(category_key, category_key)
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")

    if item.get("id") is not None:
        item_id = str(item["id"])
    else:
        stable_key = f"{category_key}:{item.get('name', '')}".encode()
        item_id = f"itm_{hashlib.sha256(stable_key).hexdigest()[:8]}"

    return {
        "id": item_id,
        "user_id": item.get("user_id", DEFAULT_USER_ID),
        "name": item.get("name", ""),
        "category": CATEGORY_LABELS.get(category_key, category_key.title()),
        "color": item.get("color", "neutral"),
        "style": item.get("style", "casual"),
        "event": item.get("event") or DEFAULT_EVENT,
        "image_url": item.get("image_url") or CATEGORY_IMAGES.get(category_key, CATEGORY_IMAGES["tops"]),
        "created_at": item.get("created_at") or now,
        "updated_at": item.get("updated_at") or now,
    }


def _normalize_outfit_category(category: str) -> str:
    return OUTFIT_CATEGORY_KEYS.get(category.strip().lower(), category.strip().lower())


def _index_wardrobe_by_category(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in CATEGORY_LABELS}
    for item in items:
        category_key = _normalize_outfit_category(item.get("category", ""))
        if category_key in grouped:
            grouped[category_key].append(item)
    return grouped


def to_agent_item(item: dict) -> dict:
    """Convert a frontend/API outfit item back to the agent item shape."""
    if item.get("source_category"):
        category = item["source_category"]
    else:
        display_category = item.get("category", "")
        category = DISPLAY_CATEGORY_TO_AGENT.get(display_category, display_category)
        category = OUTFIT_CATEGORY_KEYS.get(category.strip().lower(), category.strip().lower())

    agent_item = {
        "name": item.get("name", ""),
        "category": category,
        "color": item.get("color", ""),
        "style": item.get("style", "casual"),
    }
    if item.get("event"):
        agent_item["event"] = item["event"]
    return agent_item


def to_agent_outfit(outfit: dict) -> dict:
    """Convert a frontend/API outfit payload to the orchestrator outfit shape."""
    return {
        "items": [to_agent_item(item) for item in outfit.get("items", [])],
        "event": outfit.get("event"),
        "style": outfit.get("style"),
        "city": outfit.get("city"),
        "date": outfit.get("date"),
        "reason": outfit.get("reason"),
    }


def serialize_inline_edit_result(result: dict) -> dict:
    """Convert run_inline_edit output into a JSON-safe API response."""
    wardrobe_items = get_wardrobe_service().list_items()
    wardrobe_by_category = _index_wardrobe_by_category(wardrobe_items)

    updated_item = result.get("updated_item")
    original_item = result.get("original_item")

    return {
        "success": result.get("success", False),
        "message": result.get("message"),
        "updated_item": (
            serialize_outfit_item(updated_item, wardrobe_by_category)
            if updated_item
            else None
        ),
        "original_item": (
            serialize_outfit_item(original_item, wardrobe_by_category)
            if original_item
            else None
        ),
        "instruction": result.get("instruction"),
        "error": result.get("error"),
    }


def serialize_outfit_item(item: dict, wardrobe_by_category: dict[str, list[dict]]) -> dict:
    """Map stylist outfit items to the frontend session-board shape."""
    category_key = _normalize_outfit_category(item.get("category", ""))
    item_name = (item.get("name") or "").strip().lower()

    wardrobe_match = None
    for candidate in wardrobe_by_category.get(category_key, []):
        if (candidate.get("name") or "").strip().lower() == item_name:
            wardrobe_match = candidate
            break

    payload = {
        "name": item.get("name", ""),
        "category": category_key,
        "color": item.get("color", "neutral"),
        "style": item.get("style", "casual"),
        "event": item.get("event") or DEFAULT_EVENT,
    }
    if wardrobe_match:
        payload.update(wardrobe_match)

    serialized = serialize_wardrobe_item(payload)
    serialized["source_category"] = item.get("category", category_key)
    return serialized


def serialize_fashion_agent_result(result: dict, wardrobe_update: dict | None) -> dict:
    """Convert run_fashion_agent output into a JSON-safe API response."""
    plan = result.get("plan")
    plan_payload = plan_to_dict(plan) if isinstance(plan, Plan) else plan

    outfit = result.get("outfit")
    outfit_payload = None
    if outfit:
        wardrobe_items = get_wardrobe_service().list_items()
        wardrobe_by_category = _index_wardrobe_by_category(wardrobe_items)
        outfit_payload = {
            "event": outfit.get("event"),
            "style": outfit.get("style"),
            "city": outfit.get("city"),
            "date": outfit.get("date"),
            "reason": outfit.get("reason"),
            "items": [
                serialize_outfit_item(item, wardrobe_by_category)
                for item in outfit.get("items", [])
            ],
        }

    message = result.get("message") or ""
    if outfit_payload and outfit_payload.get("items") and not message:
        message = "Outfit generated successfully."

    return {
        "message": message,
        "plan": plan_payload,
        "outfit": outfit_payload,
        "memory": result.get("memory"),
        "stylist_notes": result.get("stylist_notes"),
        "wardrobe_update": wardrobe_update,
    }


app = FastAPI(title="StyleScout API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/api/health")
def api_health() -> dict[str, str]:
    return {"status": "ok", "version": app.version}


@app.get("/api/wardrobe/items")
def list_wardrobe_items() -> list[dict]:
    items = get_wardrobe_service().list_items()
    return [serialize_wardrobe_item(item) for item in items]


@app.post("/api/outfits")
def create_outfit(request: OutfitRequest) -> dict:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    update_memory_from_input(prompt)

    wardrobe_update = None
    try:
        wardrobe_update = update_wardrobe_from_input(prompt)
    except Exception:
        wardrobe_update = None

    result = run_fashion_agent(prompt)
    return serialize_fashion_agent_result(result, wardrobe_update)


@app.post("/api/outfits/inline-edit")
def inline_edit_outfit(request: InlineEditRequest) -> dict:
    instruction = request.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Instruction is required.")

    items = request.current_outfit.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="current_outfit.items is required.")

    if not request.target_item:
        raise HTTPException(status_code=400, detail="target_item is required.")

    result = run_inline_edit(
        current_outfit=to_agent_outfit(request.current_outfit),
        target_item=to_agent_item(request.target_item),
        instruction=instruction,
    )
    return serialize_inline_edit_result(result)


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
