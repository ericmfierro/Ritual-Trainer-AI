"""Normalize Deadlock match metadata and calculate reproducible coaching metrics."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pandas as pd

from ritual_teams import patron_name


STAT_FIELDS = {
    "net_worth": ("net_worth", "souls"),
    "kills": ("kills",),
    "deaths": ("deaths",),
    "assists": ("assists",),
    "player_damage": ("player_damage", "hero_damage"),
    "player_healing": ("player_healing", "healing"),
    "last_hits": ("last_hits",),
    "denies": ("denies",),
    "boss_damage": ("boss_damage", "objective_damage"),
}


def first_number(obj: dict, *keys: str) -> float | None:
    for key in keys:
        value = obj.get(key)
        if isinstance(value, (int, float)) and not isinstance(value, bool):
            return float(value)
    return None


def match_info(payload: dict[str, Any]) -> dict[str, Any]:
    for key in ("match_info", "match"):
        if isinstance(payload.get(key), dict) and isinstance(payload[key].get("players"), list):
            return payload[key]
    if isinstance(payload.get("players"), list):
        return payload
    raise ValueError("The API response did not include a recognizable players list.")


def get_players(payload: dict[str, Any]) -> list[dict[str, Any]]:
    return [p for p in match_info(payload)["players"] if isinstance(p, dict)]


def player_key(player: dict[str, Any], index: int) -> str:
    if player.get("account_id") is not None:
        return f"account:{player['account_id']}"
    if player.get("player_slot") is not None:
        return f"slot:{player['player_slot']}"
    return f"row:{index}"


def player_label(player: dict[str, Any], index: int, hero_names: dict[int, str] | None = None) -> str:
    hero_names = hero_names or {}
    hero_id = player.get("hero_id")
    hero = hero_names.get(hero_id, f"Hero {hero_id}" if hero_id is not None else "Unknown hero")
    name = player.get("player_name") or player.get("name") or player.get("username")
    identity = str(name) if name else f"Player {player.get('player_slot', index)}"
    return f"{identity} · {hero} · {patron_name(player.get('team'))}"


def _timeline(player: dict[str, Any]) -> list[dict[str, Any]]:
    for key in ("stats", "player_stats", "stats_history"):
        if isinstance(player.get(key), list):
            return [s for s in player[key] if isinstance(s, dict)]
    return []


def player_final_stats(player: dict[str, Any]) -> dict[str, float | None]:
    history = _timeline(player)
    result = {}
    for field, candidates in STAT_FIELDS.items():
        result[field] = first_number(player, *candidates)
        if result[field] is None and history:
            result[field] = first_number(history[-1], *candidates)
    return result


def timeline_frame(payload: dict[str, Any]) -> pd.DataFrame:
    records: list[dict] = []
    for idx, player in enumerate(get_players(payload)):
        for stat in _timeline(player):
            second = first_number(stat, "time_stamp_s", "timestamp_s", "game_time_s")
            if second is None or second < 0:
                continue
            record = {
                "player_key": player_key(player, idx),
                "team": str(player.get("team", "?")),
                "seconds": int(second),
            }
            for field, keys in STAT_FIELDS.items():
                record[field] = first_number(stat, *keys)
            records.append(record)
    if not records:
        return pd.DataFrame(columns=["player_key", "team", "seconds", *STAT_FIELDS])
    return (pd.DataFrame.from_records(records)
            .sort_values("seconds")
            .drop_duplicates(subset=["player_key", "seconds"], keep="last")
            .sort_values(["player_key", "seconds"])
            .reset_index(drop=True))


def aligned_timeline(raw: pd.DataFrame, step: int = 60) -> pd.DataFrame:
    """Carry forward the latest observed cumulative value; never invent missing stats."""
    if raw.empty:
        return raw.copy()
    end = int(raw.seconds.max())
    grid = pd.DataFrame({"seconds": list(range(0, end + 1, step)) + ([end] if end % step else [])})
    frames = []
    for key, group in raw.groupby("player_key", sort=False):
        group = group.sort_values("seconds")
        joined = pd.merge_asof(grid.sort_values("seconds"), group, on="seconds", direction="backward")
        joined["player_key"] = key
        joined["team"] = str(group.iloc[0]["team"])
        frames.append(joined)
    return pd.concat(frames, ignore_index=True)


def comparison_frame(raw: pd.DataFrame, selected_key: str) -> pd.DataFrame:
    aligned = aligned_timeline(raw)
    if aligned.empty:
        return pd.DataFrame(columns=["seconds", "minute", "You", "Teammate average", "Opponent average"])
    chosen = aligned[aligned.player_key == selected_key].copy()
    if chosen.empty:
        return pd.DataFrame(columns=["seconds", "minute", "You", "Teammate average", "Opponent average"])
    team = str(chosen.iloc[0].team)
    chosen = chosen[["seconds", "net_worth"]].rename(columns={"net_worth": "You"})
    ally = aligned[(aligned.team == team) & (aligned.player_key != selected_key)]
    opponents = aligned[aligned.team != team]
    for label, group in (("Teammate average", ally), ("Opponent average", opponents)):
        if group.empty:
            chosen[label] = float("nan")
        else:
            mean = group.groupby("seconds")["net_worth"].mean().rename(label).reset_index()
            chosen = chosen.merge(mean, how="left", on="seconds")
    chosen["minute"] = chosen.seconds / 60.0
    return chosen.sort_values("seconds").reset_index(drop=True)


def interval_summary(comparison: pd.DataFrame, interval_seconds: int = 300) -> list[dict[str, Any]]:
    """Compare changes over 5-minute intervals; differences are descriptive, not causal."""
    if comparison.empty or comparison["You"].notna().sum() < 2:
        return []
    max_s = int(comparison.seconds.max())
    results = []
    for start in range(0, max_s, interval_seconds):
        end = min(start + interval_seconds, max_s)
        start_rows = comparison[comparison.seconds <= start]
        end_rows = comparison[comparison.seconds <= end]
        if start_rows.empty or end_rows.empty:
            continue
        a, b = start_rows.iloc[-1], end_rows.iloc[-1]
        your_a, your_b = a["You"], b["You"]
        if pd.isna(your_a) or pd.isna(your_b):
            continue
        own = round(float(your_b - your_a))
        allies = None
        if pd.notna(a["Teammate average"]) and pd.notna(b["Teammate average"]):
            allies = round(float(b["Teammate average"] - a["Teammate average"]))
        results.append({
            "start_min": round(start / 60, 1),
            "end_min": round(end / 60, 1),
            "your_soul_gain": own,
            "teammate_avg_gain": allies,
            "relative_gain": own - allies if allies is not None else None,
        })
    return results


def normalize_benchmark(data: Any) -> pd.DataFrame:
    """Only use documented fields and absolute-time bucket rows."""
    if not isinstance(data, list):
        return pd.DataFrame(columns=["seconds", "minute", "High-rank hero average"])
    rows = []
    for entry in data:
        if not isinstance(entry, dict):
            continue
        second = first_number(entry, "game_time")
        networth = first_number(entry, "net_worth_avg")
        if second is not None and networth is not None:
            rows.append({"seconds": int(second), "High-rank hero average": networth})
    if not rows:
        return pd.DataFrame(columns=["seconds", "minute", "High-rank hero average"])
    df = pd.DataFrame(rows).sort_values("seconds").drop_duplicates("seconds")
    df["minute"] = df.seconds / 60
    return df


def overview(payload: dict, selected_key: str, hero_names: dict[int, str] | None = None) -> dict:
    players = get_players(payload)
    pairs = [(player_key(player, idx), player) for idx, player in enumerate(players)]
    candidate = next(((key, player) for key, player in pairs if key == selected_key), None)
    if candidate is None:
        raise ValueError("Selected player does not appear in this match.")
    key, player = candidate
    match = match_info(payload)
    stats = player_final_stats(player)
    team = str(player.get("team", "?"))
    friends = [player_final_stats(p) for pk, p in pairs if pk != key and str(p.get("team", "?")) == team]
    enemies = [player_final_stats(p) for pk, p in pairs if str(p.get("team", "?")) != team]
    def avg(field, players_list):
        vals = [p[field] for p in players_list if p[field] is not None]
        return round(sum(vals) / len(vals), 1) if vals else None
    raw = timeline_frame(payload)
    maximum = float(raw.seconds.max()) if not raw.empty else 0
    duration = first_number(match, "duration_s", "match_duration_s")
    if duration is None:
        duration = maximum if maximum else None
    return {
        "match_id": match.get("match_id", payload.get("match_id")),
        "hero_id": player.get("hero_id"),
        "hero": (hero_names or {}).get(player.get("hero_id"), f"Hero {player.get('hero_id', '?')}"),
        "player": player_label(player, pairs.index(candidate), hero_names),
        "team": patron_name(team),
        "duration_minutes": round(duration / 60, 1) if duration else None,
        "stats": stats,
        "teammates_average": {field: avg(field, friends) for field in STAT_FIELDS},
        "opponents_average": {field: avg(field, enemies) for field in STAT_FIELDS},
        "data_coverage": {
            "timeline_sample_count": int((raw.player_key == selected_key).sum()) if not raw.empty else 0,
            "available_timeline_fields": [field for field in STAT_FIELDS
                if not raw.empty and raw.loc[raw.player_key == selected_key, field].notna().any()],
        },
    }


def focus_snapshot(raw: pd.DataFrame, selected_key: str, start_min: int, end_min: int) -> dict:
    series = raw[raw.player_key == selected_key].sort_values("seconds")
    if series.empty:
        return {"note": "No timestamped player data was available."}
    start = series[series.seconds <= start_min * 60]
    end = series[series.seconds <= end_min * 60]
    if start.empty or end.empty:
        return {"note": "Not enough samples for the selected time window."}
    a, b = start.iloc[-1], end.iloc[-1]
    out = {"actual_start_min": round(float(a.seconds) / 60, 1),
           "actual_end_min": round(float(b.seconds) / 60, 1)}
    for field in ("net_worth", "kills", "deaths", "assists", "player_damage", "player_healing", "last_hits"):
        if pd.notna(a[field]) and pd.notna(b[field]):
            out[f"{field}_gain"] = round(float(b[field] - a[field]), 1)
    return out
