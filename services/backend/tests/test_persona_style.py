from app.modules.dialogue_agent.style import apply_rei_style


def test_style_only_normalizes_repeated_punctuation():
    reply = apply_rei_style("我在这里。。你又急了......别急着翻滚！！！", seed="steady")

    assert reply == "我在这里。你又急了……别急着翻滚！"


def test_style_does_not_remove_words_or_rewrite_sentences():
    reply = apply_rei_style("请问根据你的问题，建议你先观察 Boss。有什么可以帮助你", seed="service")

    assert "请问" in reply
    assert "根据你的问题" in reply
    assert "建议你" in reply
    assert "有什么可以帮助你" in reply


def test_style_keeps_readable_normal_chinese():
    reply = apply_rei_style("又死了？", seed="short")

    assert reply.endswith("？")


def test_style_never_inserts_ellipsis_or_pause():
    replies = [apply_rei_style("我在", seed=f"reply-{index}") for index in range(100)]

    assert set(replies) == {"我在"}
