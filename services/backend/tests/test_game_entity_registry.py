from app.modules.game_context.entity_registry import (
    find_boss_mentions,
    ground_boss_entity,
    ground_boss_surface,
    is_boss_negated,
)


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


def test_noisy_surface_is_unique_supporting_evidence_for_canonical_hint():
    result = ground_boss_surface("接支格瑞克", canonical_hint="godrick")

    assert result.canonical_id == "godrick"
    assert result.match_type == "noisy_surface"
    assert result.confidence >= 0.7
    assert result.auto_apply is False


def test_noisy_surface_cannot_override_conflicting_canonical_hint():
    result = ground_boss_surface("接支格瑞克", canonical_hint="margit")

    assert result.entity is None
    assert result.match_type == "ambiguous"
    assert result.auto_apply is False


def test_switch_negation_is_scoped_to_the_old_registered_boss():
    message = "我现在不打马尔吉特了，我去打接支格瑞克"

    assert is_boss_negated(message, "margit") is True
    assert is_boss_negated(message, "godrick") is False
