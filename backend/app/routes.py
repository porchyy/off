"""HTTP routes for the PostureAI backend."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Literal

from fastapi import APIRouter, Depends, HTTPException, Query, Request, Response
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .database import SessionLocal, engine, get_db
from .export import rows_to_csv
from .models import Alert, Base, Sample, Setting
from .schemas import (
    AlertIn,
    AlertOut,
    ExportResponse,
    HealthResponse,
    OkResponse,
    SampleIn,
    SettingsModel,
    SettingsUpdate,
    StatsResponse,
    SummaryResponse,
)
from .settings_store import DEFAULTS, ensure_defaults, get_all

router = APIRouter()


@router.get("/api/health", response_model=HealthResponse)
def health(db: Session = Depends(get_db)) -> HealthResponse:
    try:
        ok = db.execute(text("SELECT 1 AS ok")).scalar_one()
        db_ok = ok == 1
    except Exception:
        db_ok = False
    return HealthResponse(
        ok=True,
        db_ok=db_ok,
        db_path=str(settings.sqlite_path),
        data_dir=str(settings.data_dir.resolve()),
        time=datetime.now(timezone.utc).isoformat(),
    )


def _clamp_int(value: int | None, lo: int, hi: int, fallback: int) -> int:
    if value is None:
        return fallback
    return max(lo, min(hi, int(value)))


@router.get("/api/settings", response_model=SettingsModel)
def read_settings(db: Session = Depends(get_db)) -> SettingsModel:
    raw = get_all(db)
    return SettingsModel(
        risk_threshold=raw["riskThreshold"],
        risk_seconds=raw["riskSeconds"],
        data_dir=raw["dataDir"],
        sound_enabled=raw["soundEnabled"],
        desktop_enabled=raw["desktopEnabled"],
    )


@router.put("/api/settings", response_model=SettingsModel)
def write_settings(payload: SettingsUpdate, db: Session = Depends(get_db)) -> SettingsModel:
    current = get_all(db)
    new_dir = payload.data_dir.strip() if payload.data_dir else current["dataDir"]
    if not new_dir:
        new_dir = current["dataDir"]
    next_values: dict[str, Any] = {
        "riskThreshold": _clamp_int(payload.risk_threshold, 1, 99, current["riskThreshold"]),
        "riskSeconds": _clamp_int(payload.risk_seconds, 5, 600, current["riskSeconds"]),
        "dataDir": new_dir,
        "soundEnabled": bool(payload.sound_enabled) if payload.sound_enabled is not None else current["soundEnabled"],
        "desktopEnabled": bool(payload.desktop_enabled) if payload.desktop_enabled is not None else current["desktopEnabled"],
    }
    for key, value in next_values.items():
        row = db.get(Setting, key)
        if row is None:
            db.add(Setting(key=key, value=json_dumps(value)))
        else:
            row.value = json_dumps(value)
    db.commit()
    pending = next_values["dataDir"] != str(settings.data_dir.resolve())
    return SettingsModel(
        risk_threshold=next_values["riskThreshold"],
        risk_seconds=next_values["riskSeconds"],
        data_dir=str(settings.data_dir.resolve()),
        sound_enabled=next_values["soundEnabled"],
        desktop_enabled=next_values["desktopEnabled"],
        pending_data_dir=next_values["dataDir"] if pending else None,
    )


def json_dumps(value: Any) -> str:
    import json
    return json.dumps(value)


@router.post("/api/samples", status_code=201, response_model=OkResponse)
def add_sample(payload: SampleIn, db: Session = Depends(get_db)) -> OkResponse:
    db.add(Sample(
        score=payload.score,
        neck=payload.neck,
        shoulders=payload.shoulders,
        torso=payload.torso,
    ))
    db.commit()
    return OkResponse()


@router.post("/api/alerts", status_code=201, response_model=OkResponse)
def add_alert(payload: AlertIn, db: Session = Depends(get_db)) -> OkResponse:
    db.add(Alert(severity=payload.severity, message=payload.message))
    db.commit()
    return OkResponse()


def _today_start_iso() -> str:
    today = datetime.now(timezone.utc).replace(hour=0, minute=0, second=0, microsecond=0)
    return today.isoformat()


@router.get("/api/summary", response_model=SummaryResponse)
def summary(db: Session = Depends(get_db)) -> SummaryResponse:
    since = _today_start_iso()
    samples_count, average = db.execute(
        select(func.count(Sample.id), func.avg(Sample.score)).where(Sample.created_at >= since)
    ).one()
    alerts_rows = db.execute(
        select(Alert.id, Alert.severity, Alert.message, Alert.created_at)
        .where(Alert.created_at >= since)
        .order_by(Alert.id.desc())
        .limit(10)
    ).all()
    return SummaryResponse(
        samples=int(samples_count or 0),
        average=int(round(average)) if average is not None else None,
        alerts=[AlertOut(id=r[0], severity=r[1], message=r[2], created_at=r[3]) for r in alerts_rows],
    )


@router.get("/api/stats", response_model=StatsResponse)
def stats(db: Session = Depends(get_db)) -> StatsResponse:
    daily_rows = db.execute(
        text(
            "SELECT substr(created_at, 1, 10) AS label, "
            "ROUND(AVG(score)) AS average, COUNT(*) AS samples "
            "FROM samples GROUP BY label ORDER BY label DESC LIMIT 14"
        )
    ).all()
    daily = [{"label": r[0], "average": int(r[1] or 0), "samples": int(r[2] or 0)} for r in reversed(daily_rows)]

    alert_rows = db.execute(
        text(
            "SELECT substr(created_at, 1, 10) AS label, COUNT(*) AS alerts "
            "FROM alerts GROUP BY label ORDER BY label DESC LIMIT 14"
        )
    ).all()
    weekly_alerts = [{"label": r[0], "alerts": int(r[1] or 0)} for r in reversed(alert_rows)]

    return StatsResponse(daily=daily, weekly_alerts=weekly_alerts)


@router.get("/api/export")
def export(format: Literal["csv", "json"] = Query(default="csv"), db: Session = Depends(get_db)):
    samples = db.execute(text(
        "SELECT 'sample' AS type, id, score, neck, shoulders, torso, "
        "NULL AS severity, NULL AS message, created_at FROM samples ORDER BY id"
    )).mappings().all()
    alerts = db.execute(text(
        "SELECT 'alert' AS type, id, NULL AS score, NULL AS neck, NULL AS shoulders, NULL AS torso, "
        "severity, message, created_at FROM alerts ORDER BY id"
    )).mappings().all()
    rows = sorted([*samples, *alerts], key=lambda r: r["created_at"])
    if format == "json":
        return JSONResponse({
            "exportedAt": datetime.now(timezone.utc).isoformat(),
            "dbPath": str(settings.sqlite_path),
            "rows": [dict(r) for r in rows],
        })
    csv_text = rows_to_csv([dict(r) for r in rows])
    return PlainTextResponse(
        csv_text,
        media_type="text/csv; charset=utf-8",
        headers={"content-disposition": 'attachment; filename="postureai-export.csv"'},
    )


@router.delete("/api/data", response_model=OkResponse)
def clear_data(db: Session = Depends(get_db)) -> OkResponse:
    db.execute(delete(Sample))
    db.execute(delete(Alert))
    db.commit()
    return OkResponse()
