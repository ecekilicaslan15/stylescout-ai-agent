# StyleScout

![Tests](https://github.com/ecekilicaslan15/stylescout-ai-agent/actions/workflows/tests.yml/badge.svg)

AI-powered Fashion Agent

## Features

- Outfit Planning
- Personalized Recommendations
- Memory System (Coming Soon)
- Wardrobe Management (Coming Soon)

## Run with Docker

```bash
docker build -t stylescout .
docker run -p 8000:8000 -e PORT=8000 stylescout
```

The image sets `WARDROBE_BACKEND=sqlite` and `DB_PATH=/app/data/wardrobe.db`, runs `uvicorn api.main:app` on `${PORT:-8000}`, and includes a Docker `HEALTHCHECK` against `GET /health`.

## Deployment & Limits

### Cold start

On free-tier PaaS hosts (e.g. Render), the service may **spin down after inactivity**. The first request after idle can take **30–60+ seconds** while the container starts. Retry once if the UI or API appears unavailable — this is platform behavior, not an application bug.

Health endpoints (no orchestrator or database work):

- `GET /health`
- `GET /api/health`

Both return `{"status":"ok","version":"0.1.0"}`.

### Ephemeral filesystem

Docker production uses SQLite at `/app/data/wardrobe.db` (see `Dockerfile`). That file **survives restarts within the same container instance** but is **not guaranteed across redeploys or cold starts** unless the host attaches a persistent disk.

On startup (`lifespan` → `seed_wardrobe_if_empty`):

- When `WARDROBE_BACKEND=sqlite`, the app creates the `DB_PATH` parent directory if missing, initializes schema, and **idempotently seeds** the default sample wardrobe when the table is empty (SCOUT-007).
- New session users (`sess_<uuid>`) receive a per-user wardrobe copy on first access when their wardrobe is empty.

**Session cookies** survive in the browser; **server-side wardrobe, saved outfits, and preferences may not** after redeploy without persistent storage. Style memory (`memory/memory_store.json`) is a single global file in the container filesystem — same ephemeral risk.

### Environment variables

Copy `.env.example` for local dev. Production Docker overrides backend/path in the `Dockerfile`; cloud hosts inject `PORT`.

| Variable | Default (local) | Purpose |
|----------|-----------------|---------|
| `PORT` | `8000` | Uvicorn listen port (`${PORT:-8000}` in Docker CMD; Render injects this) |
| `WARDROBE_BACKEND` | `json` | `json` (local dev) or `sqlite` (Docker / production) |
| `DB_PATH` | `wardrobe/wardrobe.db` | SQLite file when `WARDROBE_BACKEND=sqlite` |
| `WARDROBE_JSON_PATH` | `wardrobe/wardrobe.json` | JSON wardrobe file when backend is `json` |
| `SAVED_OUTFITS_JSON_PATH` | `wardrobe/saved_outfits.json` | Saved outfit history (JSON backend) |
| `PREFERENCES_JSON_PATH` | `wardrobe/preferences.json` | Per-user shopping prefs (`max_price`, `size`) |
| `OPENROUTER_API_KEY` | *(unset)* | Optional LLM key; rule-based planner runs when unset (`USE_LLM=False` in code) |
| `ALLOW_DEFAULT_OVERRIDE` | `false` | **`false` or unset in any public deployment.** When `true`, cookie `stylescout_session=default` acts as the legacy demo user |

`memory/memory_store.json` is not env-configurable; it is created on first write under `memory/`.

## Persistence (anonymous sessions)

Each browser gets an httpOnly `stylescout_session` cookie (`sess_<uuid>`). That value is used as `user_id` for wardrobe items and saved outfits, so returning visitors see their data after refresh **in the same browser**.

- No login or accounts in MVP.
- The legacy `default` user in `wardrobe.json` is kept for manual API testing only when `ALLOW_DEFAULT_OVERRIDE=true` (see `.env.example`). By default that cookie shortcut is **disabled**; unset or `false` issues a normal `sess_<uuid>` session instead.
- **Ephemeral filesystem risk:** on free PaaS tiers without a persistent disk, SQLite/JSON files may be wiped on redeploy or cold start. Session cookies survive in the browser, but server-side data may not. Acceptable for MVP; use a persistent volume in production if you need durable multi-visit storage.
