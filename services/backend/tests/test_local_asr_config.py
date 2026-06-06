import json
import os

from fastapi.testclient import TestClient

from app.main import app
from app.modules.voice_input import local_asr_config
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV, get_local_asr_status

client = TestClient(app)


def _clear_local_asr_env(monkeypatch):
    monkeypatch.delenv(BINARY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)


def test_local_asr_not_configured(monkeypatch):
    _clear_local_asr_env(monkeypatch)

    status = get_local_asr_status()

    assert status.status == "local_asr_not_configured"
    assert status.available is False
    assert status.binary_configured is False
    assert status.model_configured is False
    assert status.safe_binary_name is None
    assert status.safe_model_name is None


def test_local_asr_binary_missing(monkeypatch, tmp_path):
    missing_binary = tmp_path / "private" / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(missing_binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    status = get_local_asr_status()
    payload = status.model_dump()

    assert status.status == "local_asr_binary_missing"
    assert status.binary_configured is True
    assert status.binary_present is False
    assert status.safe_binary_name == "whisper-cli"
    assert str(missing_binary) not in json.dumps(payload, ensure_ascii=False)
    assert str(model) not in json.dumps(payload, ensure_ascii=False)


def test_local_asr_binary_not_executable(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    binary.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    binary.chmod(0o644)
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    status = get_local_asr_status()

    assert status.status == "local_asr_binary_not_executable"
    assert status.binary_present is True
    assert status.binary_executable is False
    assert status.safe_binary_name == "whisper-cli"


def test_local_asr_model_missing(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli"
    missing_model = tmp_path / "models" / "ggml-base.bin"
    binary.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    binary.chmod(0o755)
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(missing_model))

    status = get_local_asr_status()

    assert status.status == "local_asr_model_missing"
    assert status.binary_executable is True
    assert status.model_present is False
    assert status.safe_model_name == "ggml-base.bin"


def test_local_asr_ready_does_not_run_binary(monkeypatch, tmp_path):
    marker = tmp_path / "ran.txt"
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    binary.write_text(f"#!/bin/sh\ntouch {marker}\n", encoding="utf-8")
    binary.chmod(0o755)
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    status = get_local_asr_status()

    assert status.status == "local_asr_ready"
    assert status.available is True
    assert marker.exists() is False


def test_local_asr_status_endpoint_is_safe(monkeypatch, tmp_path):
    binary = tmp_path / "secret-dir" / "whisper-cli"
    model = tmp_path / "models" / "ggml-base.bin"
    binary.parent.mkdir()
    model.parent.mkdir()
    binary.write_text("#!/bin/sh\nexit 99\n", encoding="utf-8")
    binary.chmod(0o755)
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = client.get("/api/voice-input/local-asr/status")
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)

    assert response.status_code == 200
    assert data["status"] == "local_asr_ready"
    assert data["safe_binary_name"] == "whisper-cli"
    assert data["safe_model_name"] == "ggml-base.bin"
    assert str(binary) not in payload
    assert str(model) not in payload
    assert os.environ[BINARY_ENV] not in payload
    assert os.environ[MODEL_ENV] not in payload
    assert "Traceback" not in payload
    assert "Exception" not in payload


def test_local_asr_detection_error_returns_safe_status(monkeypatch):
    def fail_detection():
        raise RuntimeError("raw env value /Users/aragoto/private/whisper-cli")

    monkeypatch.setattr(local_asr_config, "_detect_local_asr_status", fail_detection)

    status = get_local_asr_status()
    payload = json.dumps(status.model_dump(), ensure_ascii=False)

    assert status.status == "local_asr_not_configured"
    assert status.available is False
    assert status.display_message == "本地语音识别配置读取失败"
    assert "raw env value" not in payload
    assert "/Users/aragoto/private/whisper-cli" not in payload
    assert "RuntimeError" not in payload
