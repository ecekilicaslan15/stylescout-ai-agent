# StyleScout — Data Model

## Tenancy (anonymous sessions)

StyleScout uses **browser-scoped anonymous sessions**, not login/auth.

| Concept | Storage | Notes |
|---------|---------|-------|
| `stylescout_session` cookie | Browser (httpOnly, SameSite=Lax) | Issued on first API visit when missing |
| Session value | `sess_<uuid4>` | Used directly as `user_id` on all records |
| Legacy `default` user | `wardrobe/wardrobe.json` (JSON) or SQLite rows | Untouched demo/manual-test data; never re-seeded or migrated |

**Relationship:** `session_id` **is** `user_id`. No mapping table.

First visit for a new `sess_*` user triggers an **idempotent wardrobe seed**: items from the `default` sample set in `wardrobe.json` are copied once with fresh ids. Repeat requests never duplicate seed rows.

## Wardrobe item

Stored in `wardrobe.json` (JSON backend) or `wardrobe_items` (SQLite).

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

## Saved outfit

Stored in `wardrobe/saved_outfits.json` (JSON backend) or `saved_outfits` (SQLite).

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `id` | string | yes | `out_<12 hex chars>` |
| `user_id` | string | yes | Same as session cookie value |
| `outfit_json` | object | yes | Full outfit snapshot (`items`, `event`, `style`, `reason`, …) |
| `created_at` | ISO-8601 UTC | yes | |

### SQLite: `saved_outfits`

```sql
CREATE TABLE saved_outfits (
    id TEXT PRIMARY KEY,
    user_id TEXT NOT NULL,
    outfit_json TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT (datetime('now'))
);
```

Indexes: `user_id`, `(user_id, created_at DESC)`.

## API surface (persistence-related)

| Method | Path | Scope |
|--------|------|-------|
| GET | `/api/wardrobe/items` | Session `user_id` |
| POST | `/api/wardrobe/items` | Session `user_id` |
| POST | `/api/outfits/save` | Writes saved outfit for session |
| GET | `/api/outfits/history` | Lists saved outfits for session |

All browser `fetch` calls must use `credentials: 'include'` so the session cookie is sent.
