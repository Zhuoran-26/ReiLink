import base64
import json
import subprocess
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.voice_input import local_asr_transcribe
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV
from app.modules.voice_input.local_asr_transcribe import (
    MAX_TRANSCRIPT_CHARS,
    transcribe_local_asr_audio,
)

client = TestClient(app)


def _clear_local_asr_env(monkeypatch):
    monkeypatch.delenv(BINARY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)


def _write_executable(path: Path, text: str):
    path.write_text(text, encoding="utf-8")
    path.chmod(0o755)


def _ready_local_asr(monkeypatch, tmp_path: Path, script: str):
    binary = tmp_path / "private" / "whisper-cli"
    model = tmp_path / "models" / "ggml-base.bin"
    binary.parent.mkdir()
    model.parent.mkdir()
    _write_executable(binary, script)
    model.write_text("model placeholder", encoding="utf-8")
    monkeypatch.setenv(BINARY_ENV, str(binary))
    monkeypatch.setenv(MODEL_ENV, str(model))
    return binary, model


def test_transcription_not_ready_does_not_run_binary(monkeypatch):
    _clear_local_asr_env(monkeypatch)

    def forbidden_run(*args, **kwargs):
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr(subprocess, "run", forbidden_run)

    response = client.post(
        "/api/voice-input/local-asr/transcribe",
        files={"audio": ("recording.webm", b"fake-webm-audio", "audio/webm")},
        data={"duration_ms": "3000", "language": "zh"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "local_asr_transcription_not_ready"
    assert data["available"] is False
    assert data["transcript"] == ""


def test_transcription_succeeds_with_fake_binary_and_safe_command(monkeypatch, tmp_path):
    marker = tmp_path / "args.json"
    binary, model = _ready_local_asr(
        monkeypatch,
        tmp_path,
        (
            "#!/usr/bin/env python3\n"
            "import json, pathlib, sys\n"
            f"pathlib.Path(r'{marker}').write_text(json.dumps(sys.argv[1:]), encoding='utf-8')\n"
            "print('[00:00.000 --> 00:01.000] Margit 怎么打')\n"
        ),
    )

    response = client.post(
        "/api/voice-input/local-asr/transcribe",
        files={"audio": ("recording.webm", b"fake-webm-audio", "audio/webm")},
        data={"duration_ms": "3000", "language": "zh", "mime_type": "audio/webm"},
    )
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)
    args = json.loads(marker.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert data["status"] == "local_asr_transcription_succeeded"
    assert data["available"] is True
    assert data["transcript"] == "Margit 怎么打"
    assert data["transcript_char_count"] == len("Margit 怎么打")
    assert data["duration_ms"] == 3000
    assert data["size_bytes"] == len(b"fake-webm-audio")
    assert data["mime_type"] == "audio/webm"
    assert data["temporary_file_cleaned"] is True
    assert data["binary_name"] == "whisper-cli"
    assert data["model_name"] == "ggml-base.bin"
    assert args[0:2] == ["-m", str(model)]
    assert args[2] == "-f"
    assert args[4:] == ["-nt", "-l", "zh"]
    assert str(binary) not in payload
    assert str(model) not in payload
    assert args[3] not in payload
    assert "fake-webm-audio" not in payload
    assert base64.b64encode(b"fake-webm-audio").decode("ascii") not in payload


def test_transcription_uses_subprocess_args_without_shell(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: dict[str, object] = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="Margit 怎么打", stderr="raw stderr secret")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_succeeded"
    assert isinstance(seen["command"], list)
    assert seen["command"][0] == str(binary)
    assert "-m" in seen["command"]
    assert str(model) in seen["command"]
    assert seen["kwargs"].get("shell") is None
    assert "raw stderr secret" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


def test_transcription_cleans_and_truncates_transcript(monkeypatch, tmp_path):
    long_text = "打" * (MAX_TRANSCRIPT_CHARS + 80)
    _ready_local_asr(
        monkeypatch,
        tmp_path,
        (
            "#!/usr/bin/env python3\n"
            "print('whisper_init_from_file: private log')\n"
            "print('[00:00.000 --> 00:01.000] " + long_text + "')\n"
        ),
    )

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_succeeded"
    assert len(response.transcript) == MAX_TRANSCRIPT_CHARS
    assert response.transcript == "打" * MAX_TRANSCRIPT_CHARS
    assert "whisper_init" not in response.transcript
    assert "-->" not in response.transcript


def test_transcription_returns_no_text_for_empty_or_log_output(monkeypatch, tmp_path):
    _ready_local_asr(
        monkeypatch,
        tmp_path,
        "#!/bin/sh\necho 'whisper_init_from_file: private log'\necho 'total time = 1 ms'\n",
    )

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_no_text"
    assert response.available is False
    assert response.transcript == ""


def test_transcription_timeout_is_safe(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")

    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 0.1, output=f"raw stdout {binary}", stderr=f"raw stderr {model}")

    monkeypatch.setattr(subprocess, "run", timeout_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_timed_out"
    assert response.available is False
    assert "raw stdout" not in payload
    assert "raw stderr" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


def test_transcription_exit_nonzero_returns_failed_without_raw_output(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")

    def failed_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, stdout=f"raw stdout secret {binary}", stderr=f"raw stderr secret {model}")

    monkeypatch.setattr(subprocess, "run", failed_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_failed"
    assert response.transcript == ""
    assert "raw stdout secret" not in payload
    assert "raw stderr secret" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


def test_transcription_os_error_returns_safe_error(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")

    def os_error_run(*args, **kwargs):
        raise PermissionError(f"raw exception {binary} {model}")

    monkeypatch.setattr(subprocess, "run", os_error_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_error"
    assert response.display_message == "本地语音识别程序无法启动"
    assert "raw exception" not in payload
    assert "PermissionError" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


def test_transcription_cleanup_failure_returns_safe_status(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'Margit 怎么打'\n")

    def fail_delete(path: Path):
        raise OSError(f"cannot delete {path}")

    monkeypatch.setattr(local_asr_transcribe, "_delete_temp_tree", fail_delete)

    response = transcribe_local_asr_audio(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_cleanup_failed"
    assert response.available is False
    assert response.transcript == ""
    assert "cannot delete" not in payload
    assert str(tmp_path) not in payload
    assert not list(tmp_path.glob("reilink-local-asr-*"))


def test_transcription_rejects_invalid_audio_without_audio_content(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'Margit 怎么打'\n")

    response = transcribe_local_asr_audio(b"not audio", "text/plain", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_failed"
    assert response.display_message == "录音数据无效"
    assert response.temporary_file_cleaned is True
    assert "not audio" not in payload
    assert base64.b64encode(b"not audio").decode("ascii") not in payload


def test_transcription_endpoint_does_not_touch_chat_memory_or_context_before_send(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'Margit 怎么打'\n")

    response = client.post(
        "/api/voice-input/local-asr/transcribe",
        files={"audio": ("recording.webm", b"fake-webm-audio", "audio/webm")},
        data={"duration_ms": "3000", "language": "zh"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "local_asr_transcription_succeeded"
    assert client.get("/api/debug/prompt-preview?session_id=transcription-test").status_code == 200
    assert client.get("/api/debug/chat").status_code == 200
    assert client.get("/api/game/context").status_code == 200
    assert client.get("/api/memory/pending").status_code == 200
