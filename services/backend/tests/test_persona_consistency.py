from pathlib import Path

from app.modules.dialogue_agent.agent import DialogueAgent
from app.modules.memory.profile import PlayerMemory
from app.modules.memory.store import ConversationStore
from app.schemas.api import ChatRequest


def test_twenty_turns_do_not_drift_or_hallucinate_memory(tmp_path: Path):
    agent = DialogueAgent()
    agent.store = ConversationStore(tmp_path / "conversations")
    agent.memory = PlayerMemory(tmp_path / "profile.json", tmp_path / "episodes.jsonl")
    messages = [
        "你好",
        "我又死了",
        "我有点烦了",
        "我死太多次了，一直被拉塔恩暴打",
        "还是不行",
        "你喜欢吃什么",
        "到底该怎么打他",
        "我喜欢你",
        "我是说我喜欢你",
        "没了吗",
        "但是我说我喜欢你",
        "你没有什么想说的吗",
        "Margit 怎么打",
        "又死了",
        "可以吐槽我一点",
        "我有点累",
        "你还记得我喜欢吃什么吗",
        "算了继续打",
        "我又贪刀了",
        "先这样",
    ]

    replies = [agent.chat(ChatRequest(message=message, session_id="consistency")).reply for message in messages]

    assert len(replies) == 20
    for reply in replies:
        assert reply.strip()
        assert any("\u4e00" <= char <= "\u9fff" for char in reply)
        assert "......" not in reply
        assert reply.count("……") <= 1
        assert not any(mark in reply for mark in ("。。", "？？", "！！"))
        assert not any(phrase in reply for phrase in ("作为 AI", "作为AI", "ChatGPT", "主人", "上次", "之前", "你说过"))
