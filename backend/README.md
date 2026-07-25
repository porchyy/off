# PostureAI Backend (FastAPI)

FastAPI replacement for the original `server.mjs`. Keeps the same HTTP contract
(`/api/health`, `/api/settings`, `/api/samples`, `/api/alerts`, `/api/summary`,
`/api/stats`, `/api/export`, `/api/data`) so the existing frontend works
unchanged.

## Run locally

```powershell
cd backend
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
copy .env.example .env
python -m app
```

The server starts on `http://localhost:8000` by default. Interactive docs live
at `http://localhost:8000/docs`.

## Configuration

Environment variables (loaded via `pydantic-settings`, supports `.env`):

| Variable | Default | Notes |
| --- | --- | --- |
| `POSTUREAI_DATA_DIR` | `./database` | SQLite file lives in `<data_dir>/postureai.sqlite` |
| `POSTUREAI_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated list, or `*` |
| `POSTUREAI_HOST` | `0.0.0.0` | Bind address |
| `POSTUREAI_PORT` | `8000` | HTTP port |

The `dataDir` field returned by `/api/settings` always reflects the resolved
absolute path the server is actually using. Changes via `PUT /api/settings`
only persist the new path in the database — restart the server (or update the
env var) to actually move the SQLite file.

## Schema

`Base.metadata.create_all()` runs on startup and creates three tables:

- `samples(id, score, neck, shoulders, torso, created_at)`
- `alerts(id, severity, message, created_at)`
- `settings(key, value)` — key/value JSON-encoded strings

The same SQLite file format as the old `server.mjs` — drop-in compatible if
you have an existing `postureai.sqlite` (the only addition is the new
`dataDir` key in the `settings` table, which the original code stored in
`postureai.config.json` instead).
