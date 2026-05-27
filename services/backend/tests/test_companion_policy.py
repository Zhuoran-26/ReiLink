from app.modules.dialogue_agent.emotion import build_companion_policy, detect_user_emotion, wants_detailed_strategy


def test_emotion_detection_catches_common_companion_inputs():
    assert detect_user_emotion("我有点烦了").label == "frustrated"
    assert detect_user_emotion("我又死了").label == "death_loop"
    assert detect_user_emotion("我喜欢你").label == "affection"
    assert detect_user_emotion("我太菜了").label == "self_doubt"


def test_companion_policy_prioritizes_emotion_before_strategy():
    policy = build_companion_policy("我又死了", "elden_ring_boss_strategy")

    assert "当前用户情绪 > 当前用户问题 > 当前游戏上下文 > 知识库 > 长期记忆 > Rei 气质" in policy
    assert "第一句先接住状态" in policy
    assert "默认只给 1 个关键点" in policy
    assert "不要超过 2 句" in policy


def test_strategy_policy_discourages_guide_site_tone():
    policy = build_companion_policy("Margit 怎么打", "elden_ring_boss_strategy")

    assert "少用攻略站语气" in policy
    assert "先活下来" in policy
    assert "少打一刀" in policy


def test_detail_request_allows_more_explanation():
    assert wants_detailed_strategy("完整攻略怎么打") is True
    assert wants_detailed_strategy("怎么配装") is True
    assert wants_detailed_strategy("我又死了") is False
