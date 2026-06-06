from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_overlay_setting_defaults_off_and_persists():
    default_response = client.get("/api/settings")
    assert default_response.status_code == 200
    assert default_response.json()["overlay_enabled"] == "off"

    update_response = client.post("/api/settings", json={"overlay_enabled": "on"})

    assert update_response.status_code == 200
    assert update_response.json()["overlay_enabled"] == "on"
    assert client.get("/api/settings").json()["overlay_enabled"] == "on"
