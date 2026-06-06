import json
import os
from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import settings
from app.main import app
from app.modules.voice_input.audio_conversion import CONVERTER_ENV
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV, get_local_asr_status
from app.modules.voice_input.local_asr_settings import local_asr_settings_path
from app.modules.voice_input.local_asr_transcribe import transcribe_local_asr_audio

client = TestClient(app)


def _clear_local_asr_env(monkeypatch):
    monkeypatch.delenv(BINARY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)
    monkeypatch.delenv(CONVERTER_ENV, raising=False)


def _write_executable(path: Path, text: str):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _ready_paths(tmp_path: Path, prefix: str = "user"):
    binary = tmp_path / prefix / "bin" / "whisper-cli"
    model = tmp_path / prefix / "models" / "ggml-base.bin"
    converter = tmp_path / prefix / "bin" / "ffmpeg"
    _write_executable(binary, "#!/bin/sh\necho 'Usage: whisper-cli'\n")
    _write_executable(converter, "#!/bin/sh\nexit 99\n")
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text("model placeholder", encoding="utf-8")
    return binary, model, converter


def test_local_asr_settings_empty_without_file(monkeypatch):
    _clear_local_asr_env(monkeypatch)

    response = client.get("/api/voice-input/local-asr/settings")
    status = get_local_asr_status()

    assert response.status_code == 200
    assert response.json() == {
        "configured": False,
        "binary_configured": False,
        "model_configured": False,
        "converter_configured": False,
        "safe_binary_name": None,
        "safe_model_name": None,
        "safe_converter_name": None,
        "source": "none",
    }
    assert status.status == "local_asr_not_configured"
    assert local_asr_settings_path().exists() is False


def test_local_asr_settings_put_saves_paths_and_returns_safe_names(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    binary, model, converter = _ready_paths(tmp_path)

    response = client.put(
        "/api/voice-input/local-asr/settings",
        json={
            "local_asr_binary_path": str(binary),
            "local_asr_model_path": str(model),
            "audio_converter_binary_path": str(converter),
        },
    )
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)
    settings_file = local_asr_settings_path()

    assert response.status_code == 200
    assert data["configured"] is True
    assert data["source"] == "user_settings"
    assert data["safe_binary_name"] == "whisper-cli"
    assert data["safe_model_name"] == "ggml-base.bin"
    assert data["safe_converter_name"] == "ffmpeg"
    assert str(binary) not in payload
    assert str(model) not in payload
    assert str(converter) not in payload
    assert settings_file == settings.data_dir / "local_asr_settings.json"
    assert settings_file.is_file()
    assert "services/backend" not in str(settings_file)


def test_local_asr_settings_get_is_safe_and_status_uses_user_settings(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    env_binary, env_model, _ = _ready_paths(tmp_path, "env")
    binary, model, converter = _ready_paths(tmp_path, "user")
    monkeypatch.setenv(BINARY_ENV, str(env_binary))
    monkeypatch.setenv(MODEL_ENV, str(env_model))

    client.put(
        "/api/voice-input/local-asr/settings",
        json={
            "local_asr_binary_path": str(binary),
            "local_asr_model_path": str(model),
            "audio_converter_binary_path": str(converter),
        },
    )
    response = client.get("/api/voice-input/local-asr/settings")
    status_response = client.get("/api/voice-input/local-asr/status")
    status = status_response.json()
    payload = json.dumps({"settings": response.json(), "status": status}, ensure_ascii=False)

    assert response.status_code == 200
    assert response.json()["source"] == "user_settings"
    assert status["status"] == "local_asr_ready"
    assert status["source"] == "user_settings"
    assert status["safe_binary_name"] == "whisper-cli"
    assert status["safe_model_name"] == "ggml-base.bin"
    assert str(binary) not in payload
    assert str(model) not in payload
    assert str(converter) not in payload
    assert str(env_binary) not in payload
    assert str(env_model) not in payload
    assert os.environ[BINARY_ENV] not in payload
    assert os.environ[MODEL_ENV] not in payload
    assert "Traceback" not in payload
    assert "Exception" not in payload


def test_local_asr_settings_env_fallback_and_clear(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    env_binary, env_model, env_converter = _ready_paths(tmp_path, "env")
    user_binary, user_model, _ = _ready_paths(tmp_path, "user")
    monkeypatch.setenv(BINARY_ENV, str(env_binary))
    monkeypatch.setenv(MODEL_ENV, str(env_model))
    monkeypatch.setenv(CONVERTER_ENV, str(env_converter))

    env_response = client.get("/api/voice-input/local-asr/settings").json()
    client.put(
        "/api/voice-input/local-asr/settings",
        json={"local_asr_binary_path": str(user_binary), "local_asr_model_path": str(user_model)},
    )
    clear_response = client.delete("/api/voice-input/local-asr/settings")
    data = clear_response.json()

    assert env_response["source"] == "env"
    assert env_response["safe_binary_name"] == "whisper-cli"
    assert clear_response.status_code == 200
    assert data["source"] == "env"
    assert data["configured"] is True
    assert data["safe_binary_name"] == "whisper-cli"
    assert data["safe_model_name"] == "ggml-base.bin"
    assert data["safe_converter_name"] == "ffmpeg"
    assert local_asr_settings_path().exists() is False


def test_local_asr_settings_corrupted_json_does_not_crash(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    env_binary, env_model, _ = _ready_paths(tmp_path, "env")
    monkeypatch.setenv(BINARY_ENV, str(env_binary))
    monkeypatch.setenv(MODEL_ENV, str(env_model))
    local_asr_settings_path().parent.mkdir(parents=True, exist_ok=True)
    local_asr_settings_path().write_text("{not valid json", encoding="utf-8")

    response = client.get("/api/voice-input/local-asr/settings")
    status = client.get("/api/voice-input/local-asr/status")
    payload = json.dumps({"settings": response.json(), "status": status.json()}, ensure_ascii=False)

    assert response.status_code == 200
    assert response.json()["source"] == "env"
    assert status.status_code == 200
    assert status.json()["status"] == "local_asr_ready"
    assert "not valid json" not in payload
    assert "JSONDecodeError" not in payload
    assert str(env_binary) not in payload
    assert str(env_model) not in payload


def test_local_asr_settings_put_does_not_execute_configured_path(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    marker = tmp_path / "ran.txt"
    binary = tmp_path / "bin" / "whisper-cli"
    model = tmp_path / "models" / "ggml-base.bin"
    _write_executable(binary, f"#!/bin/sh\ntouch {marker}\n")
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text("model placeholder", encoding="utf-8")

    response = client.put(
        "/api/voice-input/local-asr/settings",
        json={"local_asr_binary_path": str(binary), "local_asr_model_path": str(model)},
    )

    assert response.status_code == 200
    assert marker.exists() is False


def test_local_asr_settings_empty_string_clears_individual_field(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    binary, model, converter = _ready_paths(tmp_path)
    client.put(
        "/api/voice-input/local-asr/settings",
        json={
            "local_asr_binary_path": str(binary),
            "local_asr_model_path": str(model),
            "audio_converter_binary_path": str(converter),
        },
    )

    response = client.put("/api/voice-input/local-asr/settings", json={"local_asr_model_path": ""})
    data = response.json()
    saved = json.loads(local_asr_settings_path().read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert data["configured"] is False
    assert data["binary_configured"] is True
    assert data["model_configured"] is False
    assert data["safe_model_name"] is None
    assert "local_asr_model_path" not in saved


def test_local_asr_probe_uses_resolved_user_settings(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    env_marker = tmp_path / "env-ran.txt"
    user_marker = tmp_path / "user-ran.txt"
    env_binary, env_model, _ = _ready_paths(tmp_path, "env")
    user_binary, user_model, _ = _ready_paths(tmp_path, "user")
    _write_executable(env_binary, f"#!/bin/sh\ntouch {env_marker}\necho 'Usage env'\n")
    _write_executable(user_binary, f"#!/bin/sh\ntouch {user_marker}\necho 'Usage user'\n")
    monkeypatch.setenv(BINARY_ENV, str(env_binary))
    monkeypatch.setenv(MODEL_ENV, str(env_model))
    client.put(
        "/api/voice-input/local-asr/settings",
        json={"local_asr_binary_path": str(user_binary), "local_asr_model_path": str(user_model)},
    )

    response = client.post("/api/voice-input/local-asr/probe")

    assert response.status_code == 200
    assert response.json()["status"] == "local_asr_probe_succeeded"
    assert user_marker.exists() is True
    assert env_marker.exists() is False


def test_local_asr_transcribe_uses_resolved_binary_model_and_converter(monkeypatch, tmp_path):
    _clear_local_asr_env(monkeypatch)
    args_marker = tmp_path / "asr-args.json"
    converter_marker = tmp_path / "converter-args.json"
    binary = tmp_path / "user" / "bin" / "whisper-cli"
    converter = tmp_path / "user" / "bin" / "ffmpeg"
    model = tmp_path / "user" / "models" / "ggml-base.bin"
    _write_executable(
        binary,
        (
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path(r'{args_marker}').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
            "print('Margit 怎么打')\n"
        ),
    )
    _write_executable(
        converter,
        (
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path(r'{converter_marker}').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
            "pathlib.Path(sys.argv[-1]).write_bytes(b'RIFF fake WAVE')\n"
        ),
    )
    model.parent.mkdir(parents=True, exist_ok=True)
    model.write_text("model placeholder", encoding="utf-8")
    client.put(
        "/api/voice-input/local-asr/settings",
        json={
            "local_asr_binary_path": str(binary),
            "local_asr_model_path": str(model),
            "audio_converter_binary_path": str(converter),
        },
    )

    response = transcribe_local_asr_audio(b"fake webm audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)
    asr_args = json.loads(args_marker.read_text(encoding="utf-8"))
    converter_args = json.loads(converter_marker.read_text(encoding="utf-8"))

    assert response.status == "local_asr_transcription_succeeded"
    assert response.transcript == "Margit 怎么打"
    assert response.conversion_status == "audio_conversion_succeeded"
    assert response.safe_converter_name == "ffmpeg"
    assert asr_args[asr_args.index("-m") + 1] == str(model)
    assert asr_args[asr_args.index("-f") + 1].endswith("recording-converted.wav")
    assert converter_args[0:2] == ["-y", "-i"]
    assert converter_args[-1].endswith("recording-converted.wav")
    assert str(binary) not in payload
    assert str(model) not in payload
    assert str(converter) not in payload
