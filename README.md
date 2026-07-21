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
