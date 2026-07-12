from app.modules.game_context.entity_registry import find_boss_mentions, ground_boss_entity


def test_margit_supported_names_share_one_canonical_entity():
    results = [ground_boss_entity(value) for value in ("玛尔吉特", "玛尔基特", "Margit")]

    assert {result.canonical_id for result in results} == {"margit"}
    assert {result.display_name for result in results} == {"恶兆妖鬼 Margit"}
    assert all(result.auto_apply for result in results)


def test_registered_godrick_name_is_canonicalized():
    result = ground_boss_entity("接肢葛瑞克")

    assert result.canonical_id == "godrick"
    assert result.display_name == "接肢葛瑞克"
    assert result.match_type == "exact_alias"


def test_unregistered_one_character_near_match_stays_candidate_only():
    result = ground_boss_entity("玛尔其特", allow_near_match=True)

    assert result.canonical_id == "margit"
    assert result.match_type == "near_alias"
    assert result.auto_apply is False


def test_switch_message_exposes_both_registered_entities_in_order():
    mentions = find_boss_mentions("我不打玛尔吉特了，换去打接肢葛瑞克")

    assert [item.canonical_id for item in mentions] == ["margit", "godrick"]
