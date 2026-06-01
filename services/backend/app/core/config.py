import json
import os
import sys
from pathlib import Path


SOURCE_BACKEND_DIR = Path(__file__).resolve().parents[2]


def _walk_for_repo_root(start: Path) -> Path | None:
    current = start.resolve()
    if current.is_file():
        current = current.parent
    while True:
        if (current / "data" / "knowledge" / "games" / "catalog.json").is_file():
            return current
        parent = current.parent
        if parent == current:
            return None
        current = parent


def _resolve_repo_root() -> Path:
    candidates: list[Path] = []
    for env_key in ("REILINK_PROJECT_ROOT", "REILINK_REPO_ROOT"):
        value = os.getenv(env_key)
        if value:
            candidates.append(Path(value))
    if getattr(sys, "frozen", False):
        candidates.append(Path(sys.executable))
    candidates.extend([Path.cwd(), SOURCE_BACKEND_DIR])
    for candidate in candidates:
        repo_root = _walk_for_repo_root(candidate)
        if repo_root:
            return repo_root
    return SOURCE_BACKEND_DIR.parents[1]


def _resolve_backend_dir(repo_root: Path) -> Path:
    source_backend = repo_root / "services" / "backend"
    if (source_backend / "app").is_dir():
        return source_backend
    return SOURCE_BACKEND_DIR


def _resolve_data_dir(repo_root: Path) -> Path:
    return Path(os.getenv("REILINK_DATA_DIR", repo_root / "data"))


def _resolve_resource_dir(repo_root: Path, data_dir: Path) -> Path:
    configured = os.getenv("REILINK_RESOURCE_DIR")
    if configured:
        return Path(configured)
    repo_data_dir = repo_root / "data"
    if (repo_data_dir / "personas" / "rei_like.json").is_file():
        return repo_data_dir
    return data_dir


def _resolve_knowledge_games_dir(data_dir: Path) -> Path:
    configured = os.getenv("REILINK_KNOWLEDGE_DIR")
    if not configured:
        return data_dir / "knowledge" / "games"
    path = Path(configured)
    if path.name == "games" or (path / "catalog.json").is_file():
        return path
    return path / "games"


REPO_ROOT = _resolve_repo_root()
BACKEND_DIR = _resolve_backend_dir(REPO_ROOT)
ENV_FILE = Path(os.getenv("REILINK_BACKEND_ENV", BACKEND_DIR / ".env"))
DATA_DIR = _resolve_data_dir(REPO_ROOT)
KNOWLEDGE_GAMES_DIR = _resolve_knowledge_games_dir(DATA_DIR)


def _load_env_file(path: Path) -> bool:
    if not path.is_file():
        return False
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)
    return True


ENV_FILE_LOADED = _load_env_file(ENV_FILE)
RESOURCE_DIR = _resolve_resource_dir(REPO_ROOT, DATA_DIR)


class Settings:
    env: str = os.getenv("REILINK_ENV", "development")
    llm_provider: str = os.getenv("LLM_PROVIDER", "mock")
    openai_api_key: str = os.getenv("OPENAI_API_KEY", "")
    openai_base_url: str = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
    openai_model: str = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    deepseek_api_key: str = os.getenv("DEEPSEEK_API_KEY", "")
    deepseek_base_url: str = os.getenv("DEEPSEEK_BASE_URL", "https://api.deepseek.com")
    deepseek_model: str = os.getenv("DEEPSEEK_MODEL", "deepseek-chat")
    deepseek_model_fast: str = os.getenv("DEEPSEEK_MODEL_FAST", "deepseek-v4-flash") or "deepseek-chat"
    deepseek_model_pro: str = os.getenv(
        "DEEPSEEK_MODEL_PRO",
        os.getenv("DEEPSEEK_MODEL_REASONING", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro")),
    )
    deepseek_model_reasoning: str = deepseek_model_pro
    deepseek_reasoning_effort: str = os.getenv("DEEPSEEK_REASONING_EFFORT", "medium")
    model_preference: str = os.getenv("MODEL_PREFERENCE", "auto").lower().strip() or "auto"
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    proactive_companion: str = os.getenv("PROACTIVE_COMPANION", "off").lower().strip() or "off"
    proactive_sensitivity: str = os.getenv("PROACTIVE_SENSITIVITY", "low").lower().strip() or "low"
    auto_game_detection: str = os.getenv("AUTO_GAME_DETECTION", "on").lower().strip() or "on"
    proactive_idle_seconds: float = float(os.getenv("PROACTIVE_IDLE_SECONDS", "600"))
    proactive_initial_grace_seconds: float = float(os.getenv("PROACTIVE_INITIAL_GRACE_SECONDS", "0"))
    proactive_type_cooldown_seconds: float = float(os.getenv("PROACTIVE_TYPE_COOLDOWN_SECONDS", "600"))
    proactive_global_cooldown_seconds: float = float(os.getenv("PROACTIVE_GLOBAL_COOLDOWN_SECONDS", "300"))
    proactive_user_grace_seconds: float = float(os.getenv("PROACTIVE_USER_GRACE_SECONDS", "30"))
    tts_provider: str = os.getenv("TTS_PROVIDER", "mock")
    stt_provider: str = os.getenv("STT_PROVIDER", "mock")
    enable_voice: bool = os.getenv("ENABLE_VOICE", "false").lower() == "true"
    enable_debug: bool = os.getenv("ENABLE_DEBUG", "true").lower() == "true"
    persona_mode: str = os.getenv("PERSONA_MODE", "guarded").lower().strip() or "guarded"

    backend_dir: Path = BACKEND_DIR
    repo_root: Path = REPO_ROOT
    env_file_path: Path = ENV_FILE
    env_file_loaded: bool = ENV_FILE_LOADED
    data_dir: Path = DATA_DIR
    resource_dir: Path = RESOURCE_DIR
    personas_dir: Path = resource_dir / "personas"
    persona_style_examples_path: Path = resource_dir / "persona" / "rei_style_examples.json"
    persona_golden_style_path: Path = resource_dir / "persona" / "rei_golden_style.json"
    persona_minimal_prompt_path: Path = resource_dir / "persona" / "rei_minimal_prompt.json"
    memory_dir: Path = data_dir / "memory"
    user_profile_path: Path = memory_dir / "user_profile.json"
    episodes_path: Path = memory_dir / "episodes.jsonl"
    pending_memories_path: Path = memory_dir / "pending_memories.jsonl"
    session_dir: Path = data_dir / "session"
    game_session_state_path: Path = session_dir / "game_session_state.json"
    game_context_state_path: Path = session_dir / "game_context_state.json"
    proactive_state_path: Path = session_dir / "proactive_state.json"
    conversations_dir: Path = data_dir / "conversations"
    elden_ring_dir: Path = resource_dir / "elden_ring"
    game_registry_path: Path = resource_dir / "games" / "game_registry.json"
    knowledge_games_dir: Path = KNOWLEDGE_GAMES_DIR
    settings_path: Path = data_dir / "settings.json"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "app://."]


settings = Settings()


def _runtime_setting(key: str) -> object | None:
    try:
        if not settings.settings_path.is_file():
            return None
        data = json.loads(settings.settings_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    if not isinstance(data, dict):
        return None
    return data.get(key)


def active_persona_mode() -> str:
    mode = str(_runtime_setting("persona_mode") or settings.persona_mode).lower().strip()
    if mode == "minimal":
        return "minimal"
    return "guarded"


def active_model_preference() -> str:
    preference = str(_runtime_setting("model_preference") or settings.model_preference).lower().strip()
    if preference in {"fast", "pro"}:
        return preference
    return "auto"
