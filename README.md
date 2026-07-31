# StyleScout

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

On free hosting tiers the SQLite file may not persist across container restarts; the sample wardrobe is re-seeded automatically when the database is empty.

## Persistence (anonymous sessions)

Each browser gets an httpOnly `stylescout_session` cookie (`sess_<uuid>`). That value is used as `user_id` for wardrobe items and saved outfits, so returning visitors see their data after refresh **in the same browser**.

- No login or accounts in MVP.
- The legacy `default` user in `wardrobe.json` is kept for manual API testing only (`Cookie: stylescout_session=default`).
- **Ephemeral filesystem risk:** on free PaaS tiers without a persistent disk, SQLite/JSON files may be wiped on redeploy or cold start. Session cookies survive in the browser, but server-side data may not. Acceptable for MVP; use a persistent volume in production if you need durable multi-visit storage.
