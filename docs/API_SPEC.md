# StyleScout — API specification

Base URL: local `http://localhost:8000` · production **[live URL — pending Render verification, see docs/DECISIONS.md SCOUT-017 row]**

All `/api/*` routes that persist user data require the **`stylescout_session`** httpOnly cookie (issued automatically). Browser clients must use `credentials: 'include'`.

---

## Health

### `GET /health` · `GET /api/health`

No auth. No database access.

**Response 200:**

```json
{ "status": "ok", "version": "0.1.0" }
```

---

## Wardrobe

### `GET /api/wardrobe/items`

List wardrobe items for the session user.

**Response 200:** array of wardrobe item objects:

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | `itm_*` persisted id |
| `user_id` | string | Session id |
| `name` | string | |
| `category` | string | Display label: `Tops`, `Bottoms`, … |
| `color` | string | |
| `style` | string | |
| `event` | string | Default `everyday` when unset |
| `image_url` | string | |
| `created_at` | string | ISO-8601 UTC |
| `updated_at` | string | ISO-8601 UTC |

### `POST /api/wardrobe/items`

Create item. **201** on success.

**Request body:**

| Field | Type | Required |
|-------|------|----------|
| `name` | string | yes |
| `category` | string | yes (alias → storage key) |
| `color` | string | yes |
| `style` | string | yes |
| `event` | string | yes |
| `image_url` | string | no |
| `confirm_duplicate` | boolean | no (default `false`) |

**409** duplicate name (same category) when `confirm_duplicate=false`:

```json
{
  "error": "duplicate_name",
  "message": "An item named '…' already exists in … Add it anyway?",
  "existing_item_id": "itm_…"
}
```

Resubmit with `"confirm_duplicate": true` to allow duplicate names.

### `PATCH /api/wardrobe/items/{item_id}`

Partial update. Same field set as create (all optional). Duplicate-name **409** flow identical to POST.

**404** if item missing or not owned by session user.

### `DELETE /api/wardrobe/items/{item_id}`

**204** empty body on success. **404** if not found.

### `GET /api/wardrobe/category-labels`

**Response 200:** `["All", "Tops", "Bottoms", "Shoes", "Outerwear", "Accessories"]`

---

## Outfits

### `POST /api/outfits`

Generate outfit from natural-language prompt.

**Request body:**

| Field | Type | Required | Default |
|-------|------|----------|---------|
| `prompt` | string | yes | — |
| `mode` | string | no | `my_wardrobe` |

**Mode values:** `my_wardrobe` | `wardrobe_plus_ai` | `ai_inspiration`

**Response 200:**

```json
{
  "message": "string",
  "plan": {
    "intent": "outfit_request",
    "event": "daily",
    "style": "casual",
    "colors": [],
    "disliked_items": [],
    "city": null,
    "date": null,
    "allow_external": false,
    "wardrobe_optional": false
  },
  "outfit": {
    "event": "daily",
    "style": "casual",
    "city": null,
    "date": null,
    "reason": "string",
    "items": [ "…OutfitItem…" ],
    "missing_slots": ["Tops"]
  },
  "explanation": ["string"],
  "memory": {
    "favorite_colors": [],
    "preferred_styles": [],
    "disliked_items": []
  },
  "stylist_notes": "string or null",
  "wardrobe_update": null
}
```

**Outfit item** (serialized board shape):

| Field | Type | Notes |
|-------|------|-------|
| `id` | string | `itm_*` wardrobe or `sug_*` catalogue |
| `name` | string | |
| `category` | string | Display label |
| `source_category` | string | Agent slot key (`top`, `bottom`, …) |
| `color` | string | |
| `style` | string | |
| `event` | string | |
| `image_url` | string | |
| `source` | string | `wardrobe` \| `suggested` |
| `owned` | boolean | |
| `shopping_link` | string | Mode 2/3 suggested items only; Vinted search URL |
| `created_at` | string | |
| `updated_at` | string | |

**400** empty prompt. **422** invalid `mode`.

### `POST /api/outfits/save`

Persist outfit snapshot for session user. **201**.

**Request:** `{ "outfit": { …full outfit object… } }` — requires non-empty `outfit.items`.

**Response 201:**

```json
{
  "id": "out_…",
  "user_id": "sess_…",
  "created_at": "ISO-8601",
  "outfit": { … },
  "item_count": 3
}
```

### `GET /api/outfits/history`

**Response 200:** array of save records (same shape as save response).

### `POST /api/outfits/inline-edit`

Swap one board slot via free-text instruction. **Does not run OutfitValidator** (known gap).

**Request:**

| Field | Type | Required |
|-------|------|----------|
| `current_outfit` | object | yes (must include `items`) |
| `target_item` | object | yes |
| `instruction` | string | yes |

**Response 200 (success):**

```json
{
  "success": true,
  "message": "string",
  "updated_item": { "…OutfitItem…" },
  "original_item": { "…OutfitItem…" },
  "instruction": "string",
  "error": null,
  "outfit": { "…full outfit with one slot replaced…" }
}
```

**400** missing context · **422** unrecognized instruction / no replacement · **500** agent error

---

## Preferences

Shopping filters for deep-link query text (partial SCOUT-008 scope).

### `GET /api/preferences`

**Response 200:** `{ "max_price": number | absent, "size": string | absent }` — empty `{}` when unset.

### `POST /api/preferences`

**Request body** (`PreferenceProfile` — all optional):

| Field | Type | Constraints |
|-------|------|-------------|
| `max_price` | number | > 0 |
| `size` | string | non-empty when present |

**Response 200:** stored profile (merged).

---

## Pipeline / diagnostics

### `GET /api/pipeline/trace-labels`

UI labels for the active execution path.

**Response 200:**

```json
{
  "wardrobe": "WARDROBE SERVICE",
  "memory": "MEMORY SERVICE",
  "composer": "RULE-BASED COMPOSER",
  "composer_footer": "From the rule-based composer",
  "inline_edit": "INLINE EDIT AGENT",
  "use_llm": false
}
```

---

## Static frontend

### `GET /`

Serves `frontend/index.html` and assets via `StaticFiles`.

---

## Not implemented

| Endpoint | Status |
|----------|--------|
| `GET /api/memory` | Not exposed (memory updated implicitly on outfit prompt) |
