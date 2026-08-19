# StyleScout — Data model

> Persistence tenancy and API shapes. For HTTP details see `docs/API_SPEC.md`.

---

## Tenancy (anonymous sessions)

StyleScout uses **browser-scoped anonymous sessions**, not login/auth.

| Concept | Storage | Notes |
|---------|---------|-------|
| `stylescout_session` cookie | Browser (httpOnly, SameSite=Lax) | Issued on first API visit when missing |
| Session value | `sess_<uuid4>` | Used directly as `user_id` on all records |
| Legacy `default` user | Seed data only | Manual testing when `ALLOW_DEFAULT_OVERRIDE=true` |

**Relationship:** session id **is** `user_id`. No mapping table.

First visit for a new `sess_*` user triggers an **idempotent wardrobe seed**: items from the `default` sample set in `wardrobe.json` are copied once with fresh ids.

---

## Outfit (validation schema)

Defined in `models/outfit.py` — used by **`OutfitValidator`** schema stage.

### `OutfitItemModel`

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | |
| `category` | string | yes | Agent slot key (`top`, `bottom`, …) |
| `source` | `"wardrobe"` \| `"suggested"` | no* | *Required by mode gate before response |
| `owned` | boolean | no* | *Required by mode gate |
| `color` | string | no | |
| `style` | string | no | |
| `event` | string | no | |

### `OutfitModel`

| Field | Type | Notes |
|-------|------|-------|
| `items` | list[OutfitItemModel] | |
| `event` | string | optional |
| `style` | string | optional |
| `city` | string | optional |
| `date` | string | optional |
| `reason` | string | optional |
| `missing_slots` | list[string] | Documented empty slots (e.g. `"Tops"`) |

### Provenance contract (`source` / `owned`)

Every outfit item in API responses carries:

| `source` | `owned` | Meaning |
|----------|---------|---------|
| `wardrobe` | `true` | Piece exists in the user's wardrobe snapshot |
| `suggested` | `false` | Catalogue gap-fill or inspiration item; may include `shopping_link` |

**Mode rules (enforced in compose + validation gate):**

- **my_wardrobe:** all items `wardrobe` / `owned=true`; no items outside snapshot.
- **wardrobe_plus_ai:** at most **2** `suggested` items per outfit.
- **ai_inspiration:** compose from catalogue, then **`resolve_inspiration_ownership()`** marks wardrobe matches as `wardrobe` / `owned=true`.

Id shapes after serialization:

- Wardrobe-backed: `itm_*` (persisted)
- Unowned catalogue: `sug_*` (stable synthetic, SCOUT-015)

---

## Wardrobe item (persistence)

Stored in JSON (`wardrobe.json` / session file) or SQLite `wardrobe_items`.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | `itm_*` uuid |
| `user_id` | string | yes | Session id or `default` |
| `name` | string | yes | |
| `category` | string | yes | Storage key: `tops`, `bottoms`, … |
| `color` | string | yes | |
| `style` | string | yes | e.g. `casual`, `elegant` |
| `event` | string | no | |
| `image_url` | string | no | Hotlinked demo URLs |
| `source` | string | yes | `wardrobe` \| `suggested` |
| `owned` | boolean | yes | |
| `created_at` | ISO-8601 UTC | yes | |
| `updated_at` | ISO-8601 UTC | yes | |

**Known gap (SCOUT-002 sub-task C):** SQLite vs JSON provenance column parity not fully verified — see `docs/DECISIONS.md`.

API list/create responses use **display** category labels (`Tops`, …) via `serialize_wardrobe_item()`.

---

## SearchSpec (shopping deep-links)

`models/search_spec.py` — deterministic search intent for suggested items. **Not** live inventory.

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | yes | From outfit item |
| `category` | string | yes | Normalized slot (`top`, `bottom`, …) |
| `color` | string | yes | |
| `style` | string | yes | |
| `max_price` | float | no | From user preferences |
| `size` | string | no | From user preferences |

Built by `build_search_spec(item, preferences)` → consumed by `ShoppingService` → public Vinted catalog URL (`search_text` only; no price API).

---

## PreferenceProfile

`models/preferences.py` — partial shopping profile (SCOUT-008 scope).

| Field | Type | Notes |
|-------|------|-------|
| `max_price` | float (> 0) | Optional |
| `size` | string | Optional |

Stored per session user in `preferences.json` (or path from `PREFERENCES_JSON_PATH`).

**Deferred fields** (documented in DECISIONS, not implemented): `currency`, `country`, `second_hand`, `exclude_brands`.

---

## Saved outfit

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | `out_<12 hex>` |
| `user_id` | string | yes | Session cookie value |
| `outfit_json` | object | yes | Full outfit snapshot |
| `created_at` | ISO-8601 UTC | yes | |

SQLite table `saved_outfits` mirrors this when `WARDROBE_BACKEND=sqlite`.

---

## Plan (orchestrator routing)

`models/plan.py` — output of **`RuleBasedPlanner`** today.

| Field | Type | Default | Notes |
|-------|------|---------|-------|
| `intent` | string | `outfit_request` | |
| `event` | string | `daily` | |
| `style` | string | `casual` | |
| `colors` | list[string] | `[]` | |
| `disliked_items` | list[string] | `[]` | |
| `city` | string | null | |
| `date` | string | null | |
| `allow_external` | boolean | false | Set by `apply_styling_mode()` |
| `wardrobe_optional` | boolean | false | Set for `ai_inspiration` |

---

## Style memory (global)

`memory/memory_store.json` — **not per-session**; updated from outfit prompts via keyword rules.

```json
{
  "favorite_colors": [],
  "preferred_styles": [],
  "disliked_items": []
}
```

No delete UI; not env-configurable.
