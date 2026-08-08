"""Unit tests for PostureAI FastAPI routes and API logic."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
from app.config import settings
from app.main import app
from app.settings_store import ensure_defaults

# Setup in-memory SQLite database for testing
SQLALCHEMY_TEST_DATABASE_URL = "sqlite:///:memory:"

engine = create_engine(
    SQLALCHEMY_TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)


def override_get_db():
    db = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()


app.dependency_overrides[get_db] = override_get_db


@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with TestingSessionLocal() as db:
        ensure_defaults(db)
    yield
    Base.metadata.drop_all(bind=engine)


client = TestClient(app)


def test_health_check():
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["ok"] is True
    assert data["dbOk"] is True
    assert "time" in data


def test_latest_sensor_readings_round_trip():
    initial = client.get("/api/sensors/latest")
    assert initial.status_code == 200
    assert initial.json()["updatedAt"] is None

    response = client.put(
        "/api/sensors/latest",
        json={
            "lux": 423.5,
            "distanceCm": 62.4,
            "bh1750Ok": True,
            "tof200cOk": True,
        },
    )
    assert response.status_code == 204

    latest = client.get("/api/sensors/latest")
    assert latest.status_code == 200
    assert latest.json()["lux"] == 423.5
    assert latest.json()["distanceCm"] == 62.4
    assert latest.json()["bh1750Ok"] is True
    assert latest.json()["tof200cOk"] is True
    assert latest.json()["updatedAt"]


def test_camera_frame_round_trip():
    jpeg = b"\xff\xd8pi-camera-preview\xff\xd9"
    put_res = client.put(
        "/api/camera/frame",
        content=jpeg,
        headers={"content-type": "image/jpeg"},
    )
    assert put_res.status_code == 204

    status_res = client.get("/api/camera/status")
    assert status_res.status_code == 200
    assert status_res.json()["available"] is True
    assert status_res.json()["updatedAt"]

    get_res = client.get("/api/camera/frame")
    assert get_res.status_code == 200
    assert get_res.content == jpeg
    assert get_res.headers["content-type"] == "image/jpeg"
    assert "no-store" in get_res.headers["cache-control"]


def test_camera_frame_requires_jpeg():
    response = client.put(
        "/api/camera/frame",
        content=b"not-a-frame",
        headers={"content-type": "application/octet-stream"},
    )
    assert response.status_code == 415


def test_get_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["riskThreshold"] == 60
    assert data["riskSeconds"] == 45
    assert data["soundEnabled"] is True
    assert data["voiceEnabled"] is True
    assert data["desktopEnabled"] is False


def test_update_settings():
    payload = {
        "riskThreshold": 75,
        "riskSeconds": 30,
        "soundEnabled": False,
        "voiceEnabled": False,
        "desktopEnabled": True,
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["riskThreshold"] == 75
    assert data["riskSeconds"] == 30
    assert data["soundEnabled"] is False
    assert data["voiceEnabled"] is False
    assert data["desktopEnabled"] is True

    # Verify persistent update
    get_res = client.get("/api/settings")
    assert get_res.json()["riskThreshold"] == 75


def test_update_settings_accepts_internal_field_names():
    payload = {
        "risk_threshold": 70,
        "risk_seconds": 35,
        "sound_enabled": False,
        "desktop_enabled": True,
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["riskThreshold"] == 70
    assert data["riskSeconds"] == 35
    assert data["soundEnabled"] is False
    assert data["desktopEnabled"] is True


def test_update_settings_rejects_out_of_range_values():
    response = client.put("/api/settings", json={"risk_threshold": 150, "risk_seconds": 1})
    assert response.status_code == 422


def test_add_sample_success():
    sample = {
        "score": 88.5,
        "neck": 11.2,
        "shoulders": 4.1,
        "torso": 3.0,
    }
    response = client.post("/api/samples", json=sample)
    assert response.status_code == 201
    assert response.json() == {"ok": True}


def test_add_sample_validation_invalid_score():
    sample = {
        "score": 150.0,  # exceeds max 100
        "neck": 10.0,
        "shoulders": 5.0,
        "torso": 2.0,
    }
    response = client.post("/api/samples", json=sample)
    assert response.status_code == 422  # Unprocessable Entity


def test_add_alert_success():
    alert = {
        "severity": "risk",
        "message": "Poor posture detected for 45s",
    }
    response = client.post("/api/alerts", json=alert)
    assert response.status_code == 201
    assert response.json() == {"ok": True}


def test_add_alert_invalid_severity():
    alert = {
        "severity": "critical",  # invalid, only 'caution' or 'risk' allowed
        "message": "Test alert",
    }
    response = client.post("/api/alerts", json=alert)
    assert response.status_code == 422


def test_summary_and_stats():
    # Add samples and alert
    client.post("/api/samples", json={"score": 90.0, "neck": 10.0, "shoulders": 2.0, "torso": 1.0})
    client.post("/api/samples", json={"score": 70.0, "neck": 15.0, "shoulders": 8.0, "torso": 6.0})
    client.post("/api/alerts", json={"severity": "caution", "message": "Slouching warning"})

    # Check Summary
    sum_res = client.get("/api/summary")
    assert sum_res.status_code == 200
    sum_data = sum_res.json()
    assert sum_data["samples"] == 2
    assert sum_data["average"] == 80  # (90 + 70)/2 = 80
    assert len(sum_data["alerts"]) == 1
    assert sum_data["alerts"][0]["message"] == "Slouching warning"

    # Check Stats
    stats_res = client.get("/api/stats")
    assert stats_res.status_code == 200
    stats_data = stats_res.json()
    assert len(stats_data["daily"]) >= 1
    assert len(stats_data["weekly_alerts"]) >= 1


def test_export_csv_and_json():
    client.post("/api/samples", json={"score": 85.0, "neck": 10.0, "shoulders": 4.0, "torso": 3.0})
    client.post("/api/alerts", json={"severity": "risk", "message": "Posture risk alert"})

    # Test CSV export
    csv_res = client.get("/api/export?format=csv")
    assert csv_res.status_code == 200
    assert "text/csv" in csv_res.headers["content-type"]
    assert "sample,1,85.0" in csv_res.text
    assert "Posture risk alert" in csv_res.text

    # Test JSON export
    json_res = client.get("/api/export?format=json")
    assert json_res.status_code == 200
    json_data = json_res.json()
    assert "exportedAt" in json_data
    assert len(json_data["rows"]) == 2

    # Test Invalid export format validation
    invalid_res = client.get("/api/export?format=xml")
    assert invalid_res.status_code == 422


def test_clear_data():
    client.post("/api/samples", json={"score": 85.0, "neck": 10.0, "shoulders": 4.0, "torso": 3.0})
    client.post("/api/alerts", json={"severity": "risk", "message": "Posture risk alert"})

    clear_res = client.delete("/api/data")
    assert clear_res.status_code == 200
    assert clear_res.json() == {"ok": True}

    # Verify empty summary
    sum_res = client.get("/api/summary")
    assert sum_res.json()["samples"] == 0
    assert sum_res.json()["alerts"] == []


def test_prune_data():
    client.post("/api/samples", json={"score": 85.0, "neck": 10.0, "shoulders": 4.0, "torso": 3.0})
    prune_res = client.post("/api/data/prune?days=90")
    assert prune_res.status_code == 200
    assert prune_res.json() == {"ok": True}


def test_admin_token_protects_settings_and_clear_data():
    original_required = settings.require_admin_token
    original_token = settings.admin_token
    settings.require_admin_token = True
    settings.admin_token = "test-admin-token"
    try:
        assert client.put("/api/settings", json={"riskThreshold": 70}).status_code == 401
        assert client.delete("/api/data").status_code == 401
        headers = {"x-postureai-admin-token": "test-admin-token"}
        assert client.put("/api/settings", json={"riskThreshold": 70}, headers=headers).status_code == 200
        assert client.delete("/api/data", headers=headers).status_code == 200
    finally:
        settings.require_admin_token = original_required
        settings.admin_token = original_token


def test_client_status_round_trip():
    put_res = client.put(
        "/api/client/status",
        json={"online": True, "lastSyncAt": "2026-08-06T00:00:00+00:00", "message": "settings synchronized"},
    )
    assert put_res.status_code == 204
    get_res = client.get("/api/client/status")
    assert get_res.status_code == 200
    assert get_res.json()["online"] is True
    assert get_res.json()["lastSyncAt"] == "2026-08-06T00:00:00+00:00"
    assert get_res.json()["retentionDays"] == 30
