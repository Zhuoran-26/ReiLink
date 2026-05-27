from pathlib import Path

from app.modules.dialogue_agent.agent import DialogueAgent
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatRequest

_GUIDE_SITE_TERMS = ("先保证", "输出", "连段", "方向", "节奏", "机制", "建议", "如果")


def _sentence_count(text: str) -> int:
    return sum(mark in text for mark in "。！？!?") or 1


def test_emotional_game_input_is_short_and_not_guide_site_tone(tmp_path: Path):
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    response = agent.chat(ChatRequest(message="我又死了", session_id="companion-quality"))

    assert _sentence_count(response.reply) <= 2
    assert any(marker in response.reply for marker in ("急", "停", "死", "先活", "少打"))
    assert not any(term in response.reply for term in _GUIDE_SITE_TERMS)


def test_strategy_reply_defaults_to_one_companion_key_point(tmp_path: Path):
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    response = agent.chat(ChatRequest(message="Margit 怎么打", session_id="strategy-quality"))

    assert _sentence_count(response.reply) <= 2
    assert any(marker in response.reply for marker in ("别急", "少打", "先活", "翻滚", "躲"))
    assert not any(term in response.reply for term in _GUIDE_SITE_TERMS)
