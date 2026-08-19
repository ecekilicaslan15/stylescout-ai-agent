"""SCOUT-015 evaluation harness — in-process TestClient metrics runner."""

from __future__ import annotations

import json
import os
import statistics
import time
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from unittest.mock import patch

from fastapi.testclient import TestClient

from api.main import app, get_wardrobe_service
from api.session import generate_session_id, get_session_user_id
from models.outfit import outfit_schema_errors
from models.search_spec import build_search_spec
from models.styling_mode import StylingMode
from services.outfit_validator import FALLBACK_REASON, REPAIR_REASON_SUFFIX, OutfitValidator
from services.shopping_service import build_search_query
from wardrobe.constants import CATEGORIES
from wardrobe.json_wardrobe_repository import JsonWardrobeRepository
from wardrobe.seed import seed_user_wardrobe_if_empty
from wardrobe.wardrobe_service import WardrobeService

EVAL_DIR = Path(__file__).resolve().parent
FIXTURES_PATH = EVAL_DIR / "fixtures.json"
DEFAULT_REPORT_PATH = EVAL_DIR / "report.md"

PARTIAL_TOP = {
    "id": "eval_partial_top",
    "name": "Context Casual Top",
    "category": "tops",
    "color": "white",
    "style": "casual",
    "event": "everyday",
    "source": "wardrobe",
    "owned": True,
}

EMPTY_WARDROBE = {category: [] for category in CATEGORIES}


@dataclass
class FixtureResult:
    fixture_id: str
    mode: str
    wardrobe: str
    prompt: str
    latency_ms: float
    http_status: int
    schema_valid: bool
    provenance_ok: bool
    mode1_compliant: bool | None
    cap_ok: bool | None
    search_spec_ok: bool | None
    validation_path: str | None
    errors: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


def load_fixtures(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or FIXTURES_PATH
    payload = json.loads(source.read_text(encoding="utf-8"))
    fixtures = payload.get("fixtures") or []
    if not 20 <= len(fixtures) <= 40:
        raise ValueError(f"Expected 20-40 fixtures, found {len(fixtures)}")
    return fixtures


def _write_empty_wardrobe_file(path: Path) -> None:
    path.write_text(json.dumps(EMPTY_WARDROBE, indent=2), encoding="utf-8")


def _build_partial_wardrobe_file(path: Path, user_id: str) -> JsonWardrobeRepository:
    _write_empty_wardrobe_file(path)
    repository = JsonWardrobeRepository(path, user_id=user_id)
    repository.add_item("tops", dict(PARTIAL_TOP))
    return repository


def _build_full_wardrobe_file(path: Path, user_id: str) -> JsonWardrobeRepository:
    _write_empty_wardrobe_file(path)
    repository = JsonWardrobeRepository(path, user_id=user_id)
    seed_user_wardrobe_if_empty(repository)
    return repository


def _build_empty_wardrobe_file(path: Path, user_id: str) -> JsonWardrobeRepository:
    _write_empty_wardrobe_file(path)
    return JsonWardrobeRepository(path, user_id=user_id)


def _prepare_repository(path: Path, user_id: str, wardrobe_state: str) -> JsonWardrobeRepository:
    if wardrobe_state == "empty":
        return _build_empty_wardrobe_file(path, user_id)
    if wardrobe_state == "partial":
        return _build_partial_wardrobe_file(path, user_id)
    if wardrobe_state == "full":
        return _build_full_wardrobe_file(path, user_id)
    raise ValueError(f"Unknown wardrobe state: {wardrobe_state}")


def _document_outfit(outfit: dict) -> dict:
    return OutfitValidator._document_missing_slots(dict(outfit))


def _evaluate_outfit(
    outfit: dict | None,
    wardrobe_snapshot: dict,
    mode: StylingMode,
) -> tuple[bool, bool, list[str]]:
    if not outfit:
        return False, False, ["missing outfit payload"]

    documented = _document_outfit(outfit)
    schema_valid = len(outfit_schema_errors(documented)) == 0
    all_errors = OutfitValidator.collect_errors(documented, wardrobe_snapshot, mode)
    provenance_ok = len(OutfitValidator._mode_constraint_errors(documented, wardrobe_snapshot, mode)) == 0
    if not schema_valid:
        all_errors = list(dict.fromkeys([*outfit_schema_errors(documented), *all_errors]))
    return schema_valid, provenance_ok, all_errors


def _mode1_compliant(outfit: dict | None) -> tuple[bool | None, list[str]]:
    if not outfit:
        return False, ["missing outfit payload"]
    items = outfit.get("items") or []
    violations: list[str] = []
    for item in items:
        if item.get("source") != "wardrobe" or item.get("owned") is not True:
            violations.append(
                f"non-owned item {item.get('name')!r} "
                f"(source={item.get('source')!r}, owned={item.get('owned')!r})"
            )
    return len(violations) == 0, violations


def _cap_ok(outfit: dict | None) -> tuple[bool | None, list[str]]:
    if not outfit:
        return False, ["missing outfit payload"]
    suggested = [
        item
        for item in outfit.get("items") or []
        if item.get("source") == "suggested"
    ]
    if len(suggested) > 2:
        return False, [f"{len(suggested)} suggested items (>2 cap)"]
    return True, []


def _detect_validation_path(outfit: dict | None) -> str | None:
    if not outfit:
        return None
    reason = (outfit.get("reason") or "").strip()
    if FALLBACK_REASON in reason:
        return "fallback"
    if REPAIR_REASON_SUFFIX.strip() in reason:
        return "repair"
    return "validated"


def _check_search_spec(
    outfit: dict | None,
    preferences: dict,
) -> tuple[bool, list[str]]:
    if not outfit:
        return False, ["missing outfit payload"]
    issues: list[str] = []
    suggested = [
        item
        for item in outfit.get("items") or []
        if item.get("source") == "suggested" and item.get("owned") is False
    ]
    if not suggested:
        issues.append("no suggested items to evaluate search_spec against")
        return False, issues

    for item in suggested:
        spec = build_search_spec(item, preferences)
        if preferences.get("size") and spec.size != str(preferences["size"]).strip():
            issues.append(f"{item.get('name')}: size mismatch ({spec.size!r})")
        if preferences.get("max_price") is not None and spec.max_price != float(preferences["max_price"]):
            issues.append(f"{item.get('name')}: max_price mismatch ({spec.max_price!r})")
        query = build_search_query(spec)
        if preferences.get("size") and f"size {preferences['size']}" not in query:
            issues.append(f"{item.get('name')}: query missing size token")
        if preferences.get("max_price") is not None and f"under {float(preferences['max_price']):g}" not in query:
            issues.append(f"{item.get('name')}: query missing budget token")
        link = item.get("shopping_link") or ""
        if link and preferences.get("size") and f"size+{preferences['size']}" not in link.replace(" ", "+"):
            if f"size {preferences['size']}" not in link:
                issues.append(f"{item.get('name')}: shopping_link missing size")
    return len(issues) == 0, issues


def _corrupt_result(result: dict, corruption: str) -> dict:
    outfit = dict(result.get("outfit") or {})
    items = [dict(item) for item in outfit.get("items") or [] if isinstance(item, dict)]

    if corruption == "duplicate_slot" and items:
        duplicate = dict(items[0])
        duplicate["name"] = f"Duplicate {duplicate.get('name', 'Item')}"
        items.append(duplicate)
    elif corruption == "over_cap_suggested":
        items = [
            {"name": "Suggested Bottom", "category": "bottom", "source": "suggested", "owned": False},
            {"name": "Suggested Shoes", "category": "shoes", "source": "suggested", "owned": False},
            {"name": "Suggested Jacket", "category": "outerwear", "source": "suggested", "owned": False},
        ]
    elif corruption == "schema_invalid_fallback":
        items = [{"name": "", "category": "tops", "source": "suggested", "owned": False}]
    else:
        raise ValueError(f"Unknown corruption type: {corruption}")

    outfit["items"] = items
    outfit.setdefault("reason", "eval corruption injected")
    mutated = dict(result)
    mutated["outfit"] = outfit
    return mutated


def _run_fixture(
    fixture: dict[str, Any],
    *,
    storage_dir: Path,
    session_id: str,
) -> FixtureResult:
    from orchestrator import fashion_orchestrator

    wardrobe_path = storage_dir / f"{fixture['id']}-wardrobe.json"
    preferences_path = storage_dir / f"{fixture['id']}-preferences.json"
    saved_path = storage_dir / f"{fixture['id']}-saved.json"

    os.environ["WARDROBE_JSON_PATH"] = str(wardrobe_path)
    os.environ["PREFERENCES_JSON_PATH"] = str(preferences_path)
    os.environ["SAVED_OUTFITS_JSON_PATH"] = str(saved_path)
    os.environ.setdefault("ALLOW_DEFAULT_OVERRIDE", "true")

    repository = _prepare_repository(wardrobe_path, session_id, fixture["wardrobe"])
    auto_seed = fixture["wardrobe"] == "full"
    service = WardrobeService(repository=repository, auto_seed=auto_seed)
    wardrobe_snapshot = repository.get_by_category()
    mode = StylingMode(fixture["mode"])

    client = TestClient(app)
    client.cookies.set("stylescout_session", session_id)
    app.dependency_overrides[get_session_user_id] = lambda session_id=session_id: session_id
    app.dependency_overrides[get_wardrobe_service] = lambda service=service: service

    preferences = fixture.get("preferences") or {}
    if preferences:
        pref_response = client.post("/api/preferences", json=preferences)
        if pref_response.status_code != 200:
            app.dependency_overrides.clear()
            return FixtureResult(
                fixture_id=fixture["id"],
                mode=fixture["mode"],
                wardrobe=fixture["wardrobe"],
                prompt=fixture["prompt"],
                latency_ms=0.0,
                http_status=pref_response.status_code,
                schema_valid=False,
                provenance_ok=False,
                mode1_compliant=None,
                cap_ok=None,
                search_spec_ok=None,
                validation_path=None,
                errors=[f"preferences setup failed: {pref_response.text}"],
            )

    corruption = fixture.get("corruption")
    patch_target = "api.main.run_fashion_agent"
    real_run = fashion_orchestrator.run_fashion_agent

    def run_with_optional_corruption(*args, **kwargs):
        result = real_run(*args, **kwargs)
        if corruption:
            return _corrupt_result(result, corruption)
        return result

    started = time.perf_counter()
    try:
        with patch(patch_target, side_effect=run_with_optional_corruption):
            response = client.post(
                "/api/outfits",
                json={"prompt": fixture["prompt"], "mode": fixture["mode"]},
            )
    except Exception as exc:
        app.dependency_overrides.clear()
        latency_ms = (time.perf_counter() - started) * 1000.0
        return FixtureResult(
            fixture_id=fixture["id"],
            mode=fixture["mode"],
            wardrobe=fixture["wardrobe"],
            prompt=fixture["prompt"],
            latency_ms=latency_ms,
            http_status=500,
            schema_valid=False,
            provenance_ok=False,
            mode1_compliant=False if mode == StylingMode.MY_WARDROBE else None,
            cap_ok=False if mode == StylingMode.WARDROBE_PLUS_AI else None,
            search_spec_ok=False if fixture.get("check_search_spec") else None,
            validation_path=None,
            errors=[f"request raised {type(exc).__name__}: {exc}"],
        )
    finally:
        app.dependency_overrides.clear()

    latency_ms = (time.perf_counter() - started) * 1000.0
    payload = response.json() if response.content else {}
    outfit = payload.get("outfit")

    schema_valid, provenance_ok, eval_errors = _evaluate_outfit(outfit, wardrobe_snapshot, mode)
    mode1_ok, mode1_notes = _mode1_compliant(outfit) if mode == StylingMode.MY_WARDROBE else (None, [])
    cap_pass, cap_notes = _cap_ok(outfit) if mode == StylingMode.WARDROBE_PLUS_AI else (None, [])
    search_ok, search_notes = (None, [])
    if fixture.get("check_search_spec"):
        search_ok, search_notes = _check_search_spec(outfit, preferences)

    validation_path = _detect_validation_path(outfit)
    notes = [*mode1_notes, *cap_notes, *search_notes]
    if fixture.get("expect_path") and validation_path != fixture["expect_path"]:
        eval_errors.append(
            f"expected validation path {fixture['expect_path']!r}, got {validation_path!r}"
        )

    if mode == StylingMode.MY_WARDROBE and mode1_ok is False:
        eval_errors.extend(mode1_notes)

    return FixtureResult(
        fixture_id=fixture["id"],
        mode=fixture["mode"],
        wardrobe=fixture["wardrobe"],
        prompt=fixture["prompt"],
        latency_ms=latency_ms,
        http_status=response.status_code,
        schema_valid=schema_valid and response.status_code == 200,
        provenance_ok=provenance_ok and response.status_code == 200,
        mode1_compliant=mode1_ok if mode == StylingMode.MY_WARDROBE else None,
        cap_ok=cap_pass if mode == StylingMode.WARDROBE_PLUS_AI else None,
        search_spec_ok=search_ok,
        validation_path=validation_path,
        errors=eval_errors,
        notes=notes,
    )


def run_evaluation(
    *,
    report_path: Path | None = None,
    fixtures_path: Path | None = None,
    storage_dir: Path | None = None,
) -> dict[str, Any]:
    fixtures = load_fixtures(fixtures_path)
    report_target = report_path or DEFAULT_REPORT_PATH
    work_dir = storage_dir or (EVAL_DIR / ".scratch")
    work_dir.mkdir(parents=True, exist_ok=True)

    session_id = generate_session_id()
    results: list[FixtureResult] = []
    for fixture in fixtures:
        results.append(_run_fixture(fixture, storage_dir=work_dir, session_id=session_id))

    summary = _summarize(results)
    summary["fixture_count"] = len(results)
    report_md = _render_report(results, summary)
    report_target.parent.mkdir(parents=True, exist_ok=True)
    report_target.write_text(report_md, encoding="utf-8")

    summary["report_path"] = str(report_target)
    return summary


def _summarize(results: list[FixtureResult]) -> dict[str, Any]:
    mode1 = [result for result in results if result.mode1_compliant is not None]
    mode1_pass = [result for result in mode1 if result.mode1_compliant]
    cap = [result for result in results if result.cap_ok is not None]
    cap_pass = [result for result in cap if result.cap_ok]
    search = [result for result in results if result.search_spec_ok is not None]
    search_pass = [result for result in search if result.search_spec_ok]

    latencies = [result.latency_ms for result in results if result.http_status == 200]

    mode1_failures = [
        {"id": result.fixture_id, "errors": result.errors, "notes": result.notes}
        for result in mode1
        if not result.mode1_compliant
    ]

    return {
        "generated_at": datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z"),
        "latency_label": "local, in-process (TestClient — not a production SLA)",
        "mode1_compliance_pct": _pct(len(mode1_pass), len(mode1)),
        "schema_validity_pct": _pct(len([r for r in results if r.schema_valid]), len(results)),
        "provenance_correctness_pct": _pct(len([r for r in results if r.provenance_ok]), len(results)),
        "cap_adherence_pct": _pct(len(cap_pass), len(cap)),
        "search_spec_honoring_pct": _pct(len(search_pass), len(search)) if search else None,
        "p50_latency_ms": statistics.median(latencies) if latencies else 0.0,
        "mode1_failures": mode1_failures,
        "failures": [
            {
                "id": result.fixture_id,
                "errors": result.errors,
            }
            for result in results
            if result.errors or result.http_status != 200
        ],
        "validation_paths": {
            path: len([r for r in results if r.validation_path == path])
            for path in sorted({r.validation_path for r in results if r.validation_path})
        },
    }


def _pct(numerator: int, denominator: int) -> float:
    if denominator == 0:
        return 100.0
    return round(100.0 * numerator / denominator, 2)


def _render_report(results: list[FixtureResult], summary: dict[str, Any]) -> str:
    lines = [
        "# StyleScout evaluation report (SCOUT-015)",
        "",
        f"Generated: {summary['generated_at']}",
        "",
        "> **Latency note:** All latency figures are **local, in-process** measurements via FastAPI `TestClient`. They are **not** production or live-deployment SLA claims.",
        "",
        "## Summary metrics",
        "",
        "| Metric | Value |",
        "|--------|------:|",
        f"| Mode 1 compliance | {summary['mode1_compliance_pct']}% |",
        f"| Schema validity | {summary['schema_validity_pct']}% |",
        f"| Provenance correctness | {summary['provenance_correctness_pct']}% |",
        f"| Mode 2 cap adherence (≤2 suggested) | {summary['cap_adherence_pct']}% |",
    ]
    if summary["search_spec_honoring_pct"] is not None:
        lines.append(f"| Search spec honors preferences | {summary['search_spec_honoring_pct']}% |")
    lines.extend(
        [
            f"| p50 latency (ms, in-process) | {summary['p50_latency_ms']:.2f} |",
            "",
            f"Fixtures run: {summary['fixture_count']}",
            "",
            "### Validation paths observed",
            "",
        ]
    )
    for path, count in summary["validation_paths"].items():
        lines.append(f"- `{path}`: {count} fixture(s)")

    if summary["mode1_failures"]:
        lines.extend(
            [
                "",
                "## Mode 1 compliance failures (must be 100%)",
                "",
                "These are **bugs to triage**, not fixed in SCOUT-015:",
                "",
            ]
        )
        for failure in summary["mode1_failures"]:
            lines.append(f"- **`{failure['id']}`**: {'; '.join(failure['errors'] or failure['notes'])}")

    other_failures = [
        entry for entry in summary["failures"] if entry["id"] not in {f["id"] for f in summary["mode1_failures"]}
    ]
    if other_failures:
        lines.extend(["", "## Other fixture failures", ""])
        for failure in other_failures:
            lines.append(f"- **`{failure['id']}`**: {'; '.join(failure['errors']) or 'see notes'}")

    lines.extend(["", "## Per-fixture results", ""])
    lines.append("| ID | Mode | Wardrobe | ms | Schema | Provenance | Mode1 | Cap | Path |")
    lines.append("|----|------|----------|---:|--------|------------|-------|-----|------|")
    for result in results:
        lines.append(
            "| {id} | {mode} | {wardrobe} | {ms:.1f} | {schema} | {prov} | {mode1} | {cap} | {path} |".format(
                id=result.fixture_id,
                mode=result.mode,
                wardrobe=result.wardrobe,
                ms=result.latency_ms,
                schema="pass" if result.schema_valid else "FAIL",
                prov="pass" if result.provenance_ok else "FAIL",
                mode1="pass" if result.mode1_compliant else ("FAIL" if result.mode1_compliant is False else "—"),
                cap="pass" if result.cap_ok else ("FAIL" if result.cap_ok is False else "—"),
                path=result.validation_path or "—",
            )
        )

    lines.append("")
    return "\n".join(lines)
