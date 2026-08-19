"""JSON-backed shopping preference storage keyed by session user_id."""

from __future__ import annotations

import json
import os
from pathlib import Path

DEFAULT_PREFERENCES_PATH = Path(__file__).resolve().parent.parent / "wardrobe" / "preferences.json"
PREFERENCES_JSON_PATH_ENV = "PREFERENCES_JSON_PATH"

KNOWN_PREFERENCE_KEYS = frozenset({"max_price", "size"})


def _resolve_preferences_path() -> Path:
    configured = os.getenv(PREFERENCES_JSON_PATH_ENV)
    if configured:
        return Path(configured)
    return DEFAULT_PREFERENCES_PATH


def _is_pytest_run() -> bool:
    return bool(os.getenv("PYTEST_CURRENT_TEST"))


def _guard_production_preference_writes(path: Path) -> None:
    if path.resolve() == DEFAULT_PREFERENCES_PATH.resolve() and _is_pytest_run():
        raise RuntimeError(
            "Refusing to write to production preferences.json during tests. "
            "Set PREFERENCES_JSON_PATH to a temp file in the test fixture."
        )


def _load_all(path: Path | None = None) -> dict[str, dict]:
    target = path or _resolve_preferences_path()
    if not target.exists():
        return {}
    with target.open(encoding="utf-8") as file:
        data = json.load(file)
    if not isinstance(data, dict):
        return {}
    return {
        str(user_id): dict(profile)
        for user_id, profile in data.items()
        if isinstance(profile, dict)
    }


def _save_all(records: dict[str, dict], path: Path | None = None) -> None:
    target = path or _resolve_preferences_path()
    _guard_production_preference_writes(target)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("w", encoding="utf-8") as file:
        json.dump(records, file, indent=2, ensure_ascii=False)


def _normalize_profile(profile: dict) -> dict:
    normalized: dict = {}
    for key in KNOWN_PREFERENCE_KEYS:
        if key not in profile:
            continue
        value = profile[key]
        if value is None:
            continue
        normalized[key] = value
    return normalized


def load_preferences(user_id: str) -> dict:
    """Return stored shopping preferences for one user (empty dict when unset)."""
    records = _load_all()
    return _normalize_profile(records.get(user_id, {}))


def save_preferences(user_id: str, prefs: dict) -> dict:
    """Merge and persist shopping preferences for one user."""
    records = _load_all()
    merged = {**records.get(user_id, {}), **_normalize_profile(prefs)}
    stored = {key: value for key, value in merged.items() if value is not None}
    records[user_id] = stored
    _save_all(records)
    return stored
