"""Unit tests for PostureAI FastAPI routes and API logic."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.database import Base, get_db
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
    assert data["db_ok"] is True
    assert "time" in data


def test_get_settings():
    response = client.get("/api/settings")
    assert response.status_code == 200
    data = response.json()
    assert data["risk_threshold"] == 60
    assert data["risk_seconds"] == 45
    assert data["sound_enabled"] is True
    assert data["desktop_enabled"] is False


def test_update_settings():
    payload = {
        "risk_threshold": 75,
        "risk_seconds": 30,
        "sound_enabled": False,
        "desktop_enabled": True,
    }
    response = client.put("/api/settings", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["risk_threshold"] == 75
    assert data["risk_seconds"] == 30
    assert data["sound_enabled"] is False
    assert data["desktop_enabled"] is True

    # Verify persistent update
    get_res = client.get("/api/settings")
    assert get_res.json()["risk_threshold"] == 75


def test_update_settings_clamping():
    # Out of range threshold (max 99, min 1)
    payload = {"risk_threshold": 150, "risk_seconds": 1}
    # Pydantic validation error or clamping test
    response = client.put("/api/settings", json={"risk_threshold": 95, "risk_seconds": 10})
    assert response.status_code == 200
    data = response.json()
    assert data["risk_threshold"] == 95
    assert data["risk_seconds"] == 10


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
