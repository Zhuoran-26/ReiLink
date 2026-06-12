import json
from pathlib import Path

from app.core.config import settings
from app.modules.persona_engine.persona_pack import (
    MARKDOWN_FILES,
    MAX_PERSONA_PACK_PROMPT_CHARS,
    PROMPT_SECTION_KEYS,
    PersonaPackLoader,
)


FORBIDDEN_EXTERNAL_IDENTITY_TERMS = (
    "Evangelion",
    "Rei Ayanami",
    "Ayanami",
    "绫波",
    "綾波",
    "NERV",
    "EVA",
    "永雏塔菲",
    "taffy-skill",
)


def _write_pack(root: Path, *, version_text: str | None = None, skip: set[str] | None = None) -> Path:
    pack_dir = root / "personas" / "rei"
    pack_dir.mkdir(parents=True)
    skip = skip or set()
    if version_text is None:
        version_text = json.dumps(
            {
                "id": "rei",
                "name": "Rei",
                "version": "1.0.0",
                "language": "zh-CN",
                "description": "test pack",
                "created_for": "ReiLink",
                "original_character": True,
            },
            ensure_ascii=False,
        )
    (pack_dir / "version.json").write_text(version_text, encoding="utf-8")
    for key, filename, title in MARKDOWN_FILES:
        if key in skip:
            continue
        (pack_dir / filename).write_text(f"# {title}\n\n{key} content.\n", encoding="utf-8")
    return pack_dir


def test_persona_pack_loader_loads_complete_pack(tmp_path: Path):
    _write_pack(tmp_path)

    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")

    assert pack.enabled is True
    assert pack.status == "loaded"
    assert pack.version == "1.0.0"
    assert pack.name == "Rei"
    assert pack.language == "zh-CN"
    assert set(pack.sections) == {key for key, _filename, _title in MARKDOWN_FILES}
    assert pack.missing_sections == []
    summary = pack.as_safe_summary()
    assert summary["raw_content_omitted"] is True
    assert summary["path_omitted"] is True
    assert summary["persona_section_truncated"] is False
    assert set(summary["injected_sections"]) == set(PROMPT_SECTION_KEYS)


def test_persona_pack_loader_prefers_bundled_resource_dir(tmp_path: Path):
    repo_pack = _write_pack(tmp_path / "repo")
    resource_root = tmp_path / "resources"
    resource_pack = _write_pack(resource_root)
    (repo_pack / "voice.md").write_text("# Voice\n\nrepo voice.\n", encoding="utf-8")
    (resource_pack / "voice.md").write_text("# Voice\n\nbundled voice.\n", encoding="utf-8")

    pack = PersonaPackLoader(repo_root=tmp_path / "repo", resource_dir=resource_root).load("rei")

    assert "bundled voice" in pack.sections["voice"]
    assert "repo voice" not in pack.sections["voice"]


def test_persona_pack_loader_missing_noncritical_markdown_fails_soft(tmp_path: Path):
    _write_pack(tmp_path, skip={"anti_examples"})

    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")

    assert pack.enabled is True
    assert pack.status == "partial"
    assert "anti_examples" in pack.missing_sections
    assert "persona" in pack.sections


def test_persona_pack_loader_invalid_version_json_fails_soft(tmp_path: Path):
    _write_pack(tmp_path, version_text="{invalid json")

    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")

    assert pack.enabled is True
    assert pack.status == "loaded_with_warnings"
    assert pack.version == "unknown"
    assert pack.errors == ["version_json_invalid"]
    assert "persona" in pack.as_prompt_section()


def test_persona_pack_loader_missing_pack_falls_back_without_path_leak(tmp_path: Path):
    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")

    assert pack.enabled is False
    assert pack.status == "missing"
    summary_text = json.dumps(pack.as_safe_summary(), ensure_ascii=False)
    assert "/Users/" not in summary_text
    assert str(tmp_path) not in summary_text
    assert "raw_content_omitted" in summary_text


def test_persona_pack_prompt_section_sanitizes_sensitive_text(tmp_path: Path):
    pack_dir = _write_pack(tmp_path)
    (pack_dir / "boundaries.md").write_text(
        "# Boundaries\n\nDEEPSEEK_API_KEY=secret /Users/alice/private/.env raw prompt.\n",
        encoding="utf-8",
    )

    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")
    prompt_section = pack.as_prompt_section()

    assert "DEEPSEEK_API_KEY=secret" not in prompt_section
    assert "/Users/" not in prompt_section
    assert ".env" not in prompt_section
    assert "<redacted>" in prompt_section
    assert "<local-path>" in prompt_section


def test_persona_pack_prompt_has_budget_and_selects_examples(tmp_path: Path):
    pack_dir = _write_pack(tmp_path)
    (pack_dir / "persona.md").write_text("# Persona\n\n" + ("quiet companion. " * 300), encoding="utf-8")
    (pack_dir / "examples.md").write_text(
        "# Examples\n\nThese are style examples, not scripts.\n\n"
        + "\n\n".join(f"- Player {index}: example\n  Rei: reply" for index in range(1, 7)),
        encoding="utf-8",
    )
    (pack_dir / "anti_examples.md").write_text(
        "# Anti Examples\n\n"
        + "\n".join(f"- Bad {index}: do not copy" for index in range(1, 6)),
        encoding="utf-8",
    )

    pack = PersonaPackLoader(repo_root=tmp_path, resource_dir=tmp_path / "missing").load("rei")
    prompt_section = pack.as_prompt_section()
    summary = pack.as_safe_summary()

    assert len(prompt_section) <= MAX_PERSONA_PACK_PROMPT_CHARS
    assert summary["persona_section_truncated"] is True
    assert "persona" in summary["truncated_sections"]
    assert "examples" in summary["truncated_sections"]
    assert "anti_examples" in summary["truncated_sections"]
    assert "Player 1" in prompt_section
    assert "Player 3" in prompt_section
    assert "Player 4" not in prompt_section
    assert "Bad 1" in prompt_section
    assert "Bad 3" in prompt_section
    assert "Bad 4" not in prompt_section


def test_persona_pack_loads_v11_calibration_sections_from_repo():
    pack = PersonaPackLoader(repo_root=settings.repo_root, resource_dir=settings.repo_root / "missing").load("rei")

    assert pack.version == "1.1.0"
    assert "style_calibration" in pack.sections
    assert "response_patterns" in pack.sections
    assert "style_calibration" in pack.as_safe_summary()["injected_sections"]
    assert "response_patterns" in pack.as_safe_summary()["injected_sections"]
    prompt_section = pack.as_prompt_section()
    assert "表达通道很窄" in prompt_section
    assert "不是没有情绪" in prompt_section
    assert "不要把“也”“还”“嗯”之类变成新口癖" in prompt_section
    assert "连续相似问题" in prompt_section


def test_persona_pack_runtime_sections_are_chinese_first():
    pack = PersonaPackLoader(repo_root=settings.repo_root, resource_dir=settings.repo_root / "missing").load("rei")

    for key in PROMPT_SECTION_KEYS:
        section = pack.sections[key]
        chinese_chars = _count_chinese_chars(section)
        latin_chars = sum(1 for char in section if ("a" <= char.lower() <= "z"))
        assert chinese_chars > 20, key
        assert chinese_chars >= latin_chars, key


def test_version_json_keys_remain_compatible():
    metadata = json.loads((settings.repo_root / "personas" / "rei" / "version.json").read_text(encoding="utf-8"))

    assert {
        "id",
        "name",
        "version",
        "language",
        "description",
        "created_for",
        "original_character",
    } <= set(metadata)
    assert metadata["version"] == "1.1.0"
    assert metadata["language"] == "zh-CN"


def test_persona_pack_files_and_prompt_do_not_contain_forbidden_external_identity_terms():
    pack_dir = settings.repo_root / "personas" / "rei"
    file_text = "\n".join(path.read_text(encoding="utf-8") for path in sorted(pack_dir.iterdir()) if path.is_file())
    prompt_section = PersonaPackLoader(repo_root=settings.repo_root, resource_dir=settings.repo_root / "missing").load(
        "rei"
    ).as_prompt_section()

    for term in FORBIDDEN_EXTERNAL_IDENTITY_TERMS:
        assert term.lower() not in file_text.lower()
        assert term.lower() not in prompt_section.lower()


def _count_chinese_chars(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")
