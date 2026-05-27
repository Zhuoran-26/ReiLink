from app.modules.dialogue_agent.routing import select_model_route


def test_casual_chat_selects_fast_model():
    route = select_model_route("casual_chat", "你好")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.thinking_enabled is False
    assert route.reasoning_effort is None


def test_affection_selects_fast_model():
    route = select_model_route("casual_chat", "我喜欢你")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.thinking_enabled is False


def test_emotional_death_loop_selects_fast_model():
    route = select_model_route("casual_chat", "我又死了")

    assert route.selected_model == "deepseek-v4-flash"
    assert route.thinking_enabled is False


def test_detailed_guide_selects_reasoning_model():
    route = select_model_route("elden_ring_boss_strategy", "Margit 完整攻略怎么打")

    assert route.selected_model == "deepseek-v4-pro"
    assert route.thinking_enabled is True
    assert route.reasoning_effort == "medium"
