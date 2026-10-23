"""Offline tests for verified hero/item evidence and replay schema dispatch."""
from unittest.mock import Mock

import pytest

from ritual_knowledge import ASSETS_BASE, AssetClient, KnowledgeUnavailable, build_knowledge_pack
from ritual_api import DeadlockClient
from ritual_coach import default_model, payload_for_ai


def fixture_records():
    hero = {"id": 7, "name": "Example Hero", "description": {"role": "Controls space", "playstyle": "Controls objectives"},
            "items": {"signature1": 101, "signature2": "ability_b", "weapon_primary": 999}}
    items = [
        {"id": 101, "name": "Example Ability", "class_name": "ability_a", "description": "Stuns nearby units", "type": "ability"},
        {"id": 102, "name": "Second Ability", "class_name": "ability_b", "description": "Provides a shield", "type": "ability"},
        {"id": 999, "name": "Weapon", "class_name": "weapon", "description": "Weapon effect", "type": "weapon"},
        {"id": 555, "name": "Bought Upgrade", "description": "Improves stamina recovery", "cost": 500, "type": "upgrade"},
    ]
    return hero, items


def test_knowledge_includes_linked_abilities_and_only_actual_bought_items():
    hero, assets = fixture_records()
    pack = build_knowledge_pack(hero, assets, [{"item_id": 555, "minute": 7.2}, {"item_id": 404, "minute": 15}], fetched_at="2026-10-19T00:00:00Z")
    assert pack["hero"]["name"] == "Example Hero"
    assert [x["name"] for x in pack["hero_abilities"]] == ["Example Ability", "Second Ability"]
    assert len(pack["purchased_item_definitions"]) == 1
    assert pack["purchased_item_definitions"][0]["name"] == "Bought Upgrade"
    assert pack["retrieved_utc"] == "2026-10-19T00:00:00Z"
    assert pack["source"].startswith("Deadlock API /v1/assets")
    assert "Weapon" not in str(pack["hero_abilities"])


def test_unknown_abilities_are_omitted_not_invented():
    hero, assets = fixture_records()
    hero["items"]["signature3"] = 444444
    pack = build_knowledge_pack(hero, assets, [], fetched_at="now")
    assert len(pack["hero_abilities"]) == 2
    assert pack["purchased_item_definitions"] == []


def test_bad_assets_fail_closed():
    with pytest.raises(ValueError, match="valid hero"):
        build_knowledge_pack({}, [], [])


def test_knowledge_flows_into_prompt_without_changing_existing_callers():
    hero, assets = fixture_records()
    pack = build_knowledge_pack(hero, assets, [], fetched_at="now")
    prompt = payload_for_ai({"hero":"Example Hero"}, {"available": False}, [], "Hard Carry", "Farming", {}, pack)
    assert "Stuns nearby units" in prompt
    assert "verified_game_knowledge" in prompt
    assert "Example Ability" in prompt
    fallback = payload_for_ai({}, {}, [], "Hard Carry", "Farming", {})
    assert '"available": false' in fallback.lower()


def test_default_ollama_is_gpt_oss(monkeypatch):
    monkeypatch.delenv("OLLAMA_MODEL", raising=False)
    assert default_model("Ollama (local, offline)") == "gpt-oss:20b"


def test_demo_schema_sends_correct_match_id(monkeypatch):
    client = DeadlockClient()
    request = Mock(return_value={"tables": ["CCitadelPlayerPawn"]})
    monkeypatch.setattr(client, "get", request)
    assert client.demo_schema(120208613)["tables"] == ["CCitadelPlayerPawn"]
    request.assert_called_once_with("/v1/matches/demo/schema", {"match_id": 120208613})
    with pytest.raises(ValueError):
        client.demo_schema(0)


def test_current_asset_routes_use_documented_api():
    session = Mock()
    hero_reply = Mock()
    hero_reply.json.return_value = {"id": 17, "name": "Example Hero"}
    items_reply = Mock()
    items_reply.json.return_value = [{"id": 2, "name": "Example Item"}]
    session.get.side_effect = [hero_reply, items_reply]
    client = AssetClient(session)
    assert client.hero(17)["id"] == 17
    assert client.all_items()[0]["id"] == 2
    assert ASSETS_BASE == "https://api.deadlock-api.com"
    assert session.get.call_args_list[0].args[0] == "https://api.deadlock-api.com/v1/assets/heroes/17"
    assert session.get.call_args_list[1].args[0] == "https://api.deadlock-api.com/v1/assets/items"


def test_dns_error_has_actionable_message():
    import requests
    session = Mock()
    session.get.side_effect = requests.exceptions.ConnectionError("name resolution failed")
    with pytest.raises(KnowledgeUnavailable, match="internet/DNS"):
        AssetClient(session).hero(17)


def test_evidence_urls_are_real_routes():
    hero, items = fixture_records()
    evidence = build_knowledge_pack(hero, items, [], fetched_at="now")
    assert evidence["hero_url"] == "https://api.deadlock-api.com/v1/assets/heroes/7"
    assert evidence["item_url"] == "https://api.deadlock-api.com/v1/assets/items"
