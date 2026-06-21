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
    assert defaults["voice_interaction_mode"] == "confirm_send"
    assert defaults["voice_profile_id"] == "rei_calm"
    assert defaults["voice_spoken_reply_mode"] == "full"
    assert defaults["voice_direct_spoken_reply_mode"] == "brief"
    assert defaults["voice_speak_proactive"] is False
    assert defaults["voice_speak_memory_prompts"] is False
    assert defaults["voice_max_spoken_chars"] == 120
    assert defaults["voice_max_spoken_sentences"] == 2

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


def test_voice_interaction_mode_defaults_off_and_persists():
    default_response = client.get("/api/settings")
    assert default_response.status_code == 200
    assert default_response.json()["voice_interaction_mode"] == "confirm_send"

    updated = client.post("/api/settings", json={"voice_interaction_mode": "direct_conversation"})

    assert updated.status_code == 200
    assert updated.json()["voice_interaction_mode"] == "direct_conversation"
    assert client.get("/api/settings").json()["voice_interaction_mode"] == "direct_conversation"


def test_voice_interaction_mode_rejects_unknown_values():
    assert client.post("/api/settings", json={"voice_interaction_mode": "hands_free"}).status_code == 422


def test_voice_profile_settings_persist():
    updated = client.post(
        "/api/settings",
        json={
            "voice_spoken_reply_mode": "brief",
            "voice_direct_spoken_reply_mode": "silent",
            "voice_speak_proactive": True,
            "voice_speak_memory_prompts": True,
            "voice_max_spoken_chars": 180,
            "voice_max_spoken_sentences": 3,
        },
    )

    assert updated.status_code == 200
    payload = updated.json()
    assert payload["voice_profile_id"] == "rei_calm"
    assert payload["voice_spoken_reply_mode"] == "brief"
    assert payload["voice_direct_spoken_reply_mode"] == "silent"
    assert payload["voice_speak_proactive"] is True
    assert payload["voice_speak_memory_prompts"] is True
    assert payload["voice_max_spoken_chars"] == 180
    assert payload["voice_max_spoken_sentences"] == 3
    assert client.get("/api/settings").json()["voice_direct_spoken_reply_mode"] == "silent"


def test_voice_profile_settings_reject_unsafe_values():
    assert client.post("/api/settings", json={"voice_profile_id": "custom_character"}).status_code == 422
    assert client.post("/api/settings", json={"voice_spoken_reply_mode": "debug"}).status_code == 422
    assert client.post("/api/settings", json={"voice_direct_spoken_reply_mode": "hands_free"}).status_code == 422
    assert client.post("/api/settings", json={"voice_max_spoken_chars": 20}).status_code == 422
    assert client.post("/api/settings", json={"voice_max_spoken_chars": 320}).status_code == 422
    assert client.post("/api/settings", json={"voice_max_spoken_sentences": 0}).status_code == 422
    assert client.post("/api/settings", json={"voice_max_spoken_sentences": 5}).status_code == 422
