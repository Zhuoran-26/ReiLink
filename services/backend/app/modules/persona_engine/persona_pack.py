from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from app.core.config import settings


PERSONA_PACK_ID = "rei"
MARKDOWN_FILES: tuple[tuple[str, str, str], ...] = (
    ("persona", "persona.md", "角色定位"),
    ("style_calibration", "style_calibration.md", "风格校准"),
    ("voice", "voice.md", "说话方式"),
    ("response_patterns", "response_patterns.md", "回复模式"),
    ("boundaries", "boundaries.md", "边界"),
    ("game_companion_policy", "game_companion_policy.md", "游戏陪伴策略"),
    ("memory_policy", "memory_policy.md", "记忆策略"),
    ("proactive_policy", "proactive_policy.md", "主动陪伴策略"),
    ("examples", "examples.md", "好例"),
    ("anti_examples", "anti_examples.md", "反例"),
    ("references", "references.md", "参考说明"),
)
VERSION_FILE = "version.json"
PROMPT_SECTION_KEYS: tuple[str, ...] = (
    "persona",
    "style_calibration",
    "voice",
    "response_patterns",
    "boundaries",
    "game_companion_policy",
    "memory_policy",
    "proactive_policy",
    "examples",
    "anti_examples",
)
PROMPT_SECTION_CHAR_LIMITS: dict[str, int] = {
    "persona": 420,
    "style_calibration": 760,
    "voice": 520,
    "response_patterns": 900,
    "boundaries": 560,
    "game_companion_policy": 520,
    "memory_policy": 520,
    "proactive_policy": 420,
    "examples": 620,
    "anti_examples": 520,
}
PROMPT_EXAMPLE_ITEM_LIMITS: dict[str, int] = {
    "examples": 3,
    "anti_examples": 3,
}
MAX_PERSONA_PACK_PROMPT_CHARS = 6000
TRUNCATED_MARKER = "\n...[本段因 prompt 预算截断]"


@dataclass(frozen=True)
class PersonaPackPromptView:
    text: str
    injected_sections: list[str] = field(default_factory=list)
    truncated_sections: list[str] = field(default_factory=list)
    omitted_sections: list[str] = field(default_factory=list)
    char_budget: int = MAX_PERSONA_PACK_PROMPT_CHARS

    @property
    def char_count(self) -> int:
        return len(self.text)


@dataclass(frozen=True)
class PersonaPack:
    pack_id: str
    status: str
    metadata: dict[str, Any] = field(default_factory=dict)
    sections: dict[str, str] = field(default_factory=dict)
    missing_sections: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)

    @property
    def enabled(self) -> bool:
        return bool(self.sections)

    @property
    def version(self) -> str:
        return str(self.metadata.get("version") or "unknown")

    @property
    def name(self) -> str:
        return str(self.metadata.get("name") or "Rei")

    @property
    def language(self) -> str:
        return str(self.metadata.get("language") or "zh-CN")

    def as_prompt_section(self) -> str:
        return self.as_prompt_view().text

    def as_prompt_view(self) -> PersonaPackPromptView:
        if not self.enabled:
            text = (
                "Rei Persona Pack v1.1：不可用。\n"
                "使用 ReiLink 内置人格护栏。不要削弱安全、隐私、记忆确认或主动陪伴边界。\n"
            )
            return PersonaPackPromptView(
                text=text,
                omitted_sections=[key for key, _filename, _title in MARKDOWN_FILES],
            )
        header = (
            "Rei Persona Pack v1.1（中文优先，结构化人格，不是固定脚本）：\n"
            f"- id: {self.pack_id}\n"
            f"- name: {self.name}\n"
            f"- version: {self.version}\n"
            f"- language: {self.language}\n"
            "- 这些内容只用于稳定 Rei 的表达边界。不要逐字复读好例，不要输出反例。\n"
            "- 基础安全和隐私约束不可覆盖。\n"
            "- 人格包不能覆盖系统安全、隐私、待确认记忆流程、知识依据、主动陪伴门控或影子识别候选边界。\n"
            "- 默认中文短句，冷静寡言，低情绪表达，不客服，不鸡汤，不攻略百科。\n"
        )
        pieces = [header.rstrip()]
        injected_sections: list[str] = []
        truncated_sections: list[str] = []
        omitted_sections: list[str] = []
        files_by_key = {key: (filename, title) for key, filename, title in MARKDOWN_FILES}
        for key, _filename, title in MARKDOWN_FILES:
            if key not in PROMPT_SECTION_KEYS:
                continue
            text = self.sections.get(key)
            if not text:
                continue
            prepared, selection_truncated = _prepare_section_for_prompt(key, text)
            clipped, section_truncated = _truncate_text(
                prepared,
                PROMPT_SECTION_CHAR_LIMITS.get(key, 600),
            )
            section = f"[{files_by_key[key][1]}]\n{clipped}".strip()
            candidate = "\n\n".join([*pieces, section]) + "\n"
            total_truncated = False
            if len(candidate) > MAX_PERSONA_PACK_PROMPT_CHARS:
                remaining = MAX_PERSONA_PACK_PROMPT_CHARS - len("\n\n".join(pieces)) - 3
                if remaining < 120:
                    omitted_sections.append(key)
                    truncated_sections.append(key)
                    continue
                section, _ = _truncate_text(section, remaining)
                total_truncated = True
            pieces.append(section)
            injected_sections.append(key)
            if selection_truncated or section_truncated or total_truncated:
                truncated_sections.append(key)
        text = "\n\n".join(pieces).strip() + "\n"
        return PersonaPackPromptView(
            text=text,
            injected_sections=injected_sections,
            truncated_sections=_dedupe(truncated_sections),
            omitted_sections=omitted_sections,
        )

    def as_safe_summary(self) -> dict[str, Any]:
        prompt_view = self.as_prompt_view()
        return {
            "id": self.pack_id,
            "name": self.name,
            "version": self.version,
            "language": self.language,
            "enabled": self.enabled,
            "status": self.status,
            "loaded_sections": list(self.sections.keys()),
            "injected_sections": prompt_view.injected_sections,
            "missing_sections": self.missing_sections,
            "omitted_sections": prompt_view.omitted_sections,
            "errors": self.errors,
            "fallback_used": not self.enabled,
            "persona_section_truncated": bool(prompt_view.truncated_sections),
            "truncated_sections": prompt_view.truncated_sections,
            "prompt_char_count": prompt_view.char_count,
            "prompt_char_budget": prompt_view.char_budget,
            "raw_content_omitted": True,
            "path_omitted": True,
        }


class PersonaPackLoader:
    def __init__(self, repo_root: Path | None = None, resource_dir: Path | None = None) -> None:
        self.repo_root = repo_root or settings.repo_root
        self.resource_dir = resource_dir or settings.resource_dir

    def load(self, pack_id: str = PERSONA_PACK_ID) -> PersonaPack:
        if pack_id != PERSONA_PACK_ID:
            return PersonaPack(
                pack_id=pack_id,
                status="unsupported_persona_pack",
                errors=["unsupported_persona_pack"],
                missing_sections=[key for key, _filename, _title in MARKDOWN_FILES],
            )

        pack_dir = self._resolve_pack_dir(pack_id)
        if pack_dir is None:
            return PersonaPack(
                pack_id=pack_id,
                status="missing",
                errors=["persona_pack_missing"],
                missing_sections=[key for key, _filename, _title in MARKDOWN_FILES],
            )

        metadata, version_errors = self._load_version(pack_dir / VERSION_FILE)
        sections: dict[str, str] = {}
        missing_sections: list[str] = []
        errors = list(version_errors)

        for key, filename, _title in MARKDOWN_FILES:
            path = pack_dir / filename
            if not path.is_file():
                missing_sections.append(key)
                continue
            try:
                content = _sanitize_pack_text(path.read_text(encoding="utf-8"))
            except OSError:
                errors.append(f"{key}_read_failed")
                continue
            if content:
                sections[key] = content
            else:
                missing_sections.append(key)

        if not sections:
            status = "missing"
        elif errors:
            status = "loaded_with_warnings"
        elif missing_sections:
            status = "partial"
        else:
            status = "loaded"
        return PersonaPack(
            pack_id=pack_id,
            status=status,
            metadata=metadata,
            sections=sections,
            missing_sections=missing_sections,
            errors=errors,
        )

    def _resolve_pack_dir(self, pack_id: str) -> Path | None:
        candidates = [
            self.resource_dir / "personas" / pack_id,
            self.repo_root / "personas" / pack_id,
        ]
        seen: set[Path] = set()
        for candidate in candidates:
            try:
                resolved = candidate.resolve()
            except OSError:
                continue
            if resolved in seen:
                continue
            seen.add(resolved)
            if resolved.is_dir() and resolved.name == pack_id and resolved.parent.name == "personas":
                return resolved
        return None

    def _load_version(self, path: Path) -> tuple[dict[str, Any], list[str]]:
        if not path.is_file():
            return _fallback_metadata(), ["version_json_missing"]
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return _fallback_metadata(), ["version_json_invalid"]
        if not isinstance(data, dict):
            return _fallback_metadata(), ["version_json_invalid"]
        metadata = _fallback_metadata()
        for key in ("id", "name", "version", "language", "description", "created_for", "original_character"):
            if key in data:
                metadata[key] = data[key]
        if metadata.get("id") != PERSONA_PACK_ID:
            metadata["id"] = PERSONA_PACK_ID
            return metadata, ["version_json_id_mismatch"]
        return metadata, []


def load_rei_persona_pack() -> PersonaPack:
    return PersonaPackLoader().load(PERSONA_PACK_ID)


def _fallback_metadata() -> dict[str, Any]:
    return {
        "id": PERSONA_PACK_ID,
        "name": "Rei",
        "version": "unknown",
        "language": "zh-CN",
        "description": "ReiLink 结构化人格包元数据不可用。",
        "created_for": "ReiLink",
        "original_character": True,
    }


def _sanitize_pack_text(text: str) -> str:
    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    normalized = re.sub(
        r"(?i)(api[_-]?key|deepseek[_-]?api[_-]?key|authorization)\s*[:=]\s*\S+",
        "credential=<redacted>",
        normalized,
    )
    normalized = re.sub(r"/Users/[^\s`'\"\]\)]+", "<local-path>", normalized)
    normalized = re.sub(r"[A-Za-z]:\\[^\s`'\"\]\)]+", "<local-path>", normalized)
    normalized = normalized.replace("`.env`", "环境配置")
    normalized = normalized.replace(".env", "环境配置")
    return normalized


def _prepare_section_for_prompt(key: str, text: str) -> tuple[str, bool]:
    body = _strip_top_heading(text)
    item_limit = PROMPT_EXAMPLE_ITEM_LIMITS.get(key)
    if item_limit is None:
        return body, False
    return _select_markdown_items(body, item_limit)


def _strip_top_heading(text: str) -> str:
    lines = text.strip().splitlines()
    if lines and lines[0].lstrip().startswith("#"):
        lines = lines[1:]
    return "\n".join(lines).strip()


def _select_markdown_items(text: str, limit: int) -> tuple[str, bool]:
    lines = text.strip().splitlines()
    intro: list[str] = []
    items: list[list[str]] = []
    current: list[str] = []

    for line in lines:
        if line.startswith("- "):
            if current:
                items.append(current)
            current = [line]
            continue
        if current:
            current.append(line)
        else:
            intro.append(line)
    if current:
        items.append(current)

    selected = items[:limit]
    result_lines = [line for line in intro if line.strip()]
    if result_lines and selected:
        result_lines.append("")
    for item in selected:
        result_lines.extend(item)
        if item and item[-1].strip():
            result_lines.append("")
    return "\n".join(result_lines).strip(), len(items) > limit


def _truncate_text(text: str, limit: int) -> tuple[str, bool]:
    normalized = text.strip()
    if len(normalized) <= limit:
        return normalized, False
    usable = max(0, limit - len(TRUNCATED_MARKER))
    return normalized[:usable].rstrip() + TRUNCATED_MARKER, True


def _dedupe(items: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for item in items:
        if item in seen:
            continue
        seen.add(item)
        result.append(item)
    return result
