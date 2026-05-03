import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
from shared.utils import (
    TIMEZONES, DEFAULT_TZ_NAME,
    convert_to_tz, get_future_games, get_national_teams,
    get_games_for_team, get_games_in_time_range,
    get_all_weeks, get_games_for_week, get_flag,
)
from shared.fetch import fetch_schedule

st.set_page_config(
    page_title="FIFA World Cup 2026",
    page_icon="⚽",
    layout="wide",
)

st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }

    .game-card {
        background: #ffffff;
        border-radius: 14px;
        padding: 18px 24px;
        margin: 10px 0;
        box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        border-left: 5px solid #2e7d32;
    }
    .game-card.knockout { border-left-color: #1565c0; }
    .game-row {
        display: flex;
        justify-content: space-between;
        align-items: center;
        gap: 12px;
    }
    .team-block {
        flex: 1;
        display: flex;
        align-items: center;
        gap: 10px;
        font-size: 17px;
        font-weight: 600;
        color: #1a1a2e;
    }
    .team-block.right { justify-content: flex-end; }
    .team-flag { font-size: 26px; }
    .center-block {
        text-align: center;
        min-width: 120px;
    }
    .game-time {
        font-size: 28px;
        font-weight: 800;
        color: #1565c0;
        line-height: 1.1;
    }
    .game-date {
        font-size: 13px;
        color: #666;
        margin-top: 2px;
    }
    .tz-label {
        font-size: 11px;
        color: #999;
    }
    .game-meta {
        margin-top: 12px;
        display: flex;
        align-items: center;
        gap: 14px;
        font-size: 13px;
        color: #777;
    }
    .badge {
        background: #e8f5e9;
        color: #2e7d32;
        padding: 3px 10px;
        border-radius: 20px;
        font-size: 12px;
        font-weight: 600;
    }
    .badge.knockout-badge { background: #e3f2fd; color: #1565c0; }
    .vs { font-size: 15px; font-weight: 700; color: #bbb; }
</style>
""", unsafe_allow_html=True)

GROUP_LABELS = {
    "R32": "Round of 32",
    "R16": "Round of 16",
    "QF": "Quarter-Final",
    "SF": "Semi-Final",
    "3RD": "3rd Place",
    "FINAL": "Final",
}
KNOCKOUT_STAGES = {"R32", "R16", "QF", "SF", "3RD", "FINAL"}


def format_group(group):
    if group in GROUP_LABELS:
        return GROUP_LABELS[group]
    if group and len(group) == 1:
        return f"Group {group}"
    return group or ""


def render_game_card(game, dt, tz_name):
    home_flag = get_flag(game["home_team"])
    away_flag = get_flag(game["away_team"])
    group = game.get("group", "")
    group_label = format_group(group)
    is_knockout = group in KNOCKOUT_STAGES
    card_class = "game-card knockout" if is_knockout else "game-card"
    badge_class = "badge knockout-badge" if is_knockout else "badge"

    st.markdown(f"""
    <div class="{card_class}">
        <div class="game-row">
            <div class="team-block">
                <span class="team-flag">{home_flag}</span>
                <span>{game["home_team"]}</span>
            </div>
            <div class="center-block">
                <div class="game-time">{dt.strftime("%H:%M")}</div>
                <div class="game-date">{dt.strftime("%a, %b %d")}</div>
                <div class="tz-label">{tz_name}</div>
            </div>
            <div class="team-block right">
                <span>{game["away_team"]}</span>
                <span class="team-flag">{away_flag}</span>
            </div>
        </div>
        <div class="game-meta">
            <span>📍 {game.get("venue", "")}</span>
            <span class="{badge_class}">{group_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


@st.cache_data(ttl=3600)
def load_data():
    return fetch_schedule()


def main():
    st.markdown("# ⚽ FIFA World Cup 2026")
    st.markdown("### Match Schedule")
    st.markdown("---")

    # Sidebar — settings
    st.sidebar.title("⚙️ Settings")
    tz_names = list(TIMEZONES.keys())
    tz_name = st.sidebar.selectbox(
        "Time Zone",
        tz_names,
        index=tz_names.index(DEFAULT_TZ_NAME),
    )
    tz = TIMEZONES[tz_name]

    st.sidebar.markdown("---")
    st.sidebar.title("🔍 Filter")
    view_option = st.sidebar.radio(
        "View by:",
        ["All Games", "By Team", "By Time", "By Week"],
    )

    # Load and filter data
    with st.spinner("Loading schedule..."):
        schedule = load_data()

    if not schedule:
        st.error("Could not load the schedule. Please check your internet connection and refresh.")
        return

    future_games = get_future_games(schedule)
    teams = get_national_teams(future_games)

    total = len(future_games)
    st.info(f"📊 {total} upcoming {'match' if total == 1 else 'matches'} · Data refreshes every hour")

    # --- All Games ---
    if view_option == "All Games":
        st.subheader("📅 All Upcoming Matches")
        for g in future_games:
            dt = convert_to_tz(g["date"], g["time"], g["utc_offset"], tz)
            render_game_card(g, dt, tz_name)

    # --- By Team ---
    elif view_option == "By Team":
        st.subheader("👥 Team Schedule")
        options = ["— Select a team —"] + teams
        selected_team = st.selectbox("Team:", options)
        if selected_team != "— Select a team —":
            flag = get_flag(selected_team)
            team_games = get_games_for_team(future_games, selected_team)
            st.markdown(f"### {flag} {selected_team} — {len(team_games)} match{'es' if len(team_games) != 1 else ''}")
            if not team_games:
                st.info("No upcoming matches for this team.")
            for g in team_games:
                dt = convert_to_tz(g["date"], g["time"], g["utc_offset"], tz)
                render_game_card(g, dt, tz_name)

    # --- By Time ---
    elif view_option == "By Time":
        st.subheader("🕐 Games by Local Time Window")
        col1, col2 = st.columns(2)
        with col1:
            start_hour = st.slider("From", 0, 23, 18, format="%d:00")
        with col2:
            end_hour = st.slider("To", 1, 24, 23, format="%d:00")
        if start_hour >= end_hour:
            st.error("'From' must be earlier than 'To'.")
        else:
            filtered = get_games_in_time_range(future_games, start_hour, end_hour, tz)
            st.markdown(f"### {start_hour}:00 – {end_hour}:00 {tz_name} · {len(filtered)} match{'es' if len(filtered) != 1 else ''}")
            if not filtered:
                st.info("No matches in this time window.")
            for g, dt in filtered:
                render_game_card(g, dt, tz_name)

    # --- By Week ---
    elif view_option == "By Week":
        st.subheader("📆 Games by Week")
        weeks = get_all_weeks(future_games, tz)
        if not weeks:
            st.info("No upcoming matches found.")
        else:
            week_labels = [
                f"Week {w[0]}: {w[1].strftime('%b %d')} – {w[2].strftime('%b %d')}"
                for w in weeks
            ]
            selected = st.selectbox("Week:", ["— Select a week —"] + week_labels)
            if selected != "— Select a week —":
                week_index = week_labels.index(selected) + 1
                week_games = get_games_for_week(future_games, week_index, tz)
                st.markdown(f"### {selected} · {len(week_games)} match{'es' if len(week_games) != 1 else ''}")
                for g, dt in week_games:
                    render_game_card(g, dt, tz_name)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center; color:#aaa; font-size:12px;'>"
        "Data from OpenFootball · Updates hourly"
        "</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
