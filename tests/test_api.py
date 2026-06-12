from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_loads():
    client = TestClient(app)
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    payload = response.json()
    assert payload["settings"]["title"] == "Welcome to Aman's FIFA Sweepstake"
    assert len(payload["players"]) == 4
    assert len(payload["teams"]) == 48
    assert payload["team_flags"]["Argentina"] == "🇦🇷"


def test_admin_route_requires_password():
    client = TestClient(app)
    response = client.post("/api/admin/sync")
    assert response.status_code == 401


def test_admin_route_accepts_default_local_password():
    client = TestClient(app)
    response = client.post("/api/admin/sync", headers={"X-Admin-Password": "change-me"})
    assert response.status_code == 200
    assert response.json()["ok"] is True
