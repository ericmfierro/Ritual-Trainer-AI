from ritual_roles import AUTO_ROLE, ROLE_BY_NAME, ROLES, resolve_role, suggested_roles


def test_positions_and_user_supplied_hero_examples():
    assert len(ROLES) == 4
    assert all(role.heroes and role.coaching_angle and role.farm_priority for role in ROLES)
    assert "Hard Carry" in suggested_roles("Seven")
    assert "Hard Carry" in suggested_roles("Lady Geist")
    assert "Tempo / Off-Carry" in suggested_roles("Haze")
    assert "Tempo / Off-Carry" in suggested_roles("Drifter")
    assert "Tempo / Off-Carry" in suggested_roles("The Drifter")
    assert "Frontliner / Space Creator" in suggested_roles("Mo & Krill")
    assert suggested_roles("Mo and Krill") == suggested_roles("Mo & Krill")
    assert "Support & Utility" in suggested_roles("Dynamo")


def test_auto_role_is_only_a_suggestion():
    result = resolve_role("Ivy", AUTO_ROLE)
    assert result["role"] in ROLE_BY_NAME
    assert result["role_is_flexible"] is True
    assert "suggested" in result["source"]
    assert "lower farm priority" in result["farm_priority"].lower()


def test_player_can_override_and_unknown_hero_is_not_guessed():
    assert resolve_role("Training Hero A", AUTO_ROLE)["role"] == "Not specified"
    result = resolve_role("Dynamo", "Hard Carry")
    assert result["role"] == "Hard Carry"
    assert result["source"] == "chosen by the player"
    assert "Highest farm priority" in result["farm_priority"]


def test_role_source_is_preserved_in_ai_evidence():
    import json
    from ritual_coach import payload_for_ai

    role = resolve_role("Ivy", AUTO_ROLE)
    analysis = {"hero_combat_archetype": role}
    data = json.loads(payload_for_ai(analysis, {"available": False}, [],
                                     role["role"], "Balanced improvement", {}))
    assert data["selected_combat_archetype"] == "Support & Utility"
    assert data["archetype_source"].startswith("suggested")
    assert data["match_analysis"]["hero_combat_archetype"]["role_is_flexible"] is True
    assert "lower farm priority" in data["match_analysis"]["hero_combat_archetype"]["farm_priority"].lower()
