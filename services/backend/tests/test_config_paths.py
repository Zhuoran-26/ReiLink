from app.core import config
from app.modules.knowledge.catalog import GameCatalog


def test_reilink_data_dir_overrides_writable_data_path(tmp_path, monkeypatch):
    data_dir = tmp_path / "user-data"
    monkeypatch.setenv("REILINK_DATA_DIR", str(data_dir))

    assert config._resolve_data_dir(tmp_path / "repo") == data_dir


def test_reilink_resource_dir_overrides_read_only_resource_path(tmp_path, monkeypatch):
    data_dir = tmp_path / "user-data"
    resource_dir = tmp_path / "resources"
    monkeypatch.setenv("REILINK_RESOURCE_DIR", str(resource_dir))

    assert config._resolve_resource_dir(tmp_path / "repo", data_dir) == resource_dir


def test_resource_dir_prefers_repo_data_when_data_dir_is_user_writable(tmp_path, monkeypatch):
    repo_root = tmp_path / "repo"
    data_dir = tmp_path / "user-data"
    (repo_root / "data" / "personas").mkdir(parents=True)
    (repo_root / "data" / "personas" / "rei_like.json").write_text("{}\n", encoding="utf-8")
    monkeypatch.delenv("REILINK_RESOURCE_DIR", raising=False)

    assert config._resolve_resource_dir(repo_root, data_dir) == repo_root / "data"


def test_reilink_knowledge_dir_overrides_repo_knowledge_path(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "resources" / "knowledge" / "games"
    knowledge_dir.mkdir(parents=True)
    (knowledge_dir / "catalog.json").write_text('{"games":[]}\n', encoding="utf-8")
    monkeypatch.setenv("REILINK_KNOWLEDGE_DIR", str(knowledge_dir))

    assert config._resolve_knowledge_games_dir(tmp_path / "data") == knowledge_dir


def test_reilink_knowledge_dir_accepts_knowledge_root(tmp_path, monkeypatch):
    knowledge_root = tmp_path / "resources" / "knowledge"
    monkeypatch.setenv("REILINK_KNOWLEDGE_DIR", str(knowledge_root))

    assert config._resolve_knowledge_games_dir(tmp_path / "data") == knowledge_root / "games"


def test_config_path_fallback_uses_repo_data(tmp_path, monkeypatch):
    monkeypatch.delenv("REILINK_DATA_DIR", raising=False)
    monkeypatch.delenv("REILINK_KNOWLEDGE_DIR", raising=False)
    repo_root = tmp_path / "repo"

    data_dir = config._resolve_data_dir(repo_root)

    assert data_dir == repo_root / "data"
    assert config._resolve_knowledge_games_dir(data_dir) == repo_root / "data" / "knowledge" / "games"


def test_catalog_resolves_repo_style_paths_against_configured_knowledge_dir(tmp_path, monkeypatch):
    knowledge_dir = tmp_path / "bundled" / "knowledge" / "games"
    snippets_path = knowledge_dir / "elden_ring" / "snippets.json"
    manifest_path = knowledge_dir / "elden_ring" / "manifest.json"
    snippets_path.parent.mkdir(parents=True)
    snippets_path.write_text("[]\n", encoding="utf-8")
    manifest_path.write_text("{}\n", encoding="utf-8")
    monkeypatch.setattr("app.modules.knowledge.catalog.settings.knowledge_games_dir", knowledge_dir)
    monkeypatch.setattr("app.modules.knowledge.catalog.settings.repo_root", tmp_path / "repo")
    catalog = GameCatalog(knowledge_dir / "catalog.json")

    assert catalog.resolve_knowledge_path("data/knowledge/games/elden_ring/snippets.json") == snippets_path
    assert catalog.resolve_manifest_path("data/knowledge/games/elden_ring/manifest.json") == manifest_path
