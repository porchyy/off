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

## Testing

Install development dependencies and run pytest:

```bash
pip install -r requirements-dev.txt
python -m pytest
```

Tests cover:
- Health check and database connection status
- Settings read, write, and range clamping
- Posture sample ingestion and score bounds validation
- Alert recording and severity validation
- Today's summary and 14-day stats aggregation
- Export to CSV and JSON formats
- Complete database clearing

## Configuration

Environment variables (loaded via `pydantic-settings`, supports `.env`):

| Variable | Default | Notes |
| --- | --- | --- |
| `POSTUREAI_DATA_DIR` | `./database` | SQLite file lives in `<data_dir>/postureai.sqlite` |
| `POSTUREAI_CORS_ORIGINS` | `http://localhost:5173,http://localhost:3000` | Comma-separated list, or `*` |
| `POSTUREAI_HOST` | `0.0.0.0` | Bind address |
| `POSTUREAI_PORT` | `8000` | HTTP port |
| `POSTUREAI_REQUIRE_ADMIN_TOKEN` | `false` | Require an admin token for settings/data mutations |
| `POSTUREAI_ADMIN_TOKEN` | empty | Secret sent as `X-PostureAI-Admin-Token` by the dashboard |
| `POSTUREAI_RETENTION_DAYS` | `30` | Remove samples and alerts older than this at startup and then daily |

The `dataDir` field returned by `/api/settings` always reflects the resolved
absolute path the server is actually using. Changes via `PUT /api/settings`
only persist the new path in the database — restart the server (or update the
env var) to actually move the SQLite file.

When `POSTUREAI_REQUIRE_ADMIN_TOKEN=true`, `PUT /api/settings`, `DELETE /api/data`,
and `POST /api/data/prune` require the `X-PostureAI-Admin-Token` header. Keep the
token in a local `.env` file with mode `600`; never commit it.

## Schema

FastAPI lifespan handler initializes the database on boot (`Base.metadata.create_all()`):

- `samples(id, score, neck, shoulders, torso, created_at)`
- `alerts(id, severity, message, created_at)`
- `settings(key, value)` — key/value JSON-encoded strings
