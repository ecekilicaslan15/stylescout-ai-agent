"""Post-generation outfit validation by styling mode."""

from __future__ import annotations

from typing import Callable

from agents.stylist_agent import MAX_HYBRID_SUGGESTED_ITEMS, resolve_inspiration_ownership
from models.outfit import outfit_schema_errors
from models.styling_mode import StylingMode

# Frontend board slots (frontend/index.html SLOTS) — normalized keys.
REQUIRED_SLOT_CATEGORIES = frozenset({"outerwear", "top", "bottom", "shoes"})
SLOT_DISPLAY_LABELS = {
    "outerwear": "Outerwear",
    "top": "Tops",
    "bottom": "Bottoms",
    "shoes": "Shoes",
}
ALLOWED_SOURCES = frozenset({"wardrobe", "suggested"})

FALLBACK_REASON = (
    "Could not validate an outfit for your selected styling mode. "
    "Showing a wardrobe-only result instead."
)
REPAIR_REASON_SUFFIX = " Adjusted after a validation issue."

CATEGORY_NORMALIZATION = {
    "tops": "top",
    "top": "top",
    "bottoms": "bottom",
    "bottom": "bottom",
    "shoes": "shoes",
    "outerwear": "outerwear",
    "accessories": "accessory",
    "accessory": "accessory",
    "Tops": "top",
    "Bottoms": "bottom",
    "Shoes": "shoes",
    "Outerwear": "outerwear",
    "Accessories": "accessory",
}


def _normalize_category(category: str | None) -> str | None:
    if not category:
        return None

    stripped = category.strip()
    lowered = stripped.lower()
    return CATEGORY_NORMALIZATION.get(lowered) or CATEGORY_NORMALIZATION.get(stripped)


def _normalize_missing_slot_label(label: str) -> str | None:
    normalized = _normalize_category(label)
    if normalized in REQUIRED_SLOT_CATEGORIES:
        return SLOT_DISPLAY_LABELS[normalized]
    return None


def wardrobe_item_key(item: dict) -> tuple:
    """Stable wardrobe identity: repository id when present, else (category, name)."""
    item_id = item.get("id")
    if item_id is not None:
        return ("id", item_id)
    category = _normalize_category(item.get("category")) or (item.get("category") or "")
    name = (item.get("name") or "").strip().lower()
    return ("name", category, name)


def build_wardrobe_identity_set(wardrobe: dict) -> set[tuple]:
    keys: set[tuple] = set()
    for category_items in wardrobe.values():
        for item in category_items:
            keys.add(wardrobe_item_key(item))
    return keys


def _regenerate_outfit(plan, memory: dict, wardrobe: dict, mode: StylingMode) -> dict:
    from agents.stylist_agent import generate_outfit

    return generate_outfit(plan=plan, memory=memory, wardrobe=wardrobe, mode=mode)


class OutfitValidator:
    @staticmethod
    def collect_errors(outfit: dict, wardrobe: dict, mode: StylingMode) -> list[str]:
        errors: list[str] = []
        errors.extend(OutfitValidator._validate_schema(outfit))
        errors.extend(OutfitValidator._mode_constraint_errors(outfit, wardrobe, mode))
        errors.extend(OutfitValidator._validate_coherence(outfit))
        return errors

    @staticmethod
    def _mode_constraint_errors(outfit: dict, wardrobe: dict, mode: StylingMode) -> list[str]:
        if mode == StylingMode.MY_WARDROBE:
            return OutfitValidator._my_wardrobe_errors(outfit, wardrobe)
        if mode == StylingMode.WARDROBE_PLUS_AI:
            return OutfitValidator._wardrobe_plus_ai_errors(outfit)
        if mode == StylingMode.AI_INSPIRATION:
            return OutfitValidator._ai_inspiration_errors(outfit, wardrobe)
        return []

    @staticmethod
    def validate(outfit: dict, wardrobe: dict, mode: StylingMode) -> None:
        normalized = OutfitValidator._document_missing_slots(dict(outfit))
        errors = OutfitValidator.collect_errors(normalized, wardrobe, mode)
        if errors:
            raise RuntimeError(errors[0])

    @staticmethod
    def _document_missing_slots(outfit: dict) -> dict:
        """Mark unfilled frontend SLOTS as explicitly missing (partial outfits are valid)."""
        filled_required = {
            slot
            for item in outfit.get("items") or []
            if isinstance(item, dict)
            if (slot := _normalize_category(item.get("category"))) in REQUIRED_SLOT_CATEGORIES
        }
        existing = {
            label
            for label in (outfit.get("missing_slots") or [])
            if _normalize_missing_slot_label(str(label))
        }
        missing_labels = sorted(
            {
                *existing,
                *(
                    SLOT_DISPLAY_LABELS[slot]
                    for slot in REQUIRED_SLOT_CATEGORIES
                    if slot not in filled_required
                ),
            },
            key=lambda label: list(SLOT_DISPLAY_LABELS.values()).index(label)
            if label in SLOT_DISPLAY_LABELS.values()
            else 0,
        )
        outfit["missing_slots"] = missing_labels
        return outfit

    @staticmethod
    def collect_satisfied_constraints(outfit: dict, wardrobe: dict, mode: StylingMode) -> list[str]:
        """Constraint ids for checks that passed on this outfit (gate-grounded only)."""
        satisfied: list[str] = []

        if not OutfitValidator._validate_schema(outfit):
            satisfied.append("schema_valid")

        coherence_errors = OutfitValidator._validate_coherence(outfit)
        if not any("duplicate category slot" in error for error in coherence_errors):
            satisfied.append("no_duplicate_slots")
        if not any("missing required slot" in error for error in coherence_errors):
            satisfied.append("required_slots_documented")

        mode_errors = OutfitValidator._mode_constraint_errors(outfit, wardrobe, mode)
        if not mode_errors:
            if mode == StylingMode.MY_WARDROBE:
                satisfied.append("my_wardrobe_provenance")
            elif mode == StylingMode.WARDROBE_PLUS_AI:
                satisfied.append("wardrobe_plus_ai_provenance")
                suggested = [
                    item
                    for item in outfit.get("items") or []
                    if isinstance(item, dict) and item.get("source") == "suggested"
                ]
                if len(suggested) <= MAX_HYBRID_SUGGESTED_ITEMS:
                    satisfied.append("wardrobe_plus_ai_suggested_cap")
            elif mode == StylingMode.AI_INSPIRATION:
                satisfied.append("ai_inspiration_provenance")

        return satisfied

    @staticmethod
    def _attach_explanation(
        outfit: dict,
        wardrobe: dict,
        mode: StylingMode,
        validation_outcome: str,
    ) -> dict:
        from services.stylist_notes_builder import build_outfit_explanation

        satisfied = OutfitValidator.collect_satisfied_constraints(outfit, wardrobe, mode)
        outfit["validation_outcome"] = validation_outcome
        outfit["satisfied_constraints"] = satisfied
        outfit["explanation"] = build_outfit_explanation(
            satisfied_constraints=satisfied,
            validation_outcome=validation_outcome,
            mode=mode,
            outfit=outfit,
            reason=outfit.get("reason"),
        )
        return outfit

    @staticmethod
    def validate_and_finalize(
        outfit: dict,
        wardrobe: dict,
        mode: StylingMode,
        *,
        plan,
        memory: dict,
        regenerate: Callable[..., dict] | None = None,
    ) -> dict:
        """Run the gate once; on failure apply one deterministic repair, then MY_WARDROBE fallback."""
        compose = regenerate or _regenerate_outfit

        outfit = OutfitValidator._document_missing_slots(dict(outfit))
        errors = OutfitValidator.collect_errors(outfit, wardrobe, mode)
        if not errors:
            return OutfitValidator._attach_explanation(outfit, wardrobe, mode, "validated")

        repaired = OutfitValidator._repair_outfit(dict(outfit), wardrobe, mode)
        repair_errors = OutfitValidator.collect_errors(repaired, wardrobe, mode)
        if not repair_errors:
            reason = (repaired.get("reason") or "").strip()
            repaired["reason"] = f"{reason}{REPAIR_REASON_SUFFIX}".strip()
            return OutfitValidator._attach_explanation(repaired, wardrobe, mode, "repaired")

        fallback = compose(plan, memory, wardrobe, StylingMode.MY_WARDROBE)
        fallback = OutfitValidator._document_missing_slots(fallback)
        fallback["reason"] = FALLBACK_REASON
        return OutfitValidator._attach_explanation(
            fallback,
            wardrobe,
            StylingMode.MY_WARDROBE,
            "fallback",
        )

    @staticmethod
    def _validate_schema(outfit: dict) -> list[str]:
        return outfit_schema_errors(outfit)

    @staticmethod
    def _validate_coherence(outfit: dict) -> list[str]:
        errors: list[str] = []
        seen_slots: dict[str, str] = {}
        filled_required: set[str] = set()

        for item in outfit.get("items") or []:
            if not isinstance(item, dict):
                continue

            slot = _normalize_category(item.get("category"))
            if not slot:
                continue

            label = item.get("name") or slot
            if slot in seen_slots:
                errors.append(
                    "outfit has duplicate category slot "
                    f"{slot!r} ({seen_slots[slot]!r} and {label!r})"
                )
            else:
                seen_slots[slot] = label

            if slot in REQUIRED_SLOT_CATEGORIES:
                filled_required.add(slot)

        explicit_missing: set[str] = set()
        for label in outfit.get("missing_slots") or []:
            normalized = _normalize_missing_slot_label(str(label))
            if normalized:
                explicit_missing.add(normalized)

        for slot in REQUIRED_SLOT_CATEGORIES:
            display = SLOT_DISPLAY_LABELS[slot]
            if slot not in filled_required and display not in explicit_missing:
                errors.append(f"outfit missing required slot {display!r}")

        return errors

    @staticmethod
    def _my_wardrobe_errors(outfit: dict, wardrobe: dict) -> list[str]:
        items = outfit.get("items") or []
        wardrobe_identities = build_wardrobe_identity_set(wardrobe)
        if not items:
            return []
        if not wardrobe_identities:
            return []

        errors: list[str] = []
        for item in items:
            label = item.get("name")
            if item.get("source") != "wardrobe" or item.get("owned") is not True:
                errors.append(f"my_wardrobe outfit item {label!r} has invalid provenance")
            elif wardrobe_item_key(item) not in wardrobe_identities:
                errors.append(
                    f"my_wardrobe outfit item {label!r} is not in the wardrobe snapshot"
                )
        return errors

    @staticmethod
    def _wardrobe_plus_ai_errors(outfit: dict) -> list[str]:
        suggested = [
            item
            for item in outfit.get("items") or []
            if isinstance(item, dict) and item.get("source") == "suggested"
        ]
        if len(suggested) > MAX_HYBRID_SUGGESTED_ITEMS:
            return [
                "wardrobe_plus_ai outfit has "
                f"{len(suggested)} suggested items; max is {MAX_HYBRID_SUGGESTED_ITEMS}"
            ]

        errors: list[str] = []
        for item in outfit.get("items") or []:
            if not isinstance(item, dict):
                continue
            source = item.get("source")
            owned = item.get("owned")
            if source not in ALLOWED_SOURCES:
                errors.append(f"wardrobe_plus_ai outfit item {item.get('name')!r} has invalid source")
            elif not isinstance(owned, bool):
                errors.append(f"wardrobe_plus_ai outfit item {item.get('name')!r} missing owned flag")
        return errors

    @staticmethod
    def _ai_inspiration_errors(outfit: dict, wardrobe: dict) -> list[str]:
        errors: list[str] = []
        wardrobe_identities = build_wardrobe_identity_set(wardrobe)

        for item in outfit.get("items") or []:
            if not isinstance(item, dict):
                continue

            label = item.get("name")
            source = item.get("source")
            owned = item.get("owned")

            if source not in ALLOWED_SOURCES:
                errors.append(f"ai_inspiration outfit item {label!r} has invalid source")
                continue
            if not isinstance(owned, bool):
                errors.append(f"ai_inspiration outfit item {label!r} missing owned flag")
                continue

            in_wardrobe = wardrobe_item_key(item) in wardrobe_identities
            if in_wardrobe:
                if source != "wardrobe" or owned is not True:
                    errors.append(
                        f"ai_inspiration outfit item {label!r} matches wardrobe "
                        "but is not marked owned"
                    )
            elif source == "wardrobe" and owned is True:
                errors.append(
                    f"ai_inspiration outfit item {label!r} is marked owned "
                    "but is not in the wardrobe snapshot"
                )

        return errors

    @staticmethod
    def _repair_outfit(outfit: dict, wardrobe: dict, mode: StylingMode) -> dict:
        """One deterministic repair pass — dedupe, trim, reprovenance, mark missing slots."""
        items = [dict(item) for item in (outfit.get("items") or []) if isinstance(item, dict)]

        if mode == StylingMode.AI_INSPIRATION:
            items = [resolve_inspiration_ownership(item, wardrobe) for item in items]
        elif mode == StylingMode.MY_WARDROBE:
            wardrobe_identities = build_wardrobe_identity_set(wardrobe)
            items = [
                item
                for item in items
                if item.get("source") == "wardrobe"
                and item.get("owned") is True
                and wardrobe_item_key(item) in wardrobe_identities
            ]
        elif mode == StylingMode.WARDROBE_PLUS_AI:
            wardrobe_items = [item for item in items if item.get("source") == "wardrobe"]
            suggested_items = [item for item in items if item.get("source") == "suggested"]
            items = wardrobe_items + suggested_items[:MAX_HYBRID_SUGGESTED_ITEMS]

        deduped: list[dict] = []
        seen_slots: set[str] = set()
        for item in items:
            slot = _normalize_category(item.get("category"))
            if slot and slot in seen_slots:
                continue
            if slot:
                seen_slots.add(slot)
            deduped.append(item)

        outfit["items"] = deduped
        return OutfitValidator._document_missing_slots(outfit)
