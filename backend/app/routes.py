"""HTTP routes for the PostureAI backend."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone
import hmac
import json
import logging
from typing import Any, Literal

from fastapi import APIRouter, Depends, Header, HTTPException, Query, Request, Response, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, PlainTextResponse
from sqlalchemy import delete, func, select, text
from sqlalchemy.orm import Session

from .config import settings
from .camera_store import camera_frames
from .camera_signaling import camera_signaling
from .database import SessionLocal, engine, get_db
from .export import rows_to_csv
from .models import Alert, Base, Sample, Setting
from .schemas import (
    AlertIn,
    AlertOut,
    ClientStatusIn,
    ClientStatusResponse,
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
from .runtime_state import client_runtime_state

router = APIRouter()
logger = logging.getLogger(__name__)

MAX_CAMERA_FRAME_BYTES = 3 * 1024 * 1024


def require_admin_token(x_postureai_admin_token: str | None = Header(default=None)) -> None:
    """Protect mutations without requiring a login to view the LAN dashboard."""
    if not settings.require_admin_token:
        return
    if not settings.admin_token:
        raise HTTPException(status_code=503, detail="admin token is not configured")
    if not x_postureai_admin_token or not hmac.compare_digest(x_postureai_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="administrator token is required")


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


@router.get("/api/client/status", response_model=ClientStatusResponse)
def client_status() -> ClientStatusResponse:
    online = client_runtime_state.is_online()
    return ClientStatusResponse(
        online=online,
        last_sync_at=client_runtime_state.last_sync_at,
        message=client_runtime_state.message if online else "Pi client heartbeat is stale or unavailable",
        updated_at=client_runtime_state.updated_at,
        retention_days=settings.retention_days,
    )


@router.put("/api/client/status", status_code=204)
def update_client_status(payload: ClientStatusIn) -> Response:
    client_runtime_state.update(payload.online, payload.last_sync_at, payload.message)
    return Response(status_code=204)


@router.put("/api/camera/frame", status_code=204)
async def put_camera_frame(request: Request) -> Response:
    """Accept the newest Pi Camera JPEG without persisting it."""
    content_type = request.headers.get("content-type", "")
    if not content_type.startswith("image/jpeg"):
        raise HTTPException(status_code=415, detail="camera frame must be image/jpeg")
    frame = await request.body()
    if not frame:
        raise HTTPException(status_code=422, detail="camera frame is empty")
    if len(frame) > MAX_CAMERA_FRAME_BYTES:
        raise HTTPException(status_code=413, detail="camera frame is too large")
    camera_frames.put(frame)
    return Response(status_code=204)


@router.get("/api/camera/frame")
def get_camera_frame() -> Response:
    """Return the current Pi Camera frame, if the sensor client is online."""
    frame, updated_at = camera_frames.get()
    if frame is None:
        raise HTTPException(status_code=404, detail="no Pi Camera frame is available yet")
    headers = {
        "Cache-Control": "no-store, max-age=0",
        "X-PostureAI-Frame-Time": updated_at or "",
    }
    return Response(content=frame, media_type="image/jpeg", headers=headers)


@router.get("/api/camera/status")
async def camera_status() -> dict[str, str | bool | None]:
    _, updated_at = camera_frames.get()
    signaling = await camera_signaling.status()
    return {"available": updated_at is not None or signaling["clientConnected"], "updatedAt": updated_at, **signaling}


@router.websocket("/api/camera/webrtc")
async def camera_webrtc(websocket: WebSocket) -> None:
    """Relay SDP between the Pi client and one dashboard browser.

    This is signaling only. WebRTC media travels directly across the LAN and
    is never stored by the backend.
    """
    role = websocket.query_params.get("role", "")
    if role not in {"pi", "viewer"}:
        await websocket.close(code=1008, reason="role must be pi or viewer")
        return
    await websocket.accept()
    if not await camera_signaling.register(role, websocket):
        state = await camera_signaling.status()
        if role == "viewer" and state["viewerConnected"]:
            reason = "camera is already being viewed by another dashboard"
        elif role == "viewer":
            reason = "camera client is unavailable"
        else:
            reason = "camera client already connected"
        await websocket.send_json({"type": "error", "code": "unavailable", "message": reason})
        await websocket.close(code=1013, reason=reason)
        return
    try:
        await websocket.send_json({"type": "ready", "role": role})
        while True:
            message = await websocket.receive_text()
            if role == "pi":
                try:
                    payload = json.loads(message)
                except ValueError:
                    payload = {}
                if payload.get("type") == "stream_info":
                    print(
                        "PostureAI actual Pi Camera stream format: "
                        f"{payload.get('cameraFormat', 'unknown')} "
                        f"[{payload.get('displayColorMode', 'unknown')}] "
                        f"(normalized output: {payload.get('outputColorSpace', 'unknown')})",
                        flush=True,
                    )
                    peer = await camera_signaling.peer(role)
                    if peer is not None:
                        await peer.send_text(message)
                    continue
            peer = await camera_signaling.peer(role)
            if peer is None:
                await websocket.send_json({"type": "error", "code": "peer_unavailable", "message": "camera peer disconnected"})
                continue
            await peer.send_text(message)
    except WebSocketDisconnect:
        pass
    finally:
        await camera_signaling.unregister(role, websocket)


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
        voice_enabled=raw["voiceEnabled"],
        desktop_enabled=raw["desktopEnabled"],
    )


@router.put("/api/settings", response_model=SettingsModel)
def write_settings(
    payload: SettingsUpdate,
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
) -> SettingsModel:
    current = get_all(db)
    new_dir = payload.data_dir.strip() if payload.data_dir else current["dataDir"]
    if not new_dir:
        new_dir = current["dataDir"]
    next_values: dict[str, Any] = {
        "riskThreshold": _clamp_int(payload.risk_threshold, 1, 99, current["riskThreshold"]),
        "riskSeconds": _clamp_int(payload.risk_seconds, 5, 600, current["riskSeconds"]),
        "dataDir": new_dir,
        "soundEnabled": bool(payload.sound_enabled) if payload.sound_enabled is not None else current["soundEnabled"],
        "voiceEnabled": bool(payload.voice_enabled) if payload.voice_enabled is not None else current["voiceEnabled"],
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
        voice_enabled=next_values["voiceEnabled"],
        desktop_enabled=next_values["desktopEnabled"],
        pending_data_dir=next_values["dataDir"] if pending else None,
    )


def json_dumps(value: Any) -> str:
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
def clear_data(db: Session = Depends(get_db), _: None = Depends(require_admin_token)) -> OkResponse:
    db.execute(delete(Sample))
    db.execute(delete(Alert))
    db.commit()
    return OkResponse()


def prune_expired_data(db: Session, days: int) -> None:
    cutoff = (datetime.now(timezone.utc) - timedelta(days=days)).isoformat()
    deleted_samples = db.execute(delete(Sample).where(Sample.created_at < cutoff)).rowcount
    deleted_alerts = db.execute(delete(Alert).where(Alert.created_at < cutoff)).rowcount
    db.commit()
    logger.info(
        "retention cleanup completed: days=%s samples=%s alerts=%s",
        days,
        deleted_samples or 0,
        deleted_alerts or 0,
    )


@router.post("/api/data/prune", response_model=OkResponse)
def prune_old_data(
    days: int = Query(default=30, ge=1, le=365),
    db: Session = Depends(get_db),
    _: None = Depends(require_admin_token),
) -> OkResponse:
    prune_expired_data(db, days)
    return OkResponse()
