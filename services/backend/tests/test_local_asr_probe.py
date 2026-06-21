import json
import subprocess

from fastapi.testclient import TestClient

from app.main import app
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV
from app.modules.voice_input.local_asr_probe import probe_local_asr_binary

client = TestClient(app)


def _clear_local_asr_env(monkeypatch):
    monkeypatch.delenv(BINARY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)


def _write_executable(path, text: str):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def test_local_asr_probe_not_ready_does_not_run_binary(monkeypatch, tmp_path):
    marker = tmp_path / "ran.txt"
    binary = tmp_path / "missing-binary"
    model = tmp_path / "ggml-base.bin"
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = probe_local_asr_binary()

    assert response.status == "local_asr_probe_not_ready"
    assert response.available is False
    assert marker.exists() is False


def test_local_asr_probe_succeeds_with_help(monkeypatch, tmp_path):
    marker = tmp_path / "args.txt"
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    _write_executable(
        binary,
        f"#!/bin/sh\nprintf '%s' \"$1\" > {marker}\necho 'Usage: whisper-cli --help'\nexit 0\n",
    )
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    # Keep the product default covered elsewhere; this success path only needs
    # enough room for occasional macOS process-start jitter in full-suite runs.
    response = probe_local_asr_binary(timeout_seconds=10)

    assert response.status == "local_asr_probe_succeeded"
    assert response.available is True
    assert response.binary_name == "whisper-cli"
    assert response.model_name == "ggml-base.bin"
    assert marker.read_text(encoding="utf-8") == "--help"


def test_local_asr_probe_falls_back_to_short_help(monkeypatch, tmp_path):
    marker = tmp_path / "args.txt"
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    _write_executable(
        binary,
        (
            f"#!/bin/sh\nprintf '%s\\n' \"$1\" >> {marker}\n"
            "if [ \"$1\" = \"-h\" ]; then echo 'options: help'; exit 0; fi\n"
            "echo 'unknown flag'\nexit 2\n"
        ),
    )
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = probe_local_asr_binary()

    assert response.status == "local_asr_probe_succeeded"
    assert marker.read_text(encoding="utf-8").splitlines() == ["--help", "-h"]


def test_local_asr_probe_times_out(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    _write_executable(binary, "#!/bin/sh\nsleep 5\n")
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = probe_local_asr_binary(timeout_seconds=0.1)

    assert response.status == "local_asr_probe_timed_out"
    assert response.available is False
    assert response.display_message == "本地语音识别程序启动超时"


def test_local_asr_probe_failed_without_help_like_output(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    _write_executable(binary, "#!/bin/sh\necho 'nope'\necho 'bad' >&2\nexit 2\n")
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = probe_local_asr_binary()
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_probe_failed"
    assert response.available is False
    assert "nope" not in payload
    assert "bad" not in payload


def test_local_asr_probe_error_is_safe(monkeypatch, tmp_path):
    binary = tmp_path / "secret-dir" / "whisper-cli"
    model = tmp_path / "models" / "ggml-base.bin"
    binary.parent.mkdir()
    model.parent.mkdir()
    _write_executable(binary, "#!/bin/sh\necho help\n")
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    def fail_run(*args, **kwargs):
        raise PermissionError(f"raw exception {binary}")

    monkeypatch.setattr(subprocess, "run", fail_run)

    response = probe_local_asr_binary()
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_probe_error"
    assert response.available is False
    assert response.binary_name == "whisper-cli"
    assert str(binary) not in payload
    assert str(model) not in payload
    assert "raw exception" not in payload
    assert "PermissionError" not in payload


def test_local_asr_probe_endpoint_is_safe(monkeypatch, tmp_path):
    binary = tmp_path / "private" / "whisper-cli"
    model = tmp_path / "models" / "ggml-base.bin"
    binary.parent.mkdir()
    model.parent.mkdir()
    _write_executable(
        binary,
        "#!/bin/sh\necho 'Usage: /Users/aragoto/private/whisper-cli'\necho 'stderr secret' >&2\nexit 0\n",
    )
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    response = client.post("/api/voice-input/local-asr/probe")
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)

    assert response.status_code == 200
    assert data["status"] == "local_asr_probe_succeeded"
    assert data["binary_name"] == "whisper-cli"
    assert data["model_name"] == "ggml-base.bin"
    assert str(binary) not in payload
    assert str(model) not in payload
    assert "Usage:" not in payload
    assert "stderr secret" not in payload
    assert "Traceback" not in payload


def test_local_asr_probe_does_not_create_audio_or_read_model(monkeypatch, tmp_path):
    binary = tmp_path / "whisper-cli"
    model = tmp_path / "ggml-base.bin"
    args_marker = tmp_path / "args.txt"
    _write_executable(
        binary,
        f"#!/bin/sh\nprintf '%s' \"$*\" > {args_marker}\necho 'Usage: whisper-cli'\n",
    )
    model.write_text("model placeholder", encoding="utf-8")
    model.chmod(0o000)
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))

    try:
        response = probe_local_asr_binary()
    finally:
        model.chmod(0o644)

    assert response.status == "local_asr_probe_succeeded"
    assert args_marker.read_text(encoding="utf-8") == "--help"
    assert not list(tmp_path.glob("*.wav"))
    assert not list(tmp_path.glob("*.mp3"))
    assert not list(tmp_path.glob("*.m4a"))
