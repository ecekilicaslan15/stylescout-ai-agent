"""Persistence for saved outfit history keyed by user_id."""

from __future__ import annotations

import json
import os
import sqlite3
import uuid
from abc import ABC, abstractmethod
from pathlib import Path

from wardrobe.database import get_db_path, init_saved_outfits_db, wardrobe_connection
from wardrobe.item_metadata import utc_timestamp

DEFAULT_SAVED_OUTFITS_PATH = Path(__file__).resolve().parent / "saved_outfits.json"
SAVED_OUTFITS_JSON_PATH_ENV = "SAVED_OUTFITS_JSON_PATH"


def _resolve_saved_outfits_path() -> Path:
    configured = os.getenv(SAVED_OUTFITS_JSON_PATH_ENV)
    if configured:
        return Path(configured)
    return DEFAULT_SAVED_OUTFITS_PATH
LEGACY_USER_ID = "default"


def _is_pytest_run() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _guard_production_saved_outfit_writes(path: Path) -> None:
    if path.resolve() == DEFAULT_SAVED_OUTFITS_PATH.resolve() and _is_pytest_run():
        raise RuntimeError(
            "Refusing to write to production saved_outfits.json during tests. "
            "Use JsonSavedOutfitRepository(tmp_path / 'saved_outfits.json') instead."
        )


class SavedOutfitRepository(ABC):
    @abstractmethod
    def save(self, user_id: str, outfit: dict) -> dict:
        """Persist one outfit snapshot and return the stored record."""

    @abstractmethod
    def list_for_user(self, user_id: str) -> list[dict]:
        """Return saved outfits for one user, newest first."""


class JsonSavedOutfitRepository(SavedOutfitRepository):
    def __init__(self, path: Path | str | None = None) -> None:
        self._path = Path(path) if path is not None else _resolve_saved_outfits_path()

    def _load(self) -> list[dict]:
        if not self._path.exists():
            return []
        with self._path.open(encoding="utf-8") as file:
            data = json.load(file)
        if isinstance(data, list):
            return data
        return []

    def _save_all(self, records: list[dict]) -> None:
        _guard_production_saved_outfit_writes(self._path)
        self._path.parent.mkdir(parents=True, exist_ok=True)
        with self._path.open("w", encoding="utf-8") as file:
            json.dump(records, file, indent=2, ensure_ascii=False)

    def save(self, user_id: str, outfit: dict) -> dict:
        records = self._load()
        record = {
            "id": f"out_{uuid.uuid4().hex[:12]}",
            "user_id": user_id,
            "outfit_json": outfit,
            "created_at": utc_timestamp(),
        }
        records.append(record)
        self._save_all(records)
        return record

    def list_for_user(self, user_id: str) -> list[dict]:
        records = [
            record
            for record in self._load()
            if record.get("user_id") == user_id
        ]
        records.sort(key=lambda row: row.get("created_at", ""), reverse=True)
        return records


class SqliteSavedOutfitRepository(SavedOutfitRepository):
    def __init__(self, db_path: Path | str | None = None) -> None:
        self._db_path = Path(db_path) if db_path is not None else get_db_path()
        with wardrobe_connection(self._db_path) as connection:
            init_saved_outfits_db(connection)

    def save(self, user_id: str, outfit: dict) -> dict:
        record_id = f"out_{uuid.uuid4().hex[:12]}"
        created_at = utc_timestamp()
        outfit_json = json.dumps(outfit, ensure_ascii=False)

        with wardrobe_connection(self._db_path) as connection:
            connection.execute(
                """
                INSERT INTO saved_outfits (id, user_id, outfit_json, created_at)
                VALUES (?, ?, ?, ?)
                """,
                (record_id, user_id, outfit_json, created_at),
            )

        return {
            "id": record_id,
            "user_id": user_id,
            "outfit_json": outfit,
            "created_at": created_at,
        }

    def list_for_user(self, user_id: str) -> list[dict]:
        with wardrobe_connection(self._db_path) as connection:
            rows = connection.execute(
                """
                SELECT id, user_id, outfit_json, created_at
                FROM saved_outfits
                WHERE user_id = ?
                ORDER BY created_at DESC
                """,
                (user_id,),
            ).fetchall()

        records: list[dict] = []
        for row in rows:
            outfit_payload = json.loads(row["outfit_json"])
            records.append(
                {
                    "id": row["id"],
                    "user_id": row["user_id"],
                    "outfit_json": outfit_payload,
                    "created_at": row["created_at"],
                }
            )
        return records


def create_saved_outfit_repository(
    backend: str | None = None,
    *,
    json_path: Path | str | None = None,
    db_path: Path | str | None = None,
) -> SavedOutfitRepository:
    from wardrobe.repository_factory import WARDROBE_BACKEND_ENV

    selected = (backend or os.getenv(WARDROBE_BACKEND_ENV) or "json").strip().lower()
    if selected == "sqlite":
        return SqliteSavedOutfitRepository(db_path=db_path)
    return JsonSavedOutfitRepository(path=json_path)
