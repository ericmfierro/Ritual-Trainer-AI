"""Ritual Trainer.ai — Deadlock match analysis and evidence-grounded AI coaching."""
from __future__ import annotations

import json
import os
from pathlib import Path

import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from dotenv import load_dotenv

from ritual_api import DeadlockApiError, DeadlockClient
from ritual_knowledge import AssetClient, KnowledgeUnavailable, build_knowledge_pack
from ritual_coach import ask_followup, generate_report, default_model, provider_ready
from ritual_roles import AUTO_ROLE, ROLE_OPTIONS, ROLES, ROLE_BY_NAME, resolve_role, suggested_roles
from ritual_teams import patron_name
from ritual_core import (
    comparison_frame,
    first_number,
    focus_snapshot,
    get_players,
    interval_summary,
    match_info,
    normalize_benchmark,
    overview,
    player_final_stats,
    player_key,
    player_label,
    timeline_frame,
)

load_dotenv()
st.set_page_config(page_title="Ritual Trainer.ai", page_icon="◈", layout="wide", initial_sidebar_state="expanded")
st.markdown("""
<style>
.stApp {background: radial-gradient(circle at 95% 0%, #262320 0%, #101415 36%, #0c1113 100%); color: #f5efdf;}
h1, h2, h3 {letter-spacing: -.025em;}
h1 {color: #f1ce8a !important;}
[data-testid="stHeader"] {background: rgba(12, 17, 19, 0.75);}
[data-testid="stSidebar"] h2 {color:#edc47b;}
.stTabs [data-baseweb="tab-highlight"] {background-color: #e0ae70;}
.stCaption {line-height: 1.5;}
[data-testid="stSidebar"] {background: #131a1b;}
[data-testid="stMetric"] {border: 1px solid #37403d; border-radius: 12px; padding: 13px 14px; background: #172020;}
[data-testid="stMetricLabel"] {color: #d2c3a2;}
.stButton>button[kind="primary"] {background: #dfac61; color: #18201e; border: none; font-weight: 750;}
.stTabs [data-baseweb="tab"] {font-weight: 650;}
div[data-testid="stAlert"] {border-radius: 10px;}
</style>
""", unsafe_allow_html=True)

ROOT = Path(__file__).parent
DEMO_PATH = ROOT / "data" / "sample_match.json"
DEMO_HERO_PATH = ROOT / "data" / "demo_heroes.json"


@st.cache_data(ttl=600, show_spinner=False)
def get_match_remote(match_id: int) -> dict:
    return DeadlockClient().match(match_id)


@st.cache_data(ttl=86400, show_spinner=False)
def get_hero_names() -> dict[int, str]:
    return DeadlockClient().heroes()


@st.cache_data(ttl=3600, show_spinner=False)
def get_item_names() -> dict[int, str]:
    return DeadlockClient().items()


@st.cache_data(ttl=21600, show_spinner=False)
def get_current_hero(hero_id: int) -> dict:
    return AssetClient().hero(hero_id)


@st.cache_data(ttl=21600, show_spinner=False)
def get_current_assets() -> list[dict]:
    return AssetClient().all_items()


@st.cache_data(ttl=1800, show_spinner=False)
def get_replay_schema(match_id: int):
    return DeadlockClient().demo_schema(match_id)


@st.cache_data(ttl=43200, show_spinner=False)
def get_curve(hero_id: int, threshold: int, lookback_days: int) -> list[dict]:
    return DeadlockClient().high_rank_curve(hero_id, threshold, lookback_days)


@st.cache_data(ttl=3600, show_spinner=False)
def get_patches() -> list[dict]:
    return DeadlockClient().recent_patches(3)


@st.cache_data(ttl=21600, show_spinner=False)
def get_item_meta(hero_id: int, threshold: int, lookback_days: int) -> list[dict]:
    return DeadlockClient().hero_item_meta(hero_id, threshold, lookback_days)


def set_match(data: dict, demo: bool, hero_names: dict[int, str]):
    get_players(data)
    st.session_state.match_data = data
    st.session_state.demo_mode = demo
    st.session_state.hero_names = hero_names
    for name in ("ai_report", "ai_chat", "cohort", "patches", "items_map", "meta_items", "last_selected", "knowledge", "replay_schema"):
        st.session_state.pop(name, None)


def metric(v, suffix: str = "", missing: str = "N/A") -> str:
    if v is None or pd.isna(v):
        return missing
    return f"{v:,.0f}{suffix}"


def render_chart(df: pd.DataFrame, cols: dict[str, str], y_label: str, title: str):
    fig = go.Figure()
    for field, color in cols.items():
        if field in df.columns and df[field].notna().any():
            fig.add_trace(go.Scatter(x=df["minute"], y=df[field], name=field,
                                     mode="lines", line={"color": color, "width": 3},
                                     hovertemplate="%{x:.1f} min · %{y:,.0f}<extra>%{fullData.name}</extra>"))
    fig.update_layout(title={"text": title, "font": {"size": 17}}, height=380,
                      margin={"l": 16, "r": 16, "t": 60, "b": 20},
                      paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                      font={"color": "#ede4d2"}, legend={"orientation": "h", "y": -0.22},
                      xaxis={"title": "Match minute", "gridcolor": "#303838"},
                      yaxis={"title": y_label, "gridcolor": "#303838"},
                      hovermode="x unified")
    st.plotly_chart(fig, use_container_width=True)


def benchmark_context(df: pd.DataFrame, threshold: int, lookback: int) -> dict:
    if df.empty:
        return {"available": False, "reason": "No verified hero/rank curve loaded."}
    sample = df.sort_values("seconds").iloc[::max(1, len(df) // 18)]
    return {"available": True, "source": "Deadlock API /v1/analytics/player-performance-curve",
            "cohort": f"Ranked normal-mode games, same hero, average badge >= {threshold}, last {lookback} days",
            "sample_size": "Not returned by this endpoint; do not claim a sample size",
            "net_worth_curve": [{"minute": round(float(r.minute), 1),
                                  "mean_souls": int(r["High-rank hero average"])}
                                 for _, r in sample.iterrows()]}


def item_summary(player: dict, names: dict[int, str]) -> list[dict]:
    raw = player.get("items", [])
    if not isinstance(raw, list):
        return []
    result = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        item_id = entry.get("item_id")
        when = first_number(entry, "game_time_s", "purchase_time_s")
        result.append({"item": names.get(item_id, f"Item ID {item_id}"),
                       "minute": round(when / 60, 1) if when is not None else None,
                       "item_id": item_id})
    return sorted(result, key=lambda r: r["minute"] if r["minute"] is not None else 99999)[:35]


with st.sidebar:
    st.markdown("## ◈ Ritual Trainer.ai")
    st.caption("THE PATRON'S LEDGER · DEADLOCK MATCH REVIEW")
    mode = st.radio("Choose your record", ["Sample match", "Real Deadlock match ID", "Upload match metadata JSON"], index=0)
    match_id = None
    if mode == "Real Deadlock match ID":
        match_text = st.text_input("Match ID", placeholder="e.g. 92484329")
        if match_text and not match_text.isdecimal():
            st.warning("Match ID must contain digits only.")
        elif match_text:
            match_id = int(match_text)
    uploaded = st.file_uploader("Metadata JSON", type=["json"], help="API match metadata JSON, not a .dem video file") if mode == "Upload match metadata JSON" else None
    load_clicked = st.button("Open the match ledger", type="primary", use_container_width=True)
    st.divider()
    st.subheader("Shape your training")
    role_preference = st.selectbox(
        "Role / soul priority", ROLE_OPTIONS,
        help="Flexible community archetypes indicate farm priority and team responsibilities, not locked hero classes.",
    )
    if role_preference == AUTO_ROLE:
        st.caption("The Oracle suggests a playstyle from your hero; override it to reflect your actual soul priority and duties.")
    else:
        example_role = ROLE_BY_NAME[role_preference]
        st.caption("Example heroes: " + ", ".join(example_role.heroes))
        st.caption("Soul priority: " + example_role.farm_priority)
        st.caption("Training emphasis: " + example_role.coaching_angle)
    with st.expander("Hero roles and example heroes"):
        st.caption("Community framework, not official locked roles or a tier list. A build can change a hero’s duties and soul priority.")
        for r in ROLES:
            st.markdown(f"**{r.name}**")
            st.caption("Examples: " + ", ".join(r.heroes))
            st.caption("Soul priority: " + r.farm_priority)
    emphasis = st.selectbox("Training focus", ["Balanced improvement", "Farming and rotations", "Combat and positioning", "Team contribution", "Survivability", "Itemization"])
    provider = st.selectbox("Coaching engine", ["Ollama (local, offline)", "Gemini (free tier)"],
                            help="Gemini uses a free-tier API key. Ollama runs an open-source model on your own PC.")
    model = st.text_input("AI model", value=default_model(provider), key=f"model_{provider}",
                          help="Local Ollama: gpt-oss:20b. Gemini is optional and may be free-tier limited.")
    if provider == "Gemini (free tier)":
        st.caption("Recommended: `gemini-3.8-flash` · Free-tier alternative: `gemini-3.5-flash-lite`. If Google rejects an old model, edit this field and your `.env` file.")
    if provider == "Gemini (free tier)":
        env_key = os.getenv("GEMINI_API_KEY", "")
        api_key = st.text_input("Gemini API key (optional when saved in .env)", value="", type="password") or env_key
        st.caption("Use a Gemini project labeled Free Tier. Do not enable billing if you want zero API charges.")
    else:
        api_key = ""
        st.caption("Ollama runs locally, without an API key. Required model: `ollama pull gpt-oss:20b`.")
    st.caption("Do not upload your .env file or any API credentials to GitHub.")
    st.divider()
    st.caption("Fan-made training ledger from the Cursed Apple. Not affiliated with Valve or the Deadlock API team.")

if load_clicked:
    if mode == "Sample match":
        set_match(json.loads(DEMO_PATH.read_text(encoding="utf-8")), True,
                  {int(k): v for k, v in json.loads(DEMO_HERO_PATH.read_text()).items()})
        st.success("Training record opened. All sample statistics are fictional.")
    elif mode == "Upload match metadata JSON":
        if uploaded is None:
            st.warning("Choose a JSON match metadata file first.")
        else:
            try:
                data = json.load(uploaded)
                get_players(data)
                set_match(data, False, {})
                st.success("Match record opened from your metadata JSON.")
            except (ValueError, json.JSONDecodeError, TypeError) as exc:
                st.error(f"Not a valid match metadata file: {exc}")
    elif match_id:
        try:
            with st.spinner("Searching the archives for your match…"):
                data = get_match_remote(match_id)
                try:
                    names = get_hero_names()
                except DeadlockApiError:
                    names = {}
            set_match(data, False, names)
            st.success(f"Match {match_id} entered into the ledger from the community Deadlock API.")
        except (DeadlockApiError, ValueError) as exc:
            st.error(str(exc))
    else:
        st.warning("Enter a valid match ID first.")

st.title("◈ Ritual Trainer.ai")
st.markdown("**Every soul leaves a trace. Read the match. Rewrite the next ritual.**")
st.caption("An independent Deadlock coaching archive · The Cursed Apple · Patrons · Souls · Evidence-driven improvement")

if "match_data" not in st.session_state:
    st.info("Begin your investigation: choose **Sample match** or enter a real match ID, then select **Open the match ledger** in the sidebar.")
    st.stop()

payload = st.session_state.match_data
names = st.session_state.hero_names
players = get_players(payload)
labels = {player_key(p, i): player_label(p, i, names) for i, p in enumerate(players)}
selected_key = st.selectbox("Select the player to coach", list(labels), format_func=lambda k: labels[k])
selected = next(p for i, p in enumerate(players) if player_key(p, i) == selected_key)
selected_hero = names.get(selected.get("hero_id"), f"Hero {selected.get('hero_id', '?')}")
resolved_role = resolve_role(selected_hero, role_preference)
role = str(resolved_role["role"])
if st.session_state.get("last_selected") != selected_key:
    st.session_state.pop("ai_report", None)
    st.session_state.pop("ai_chat", None)
    st.session_state.pop("knowledge", None)
    st.session_state.last_selected = selected_key
coaching_signature = (selected_key, role, emphasis, provider, model)
if st.session_state.get("last_coaching_signature") != coaching_signature:
    st.session_state.pop("ai_report", None)
    st.session_state.pop("ai_chat", None)
    st.session_state.last_coaching_signature = coaching_signature
raw = timeline_frame(payload)
summary = overview(payload, selected_key, names)
comparison = comparison_frame(raw, selected_key)
windows = interval_summary(comparison)

if st.session_state.demo_mode:
    st.warning("TRAINING ILLUSION — Real Deadlock hero names, fictional match statistics. For testing the ledger, charts, and coaching prompts only.")
else:
    st.caption("MATCH ARCHIVE — Statistics come from the community API or an uploaded record. Data coverage varies by match.")
if role != "Not specified":
    st.caption(f"**Intended role:** {role} · {resolved_role['source']}. "
               + (f"Other possible playstyles for {selected_hero}: {', '.join(resolved_role['other_plausible_roles'])}. "
                  if resolved_role['other_plausible_roles'] else "")
               + f"Soul priority: {resolved_role['farm_priority']} Roles are flexible and change with your build and team needs.")
else:
    st.caption("**Intended role:** Not specified for this hero. Select your farm priority in the sidebar for role-aware coaching.")

st.caption(f"**Your Patron:** {patron_name(selected.get('team'))}")
m1, m2, m3, m4, m5 = st.columns(5)
final = summary["stats"]
m1.metric("Souls", metric(final["net_worth"]))
m2.metric("Kills / Deaths / Assists", "/".join(metric(final[k], missing="-") for k in ("kills", "deaths", "assists")))
m3.metric("Hero damage", metric(final["player_damage"]))
m4.metric("Healing", metric(final["player_healing"]))
m5.metric("Duration", f"{summary['duration_minutes']} min" if summary["duration_minutes"] else "N/A")

overview_tab, economy_tab, team_tab, replay_tab, coach_tab, sources_tab = st.tabs([
    "The Match Ledger", "The Soul Ledger", "Battle Chronicle", "Replay Forensics", "Consult the Oracle", "The Archives"])

with overview_tab:
    st.subheader("The match at a glance")
    c1, c2 = st.columns([1.2, 1])
    with c1:
        rows = []
        for idx, person in enumerate(players):
            stats = player_final_stats(person)
            rows.append({"Patron": patron_name(person.get("team")),
                         "Player": player_label(person, idx, names),
                         "K": stats["kills"], "D": stats["deaths"], "A": stats["assists"],
                         "Souls": stats["net_worth"], "Damage": stats["player_damage"]})
        st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
    with c2:
        st.markdown("#### Record completeness")
        count = summary["data_coverage"]["timeline_sample_count"]
        st.metric("Player timeline samples", count)
        available = summary["data_coverage"]["available_timeline_fields"]
        st.write("Available timeline metrics: " + (", ".join(available) if available else "None"))
        st.info("A low statistic isn't automatically a mistake. Role, matchup, objectives, and available opportunities all matter.")
    st.markdown("#### Acquired relics · Item purchases")
    item_names = st.session_state.get("items_map", {})
    if st.button("Resolve current item names via API"):
        if st.session_state.demo_mode:
            st.info("Fictional sample items have no real asset IDs.")
        else:
            try:
                st.session_state.items_map = get_item_names()
                item_names = st.session_state.items_map
            except DeadlockApiError as exc:
                st.warning(str(exc))
    purchases = item_summary(selected, item_names)
    if purchases:
        st.dataframe(pd.DataFrame(purchases), hide_index=True, use_container_width=True)
        st.caption("Item purchase records are evidence of timing, not proof an item was correct for the matchup.")
    else:
        st.caption("No purchase list available for this player in the supplied metadata.")

with economy_tab:
    st.subheader("Follow the souls")
    st.caption("Trace where your soul income diverged from the rest of the lobby. A gap is a clue, not a verdict.")
    if not comparison.empty and comparison["You"].notna().any():
        render_chart(comparison, {
            "You": "#efbe70", "Teammate average": "#7cc8bd", "Opponent average": "#c18ee6",
        }, "Cumulative souls", "Soul ledger · Income over time")
        st.caption("Teammate and opponent averages include different heroes and roles. They are descriptive, not skill-adjusted benchmarks.")
        if windows:
            valid_windows = [w for w in windows if w["relative_gain"] is not None]
            if valid_windows:
                worst = min(valid_windows, key=lambda w: w["relative_gain"])
                st.info(f"Largest relative 5-minute farming gap: **{worst['start_min']:g}–{worst['end_min']:g} min**. "
                        f"You gained **{worst['your_soul_gain']:,} souls** vs teammate average **{worst['teammate_avg_gain']:,} souls**. "
                        "Review the replay for context; this comparison does not identify the cause.")
            st.dataframe(pd.DataFrame(windows).rename(columns={
                "start_min":"Start (min)", "end_min":"End (min)",
                "your_soul_gain":"Your soul gain", "teammate_avg_gain":"Teammate avg. gain",
                "relative_gain":"Difference"}), use_container_width=True, hide_index=True)
    else:
        st.warning("This match does not include enough timestamped net-worth data for an economy chart.")

    st.divider()
    st.subheader("Study high-rank practitioners of your hero")
    st.caption("This is a cohort average—not proof of what any one professional player would do.")
    b1, b2 = st.columns(2)
    with b1:
        min_badge = st.slider("Minimum average match badge", 0, 116, 91, help="API filter; higher values restrict the cohort.")
    with b2:
        lookback = st.selectbox("Comparison period", [7, 14, 30, 60], index=2, format_func=lambda d: f"Last {d} days")
    if st.button("Load high-rank benchmark and item trends"):
        if st.session_state.demo_mode:
            st.info("Live cohort comparison is disabled for fictional heroes.")
        elif summary["hero_id"] is None:
            st.warning("No hero ID was found for the selected player.")
        else:
            try:
                with st.spinner("Loading high-rank curve…"):
                    curve = get_curve(int(summary["hero_id"]), min_badge, lookback)
                st.session_state.cohort = {"data": curve, "hero_id": summary["hero_id"],
                                            "threshold": min_badge, "lookback": lookback}
                try:
                    st.session_state.meta_items = get_item_meta(int(summary["hero_id"]), min_badge, lookback)
                    st.session_state.items_map = get_item_names()
                except DeadlockApiError as exc:
                    st.warning(f"Item trends unavailable; economy benchmark remains usable. {exc}")
            except DeadlockApiError as exc:
                st.warning(f"Benchmark unavailable: {exc}")
    cohort = st.session_state.get("cohort", {})
    if cohort and cohort.get("hero_id") == summary["hero_id"]:
        cohort_frame = normalize_benchmark(cohort.get("data", []))
        if not cohort_frame.empty:
            combined = comparison[["minute", "You"]].merge(
                cohort_frame[["minute", "High-rank hero average"]], how="outer", on="minute").sort_values("minute")
            render_chart(combined, {"You": "#efbe70", "High-rank hero average": "#7cc8bd"},
                         "Cumulative souls", "You vs high-rank same-hero cohort")
            st.caption(f"Ranked normal-mode matches · Same hero · Average badge ≥ {cohort['threshold']} · Last {cohort['lookback']} days. "
                       "The endpoint does not return sample counts; interpret cautiously.")
        else:
            st.info("No comparable curve was returned for this hero and filter.")

        meta_items = st.session_state.get("meta_items", [])
        item_names = st.session_state.get("items_map", {})
        if isinstance(meta_items, list) and meta_items and item_names:
            rows = []
            for row in meta_items:
                if not isinstance(row, dict):
                    continue
                item_id = row.get("item_id")
                count = row.get("matches")
                wins = row.get("wins")
                name = item_names.get(item_id)
                if not name or not isinstance(count, int) or count < 20:
                    continue
                rows.append({"Item": name, "Purchase matches": count,
                             "Buyer win rate": round(100*wins/count, 1) if isinstance(wins, (int, float)) else None,
                             "Avg. buy minute": round(float(row.get("avg_buy_time_s", 0))/60, 1)})
            rows = sorted(rows, key=lambda r: r["Purchase matches"], reverse=True)[:12]
            if rows:
                st.markdown("#### Recent high-rank item purchasing trends")
                st.dataframe(pd.DataFrame(rows), hide_index=True, use_container_width=True)
                st.caption("Ranked same-hero purchases for the filters above. Buyer win rate is observational and affected by selection bias, timing, and game state; not proof of item strength.")

with team_tab:
    st.subheader("The battle chronicle")
    st.caption("Track damage, healing, and combat events across the ritual. Numbers alone cannot show positioning or intent.")
    own = raw[raw.player_key == selected_key].copy()
    if not own.empty:
        own["minute"] = own.seconds / 60
        if own.player_damage.notna().any():
            render_chart(own, {"player_damage": "#ecaf7a"}, "Cumulative damage", "Damage to heroes")
        if own.player_healing.notna().any():
            render_chart(own, {"player_healing": "#79cdb9"}, "Cumulative healing", "Healing contribution")
        if own.kills.notna().any():
            render_chart(own, {"kills": "#edb963", "assists": "#7cc8bd", "deaths": "#d5808c"},
                         "Cumulative events", "Kill / assist / death progression")
    else:
        st.warning("No timestamped combat statistics were supplied for this player.")
    st.caption("Damage, healing, and KDA are partial signals; teamfight positioning and objective decisions need replay evidence.")

with replay_tab:
    st.subheader("Replay Forensics · Inspect the archive")
    st.caption("This stage checks the demo parser's queryable schema. It does not yet extract movements, ability casts or fights, and it never claims to have watched footage.")
    replay_id = summary.get("match_id")
    if st.session_state.demo_mode or not str(replay_id or "").isdecimal():
        st.info("Open a real match ID to check replay availability. The fictional sample has no replay.")
    else:
        if st.button("Check whether this replay is queryable"):
            try:
                with st.spinner("Checking the replay archive; this may take a while…"):
                    result = get_replay_schema(int(replay_id))
                st.session_state.replay_schema = {"match_id": replay_id, "schema": result}
                st.success("Replay schema returned. This indicates queryable tables were advertised, not that we have extracted player movements.")
            except (DeadlockApiError, ValueError) as exc:
                st.warning(f"Could not inspect this replay: {exc}")
        saved = st.session_state.get("replay_schema", {})
        if saved.get("match_id") == replay_id:
            schema = saved["schema"]
            with st.expander("View queryable replay schema"):
                st.json(schema, expanded=False)
            st.caption("Next development stage: select and test event/entity tables, submit safe fixed queries, then use verified timestamped events for coaching. No SQL queries are submitted in v0.6.")

with coach_tab:
    st.subheader("Ask the Oracle · Personalized coaching")
    st.caption("The Oracle reads measured evidence, not unseen replay footage. Expect specific drills, explanations, and priorities.")
    ready = provider_ready(provider, api_key)
    if ready and provider == "Gemini (free tier)":
        st.success("Gemini key detected (not yet verified). The Oracle can request a free-tier report, subject to available quota.")
    elif ready:
        st.info("Local mode selected. Make sure Ollama is running with the selected model downloaded.")
    else:
        st.warning("The Oracle needs a Gemini API key. Add GEMINI_API_KEY in .env or the sidebar, or switch to local Ollama.")
    if not windows:
        st.caption("The report will acknowledge that interval-level evidence is unavailable.")
    max_minute = int(raw.seconds.max() // 60) if not raw.empty else 0
    if max_minute >= 2:
        focus_start, focus_end = st.slider("Analyze a particular match period (minutes)", 0,
                                           max_minute, (min(10, max_minute - 1), min(20, max_minute)))
    else:
        focus_start, focus_end = 0, max_minute
    focus = focus_snapshot(raw, selected_key, focus_start, focus_end)
    cohort = st.session_state.get("cohort", {})
    benchmark_df = normalize_benchmark(cohort.get("data", [])) if cohort.get("hero_id") == summary["hero_id"] else pd.DataFrame()
    cohort_ctx = benchmark_context(benchmark_df, cohort.get("threshold", 91), cohort.get("lookback", 30))
    patches = st.session_state.get("patches", [])
    if st.button("Refresh recent patch information"):
        if st.session_state.demo_mode:
            st.info("Patch lookup is optional in demo mode; recommendations will not claim to know a current meta.")
        else:
            try:
                st.session_state.patches = get_patches()
                patches = st.session_state.patches
            except DeadlockApiError as exc:
                st.warning(f"Patch feed unavailable: {exc}")
    for patch in patches[:3]:
        st.caption(f"Patch feed: {patch['title']} · {patch.get('date') or 'date unknown'}")
    data_for_ai = dict(summary)
    data_for_ai["hero_combat_archetype"] = resolved_role
    data_for_ai["economy_windows"] = windows[:24]
    data_for_ai["selected_items"] = item_summary(selected, st.session_state.get("items_map", {}))
    trend_data = st.session_state.get("meta_items", [])
    item_map = st.session_state.get("items_map", {})
    if cohort.get("hero_id") == summary["hero_id"] and isinstance(trend_data, list):
        top_trends = []
        for row in sorted((r for r in trend_data if isinstance(r, dict) and isinstance(r.get("matches"), int)),
                          key=lambda r: r["matches"], reverse=True):
            item_name = item_map.get(row.get("item_id"))
            if item_name and row["matches"] >= 20:
                top_trends.append({"item": item_name, "purchase_matches": row["matches"],
                                   "buyer_wins": row.get("wins"), "avg_buy_time_seconds": row.get("avg_buy_time_s")})
            if len(top_trends) == 12:
                break
        data_for_ai["high_rank_hero_item_purchase_trends"] = {
            "filters": f"same hero, average badge >= {cohort.get('threshold')}, ranked normal-mode games, last {cohort.get('lookback')} days",
            "source": "Deadlock API item-stats (observational item purchase counts, not a build guide)",
            "items": top_trends,
        }
    data_for_ai["timeline_warning"] = "Statistics do not reveal locations, intentions, fights, or mistakes directly."
    data_for_ai["match_source"] = "fictional demonstration" if st.session_state.demo_mode else "live community API metadata"
    if not st.session_state.demo_mode and (not cohort_ctx.get("available") or not patches):
        st.info("For patch-aware, higher-rank coaching, load a high-rank benchmark in **The Soul Ledger** "
                "and select **Refresh recent patch information** before generating your report. "
                "Without those sources, the AI must avoid unsupported meta claims.")
    st.divider()
    st.markdown("#### Verified hero knowledge · The Archivist")
    st.caption("Loads game-file-derived hero abilities and purchased item definitions. Refresh after patches. This does not observe actions in the replay.")
    existing = st.session_state.get("knowledge", {})
    if existing.get("hero", {}).get("id") != summary.get("hero_id"):
        existing = {}
    def load_knowledge():
        if st.session_state.demo_mode:
            raise KnowledgeUnavailable("The sample match is fictional. Hero mechanics will not be attached to made-up match data.")
        hid = summary.get("hero_id")
        if not isinstance(hid, int) or hid <= 0:
            raise KnowledgeUnavailable("This match has no valid hero ID.")
        hero_record = get_current_hero(hid)
        item_records = get_current_assets()
        return build_knowledge_pack(hero_record, item_records, data_for_ai["selected_items"])
    if st.button("Refresh verified hero and item information", disabled=st.session_state.demo_mode):
        try:
            with st.spinner("Fetching the selected hero's current kit and purchased items…"):
                existing = load_knowledge()
            st.session_state.knowledge = existing
            st.session_state.pop("ai_report", None)
            st.success("Game-data reference loaded for this hero.")
        except (KnowledgeUnavailable, ValueError) as exc:
            st.warning(str(exc))
    if existing:
        hero_def = existing.get("hero", {})
        st.caption(f"Asset reference: {hero_def.get('name', 'Unknown')} · Retrieved {existing.get('retrieved_utc', 'unknown')} · "
                   f"{len(existing.get('hero_abilities', []))} linked ability definitions · "
                   f"{len(existing.get('purchased_item_definitions', []))} purchased item definitions")
        with st.expander("Review evidence supplied to the model"):
            st.json(existing, expanded=False)
    else:
        st.warning("No verified hero kit loaded. You can still generate a statistical report, but the coach must not invent hero abilities or item effects.")
    if st.button("Consult the Oracle · Generate coaching", type="primary", disabled=not ready):
        try:
            if not existing and not st.session_state.demo_mode:
                try:
                    with st.spinner("Gathering verified hero information…"):
                        existing = load_knowledge()
                        st.session_state.knowledge = existing
                except (KnowledgeUnavailable, ValueError) as exc:
                    st.warning(f"Game reference unavailable; report will be limited to verified statistics. {exc}")
            with st.spinner("The Oracle is examining the match evidence…"):
                st.session_state.ai_report = generate_report(provider, api_key, model, data_for_ai, cohort_ctx,
                                                              patches, role, emphasis, focus, existing)
                st.session_state.ai_chat = []
        except Exception as exc:
            st.error(f"AI request failed: {type(exc).__name__}: {exc}")
    if st.session_state.get("ai_report"):
        st.divider()
        st.markdown(st.session_state.ai_report)
        st.download_button("Download coaching report", st.session_state.ai_report,
                           file_name="ritual_trainer_report.md", mime="text/markdown")
        st.markdown("### Question the Oracle")
        for turn in st.session_state.get("ai_chat", []):
            with st.chat_message(turn["role"]):
                st.markdown(turn["content"])
        question = st.chat_input("Ask about a soul deficit, rotation, item decision, or practice drill…")
        if question:
            st.session_state.ai_chat.append({"role": "user", "content": question})
            try:
                with st.spinner("Reviewing the evidence…"):
                    answer = ask_followup(provider, api_key, model, question, st.session_state.ai_report,
                                          data_for_ai, cohort_ctx, patches, role, emphasis, focus, existing)
                st.session_state.ai_chat.append({"role": "assistant", "content": answer})
                st.rerun()
            except Exception as exc:
                st.error(f"Follow-up failed: {type(exc).__name__}: {exc}")
    else:
        st.info("The model will produce a multi-part diagnosis, concrete drills, measurable goals, and a replay review checklist. "
                "It will distinguish observed statistics from hypotheses.")

with sources_tab:
    st.subheader("The archives · Sources and limits")
    st.caption("Even the Patron's ledger has blind spots. Here's where the evidence comes from.")
    st.markdown("""
**Match metadata:** [Community Deadlock API](https://api.deadlock-api.com/docs),
`/v1/matches/{match_id}/metadata`.

**Hero/rank benchmark:** `/v1/analytics/player-performance-curve` with explicit hero, rank, mode,
and recent-date filters. Not equivalent to reviewing the gameplay of a named top player.

**Item meta reference:** `/v1/analytics/item-stats` with hero, rank, mode, and date filters. Purchase frequency and buyer win rates are observational, not causal.

**Patch awareness:** `/v2/patches`. Patch headlines alone do not verify tactical recommendations.

**Current hero and purchased item descriptions:** `https://api.deadlock-api.com/v1/assets/heroes/{hero_id}` and `/v1/assets/items`, refreshed periodically; definitions are game-file-derived, not observations of replay actions.

**Replay availability:** `GET /v1/matches/demo/schema?match_id=...` can inspect the schema of a queryable demo. v0.6 does not submit replay SQL jobs or extract motion data.

**Roles and soul priority:** A flexible community framework (hard carry, tempo/off-carry, frontliner/space creator, support/utility); not fixed official Deadlock roles.
The selected hero can fit multiple archetypes, and player choice takes precedence.
Examples: [Deadlock community role guide](https://deadlock.io/mechanics/hero-roles-and-tags).

**Important:** The application reads API statistics and, when retrieved, hero/item descriptions. It does not yet extract replay events or watch footage. The AI cannot observe your
rotations, positioning, or objective calls unless future replay evidence is actually provided.
""")
    st.json({"match": summary, "periods": windows[:30],
             "selected_focus": focus_snapshot(raw, selected_key, 0, max_minute)}, expanded=False)
    st.caption("No game account login is necessary. API credentials are not included in the exported report.")
