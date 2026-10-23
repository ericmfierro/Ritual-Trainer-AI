from ritual_teams import patron_name
from ritual_core import player_label


def test_metadata_patron_names():
    assert patron_name(0) == "The Hidden King"
    assert patron_name(1) == "The Archmother"
    assert patron_name("0") == "The Hidden King"
    assert patron_name("1") == "The Archmother"


def test_replay_enum_patron_names():
    assert patron_name(2) == "The Hidden King"
    assert patron_name(3) == "The Archmother"
    assert patron_name(9) == "Unknown patron"
    assert patron_name(None) == "Unknown patron"


def test_player_label_uses_patron():
    assert player_label({"team": 0, "account_id": 10, "player_name": "Test", "hero_id": 5}, 0, {5: "Ivy"}) == "Test · Ivy · The Hidden King"
    assert "Team 0" not in player_label({"team": 0, "hero_id": 5}, 0, {5: "Ivy"})
