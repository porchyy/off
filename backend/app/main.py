"""FastAPI entrypoint — wires routes, CORS, and database bootstrap."""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from datetime import datetime, time, timedelta
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .config import settings
from .database import Base, SessionLocal, engine
from .daily_report import (
    LOCAL_TZ,
    compact_legacy_samples,
    local_today,
    prune_expired_reports,
    write_daily_report,
)
from .routes import prune_expired_data, router
from .settings_store import ensure_defaults, get_all


async def _retention_loop() -> None:
    """Run daily cleanup while keeping SQLite maintenance inside the backend."""
    while True:
        await asyncio.sleep(24 * 60 * 60)
        with SessionLocal() as db:
            prune_expired_data(db, settings.retention_days)
        prune_expired_reports(settings.daily_report_dir, settings.retention_days)


async def _daily_report_loop() -> None:
    """Write yesterday's report shortly after each Bangkok midnight."""
    while True:
        now = datetime.now(LOCAL_TZ)
        next_run = datetime.combine(now.date() + timedelta(days=1), time(hour=0, minute=5), tzinfo=LOCAL_TZ)
        await asyncio.sleep((next_run - now).total_seconds())
        with SessionLocal() as db:
            write_daily_report(db, (next_run - timedelta(days=1)).date(), get_all(db)["riskThreshold"], settings.daily_report_dir)


@asynccontextmanager
async def lifespan(app: FastAPI):
    Base.metadata.create_all(engine)
    with SessionLocal() as db:
        ensure_defaults(db)
        compact_legacy_samples(db, get_all(db)["riskThreshold"])
        prune_expired_data(db, settings.retention_days)
        write_daily_report(db, local_today() - timedelta(days=1), get_all(db)["riskThreshold"], settings.daily_report_dir)
        prune_expired_reports(settings.daily_report_dir, settings.retention_days)
    retention_task = asyncio.create_task(_retention_loop())
    report_task = asyncio.create_task(_daily_report_loop())
    try:
        yield
    finally:
        retention_task.cancel()
        report_task.cancel()
        try:
            await retention_task
        except asyncio.CancelledError:
            pass
        try:
            await report_task
        except asyncio.CancelledError:
            pass


app = FastAPI(title="PostureAI Backend", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origin_list,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)


# Optional: serve the built frontend if ../frontend/dist exists.
FRONTEND_DIST = Path(__file__).resolve().parents[2] / "frontend" / "dist"

if FRONTEND_DIST.exists():
    app.mount("/assets", StaticFiles(directory=FRONTEND_DIST / "assets"), name="assets")

    @app.get("/", include_in_schema=False)
    def _root_index() -> FileResponse:
        return FileResponse(FRONTEND_DIST / "index.html")
else:
    @app.get("/", include_in_schema=False)
    def _root_index() -> dict:
        return {
            "service": "postureai-backend",
            "docs": "/docs",
            "health": "/api/health",
        }
