from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Callable

from scripts.validate_knowledge import main, validate_knowledge


def test_valid_catalog_manifests_and_snippets_pass(tmp_path: Path):
    root = build_knowledge_repo(tmp_path)

    result = validate_knowledge(root)

    assert result.ok is True
    assert result.errors == []
    assert result.checked_games == 1
    assert result.supported_packs == 1
    assert result.total_snippets == 1


def test_duplicated_game_id_fails(tmp_path: Path):
    def mutate_catalog(catalog: dict[str, Any]) -> None:
        catalog["games"].append(dict(catalog["games"][0]))

    root = build_knowledge_repo(tmp_path, mutate_catalog=mutate_catalog)

    result = validate_knowledge(root)

    assert result.ok is False
    assert "sample_game: game_id 重复" in result.errors


def test_supported_game_missing_manifest_fails(tmp_path: Path):
    root = build_knowledge_repo(tmp_path, write_manifest=False)

    result = validate_knowledge(root)

    assert result.ok is False
    assert "sample_game: manifest 文件不存在：data/knowledge/games/sample_game/manifest.json" in result.errors


def test_supported_game_missing_snippets_fails(tmp_path: Path):
    root = build_knowledge_repo(tmp_path, write_snippets=False)

    result = validate_knowledge(root)

    assert result.ok is False
    assert "sample_game: snippets 文件不存在：data/knowledge/games/sample_game/snippets.json" in result.errors


def test_duplicate_snippet_id_fails(tmp_path: Path):
    snippets = [
        valid_snippet("opening"),
        valid_snippet("opening", title="重复片段"),
    ]
    root = build_knowledge_repo(tmp_path, snippets=snippets)

    result = validate_knowledge(root)

    assert result.ok is False
    assert "sample_game: snippet id 重复：opening" in result.errors


def test_snippet_empty_text_fails(tmp_path: Path):
    snippet = valid_snippet("opening")
    snippet["text"] = "  "
    root = build_knowledge_repo(tmp_path, snippets=[snippet])

    result = validate_knowledge(root)

    assert result.ok is False
    assert "sample_game: snippet[0] text 为空" in result.errors


def test_planned_game_without_snippets_warns_but_does_not_fail(tmp_path: Path):
    root = build_knowledge_repo(tmp_path, only_planned=True)

    result = validate_knowledge(root)

    assert result.ok is True
    assert result.errors == []
    assert result.warnings == ["planned 游戏暂未接入知识包：planned_game"]
    assert result.checked_games == 1
    assert result.supported_packs == 0
    assert result.total_snippets == 0


def test_cli_exit_code_matches_validation_result(tmp_path: Path):
    valid_root = build_knowledge_repo(tmp_path / "valid")
    invalid_root = build_knowledge_repo(tmp_path / "invalid", write_snippets=False)

    assert main(["--root", str(valid_root)]) == 0
    assert main(["--root", str(invalid_root)]) == 1


def build_knowledge_repo(
    root: Path,
    *,
    snippets: list[dict[str, Any]] | None = None,
    write_manifest: bool = True,
    write_snippets: bool = True,
    only_planned: bool = False,
    mutate_catalog: Callable[[dict[str, Any]], None] | None = None,
) -> Path:
    catalog_dir = root / "data" / "knowledge" / "games"
    game_dir = catalog_dir / "sample_game"
    game_dir.mkdir(parents=True, exist_ok=True)

    if only_planned:
        catalog: dict[str, Any] = {
            "games": [
                {
                    "game_id": "planned_game",
                    "display_name": "计划游戏",
                    "aliases": ["Planned Game"],
                    "enabled": True,
                    "support_status": "planned",
                    "knowledge_available": False,
                }
            ]
        }
    else:
        catalog = {
            "games": [
                {
                    "game_id": "sample_game",
                    "display_name": "样例游戏",
                    "aliases": ["Sample Game"],
                    "enabled": True,
                    "support_status": "supported",
                    "knowledge_available": True,
                    "manifest_path": "data/knowledge/games/sample_game/manifest.json",
                    "knowledge_path": "data/knowledge/games/sample_game/snippets.json",
                }
            ]
        }

    if mutate_catalog:
        mutate_catalog(catalog)

    write_json(catalog_dir / "catalog.json", catalog)

    if write_manifest:
        write_json(
            game_dir / "manifest.json",
            {
                "game_id": "sample_game",
                "display_name": "样例游戏",
                "version": "0.1.0",
                "language": "zh-CN",
                "status": "sample",
                "knowledge_files": ["snippets.json"],
                "coverage": ["boss"],
                "last_updated": "2026-06-01",
            },
        )

    if write_snippets:
        write_json(game_dir / "snippets.json", snippets or [valid_snippet("opening")])

    return root


def valid_snippet(snippet_id: str, title: str = "开场提示") -> dict[str, Any]:
    return {
        "id": snippet_id,
        "title": title,
        "type": "boss_strategy",
        "text": "先观察攻击节奏，再寻找安全反击窗口。",
        "aliases": ["Opening"],
        "tags": ["boss"],
    }


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
