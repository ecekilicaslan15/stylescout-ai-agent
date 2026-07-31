"""Minimal StyleScout API for wardrobe data and outfit generation."""

from __future__ import annotations

import json
import os
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from functools import lru_cache
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field, field_validator

from api.session import LEGACY_USER_ID, get_session_user_id
from memory.memory_store import update_memory_from_input
from models.plan import Plan, plan_to_dict
from models.styling_mode import DEFAULT_STYLING_MODE, StylingMode
from orchestrator.fashion_orchestrator import run_fashion_agent, run_inline_edit
from services.pipeline_trace import get_pipeline_trace_labels
from services.saved_outfits_service import SavedOutfitsService, create_user_wardrobe_repository
from services.shopping_service import ShoppingService
from wardrobe.category_images import resolve_item_image_url
from wardrobe.item_metadata import read_item_id
from wardrobe.constants import CATEGORIES, DISPLAY_LABELS, FILTER_LABELS
from wardrobe.normalization import (
    clean_item_name,
    normalize_stored_category,
    normalize_stored_color,
    normalize_style,
    to_display_category,
)
from wardrobe.database import get_db_path, init_wardrobe_db, wardrobe_connection
from wardrobe.repository_factory import WARDROBE_BACKEND_ENV
from wardrobe.wardrobe_manager import update_wardrobe_from_input
from wardrobe.wardrobe_service import WardrobeService

FRONTEND_DIR = Path(__file__).resolve().parent.parent / "frontend"
SAMPLE_WARDROBE_PATH = Path(__file__).resolve().parent.parent / "wardrobe" / "wardrobe.json"
DEFAULT_USER_ID_FOR_SEED = "default"

CATEGORY_LABELS = DISPLAY_LABELS

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
DEFAULT_USER_ID = LEGACY_USER_ID

DISPLAY_CATEGORY_TO_AGENT = {
    "Tops": "top",
    "Bottoms": "bottom",
    "Shoes": "shoes",
    "Outerwear": "outerwear",
    "Accessories": "accessory",
}


class OutfitRequest(BaseModel):
    prompt: str = Field(min_length=1)
    mode: StylingMode = DEFAULT_STYLING_MODE


class InlineEditRequest(BaseModel):
    current_outfit: dict
    target_item: dict
    instruction: str = Field(min_length=1)


class SaveOutfitRequest(BaseModel):
    outfit: dict


class CreateWardrobeItemRequest(BaseModel):
    name: str = Field(min_length=1)
    category: str = Field(min_length=1)
    color: str = Field(min_length=1)
    style: str = Field(min_length=1)
    event: str = Field(min_length=1)
    image_url: str | None = None
    confirm_duplicate: bool = False

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str) -> str:
        return normalize_stored_category(value)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        normalized = normalize_stored_color(value)
        if not normalized:
            raise ValueError("Color is required.")
        return normalized

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str) -> str:
        normalized = normalize_style(value)
        if not normalized:
            raise ValueError("Style is required.")
        return normalized

    @field_validator("event")
    @classmethod
    def validate_event(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Event is required.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str) -> str:
        cleaned = clean_item_name(value)
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


class UpdateWardrobeItemRequest(BaseModel):
    name: str | None = None
    category: str | None = None
    color: str | None = None
    style: str | None = None
    event: str | None = None
    image_url: str | None = None
    confirm_duplicate: bool = False

    @field_validator("category")
    @classmethod
    def validate_category(cls, value: str | None) -> str | None:
        if value is None:
            return None
        return normalize_stored_category(value)

    @field_validator("color")
    @classmethod
    def validate_color(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_stored_color(value)
        if not normalized:
            raise ValueError("Color is required.")
        return normalized

    @field_validator("style")
    @classmethod
    def validate_style(cls, value: str | None) -> str | None:
        if value is None:
            return None
        normalized = normalize_style(value)
        if not normalized:
            raise ValueError("Style is required.")
        return normalized

    @field_validator("event")
    @classmethod
    def validate_event(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("Event is required.")
        return cleaned

    @field_validator("name")
    @classmethod
    def validate_name(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = clean_item_name(value)
        if not cleaned:
            raise ValueError("Name is required.")
        return cleaned

    @field_validator("image_url")
    @classmethod
    def validate_image_url(cls, value: str | None) -> str | None:
        if value is None:
            return None
        cleaned = value.strip()
        return cleaned or None


@lru_cache
def get_saved_outfits_service() -> SavedOutfitsService:
    return SavedOutfitsService()


def get_wardrobe_service(user_id: str = Depends(get_session_user_id)) -> WardrobeService:
    return WardrobeService(user_id=user_id)


def _find_stored_item(items: list[dict], category_key: str, name: str) -> dict | None:
    target_name = clean_item_name(name).lower()
    for item in items:
        if item.get("category") != category_key:
            continue
        if clean_item_name(item.get("name", "")).lower() == target_name:
            return item
    return None


def _find_stored_item_excluding(
    items: list[dict],
    category_key: str,
    name: str,
    exclude_item_id: str,
) -> dict | None:
    target_name = clean_item_name(name).lower()
    for item in items:
        if serialize_wardrobe_item(item)["id"] == exclude_item_id:
            continue
        if item.get("category") != category_key:
            continue
        if clean_item_name(item.get("name", "")).lower() == target_name:
            return item
    return None


def _duplicate_name_response(
    name: str,
    category_key: str,
    existing_item: dict,
    *,
    action: str = "Add",
) -> JSONResponse:
    existing_id = serialize_wardrobe_item(existing_item)["id"]
    display_category = to_display_category(category_key)
    return JSONResponse(
        status_code=409,
        content={
            "error": "duplicate_name",
            "message": (
                f"An item named '{name}' already exists in "
                f"{display_category}. {action} it anyway?"
            ),
            "existing_item_id": existing_id,
        },
    )


def _find_latest_stored_item(items: list[dict], category_key: str, name: str) -> dict | None:
    target_name = clean_item_name(name).lower()
    matches = [
        item
        for item in items
        if item.get("category") == category_key
        and clean_item_name(item.get("name", "")).lower() == target_name
    ]
    if not matches:
        return None
    return matches[-1]


def _build_create_payload(request: CreateWardrobeItemRequest, user_id: str) -> dict:
    payload = {
        "name": request.name,
        "category": request.category,
        "color": request.color,
        "style": request.style,
        "event": request.event,
        "user_id": user_id,
        "source": "wardrobe",
        "owned": True,
    }
    if request.image_url:
        payload["image_url"] = request.image_url
    return payload


def _build_update_payload(request: UpdateWardrobeItemRequest) -> dict:
    payload: dict = {}
    for field in ("name", "category", "color", "style", "event", "image_url"):
        value = getattr(request, field)
        if value is not None:
            payload[field] = value
    return payload


def _item_belongs_to_user(item: dict, user_id: str) -> bool:
    return item.get("user_id", DEFAULT_USER_ID) == user_id


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
    category_key = normalize_stored_category(item.get("category") or "")
    now = datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    item_id = read_item_id(item)

    return {
        "id": item_id,
        "user_id": item.get("user_id", DEFAULT_USER_ID),
        "name": item.get("name", ""),
        "category": to_display_category(category_key),
        "color": item.get("color", "neutral"),
        "style": item.get("style", "casual"),
        "event": item.get("event") or DEFAULT_EVENT,
        "image_url": resolve_item_image_url(item, category_key),
        "created_at": item.get("created_at") or now,
        "updated_at": item.get("updated_at") or now,
    }


def _normalize_outfit_category(category: str) -> str:
    return OUTFIT_CATEGORY_KEYS.get(category.strip().lower(), category.strip().lower())


def _index_wardrobe_by_category(items: list[dict]) -> dict[str, list[dict]]:
    grouped: dict[str, list[dict]] = {key: [] for key in CATEGORIES}
    for item in items:
        category_key = normalize_stored_category(item.get("category", ""))
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


def serialize_inline_edit_result(
    result: dict,
    service: WardrobeService,
    *,
    current_outfit: dict | None = None,
    target_item: dict | None = None,
) -> dict:
    """Convert run_inline_edit output into a JSON-safe API response."""
    wardrobe_items = service.list_items()
    wardrobe_by_category = _index_wardrobe_by_category(wardrobe_items)

    updated_item = result.get("updated_item")
    original_item = result.get("original_item")

    serialized_updated = (
        serialize_outfit_item(updated_item, wardrobe_by_category)
        if updated_item
        else None
    )
    serialized_original = (
        serialize_outfit_item(original_item, wardrobe_by_category)
        if original_item
        else None
    )

    payload = {
        "success": result.get("success", False),
        "message": result.get("message"),
        "updated_item": serialized_updated,
        "original_item": serialized_original,
        "instruction": result.get("instruction"),
        "error": result.get("error"),
    }

    if (
        result.get("success")
        and current_outfit
        and target_item
        and serialized_updated
    ):
        payload["outfit"] = _merge_inline_edit_outfit(
            current_outfit,
            target_item,
            serialized_updated,
            wardrobe_by_category,
        )

    return payload


def _merge_inline_edit_outfit(
    current_outfit: dict,
    target_item: dict,
    updated_item: dict,
    wardrobe_by_category: dict[str, list[dict]],
) -> dict:
    """Return the full outfit with only the target slot replaced."""
    target_id = target_item.get("id")
    target_name = (target_item.get("name") or "").strip().lower()
    target_category = target_item.get("category") or target_item.get("source_category")

    merged_items: list[dict] = []
    for item in current_outfit.get("items") or []:
        item_id = item.get("id")
        item_name = (item.get("name") or "").strip().lower()
        item_category = item.get("category") or item.get("source_category")
        is_target = False
        if target_id and item_id == target_id:
            is_target = True
        elif item_name == target_name and item_category == target_category:
            is_target = True

        if is_target:
            merged_items.append(dict(updated_item))
        else:
            merged_items.append(serialize_outfit_item(item, wardrobe_by_category))

    return {
        **{key: value for key, value in current_outfit.items() if key != "items"},
        "items": merged_items,
    }


INLINE_EDIT_CLIENT_ERRORS = frozenset(
    {"empty_instruction", "unrecognized_instruction", "no_replacement"}
)


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
    if item.get("id"):
        payload["id"] = item["id"]
    if wardrobe_match:
        payload.update(wardrobe_match)

    serialized = serialize_wardrobe_item(payload)
    serialized["source_category"] = item.get("category", category_key)
    if "source" in item:
        serialized["source"] = item["source"]
    if "owned" in item:
        serialized["owned"] = item["owned"]
    return serialized


SHOPPING_LINK_MODES = frozenset({StylingMode.WARDROBE_PLUS_AI, StylingMode.AI_INSPIRATION})


def _attach_shopping_links(items: list[dict], mode: StylingMode) -> list[dict]:
    """Add shopping_link only for suggested items in Mode 2/3."""
    if mode not in SHOPPING_LINK_MODES:
        return items

    shopping_service = ShoppingService()
    enriched: list[dict] = []
    for item in items:
        row = dict(item)
        if row.get("source") == "suggested" and row.get("owned") is False:
            row["shopping_link"] = shopping_service.primary_shopping_link(row)
        enriched.append(row)
    return enriched


def serialize_fashion_agent_result(
    result: dict,
    wardrobe_update: dict | None,
    service: WardrobeService,
    mode: StylingMode = DEFAULT_STYLING_MODE,
) -> dict:
    """Convert run_fashion_agent output into a JSON-safe API response."""
    plan = result.get("plan")
    plan_payload = plan_to_dict(plan) if isinstance(plan, Plan) else plan

    outfit = result.get("outfit")
    outfit_payload = None
    if outfit:
        wardrobe_items = service.list_items()
        wardrobe_by_category = _index_wardrobe_by_category(wardrobe_items)
        serialized_items = [
            serialize_outfit_item(item, wardrobe_by_category)
            for item in outfit.get("items", [])
        ]
        outfit_payload = {
            "event": outfit.get("event"),
            "style": outfit.get("style"),
            "city": outfit.get("city"),
            "date": outfit.get("date"),
            "reason": outfit.get("reason"),
            "items": _attach_shopping_links(serialized_items, mode),
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


def serialize_saved_outfit(record: dict) -> dict:
    """Map a saved outfit record to the API response shape."""
    outfit = record.get("outfit_json") or {}
    return {
        "id": record.get("id"),
        "user_id": record.get("user_id"),
        "created_at": record.get("created_at"),
        "outfit": outfit,
        "item_count": len(outfit.get("items") or []),
    }


app = FastAPI(title="StyleScout API", version="0.1.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
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
def list_wardrobe_items(service: WardrobeService = Depends(get_wardrobe_service)) -> list[dict]:
    items = service.list_items()
    return [serialize_wardrobe_item(item) for item in items]


@app.post("/api/wardrobe/items", status_code=201)
def create_wardrobe_item(
    request: CreateWardrobeItemRequest,
    service: WardrobeService = Depends(get_wardrobe_service),
    user_id: str = Depends(get_session_user_id),
):
    category_key = request.category
    payload = _build_create_payload(request, user_id)
    existing = _find_stored_item(service.list_items(), category_key, request.name)

    if existing and not request.confirm_duplicate:
        return _duplicate_name_response(
            request.name,
            category_key,
            existing,
            action="Add",
        )

    if not service.add_item(
        category_key,
        payload,
        allow_duplicate=request.confirm_duplicate,
    ):
        raise HTTPException(status_code=500, detail="Item could not be saved.")

    if request.confirm_duplicate and existing is not None:
        stored = _find_latest_stored_item(service.list_items(), category_key, request.name)
    else:
        stored = _find_stored_item(service.list_items(), category_key, request.name)

    if stored is None:
        raise HTTPException(status_code=500, detail="Item was saved but could not be loaded.")

    return serialize_wardrobe_item(stored)


@app.patch("/api/wardrobe/items/{item_id}")
def update_wardrobe_item(
    item_id: str,
    request: UpdateWardrobeItemRequest,
    service: WardrobeService = Depends(get_wardrobe_service),
    user_id: str = Depends(get_session_user_id),
):
    stored = service.get_item_by_id(item_id)
    if stored is None or not _item_belongs_to_user(stored, user_id):
        raise HTTPException(status_code=404, detail="Item not found.")

    updates = _build_update_payload(request)
    if not updates:
        raise HTTPException(status_code=400, detail="No fields to update.")

    category_key = updates.get("category") or normalize_stored_category(stored.get("category", ""))
    name = updates.get("name") or stored.get("name", "")
    existing = _find_stored_item_excluding(service.list_items(), category_key, name, item_id)

    if existing and not request.confirm_duplicate:
        return _duplicate_name_response(
            name,
            category_key,
            existing,
            action="Save",
        )

    if not service.update_item(
        item_id,
        updates,
        allow_duplicate=request.confirm_duplicate,
    ):
        raise HTTPException(status_code=500, detail="Item could not be updated.")

    updated = service.get_item_by_id(item_id)
    if updated is None:
        raise HTTPException(status_code=500, detail="Item was updated but could not be loaded.")

    return serialize_wardrobe_item(updated)


@app.delete("/api/wardrobe/items/{item_id}", status_code=204)
def delete_wardrobe_item(
    item_id: str,
    service: WardrobeService = Depends(get_wardrobe_service),
    user_id: str = Depends(get_session_user_id),
):
    stored = service.get_item_by_id(item_id)
    if stored is None or not _item_belongs_to_user(stored, user_id):
        raise HTTPException(status_code=404, detail="Item not found.")

    if not service.delete_item(item_id):
        raise HTTPException(status_code=404, detail="Item not found.")

    return Response(status_code=204)


@app.get("/api/wardrobe/category-labels")
def list_wardrobe_category_labels() -> list[str]:
    """Return ordered wardrobe filter tabs shared with the frontend."""
    return FILTER_LABELS


@app.get("/api/pipeline/trace-labels")
def pipeline_trace_labels() -> dict:
    """Return UI pipeline trace labels for the active execution path."""
    return get_pipeline_trace_labels()


@app.post("/api/outfits")
def create_outfit(
    request: OutfitRequest,
    service: WardrobeService = Depends(get_wardrobe_service),
) -> dict:
    prompt = request.prompt.strip()
    if not prompt:
        raise HTTPException(status_code=400, detail="Prompt is required.")

    update_memory_from_input(prompt)

    wardrobe_update = None
    try:
        wardrobe_update = update_wardrobe_from_input(prompt)
    except Exception:
        wardrobe_update = None

    wardrobe_repository = create_user_wardrobe_repository(service.user_id)
    result = run_fashion_agent(
        prompt,
        mode=request.mode,
        wardrobe_repository=wardrobe_repository,
    )
    return serialize_fashion_agent_result(result, wardrobe_update, service, mode=request.mode)


@app.post("/api/outfits/save", status_code=201)
def save_outfit(
    request: SaveOutfitRequest,
    user_id: str = Depends(get_session_user_id),
    saved_outfits: SavedOutfitsService = Depends(get_saved_outfits_service),
) -> dict:
    outfit = request.outfit
    items = outfit.get("items")
    if not isinstance(items, list) or not items:
        raise HTTPException(status_code=400, detail="outfit.items is required.")

    record = saved_outfits.save_outfit(user_id, outfit)
    return serialize_saved_outfit(record)


@app.get("/api/outfits/history")
def list_saved_outfits(
    user_id: str = Depends(get_session_user_id),
    saved_outfits: SavedOutfitsService = Depends(get_saved_outfits_service),
) -> list[dict]:
    records = saved_outfits.list_outfits(user_id)
    return [serialize_saved_outfit(record) for record in records]


@app.post("/api/outfits/inline-edit")
def inline_edit_outfit(
    request: InlineEditRequest,
    service: WardrobeService = Depends(get_wardrobe_service),
) -> dict:
    instruction = request.instruction.strip()
    if not instruction:
        raise HTTPException(status_code=400, detail="Instruction is required.")

    items = request.current_outfit.get("items") or []
    if not items:
        raise HTTPException(status_code=400, detail="current_outfit.items is required.")

    if not request.target_item:
        raise HTTPException(status_code=400, detail="target_item is required.")

    wardrobe_repository = create_user_wardrobe_repository(service.user_id)
    result = run_inline_edit(
        current_outfit=to_agent_outfit(request.current_outfit),
        target_item=to_agent_item(request.target_item),
        instruction=instruction,
        wardrobe_repository=wardrobe_repository,
    )

    if not result.get("success"):
        error_code = result.get("error") or "agent_error"
        message = result.get("message") or "Inline edit failed."
        if error_code in INLINE_EDIT_CLIENT_ERRORS:
            raise HTTPException(status_code=422, detail=message)
        if error_code == "missing_context":
            raise HTTPException(status_code=400, detail=message)
        raise HTTPException(status_code=500, detail=message)

    return serialize_inline_edit_result(
        result,
        service,
        current_outfit=request.current_outfit,
        target_item=request.target_item,
    )


app.mount("/", StaticFiles(directory=FRONTEND_DIR, html=True), name="frontend")
