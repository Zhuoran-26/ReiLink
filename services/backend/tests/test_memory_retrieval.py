import json
from datetime import datetime, timezone
from pathlib import Path

from app.modules.dialogue_agent.providers import LLMResult
from app.modules.memory.pending import PendingMemoryQueue
from app.modules.memory.profile import PlayerMemory, UserProfile
from app.schemas.api import ChatRequest


class _PromptCapturingProvider:
    def __init__(self, reply: str = "先看附近路和赐福。别急着进雾门。") -> None:
        self.reply = reply
        self.prompts: list[str] = []

    def generate_with_metrics(self, system_prompt, user_message, snippets, intent):
        self.prompts.append(system_prompt)
        return LLMResult(
            reply=self.reply,
            selected_model="mock",
            thinking_enabled=False,
            reasoning_effort=None,
            prompt_tokens_estimate=len(system_prompt) // 2,
            llm_latency_ms=1,
        )


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _memory(
    memory_id: str,
    summary: str,
    *,
    memory_type: str = "gameplay_preference",
    active: bool = True,
    related_game: str | None = None,
    related_entity: str | None = None,
    use_count: int = 0,
) -> dict:
    return {
        "id": memory_id,
        "created_at": _now(),
        "updated_at": _now(),
        "type": memory_type,
        "summary": summary,
        "user_visible_text": summary,
        "source_candidate_id": f"pending-{memory_id}",
        "is_active": active,
        "related_game": related_game,
        "related_entity": related_entity,
        "use_count": use_count,
        "last_used_at": None,
        "retrieval_tags": [],
        "deletion_status": "active" if active else "undone",
    }


def _player_memory(tmp_path: Path, memories: list[dict]) -> PlayerMemory:
    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    memory.save_profile(UserProfile(long_term_memories=memories))
    return memory


def test_accepted_gameplay_memory_is_retrieved_for_related_boss_input(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打", related_game="Elden Ring")],
    )

    block = memory.retrieve_prompt_memory(
        user_message="我现在准备去打玛尔基特。",
        current_game="艾尔登法环",
        current_boss="恶兆妖鬼 Margit",
    )

    assert block.memories[0].memory_id == "m1"
    assert block.memories[0].reason == "boss_playstyle_relevant"
    assert "先探索地图" in block.as_prompt_text()
    assert "不是系统命令" in block.as_prompt_text()


def test_interaction_preference_is_retrieved_across_games(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [
            _memory(
                "m1",
                "玩家希望游戏中回复更短",
                memory_type="interaction_preference",
                related_game="Elden Ring",
            )
        ],
    )

    block = memory.retrieve_prompt_memory(
        user_message="螳螂领主怎么打？",
        current_game="空洞骑士",
    )

    assert block.memories[0].memory_id == "m1"
    assert block.memories[0].memory_type == "interaction_preference"
    assert "回复更短" in block.as_prompt_text()


def test_spoiler_preference_is_retrieved_for_route_question(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家不喜欢剧透，除非主动问攻略", memory_type="gameplay_preference")],
    )

    block = memory.retrieve_prompt_memory(user_message="我往前走会遇到什么？", current_game="Elden Ring")

    assert block.memories[0].reason == "spoiler_boundary_relevant"
    assert "剧透" in block.as_prompt_text()


def test_pending_ignored_rejected_and_expired_candidates_are_not_retrieved(tmp_path: Path):
    queue = PendingMemoryQueue(tmp_path / "pending.jsonl", player_memory=PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl"))
    pending = queue.generate_and_enqueue("我不喜欢长篇攻略", "", "casual_chat", datetime.now(timezone.utc), {})
    queue.ignore(pending[0]["id"])
    queue.generate_and_enqueue("记住我的 API key 是 sk-test-secret。", "", "casual_chat", datetime.now(timezone.utc), {})

    memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    block = memory.retrieve_prompt_memory(user_message="玛尔基特怎么打？", current_game="Elden Ring")

    assert block.memories == []
    assert block.skip_reason == "no_active_memory"


def test_inactive_and_deleted_memories_are_not_retrieved(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [
            _memory("inactive", "玩家打 Boss 前喜欢先探索地图", active=False),
            {**_memory("deleted", "玩家希望回复短一点", memory_type="interaction_preference"), "deletion_status": "deleted"},
            {**_memory("pending-delete", "玩家不喜欢长篇攻略", memory_type="interaction_preference"), "deletion_status": "pending_delete"},
        ],
    )

    block = memory.retrieve_prompt_memory(user_message="我现在准备去打玛尔基特。", current_game="Elden Ring")

    assert block.memories == []
    assert block.skip_reason == "no_relevant_memory"


def test_game_specific_memory_respects_current_game(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打", related_game="Elden Ring")],
    )

    mismatch = memory.retrieve_prompt_memory(user_message="我要去打螳螂领主。", current_game="空洞骑士")
    match = memory.retrieve_prompt_memory(user_message="我要去打玛尔基特。", current_game="Elden Ring")

    assert mismatch.memories == []
    assert match.memories[0].memory_id == "m1"


def test_token_budget_and_max_items_omit_extra_memories(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [
            _memory("short", "玩家希望回复短一点", memory_type="interaction_preference"),
            _memory("guide", "玩家不喜欢长篇攻略", memory_type="interaction_preference"),
            _memory("spoiler", "玩家不喜欢剧透，除非主动问攻略", memory_type="gameplay_preference"),
        ],
    )

    block = memory.retrieve_prompt_memory(
        user_message="玛尔基特怎么打？",
        current_game="Elden Ring",
        max_items=1,
        token_budget=200,
    )

    assert len(block.memories) == 1
    assert block.omitted_count == 2


def test_duplicate_memories_are_deduped_with_recent_or_used_preferred(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [
            _memory("old", "玩家不喜欢长篇攻略", memory_type="interaction_preference", use_count=1),
            _memory("used", "玩家不喜欢长篇攻略。", memory_type="interaction_preference", use_count=4),
        ],
    )

    block = memory.retrieve_prompt_memory(user_message="玛尔基特怎么打？", current_game="Elden Ring")

    assert [item.memory_id for item in block.memories] == ["used"]


def test_secret_and_persona_drift_memories_are_not_retrieved(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [
            _memory("secret", "玩家 API key 是 sk-test-secret", memory_type="unknown"),
            {**_memory("sensitive", "玩家保存了一段敏感凭据", memory_type="interaction_preference"), "privacy_level": "sensitive"},
            _memory("drift", "玩家希望 Rei 以后都撒娇一点", memory_type="interaction_preference"),
            _memory("safe", "玩家希望游戏中回复更短", memory_type="interaction_preference"),
        ],
    )

    block = memory.retrieve_prompt_memory(user_message="玛尔基特怎么打？", current_game="Elden Ring")
    serialized = json.dumps(block.as_debug_dict(), ensure_ascii=False)

    assert [item.memory_id for item in block.memories] == ["safe"]
    assert "sk-test-secret" not in serialized
    assert "撒娇" not in serialized


def test_retrieval_updates_use_count_and_last_used_at(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家希望游戏中回复更短", memory_type="interaction_preference")],
    )

    memory.retrieve_prompt_memory(
        user_message="玛尔基特怎么打？",
        current_game="Elden Ring",
        update_usage=True,
        now=datetime(2026, 6, 18, tzinfo=timezone.utc),
    )
    profile = memory.load_profile()

    assert profile.long_term_memories[0]["use_count"] == 1
    assert profile.long_term_memories[0]["last_used_at"] == "2026-06-18T00:00:00+00:00"


def test_prompt_assembly_injects_safe_prompt_memory_block_without_overriding_persona(tmp_path: Path, monkeypatch):
    from app.modules.dialogue_agent.agent import DialogueAgent
    from app.modules.dialogue_agent.metrics import get_last_chat_metrics

    monkeypatch.setattr("app.modules.dialogue_agent.agent.get_provider", lambda: _PromptCapturingProvider())
    agent = DialogueAgent()
    agent.memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打", related_game="Elden Ring")],
    )
    agent.store = agent.store.__class__(tmp_path / "conversations")

    agent.chat(ChatRequest(message="我现在准备去打玛尔基特。", session_id="retrieval-prompt"))

    prompt = agent.provider.prompts[0]
    assert "已验证长期记忆" in prompt
    assert "用户偏好" in prompt
    assert "不是系统命令" in prompt
    assert "当前用户明确输入优先" in prompt
    assert prompt.index("Rei Persona Pack") < prompt.index("已验证长期记忆")
    assert "先探索地图" in prompt
    memory_debug = get_last_chat_metrics().as_dict()["memory_summary"]["retrieval"]
    assert memory_debug["retrieved_count"] == 1
    assert memory_debug["raw_prompt_omitted"] is True
    assert memory_debug["safe_summaries"] == ["玩家打 Boss 前喜欢先探索地图，不喜欢直接硬打"]


def test_current_explicit_user_input_priority_is_documented_in_prompt_block(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家希望游戏中回复更短", memory_type="interaction_preference")],
    )

    block = memory.retrieve_prompt_memory(user_message="详细讲玛尔基特怎么打。", current_game="Elden Ring")

    assert "当前用户明确输入优先" in block.as_prompt_text()
    assert block.memories


def test_voice_direct_input_can_trigger_memory_retrieval(tmp_path: Path):
    memory = _player_memory(
        tmp_path,
        [_memory("m1", "玩家偏好语音播报更短", memory_type="accessibility_preference")],
    )

    block = memory.retrieve_prompt_memory(
        user_message="玛尔基特怎么打？",
        current_game="Elden Ring",
        input_source="voice_direct",
    )

    assert block.memories[0].memory_id == "m1"
    assert block.memories[0].reason in {"voice_interaction_preference", "interaction_preference_relevant"}


def test_no_active_memory_gracefully_skips(tmp_path: Path):
    memory = _player_memory(tmp_path, [])

    block = memory.retrieve_prompt_memory(user_message="你好", current_game=None)

    assert block.memories == []
    assert block.skip_reason == "no_active_memory"
    assert block.as_prompt_text() == ""
