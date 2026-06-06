import base64
import json
import subprocess
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.modules.voice_input import local_asr_transcribe
from app.modules.voice_input.audio_conversion import CONVERTER_ENV
from app.modules.voice_input.local_asr_config import BINARY_ENV, MODEL_ENV
from app.modules.voice_input.local_asr_transcribe import (
    MAX_TRANSCRIPT_CHARS,
    transcribe_local_asr_audio,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def _clear_audio_converter_env(monkeypatch):
    monkeypatch.delenv(CONVERTER_ENV, raising=False)


def _clear_local_asr_env(monkeypatch):
    monkeypatch.delenv(BINARY_ENV, raising=False)
    monkeypatch.delenv(MODEL_ENV, raising=False)
    monkeypatch.delenv(CONVERTER_ENV, raising=False)


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


def _ready_audio_converter(monkeypatch, tmp_path: Path, script: str):
    converter = tmp_path / "tools" / "ffmpeg"
    converter.parent.mkdir(exist_ok=True)
    _write_executable(converter, script)
    monkeypatch.setenv(CONVERTER_ENV, str(converter))
    return converter


def _fake_stdout_script(stdout: str) -> str:
    return "#!/usr/bin/env python3\nimport sys\nsys.stdout.write(" + repr(stdout) + ")\n"


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
    assert data["conversion_status"] == "audio_conversion_needed"
    assert data["conversion_required"] is True
    assert data["converter_configured"] is False


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
        files={"audio": ("recording.wav", b"fake-wav-audio", "audio/wav")},
        data={"duration_ms": "3000", "language": "zh", "mime_type": "audio/wav"},
    )
    data = response.json()
    payload = json.dumps(data, ensure_ascii=False)
    args = json.loads(marker.read_text(encoding="utf-8"))

    assert response.status_code == 200
    assert data["status"] == "local_asr_transcription_succeeded"
    assert data["available"] is True
    assert data["transcript"] == "Margit 怎么打"
    assert data["transcript_char_count"] == len("Margit 怎么打")
    assert data["language"] == "zh"
    assert data["transcript_normalized_to_simplified"] is False
    assert data["duration_ms"] == 3000
    assert data["size_bytes"] == len(b"fake-wav-audio")
    assert data["mime_type"] == "audio/wav"
    assert data["audio_format"] == "audio/wav"
    assert data["conversion_status"] == "audio_conversion_not_needed"
    assert data["conversion_required"] is False
    assert data["converted_mime_type"] is None
    assert data["converter_configured"] is False
    assert data["safe_converter_name"] is None
    assert data["temporary_file_cleaned"] is True
    assert data["temporary_input_cleaned"] is True
    assert data["temporary_converted_cleaned"] is True
    assert data["binary_name"] == "whisper-cli"
    assert data["model_name"] == "ggml-base.bin"
    assert args[0:2] == ["-m", str(model)]
    assert args[2] == "-f"
    assert args[4:] == ["-nt", "-l", "zh"]
    assert str(binary) not in payload
    assert str(model) not in payload
    assert args[3] not in payload
    assert "fake-wav-audio" not in payload
    assert base64.b64encode(b"fake-wav-audio").decode("ascii") not in payload


@pytest.mark.parametrize(
    ("language", "expected_language"),
    [
        (None, "zh"),
        ("", "zh"),
        ("zh-CN", "zh"),
        ("zh_CN", "zh"),
        ("zh-Hans", "zh"),
        ("ja", "ja"),
        ("en;rm -rf /", "zh"),
        ("../../zh", "zh"),
    ],
)
def test_transcription_uses_safe_language_for_whisper_command(monkeypatch, tmp_path, language, expected_language):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: dict[str, object] = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="Margit 怎么打", stderr="raw stderr secret")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = transcribe_local_asr_audio(
        b"fake audio",
        "audio/wav",
        duration_ms=100,
        language=language,
        temp_root=str(tmp_path),
    )
    command = seen["command"]
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_succeeded"
    assert response.language == expected_language
    assert isinstance(command, list)
    assert command[0] == str(binary)
    assert command[0:2] != ["sh", "-c"]
    assert command[command.index("-m") + 1] == str(model)
    assert command[-2:] == ["-l", expected_language]
    if language:
        assert language not in command or language == expected_language
    assert seen["kwargs"].get("shell") is None
    assert "raw stderr secret" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


@pytest.mark.parametrize(
    ("stdout", "expected"),
    [
        ("Margit 怎么打\n", "Margit 怎么打"),
        ("[00:00:00.000 --> 00:00:02.000] Margit 怎么打\n", "Margit 怎么打"),
        (
            "[00:00:00.000 --> 00:00:01.200] Margit\n"
            "[00:00:01.200 --> 00:00:02.500] 怎么打\n",
            "Margit 怎么打",
        ),
        (
            "whisper_init_from_file_with_params_no_state: loading model\n"
            "system_info: n_threads = 4\n"
            "[00:00:00.000 --> 00:00:02.000] Margit 怎么打\n",
            "Margit 怎么打",
        ),
    ],
)
def test_transcription_parses_whisper_like_stdout_formats(monkeypatch, tmp_path, stdout, expected):
    _ready_local_asr(monkeypatch, tmp_path, _fake_stdout_script(stdout))

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_succeeded"
    assert response.transcript == expected


def test_transcription_ignores_srt_and_vtt_metadata_from_output_files(monkeypatch, tmp_path):
    _ready_local_asr(
        monkeypatch,
        tmp_path,
        (
            "#!/usr/bin/env python3\n"
            "from pathlib import Path\n"
            "audio = Path(__import__('sys').argv[__import__('sys').argv.index('-f') + 1])\n"
            "audio.with_suffix('.srt').write_text('1\\n00:00:00,000 --> 00:00:01,200\\nMargit\\n\\n2\\n00:00:01,200 --> 00:00:02,500\\n怎么打\\n', encoding='utf-8')\n"
            "audio.with_suffix('.vtt').write_text('WEBVTT\\n\\n00:00:02.500 --> 00:00:03.000\\n别贪刀\\n', encoding='utf-8')\n"
        ),
    )

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_succeeded"
    assert response.transcript == "Margit 怎么打 别贪刀"


@pytest.mark.parametrize(
    ("stdout", "expected", "normalized_to_simplified"),
    [
        ("  瑪爾基特怎麼打\n\n", "玛尔基特怎么打", True),
        ("我想問一下這個 Boss 怎麼處理\n", "我想问一下这个 Boss 怎么处理", True),
        ("Margit Boss 2 phase\n", "Margit Boss 2 phase", False),
        ("玛尔基特怎么打\n", "玛尔基特怎么打", False),
        ("Margit   Boss\n\n2\tphase\n", "Margit Boss 2 phase", False),
    ],
)
def test_transcription_normalizes_transcript_text(monkeypatch, tmp_path, stdout, expected, normalized_to_simplified):
    _ready_local_asr(monkeypatch, tmp_path, _fake_stdout_script(stdout))

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_succeeded"
    assert response.transcript == expected
    assert response.transcript_char_count == len(expected)
    assert response.transcript_normalized_to_simplified is normalized_to_simplified


def test_transcription_uses_subprocess_args_without_shell(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: dict[str, object] = {}

    def fake_run(command, **kwargs):
        seen["command"] = command
        seen["kwargs"] = kwargs
        return subprocess.CompletedProcess(command, 0, stdout="Margit 怎么打", stderr="raw stderr secret")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))
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


def test_webm_transcription_without_converter_does_not_run_asr(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'should not run'\n")

    def forbidden_run(*args, **kwargs):
        raise AssertionError("subprocess should not run without an audio converter")

    monkeypatch.setattr(subprocess, "run", forbidden_run)

    response = transcribe_local_asr_audio(b"fake webm audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_failed"
    assert response.display_message == "尚未配置音频转换工具"
    assert response.transcript == ""
    assert response.conversion_status == "audio_conversion_not_configured"
    assert response.conversion_required is True
    assert response.converter_configured is False
    assert response.converted_mime_type is None
    assert response.temporary_file_cleaned is True
    assert response.temporary_input_cleaned is True
    assert response.temporary_converted_cleaned is True
    assert "fake webm audio" not in payload
    assert str(tmp_path) not in payload


def test_webm_transcription_converts_to_wav_before_asr_without_shell(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    converter = _ready_audio_converter(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: list[tuple[list[str], dict[str, object]]] = []

    def fake_run(command, **kwargs):
        seen.append((command, kwargs))
        if command[0] == str(converter):
            Path(command[-1]).write_bytes(b"RIFF fake WAVE")
            return subprocess.CompletedProcess(command, 0, stdout=f"raw converter {converter}", stderr="converter stderr")
        return subprocess.CompletedProcess(command, 0, stdout="Margit 怎么打", stderr=f"raw asr {binary} {model}")

    monkeypatch.setattr(subprocess, "run", fake_run)

    response = transcribe_local_asr_audio(b"fake webm audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)
    converter_command, converter_kwargs = seen[0]
    asr_command, asr_kwargs = seen[1]

    assert response.status == "local_asr_transcription_succeeded"
    assert response.transcript == "Margit 怎么打"
    assert response.conversion_status == "audio_conversion_succeeded"
    assert response.conversion_required is True
    assert response.converted_mime_type == "audio/wav"
    assert response.converter_configured is True
    assert response.safe_converter_name == "ffmpeg"
    assert response.temporary_file_cleaned is True
    assert response.temporary_input_cleaned is True
    assert response.temporary_converted_cleaned is True
    assert converter_command[0] == str(converter)
    assert converter_command[1:3] == ["-y", "-i"]
    assert converter_command[4:8] == ["-ar", "16000", "-ac", "1"]
    assert converter_command[-1].endswith("recording-converted.wav")
    assert converter_kwargs.get("shell") is None
    assert asr_command[0] == str(binary)
    assert asr_command[asr_command.index("-f") + 1] == converter_command[-1]
    assert asr_kwargs.get("shell") is None
    assert converter_command[3] not in payload
    assert converter_command[-1] not in payload
    assert str(converter) not in payload
    assert str(binary) not in payload
    assert str(model) not in payload
    assert "raw converter" not in payload
    assert "raw asr" not in payload
    assert base64.b64encode(b"fake webm audio").decode("ascii") not in payload


def test_audio_conversion_timeout_is_safe_and_skips_asr(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'should not run'\n")
    converter = _ready_audio_converter(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: list[list[str]] = []

    def timeout_run(command, **kwargs):
        seen.append(command)
        raise subprocess.TimeoutExpired(command, 0.1, output=f"raw stdout {converter}", stderr="raw stderr")

    monkeypatch.setattr(subprocess, "run", timeout_run)

    response = transcribe_local_asr_audio(
        b"fake webm audio",
        "audio/webm",
        duration_ms=100,
        conversion_timeout_seconds=0.1,
        temp_root=str(tmp_path),
    )
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_timed_out"
    assert response.display_message == "音频格式转换超时"
    assert response.conversion_status == "audio_conversion_timed_out"
    assert response.transcript == ""
    assert len(seen) == 1
    assert seen[0][0] == str(converter)
    assert "raw stdout" not in payload
    assert "raw stderr" not in payload
    assert str(converter) not in payload
    assert str(tmp_path) not in payload


def test_audio_conversion_nonzero_returns_safe_failure_and_skips_asr(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\necho 'should not run'\n")
    converter = _ready_audio_converter(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")
    seen: list[list[str]] = []

    def failed_run(command, **kwargs):
        seen.append(command)
        return subprocess.CompletedProcess(command, 2, stdout=f"raw stdout {converter}", stderr="raw stderr")

    monkeypatch.setattr(subprocess, "run", failed_run)

    response = transcribe_local_asr_audio(b"fake webm audio", "audio/webm", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_failed"
    assert response.display_message == "音频格式转换失败"
    assert response.conversion_status == "audio_conversion_failed"
    assert response.transcript == ""
    assert len(seen) == 1
    assert seen[0][0] == str(converter)
    assert "raw stdout" not in payload
    assert "raw stderr" not in payload
    assert str(converter) not in payload
    assert str(tmp_path) not in payload


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

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

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

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_no_text"
    assert response.available is False
    assert response.display_message == "没有识别到可用文本"
    assert response.transcript == ""


def test_transcription_returns_no_text_for_empty_stdout(monkeypatch, tmp_path):
    _ready_local_asr(monkeypatch, tmp_path, _fake_stdout_script(""))

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))

    assert response.status == "local_asr_transcription_no_text"
    assert response.available is False
    assert response.display_message == "没有识别到可用文本"
    assert response.transcript == ""


def test_transcription_timeout_is_safe(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")

    def timeout_run(command, **kwargs):
        raise subprocess.TimeoutExpired(command, 0.1, output=f"raw stdout {binary}", stderr=f"raw stderr {model}")

    monkeypatch.setattr(subprocess, "run", timeout_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))
    payload = json.dumps(response.model_dump(), ensure_ascii=False)

    assert response.status == "local_asr_transcription_timed_out"
    assert response.available is False
    assert response.display_message == "本地语音识别超时，可以尝试更小模型或更短录音"
    assert "raw stdout" not in payload
    assert "raw stderr" not in payload
    assert str(binary) not in payload
    assert str(model) not in payload


def test_transcription_exit_nonzero_returns_failed_without_raw_output(monkeypatch, tmp_path):
    binary, model = _ready_local_asr(monkeypatch, tmp_path, "#!/bin/sh\nexit 99\n")

    def failed_run(command, **kwargs):
        return subprocess.CompletedProcess(command, 2, stdout=f"raw stdout secret {binary}", stderr=f"raw stderr secret {model}")

    monkeypatch.setattr(subprocess, "run", failed_run)

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))
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

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))
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

    response = transcribe_local_asr_audio(b"fake audio", "audio/wav", duration_ms=100, temp_root=str(tmp_path))
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
        files={"audio": ("recording.wav", b"fake-wav-audio", "audio/wav")},
        data={"duration_ms": "3000", "language": "zh"},
    )
    data = response.json()

    assert response.status_code == 200
    assert data["status"] == "local_asr_transcription_succeeded"
    assert client.get("/api/debug/prompt-preview?session_id=transcription-test").status_code == 200
    assert client.get("/api/debug/chat").status_code == 200
    assert client.get("/api/game/context").status_code == 200
    assert client.get("/api/memory/pending").status_code == 200
