from datetime import datetime, timezone
from pathlib import Path

from app.modules.dialogue_agent.agent import DialogueAgent
from app.modules.dialogue_agent.providers import LLMResult
from app.modules.dialogue_agent.segmenter import segment_reply
from app.modules.elden_ring_knowledge.knowledge import EldenRingKnowledge
from app.modules.elden_ring_knowledge.terminology import normalize_terminology
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatRequest


class _EnglishTermProvider:
    def generate_with_metrics(self, *args, **kwargs):
        return LLMResult(
            reply="Tree Sentinel 在 Stormveil Castle 前。Spirit Ashes 可以先别急着用。",
            selected_model="mock",
            thinking_enabled=False,
            reasoning_effort=None,
            prompt_tokens_estimate=1,
            llm_latency_ms=1,
        )


def test_terminology_normalizer_maps_english_terms_to_chinese():
    text = "Tree Sentinel, tree sentinel, Stormveil Castle, Spirit Ashes, Site of Grace, Radahn"

    normalized = normalize_terminology(text)

    assert "大树守卫" in normalized
    assert normalized.count("大树守卫") == 2
    assert "史东薇尔城" in normalized
    assert "骨灰" in normalized
    assert "赐福点" in normalized
    assert "拉塔恩" in normalized
    assert "Tree Sentinel" not in normalized
    assert "tree sentinel" not in normalized


def test_margit_title_normalizes_without_duplication():
    text = normalize_terminology("Margit, the Fell Omen 和 Margit")

    assert text == "恶兆妖鬼 Margit 和恶兆妖鬼 Margit"
    assert "恶兆妖鬼 恶兆妖鬼" not in text


def test_reply_and_segments_are_normalized_before_response(tmp_path: Path):
    agent = DialogueAgent()
    agent.provider = _EnglishTermProvider()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    response = agent.chat(ChatRequest(message="Tree Sentinel 怎么打", session_id="terms"))

    assert "大树守卫" in response.reply
    assert "史东薇尔城" in response.reply
    assert "骨灰" in response.reply
    assert all("Tree Sentinel" not in segment for segment in response.reply_segments)


def test_segmenter_normalizes_terms_directly():
    result = segment_reply("Tree Sentinel 很硬。Stormveil Castle 先别去。", "elden_ring_boss_strategy", "怎么打")

    assert result.segments == ["大树守卫很硬。", "史东薇尔城先别去。"]


def test_memory_current_boss_does_not_save_english_tree_sentinel(tmp_path: Path):
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")

    memory.extract_and_update(
        "我打不过 Tree Sentinel",
        "先活下来。",
        "elden_ring_boss_strategy",
        datetime.now(timezone.utc),
    )

    profile = memory.load_profile()
    episode = memory.recent_episodes()[0]
    assert profile.current_boss == "大树守卫"
    assert episode["boss"] == "大树守卫"
    assert "Tree Sentinel" not in profile.as_dict()["current_boss"]
    assert "Tree Sentinel" not in episode["summary"]


def test_knowledge_snippets_are_normalized_before_prompt_injection():
    snippets = EldenRingKnowledge().search("Margit 怎么打", "elden_ring_boss_strategy")

    assert snippets
    assert snippets[0].title == "恶兆妖鬼 Margit"
    assert "Margit, the Fell Omen" not in snippets[0].content
    assert "召唤" in snippets[0].content
