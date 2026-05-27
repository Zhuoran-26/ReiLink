import os
from pathlib import Path


BACKEND_DIR = Path(__file__).resolve().parents[2]
REPO_ROOT = BACKEND_DIR.parents[1]
ENV_FILE = BACKEND_DIR / ".env"


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
    deepseek_model_reasoning: str = os.getenv("DEEPSEEK_MODEL_REASONING", os.getenv("DEEPSEEK_MODEL", "deepseek-v4-pro"))
    deepseek_reasoning_effort: str = os.getenv("DEEPSEEK_REASONING_EFFORT", "medium")
    llm_timeout_seconds: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "20"))
    tts_provider: str = os.getenv("TTS_PROVIDER", "mock")
    stt_provider: str = os.getenv("STT_PROVIDER", "mock")
    enable_voice: bool = os.getenv("ENABLE_VOICE", "false").lower() == "true"
    enable_debug: bool = os.getenv("ENABLE_DEBUG", "true").lower() == "true"

    backend_dir: Path = BACKEND_DIR
    repo_root: Path = REPO_ROOT
    env_file_path: Path = ENV_FILE
    env_file_loaded: bool = ENV_FILE_LOADED
    data_dir: Path = Path(os.getenv("REILINK_DATA_DIR", repo_root / "data"))
    personas_dir: Path = data_dir / "personas"
    persona_style_examples_path: Path = data_dir / "persona" / "rei_style_examples.json"
    persona_golden_style_path: Path = data_dir / "persona" / "rei_golden_style.json"
    memory_dir: Path = data_dir / "memory"
    user_profile_path: Path = memory_dir / "user_profile.json"
    episodes_path: Path = memory_dir / "episodes.jsonl"
    conversations_dir: Path = data_dir / "conversations"
    elden_ring_dir: Path = data_dir / "elden_ring"
    cors_origins: list[str] = ["http://localhost:5173", "http://127.0.0.1:5173", "app://."]


settings = Settings()
