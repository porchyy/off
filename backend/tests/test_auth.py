"""Unit tests for OAuth login, JWT token auth, and cloud model sync endpoints."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from backend.app.database import Base, get_db
from backend.app.main import app


@pytest.fixture
def client(tmp_path):
    db_file = tmp_path / "test_auth.sqlite"
    engine = create_engine(f"sqlite:///{db_file}", connect_args={"check_same_thread": False})
    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)

    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


def test_demo_login_and_me(client: TestClient):
    resp = client.post("/api/auth/demo", json={"email": "employee@company.com", "name": "Somchai Test"})
    assert resp.status_code == 200
    data = resp.json()
    assert "accessToken" in data
    assert data["user"]["email"] == "employee@company.com"
    token = data["accessToken"]

    # Verify /api/auth/me with Bearer token
    me_resp = client.get("/api/auth/me", headers={"Authorization": f"Bearer {token}"})
    assert me_resp.status_code == 200
    me_data = me_resp.json()
    assert me_data["email"] == "employee@company.com"


def test_oauth_login(client: TestClient):
    resp = client.post("/api/auth/oauth", json={"provider": "google", "idToken": "mock-user-123"})
    assert resp.status_code == 200
    data = resp.json()
    assert data["user"]["provider"] == "google"
    assert "user-123@google.com" in data["user"]["email"]


def test_user_custom_model_upload_and_download(client: TestClient):
    # Log in
    login_resp = client.post("/api/auth/demo", json={"email": "model.trainer@company.com", "name": "AI Trainer"})
    token = login_resp.json()["accessToken"]
    headers = {"Authorization": f"Bearer {token}"}

    # Should return 404 initially before model is uploaded
    get_resp = client.get("/api/user/model", headers=headers)
    assert get_resp.status_code == 404

    # Upload custom model artifacts
    model_json = '{"modelTopology":{},"weightsManifest":[]}'
    weights_b64 = "SGVsbG8gV29ybGQgV2VpZ2h0cw=="
    put_resp = client.put("/api/user/model", json={
        "modelJson": model_json,
        "weightsBase64": weights_b64
    }, headers=headers)
    assert put_resp.status_code == 200
    assert put_resp.json()["ok"] is True

    # Retrieve uploaded model artifacts
    get_resp = client.get("/api/user/model", headers=headers)
    assert get_resp.status_code == 200
    model_data = get_resp.json()
    assert model_data["modelJson"] == model_json
    assert model_data["weightsBase64"] == weights_b64
