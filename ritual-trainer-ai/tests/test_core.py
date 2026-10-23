import json
from pathlib import Path

import pandas as pd
import pytest

from ritual_core import (
    aligned_timeline,
    comparison_frame,
    focus_snapshot,
    get_players,
    interval_summary,
    match_info,
    normalize_benchmark,
    overview,
    player_final_stats,
    player_key,
    timeline_frame,
)

DATA = json.loads((Path(__file__).resolve().parents[1] / "data" / "sample_match.json").read_text())


def test_match_parser_handles_nested_and_flat_payloads():
    assert len(get_players(DATA)) == 12
    assert len(get_players(DATA["match_info"])) == 12
    with pytest.raises(ValueError):
        get_players({"match_info": {"foo": []}})


def test_player_stat_final_fields_and_zero_are_preserved():
    player = get_players(DATA)[0]
    final = player_final_stats(player)
    assert final["net_worth"] == player["net_worth"]
    assert final["kills"] == player["kills"]
    assert player_key(player, 0) == "account:12345000"
    assert player_final_stats({"kills": 0, "stats": []})["kills"] == 0


def test_timeline_matches_real_snapshot_count():
    raw = timeline_frame(DATA)
    assert len(raw) == 12 * 36
    assert not raw.net_worth.isna().any()
    assert set(raw.player_key.unique()) == {f"account:{12345000 + i}" for i in range(12)}


def test_comparison_and_intervals_detect_midgame_gap():
    comparison = comparison_frame(timeline_frame(DATA), "account:12345000")
    assert not comparison.empty
    assert len(comparison) == 36
    windows = interval_summary(comparison)
    assert windows
    assert any(w["relative_gain"] < -1500 for w in windows if w["relative_gain"] is not None)
    assert any(w["relative_gain"] > 0 for w in windows if w["relative_gain"] is not None)


def test_focus_snapshot_uses_real_values_not_model_guesses():
    raw = timeline_frame(DATA)
    interval = focus_snapshot(raw, "account:12345000", 10, 20)
    assert interval["actual_start_min"] == 10
    assert interval["actual_end_min"] == 20
    assert interval["net_worth_gain"] > 0
    assert interval["deaths_gain"] >= 0


def test_missing_snapshots_do_not_become_fabricated_zeroes():
    p = {"players": [
        {"account_id": 1, "team": 0, "net_worth": 1234},
        {"account_id": 2, "team": 1, "net_worth": 2345},
    ]}
    assert timeline_frame(p).empty
    assert comparison_frame(timeline_frame(p), "account:1").empty
    assert overview(p, "account:1")["data_coverage"]["timeline_sample_count"] == 0


def test_sparse_timelines_forward_fill_only_after_real_observation():
    p = {"players": [
        {"account_id": 1, "team": 0, "stats": [
            {"time_stamp_s": 120, "net_worth": 300},
            {"time_stamp_s": 300, "net_worth": 800}]},
        {"account_id": 2, "team": 1, "stats": [{"time_stamp_s": 0, "net_worth": 0}]},
    ]}
    aligned = aligned_timeline(timeline_frame(p))
    one = aligned[aligned.player_key == "account:1"].set_index("seconds")
    assert pd.isna(one.loc[0, "net_worth"])
    assert one.loc[240, "net_worth"] == 300
    assert one.loc[300, "net_worth"] == 800


def test_normalize_benchmark_uses_documented_fields_only():
    parsed = normalize_benchmark([
        {"game_time": 0, "net_worth_avg": 20, "kills_avg": 0.1},
        {"game_time": 600, "net_worth_avg": 8500},
    ])
    assert list(parsed["minute"]) == [0, 10]
    assert list(parsed["High-rank hero average"]) == [20, 8500]
    assert normalize_benchmark([{"junk": "missing"}]).empty


def test_missing_fields_preserved_as_null_not_zero():
    p = {"players": [{"account_id": 2, "team": 0, "stats": [{"time_stamp_s": 0, "net_worth": 10}]}]}
    stats = player_final_stats(get_players(p)[0])
    assert stats["deaths"] is None
    raw = timeline_frame(p)
    assert pd.isna(raw.loc[0, "player_damage"])
