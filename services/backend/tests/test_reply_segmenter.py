from app.modules.dialogue_agent.segmenter import segment_reply


def test_short_reply_uses_one_or_two_segments():
    result = segment_reply("我在。想说的时候就说。", "casual_chat", "你好")

    assert 1 <= len(result.segments) <= 2
    assert result.mode == "compact"


def test_affection_reply_uses_at_most_two_segments():
    reply = "我听见了。别突然说这种话。"
    result = segment_reply(reply, "casual_chat", "我喜欢你")

    assert len(result.segments) <= 2
    assert result.mode == "emotion"


def test_strategy_reply_uses_two_to_four_segments():
    reply = "别急。少打一刀，先活下来。等他真的落下来再滚。"
    result = segment_reply(reply, "elden_ring_boss_strategy", "Margit 怎么打")

    assert 2 <= len(result.segments) <= 4
    assert result.mode == "strategy"


def test_each_segment_is_not_too_long():
    reply = "先停一下，别急着砍，等他真的落下来再滚，下一轮只练躲，不想着赢。"
    result = segment_reply(reply, "elden_ring_boss_strategy", "还是不行")

    assert all(len(segment) <= 80 for segment in result.segments)


def test_segments_preserve_original_reply_semantics():
    reply = "又是恶兆妖鬼 Margit。你开始急了。下一轮只练躲，不急着砍。"
    result = segment_reply(reply, "elden_ring_boss_strategy", "我又死了")

    assert "".join(result.segments) == reply


def test_emotional_reply_can_use_natural_newline_segments():
    reply = "你问得太急了。\n先慢一点。"
    result = segment_reply(reply, "casual_chat", "你喜欢我吗")

    assert result.mode == "emotion"
    assert result.segments == ["你问得太急了。", "先慢一点。"]


def test_late_night_reply_uses_short_emotional_segments():
    reply = "已经凌晨了。\n该停了。"
    result = segment_reply(reply, "casual_chat", "已经凌晨了")

    assert result.mode == "emotion"
    assert 1 <= len(result.segments) <= 2
    assert all(len(segment) <= 20 for segment in result.segments)


def test_strategy_segments_do_not_mechanically_shatter_short_phrases():
    reply = "别急着赢。\n他抬手会骗你。\n等真的落下来，再滚。"
    result = segment_reply(reply, "elden_ring_boss_strategy", "Margit 怎么打")

    assert result.segments == ["别急着赢。", "他抬手会骗你。", "等真的落下来，再滚。"]
    assert len(result.segments) <= 4
