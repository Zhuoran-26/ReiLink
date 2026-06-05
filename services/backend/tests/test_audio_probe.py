import base64
import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.modules.voice_input import audio_probe
from app.modules.voice_input.audio_probe import MAX_AUDIO_UPLOAD_BYTES, process_audio_probe

client = TestClient(app)


def test_audio_probe_endpoint_accepts_small_audio_and_cleans_temp_file(tmp_path, monkeypatch):
    created_paths: list[Path] = []
    original_mkdtemp = audio_probe.tempfile.mkdtemp

    def mkdtemp(*args, **kwargs):
        kwargs["dir"] = str(tmp_path)
        path = Path(original_mkdtemp(*args, **kwargs))
        created_paths.append(path)
        return str(path)

    monkeypatch.setattr(audio_probe.tempfile, "mkdtemp", mkdtemp)

    response = client.post(
        "/api/voice-input/audio/probe",
        content=b"fake-webm-audio",
        headers={"Content-Type": "audio/webm", "X-ReiLink-Audio-Duration-Ms": "3000"},
    )
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)

    assert response.status_code == 200
    assert data["status"] == "audio_probe_succeeded"
    assert data["available"] is True
    assert data["duration_ms"] == 3000
    assert data["size_bytes"] == len(b"fake-webm-audio")
    assert data["mime_type"] == "audio/webm"
    assert data["temporary_file_cleaned"] is True
    assert all(not path.exists() for path in created_paths)
    assert str(tmp_path) not in payload
    assert "fake-webm-audio" not in payload
    assert base64.b64encode(b"fake-webm-audio").decode("ascii") not in payload


def test_audio_probe_rejects_file_too_large():
    response = client.post(
        "/api/voice-input/audio/probe",
        content=b"",
        headers={"Content-Type": "audio/webm", "Content-Length": str(MAX_AUDIO_UPLOAD_BYTES + 1)},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "audio_probe_file_too_large"
    assert data["temporary_file_cleaned"] is True


def test_audio_probe_rejects_invalid_audio():
    response = client.post(
        "/api/voice-input/audio/probe",
        content=b"not audio",
        headers={"Content-Type": "text/plain"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "audio_probe_invalid_audio"
    assert data["temporary_file_cleaned"] is True
    assert "not audio" not in json.dumps(data, ensure_ascii=False)


def test_audio_probe_cleanup_failure_is_safe(monkeypatch, tmp_path):
    def fail_delete(path: Path):
        raise OSError(f"cannot delete {path}")

    monkeypatch.setattr(audio_probe, "_delete_temp_file", fail_delete)

    response = process_audio_probe(b"fake audio", "audio/webm", duration_ms=200, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "audio_probe_cleanup_failed"
    assert response.available is False
    assert response.display_message == "临时音频清理失败"
    assert response.temporary_file_cleaned is True
    assert str(tmp_path) not in payload
    assert "cannot delete" not in payload
    assert not list(tmp_path.iterdir())


def test_audio_probe_internal_error_is_safe(monkeypatch, tmp_path):
    def fail_mkdtemp(*args, **kwargs):
        raise RuntimeError(f"raw exception {tmp_path}")

    monkeypatch.setattr(audio_probe.tempfile, "mkdtemp", fail_mkdtemp)

    response = process_audio_probe(b"fake audio", "audio/webm", duration_ms=100)
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "audio_probe_error"
    assert response.available is False
    assert response.display_message == "录音测试失败"
    assert str(tmp_path) not in payload
    assert "raw exception" not in payload
    assert "RuntimeError" not in payload


def test_audio_probe_does_not_call_local_asr_or_whisper(monkeypatch, tmp_path):
    def forbidden_run(*args, **kwargs):
        raise AssertionError("subprocess should not run")

    monkeypatch.setattr("subprocess.run", forbidden_run)

    response = process_audio_probe(b"fake audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "audio_probe_succeeded"
    assert not list(tmp_path.iterdir())
