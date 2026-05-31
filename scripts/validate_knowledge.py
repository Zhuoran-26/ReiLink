#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Sequence


SUPPORTED_STATUSES = {"supported", "planned", "detected_only", "unsupported"}
CATALOG_REQUIRED_FIELDS = (
    "game_id",
    "display_name",
    "aliases",
    "enabled",
    "support_status",
    "knowledge_available",
)
MANIFEST_REQUIRED_FIELDS = (
    "game_id",
    "display_name",
    "version",
    "language",
    "status",
    "knowledge_files",
    "coverage",
    "last_updated",
)
SNIPPET_LIST_FIELDS = ("aliases", "tags", "topics", "intent_tags")


@dataclass
class KnowledgeValidationResult:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checked_games: int = 0
    supported_packs: int = 0
    total_snippets: int = 0

    @property
    def ok(self) -> bool:
        return not self.errors


def validate_knowledge(root: str | Path | None = None) -> KnowledgeValidationResult:
    repo_root = Path(root) if root is not None else Path(__file__).resolve().parents[1]
    repo_root = repo_root.resolve()
    result = KnowledgeValidationResult()

    catalog_path = repo_root / "data" / "knowledge" / "games" / "catalog.json"
    if not catalog_path.is_file():
        result.errors.append("catalog.json 文件不存在")
        return result

    catalog = _read_json(catalog_path, "catalog.json", result)
    if catalog is None:
        return result
    if not isinstance(catalog, dict):
        result.errors.append("catalog.json 顶层必须是 object")
        return result

    games = catalog.get("games")
    if not isinstance(games, list):
        result.errors.append("catalog.json: games 必须是 list")
        return result

    result.checked_games = len(games)
    seen_game_ids: set[str] = set()
    supported_games: list[tuple[str, dict[str, Any]]] = []

    for index, item in enumerate(games):
        if not isinstance(item, dict):
            result.errors.append(f"catalog.games[{index}]: 必须是 object")
            continue

        game_id = _clean_string(item.get("game_id"))
        label = game_id or f"catalog.games[{index}]"
        _validate_catalog_entry(item, label, seen_game_ids, supported_games, result)

    for label, game in supported_games:
        _validate_manifest(repo_root, game, label, result)
        _validate_snippets(repo_root, game, label, result)

    return result


def print_result(result: KnowledgeValidationResult) -> None:
    if result.ok:
        print("✅ 知识目录校验通过")
        print(f"已检查游戏：{result.checked_games}")
        print(f"已支持知识包：{result.supported_packs}")
        print(f"片段总数：{result.total_snippets}")
    else:
        print("❌ 知识目录校验失败")
        for error in result.errors:
            print(f"- {error}")

    for warning in result.warnings:
        print(f"⚠️ {warning}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validate ReiLink local game knowledge packs.")
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root. Defaults to the ReiLink checkout containing this script.",
    )
    args = parser.parse_args(argv)

    result = validate_knowledge(args.root)
    print_result(result)
    return 0 if result.ok else 1


def _validate_catalog_entry(
    item: dict[str, Any],
    label: str,
    seen_game_ids: set[str],
    supported_games: list[tuple[str, dict[str, Any]]],
    result: KnowledgeValidationResult,
) -> None:
    for field_name in CATALOG_REQUIRED_FIELDS:
        if field_name not in item:
            result.errors.append(f"{label}: {field_name} 缺失")

    game_id = _clean_string(item.get("game_id"))
    if not game_id and "game_id" in item:
        result.errors.append(f"{label}: game_id 为空")
    if game_id:
        if game_id in seen_game_ids:
            result.errors.append(f"{game_id}: game_id 重复")
        seen_game_ids.add(game_id)

    if "display_name" in item and not _clean_string(item.get("display_name")):
        result.errors.append(f"{label}: display_name 为空")

    if "aliases" in item and not isinstance(item.get("aliases"), list):
        result.errors.append(f"{label}: aliases 必须是 list")

    if "enabled" in item and not isinstance(item.get("enabled"), bool):
        result.errors.append(f"{label}: enabled 必须是 boolean")

    if "knowledge_available" in item and not isinstance(item.get("knowledge_available"), bool):
        result.errors.append(f"{label}: knowledge_available 必须是 boolean")

    support_status = _clean_string(item.get("support_status"))
    if support_status and support_status not in SUPPORTED_STATUSES:
        result.errors.append(f"{label}: support_status 不支持：{support_status}")

    if support_status == "supported":
        result.supported_packs += 1
        if item.get("knowledge_available") is not True:
            result.errors.append(f"{label}: knowledge_available 必须为 true")
        if not _clean_string(item.get("manifest_path")):
            result.errors.append(f"{label}: manifest_path 缺失")
        if not _clean_string(item.get("knowledge_path")):
            result.errors.append(f"{label}: knowledge_path 缺失")
        supported_games.append((label, item))
    elif support_status == "planned" and not _clean_string(item.get("knowledge_path")):
        result.warnings.append(f"planned 游戏暂未接入知识包：{label}")


def _validate_manifest(
    repo_root: Path,
    game: dict[str, Any],
    label: str,
    result: KnowledgeValidationResult,
) -> None:
    manifest_path_value = _clean_string(game.get("manifest_path"))
    if not manifest_path_value:
        return

    manifest_path = _resolve_repo_path(repo_root, manifest_path_value)
    if not manifest_path.is_file():
        result.errors.append(f"{label}: manifest 文件不存在：{manifest_path_value}")
        return

    manifest = _read_json(manifest_path, f"{label}: manifest", result)
    if manifest is None:
        return
    if not isinstance(manifest, dict):
        result.errors.append(f"{label}: manifest 顶层必须是 object")
        return

    for field_name in MANIFEST_REQUIRED_FIELDS:
        if field_name not in manifest:
            result.errors.append(f"{label}: manifest {field_name} 缺失")

    expected_game_id = _clean_string(game.get("game_id"))
    manifest_game_id = _clean_string(manifest.get("game_id"))
    if manifest_game_id and expected_game_id and manifest_game_id != expected_game_id:
        result.errors.append(f"{label}: manifest game_id 不一致：{manifest_game_id}")

    for field_name in ("game_id", "display_name", "version", "language", "status", "last_updated"):
        if field_name in manifest and not _clean_string(manifest.get(field_name)):
            result.errors.append(f"{label}: manifest {field_name} 为空")

    for field_name in ("knowledge_files", "coverage"):
        if field_name in manifest and not isinstance(manifest.get(field_name), list):
            result.errors.append(f"{label}: manifest {field_name} 必须是 list")


def _validate_snippets(
    repo_root: Path,
    game: dict[str, Any],
    label: str,
    result: KnowledgeValidationResult,
) -> None:
    snippets_path_value = _clean_string(game.get("knowledge_path"))
    if not snippets_path_value:
        return

    snippets_path = _resolve_repo_path(repo_root, snippets_path_value)
    if not snippets_path.is_file():
        result.errors.append(f"{label}: snippets 文件不存在：{snippets_path_value}")
        return

    snippets = _read_json(snippets_path, f"{label}: snippets", result)
    if snippets is None:
        return
    if not isinstance(snippets, list):
        result.errors.append(f"{label}: snippets 顶层必须是 list")
        return
    if not snippets:
        result.errors.append(f"{label}: snippet 数量必须大于 0")
        return

    result.total_snippets += len(snippets)
    seen_snippet_ids: set[str] = set()
    for index, item in enumerate(snippets):
        item_label = f"{label}: snippet[{index}]"
        if not isinstance(item, dict):
            result.errors.append(f"{item_label} 必须是 object")
            continue
        _validate_snippet(item, item_label, label, seen_snippet_ids, result)


def _validate_snippet(
    item: dict[str, Any],
    item_label: str,
    game_label: str,
    seen_snippet_ids: set[str],
    result: KnowledgeValidationResult,
) -> None:
    snippet_id = _clean_string(item.get("id"))
    if not snippet_id:
        result.errors.append(f"{item_label} id 缺失")
    elif snippet_id in seen_snippet_ids:
        result.errors.append(f"{game_label}: snippet id 重复：{snippet_id}")
    else:
        seen_snippet_ids.add(snippet_id)

    if not _clean_string(item.get("title")):
        result.errors.append(f"{item_label} title 为空")

    snippet_type = _first_present_text(item, ("type", "kind"))
    if not snippet_type:
        result.errors.append(f"{item_label} type 缺失")

    snippet_text = _snippet_text(item)
    if snippet_text is None:
        result.errors.append(f"{item_label} text 缺失")
    elif not snippet_text.strip():
        result.errors.append(f"{item_label} text 为空")

    for field_name in SNIPPET_LIST_FIELDS:
        if field_name in item and not isinstance(item.get(field_name), list):
            result.errors.append(f"{item_label} {field_name} 必须是 list")


def _read_json(path: Path, label: str, result: KnowledgeValidationResult) -> Any | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        result.errors.append(f"{label} JSON 格式错误：第 {exc.lineno} 行")
    except OSError as exc:
        result.errors.append(f"{label} 无法读取：{exc}")
    return None


def _resolve_repo_path(repo_root: Path, path_value: str) -> Path:
    path = Path(path_value)
    if path.is_absolute():
        return path
    return repo_root / path


def _clean_string(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _first_present_text(item: dict[str, Any], field_names: tuple[str, ...]) -> str | None:
    for field_name in field_names:
        if field_name in item:
            return _clean_string(item.get(field_name))
    return None


def _snippet_text(item: dict[str, Any]) -> str | None:
    for field_name in ("text", "summary", "content"):
        if field_name in item:
            return _clean_string(item.get(field_name))
    return None


if __name__ == "__main__":
    raise SystemExit(main())
