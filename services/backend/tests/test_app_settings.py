from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_overlay_setting_defaults_off_and_persists():
    default_response = client.get("/api/settings")
    assert default_response.status_code == 200
    defaults = default_response.json()
    assert defaults["overlay_enabled"] == "off"
    assert defaults["overlay_position"] == "middle-right"
    assert defaults["overlay_opacity"] == 0.72
    assert defaults["overlay_message_count"] == 2

    update_response = client.post(
        "/api/settings",
        json={
            "overlay_enabled": "on",
            "overlay_position": "bottom-left",
            "overlay_opacity": 0.85,
            "overlay_message_count": 1,
        },
    )

    assert update_response.status_code == 200
    updated = update_response.json()
    assert updated["overlay_enabled"] == "on"
    assert updated["overlay_position"] == "bottom-left"
    assert updated["overlay_opacity"] == 0.85
    assert updated["overlay_message_count"] == 1
    assert client.get("/api/settings").json() == updated


def test_overlay_settings_reject_unsafe_values():
    assert client.post("/api/settings", json={"overlay_position": "center"}).status_code == 422
    assert client.post("/api/settings", json={"overlay_opacity": 0.1}).status_code == 422
    assert client.post("/api/settings", json={"overlay_opacity": 1.0}).status_code == 422
    assert client.post("/api/settings", json={"overlay_message_count": 0}).status_code == 422
    assert client.post("/api/settings", json={"overlay_message_count": 4}).status_code == 422
