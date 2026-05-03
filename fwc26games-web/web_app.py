import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

import streamlit as st
import pytz
from datetime import timedelta
from shared.utils import (
    convert_to_tz, get_future_games, get_national_teams,
    get_games_for_team, get_games_in_time_range,
    get_all_weeks, get_games_for_week,
)
from shared.fetch import fetch_schedule

# ── Timezones ────────────────────────────────────────────────────────────────
TIMEZONES = {
    # Americas — West to East
    "Hawaii (HST)":                 pytz.timezone("Pacific/Honolulu"),
    "Alaska (AKST)":                pytz.timezone("America/Anchorage"),
    "Los Angeles / Vancouver (PT)": pytz.timezone("America/Los_Angeles"),
    "Denver / Phoenix (MT)":        pytz.timezone("America/Denver"),
    "Chicago / Mexico City (CT)":   pytz.timezone("America/Chicago"),
    "New York / Toronto (ET)":      pytz.timezone("America/New_York"),
    "Halifax / Atlantic (AT)":      pytz.timezone("America/Halifax"),
    "Colombia / Peru (COT)":        pytz.timezone("America/Bogota"),
    "Venezuela (VET)":              pytz.timezone("America/Caracas"),
    "Brazil — Brasilia (BRT)":      pytz.timezone("America/Sao_Paulo"),
    "Argentina / Uruguay (ART)":    pytz.timezone("America/Argentina/Buenos_Aires"),
    "Chile (CLT)":                  pytz.timezone("America/Santiago"),
    # Europe
    "London / Lisbon (GMT/BST)":    pytz.timezone("Europe/London"),
    "Paris / Berlin / Rome (CET)":  pytz.timezone("Europe/Paris"),
    "Athens / Helsinki (EET)":      pytz.timezone("Europe/Athens"),
    "Moscow (MSK)":                 pytz.timezone("Europe/Moscow"),
    # Africa
    "Lagos / Dakar (WAT)":          pytz.timezone("Africa/Lagos"),
    "Cairo / Johannesburg (CAT)":   pytz.timezone("Africa/Johannesburg"),
    "Nairobi / Addis Ababa (EAT)":  pytz.timezone("Africa/Nairobi"),
    # Middle East
    "Israel (IST)":                 pytz.timezone("Asia/Jerusalem"),
    "Turkey / Arabia (TRT)":        pytz.timezone("Europe/Istanbul"),
    "Gulf — Dubai / Muscat (GST)":  pytz.timezone("Asia/Dubai"),
    # Asia
    "Pakistan (PKT)":               pytz.timezone("Asia/Karachi"),
    "India / Sri Lanka (IST)":      pytz.timezone("Asia/Kolkata"),
    "Bangladesh (BST)":             pytz.timezone("Asia/Dhaka"),
    "Bangkok / Jakarta (ICT)":      pytz.timezone("Asia/Bangkok"),
    "Beijing / Singapore (CST)":    pytz.timezone("Asia/Shanghai"),
    "Tokyo / Seoul (JST)":          pytz.timezone("Asia/Tokyo"),
    # Pacific
    "Sydney / Melbourne (AEST)":    pytz.timezone("Australia/Sydney"),
    "New Zealand (NZST)":           pytz.timezone("Pacific/Auckland"),
}
DEFAULT_TZ_NAME = "New York / Toronto (ET)"

# ── Flag images ───────────────────────────────────────────────────────────────
COUNTRY_CODES = {
    "Algeria": "dz", "Argentina": "ar", "Australia": "au", "Austria": "at",
    "Belgium": "be", "Bolivia": "bo", "Brazil": "br", "Cameroon": "cm",
    "Canada": "ca", "Chile": "cl", "China": "cn", "Colombia": "co",
    "Costa Rica": "cr", "Croatia": "hr", "Czech Republic": "cz", "Czechia": "cz",
    "Denmark": "dk", "DR Congo": "cd", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh",
    "Greece": "gr", "Honduras": "hn", "Hungary": "hu", "Indonesia": "id",
    "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il",
    "Italy": "it", "Ivory Coast": "ci", "Japan": "jp", "Jordan": "jo",
    "Kenya": "ke", "Mali": "ml", "Mexico": "mx", "Morocco": "ma",
    "Netherlands": "nl", "New Zealand": "nz", "Nigeria": "ng",
    "Northern Ireland": "gb-nir", "Oman": "om", "Panama": "pa", "Paraguay": "py",
    "Peru": "pe", "Poland": "pl", "Portugal": "pt", "Qatar": "qa",
    "Romania": "ro", "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn",
    "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si", "South Africa": "za",
    "South Korea": "kr", "Spain": "es", "Switzerland": "ch", "Tunisia": "tn",
    "Turkey": "tr", "Turkiye": "tr", "UAE": "ae", "Ukraine": "ua",
    "United States": "us", "USA": "us", "Uruguay": "uy", "Uzbekistan": "uz",
    "Venezuela": "ve", "Wales": "gb-wls",
}

GROUP_LABELS = {
    "R32": "Round of 32", "R16": "Round of 16", "QF": "Quarter-Final",
    "SF": "Semi-Final", "3RD": "3rd Place", "FINAL": "Final",
}
KNOCKOUT_STAGES = {"R32", "R16", "QF", "SF", "3RD", "FINAL"}


def get_flag_img(team_name, height=24):
    code = COUNTRY_CODES.get(team_name)
    if code:
        return (
            f'<img src="https://flagcdn.com/w40/{code}.png" '
            f'height="{height}" style="vertical-align:middle; border-radius:2px; margin:0 4px;">'
        )
    return ""


def format_group(group):
    if group in GROUP_LABELS:
        return GROUP_LABELS[group]
    if group and len(group) == 1:
        return f"Group {group}"
    return group or ""


# ── Page config & CSS ─────────────────────────────────────────────────────────
st.set_page_config(page_title="FIFA World Cup 2026", page_icon="⚽", layout="wide")

st.markdown("""
<style>
    .stApp { background-color: #f5f7fa; }
    section[data-testid="stSidebar"] { background-color: #ffffff; border-right: 1px solid #e0e0e0; }
    .game-card {
        background: #ffffff; border-radius: 14px; padding: 18px 24px;
        margin: 10px 0; box-shadow: 0 2px 10px rgba(0,0,0,0.07);
        border-left: 5px solid #2e7d32;
    }
    .game-card.knockout { border-left-color: #1565c0; }
    .game-row { display: flex; justify-content: space-between; align-items: center; gap: 12px; }
    .team-block { flex: 1; display: flex; align-items: center; gap: 10px;
                  font-size: 17px; font-weight: 600; color: #1a1a2e; }
    .team-block.right { justify-content: flex-end; }
    .center-block { text-align: center; min-width: 120px; }
    .game-time { font-size: 28px; font-weight: 800; color: #1565c0; line-height: 1.1; }
    .game-date { font-size: 13px; color: #666; margin-top: 2px; }
    .tz-label  { font-size: 11px; color: #999; }
    .game-meta { margin-top: 12px; display: flex; align-items: center;
                 gap: 14px; font-size: 13px; color: #777; }
    .badge { background: #e8f5e9; color: #2e7d32; padding: 3px 10px;
             border-radius: 20px; font-size: 12px; font-weight: 600; }
    .badge.knockout-badge { background: #e3f2fd; color: #1565c0; }
    .export-bar { background: #fff; border-radius: 12px; padding: 18px 20px;
                  margin-top: 24px; box-shadow: 0 2px 8px rgba(0,0,0,0.06); }
</style>
""", unsafe_allow_html=True)


# ── Game card ─────────────────────────────────────────────────────────────────
def render_game_card(game, dt, tz_name):
    home_flag  = get_flag_img(game["home_team"])
    away_flag  = get_flag_img(game["away_team"])
    group      = game.get("group", "")
    group_label = format_group(group)
    is_knockout = group in KNOCKOUT_STAGES
    card_class  = "game-card knockout" if is_knockout else "game-card"
    badge_class = "badge knockout-badge" if is_knockout else "badge"

    st.markdown(f"""
    <div class="{card_class}">
        <div class="game-row">
            <div class="team-block">
                {home_flag}<span>{game["home_team"]}</span>
            </div>
            <div class="center-block">
                <div class="game-time">{dt.strftime("%H:%M")}</div>
                <div class="game-date">{dt.strftime("%a, %b %d")}</div>
                <div class="tz-label">{tz_name}</div>
            </div>
            <div class="team-block right">
                <span>{game["away_team"]}</span>{away_flag}
            </div>
        </div>
        <div class="game-meta">
            <span>📍 {game.get("venue", "")}</span>
            <span class="{badge_class}">{group_label}</span>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ── Export helpers ────────────────────────────────────────────────────────────
def _format_stage(group):
    if group in GROUP_LABELS:
        return GROUP_LABELS[group]
    return f"Group {group}" if group and len(group) == 1 else (group or "")


def generate_ics(games_with_dt):
    lines = ["BEGIN:VCALENDAR", "VERSION:2.0",
             "PRODID:-//FWC26Games//EN", "CALSCALE:GREGORIAN"]
    for g, dt in games_with_dt:
        dt_utc = dt.astimezone(pytz.utc)
        dt_end = dt_utc + timedelta(hours=2)
        uid = (f"{g['date']}-{g['home_team'].replace(' ','-')}"
               f"-{g['away_team'].replace(' ','-')}@fwc26")
        stage = _format_stage(g.get("group", ""))
        lines += [
            "BEGIN:VEVENT",
            f"UID:{uid}",
            f"DTSTART:{dt_utc.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTEND:{dt_end.strftime('%Y%m%dT%H%M%SZ')}",
            f"SUMMARY:⚽ {g['home_team']} vs {g['away_team']}",
            f"LOCATION:{g.get('venue', '')}",
            f"DESCRIPTION:FIFA World Cup 2026 – {stage}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def _print_html(games_with_dt, tz_name):
    rows = ""
    for g, dt in games_with_dt:
        stage = _format_stage(g.get("group", ""))
        rows += (
            f"<tr><td>{dt.strftime('%a, %b %d')}</td>"
            f"<td><strong>{dt.strftime('%H:%M')}</strong></td>"
            f"<td>{g['home_team']}</td><td style='color:#aaa'>vs</td>"
            f"<td>{g['away_team']}</td>"
            f"<td style='color:#777'>{g.get('venue','')}</td>"
            f"<td><span style='background:#e8f5e9;padding:2px 8px;border-radius:12px;"
            f"font-size:12px;color:#2e7d32'>{stage}</span></td></tr>"
        )
    return f"""<!DOCTYPE html><html><head><meta charset="utf-8">
<title>FIFA WC 2026 Schedule</title>
<style>
  body{{font-family:Arial,sans-serif;padding:32px;color:#222;max-width:960px;margin:auto}}
  h2{{color:#1565c0;margin-bottom:4px}}p{{color:#666;font-size:13px;margin-top:0}}
  table{{border-collapse:collapse;width:100%;margin-top:20px}}
  th{{background:#1565c0;color:#fff;padding:9px 12px;text-align:left;font-size:13px}}
  td{{padding:8px 12px;border-bottom:1px solid #eee;font-size:14px}}
  tr:nth-child(even) td{{background:#f5f7fa}}
  @media print{{body{{padding:16px}}}}
</style></head><body>
<h2>&#9917; FIFA World Cup 2026 &mdash; Match Schedule</h2>
<p>Times in: {tz_name} &nbsp;&bull;&nbsp; {len(games_with_dt)} matches</p>
<table><tr><th>Date</th><th>Time</th><th>Home</th><th></th><th>Away</th>
<th>Venue</th><th>Stage</th></tr>{rows}</table>
<p style="margin-top:24px;color:#bbb;font-size:12px">Generated by FWC26Games</p>
</body></html>"""


def render_export_options(games_with_dt, tz_name):
    if not games_with_dt:
        return
    n = len(games_with_dt)
    st.markdown(
        f"<div class='export-bar'><strong>📤 Export this list</strong>"
        f"&nbsp;&nbsp;<span style='color:#888;font-size:13px;'>{n} match{'es' if n != 1 else ''}</span></div>",
        unsafe_allow_html=True,
    )
    col1, col2 = st.columns(2)

    with col1:
        st.download_button(
            label="🖨️ Download for Print",
            data=_print_html(games_with_dt, tz_name),
            file_name="wc2026_schedule.html",
            mime="text/html",
            use_container_width=True,
            help="Downloads a clean HTML file — open it in your browser and press Ctrl+P to print.",
        )

    with col2:
        st.download_button(
            label=f"📅 Download Calendar ({n} events)",
            data=generate_ics(games_with_dt),
            file_name="wc2026_schedule.ics",
            mime="text/calendar",
            use_container_width=True,
            help="Downloads a .ics file with one event per match — works with Apple Calendar, Google Calendar, and Outlook.",
        )

    with st.expander("📖 How to add to your calendar app"):
        st.markdown("""
| Platform | Steps |
|---|---|
| **iPhone / iPad** | Tap the button → tap the downloaded file → tap **"Add All"** in Apple Calendar |
| **Android** | Tap the button → the file opens in **Google Calendar** automatically |
| **Mac** | Click the button → double-click the downloaded file → Apple Calendar opens and asks to import |
| **Windows – Outlook** | Click the button → double-click the downloaded `.ics` file → Outlook will import all events |
| **Google Calendar (browser)** | Click the button → go to [calendar.google.com](https://calendar.google.com) → **Settings ⚙️ → Import** → choose the file → click Import |
| **Other apps** | Any calendar app that supports `.ics` import (Thunderbird, Fantastical, etc.) will work the same way |

> Each match is added as a **separate event**, 2 hours long, with the venue in the location field.
        """)



# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=3600)
def load_data():
    return fetch_schedule()


# ── Main ──────────────────────────────────────────────────────────────────────
def main():
    st.markdown("# ⚽ FIFA World Cup 2026")
    st.markdown("### Match Schedule")
    st.markdown("---")

    # Sidebar — settings
    st.sidebar.title("⚙️ Settings")
    tz_names = list(TIMEZONES.keys())
    tz_name  = st.sidebar.selectbox(
        "Time Zone", tz_names, index=tz_names.index(DEFAULT_TZ_NAME)
    )
    tz = TIMEZONES[tz_name]

    st.sidebar.markdown("---")
    st.sidebar.title("🔍 Filter")
    view_option = st.sidebar.radio(
        "View by:",
        ["All Games", "By Teams", "By Time", "By Week", "ℹ️ About"],
    )

    # About — no data needed
    if view_option == "ℹ️ About":
        st.subheader("ℹ️ About")
        st.markdown("""
        <div style="background:white;border-radius:14px;padding:30px;max-width:620px;
        box-shadow:0 2px 10px rgba(0,0,0,0.07);">
            <h3 style="color:#1565c0;margin-top:0;">⚽ FIFA World Cup 2026 – Schedule App</h3>
            <p style="color:#444;line-height:1.8;">
            Browse the complete FIFA World Cup 2026 match schedule with kick-off times
            converted to your local timezone. Filter by team, time of day, or week —
            then export the list to your calendar, send it by email, or print it.
            </p>
            <p style="color:#444;line-height:1.8;">
            Data is fetched automatically and refreshed every hour, so knockout stage
            fixtures update as the competition progresses.
            </p>
            <hr style="border:none;border-top:1px solid #eee;margin:20px 0;">
            <p style="color:#555;font-size:14px;margin:8px 0;">
                <strong>Developed by:</strong> Idan Atiya
            </p>
            <p style="color:#555;font-size:14px;margin:8px 0;">
                <strong>Contact:</strong>
                <a href="mailto:idanatiya@outlook.com" style="color:#1565c0;">
                idanatiya@outlook.com</a>
            </p>
            <p style="color:#555;font-size:14px;margin:8px 0;">
                <strong>Source code:</strong>
                <a href="https://github.com/ia317/WC_TVkids_hours" target="_blank"
                style="color:#1565c0;">github.com/ia317/WC_TVkids_hours</a>
            </p>
        </div>
        """, unsafe_allow_html=True)
        return

    # Load schedule
    with st.spinner("Loading schedule..."):
        schedule = load_data()

    if not schedule:
        st.error("Could not load the schedule. Please check your internet connection and refresh.")
        return

    future_games = get_future_games(schedule)
    teams = get_national_teams(future_games)
    total = len(future_games)
    st.info(f"📊 {total} upcoming {'match' if total == 1 else 'matches'} · Data refreshes every hour")

    # ── All Games ──────────────────────────────────────────────────────────────
    if view_option == "All Games":
        st.subheader("📅 All Upcoming Matches")
        games_with_dt = [
            (g, convert_to_tz(g["date"], g["time"], g["utc_offset"], tz))
            for g in future_games
        ]
        for g, dt in games_with_dt:
            render_game_card(g, dt, tz_name)
        render_export_options(games_with_dt, tz_name)

    # ── By Teams ───────────────────────────────────────────────────────────────
    elif view_option == "By Teams":
        st.subheader("👥 Filter by Teams")
        selected_teams = st.multiselect(
            "Pick one or more teams to see their matches:",
            options=teams,
            placeholder="Start typing a country name...",
        )

        if not selected_teams:
            st.info("Select at least one team above to see their schedule.")
        else:
            seen, team_games = set(), []
            for team in selected_teams:
                for g in get_games_for_team(future_games, team):
                    key = (g["date"], g["time"], g["home_team"], g["away_team"])
                    if key not in seen:
                        seen.add(key)
                        team_games.append(g)
            team_games.sort(key=lambda g: (g["date"], g["time"]))

            flags_html = " ".join(get_flag_img(t, height=22) for t in selected_teams)
            count = len(team_games)
            st.markdown(
                f"<div style='background:#f0f4f8;padding:12px 18px;border-radius:8px;"
                f"font-size:15px;color:#333;margin:10px 0 16px;'>"
                f"{flags_html}&nbsp; <strong>{', '.join(selected_teams)}</strong>"
                f"&nbsp;—&nbsp; {count} match{'es' if count != 1 else ''}</div>",
                unsafe_allow_html=True,
            )

            games_with_dt = [
                (g, convert_to_tz(g["date"], g["time"], g["utc_offset"], tz))
                for g in team_games
            ]
            for g, dt in games_with_dt:
                render_game_card(g, dt, tz_name)
            render_export_options(games_with_dt, tz_name)

    # ── By Time ────────────────────────────────────────────────────────────────
    elif view_option == "By Time":
        st.subheader("🕐 Games by Kick-off Time")
        st.markdown(
            f"<div style='background:#e8f4fd;border-left:4px solid #1565c0;padding:10px 16px;"
            f"border-radius:6px;margin-bottom:18px;font-size:14px;color:#1a3a5c;'>"
            f"⏱️ Filters by <strong>match kick-off time</strong> in: <strong>{tz_name}</strong></div>",
            unsafe_allow_html=True,
        )

        TIME_PRESETS = {
            "🌅  Morning        06:00 – 12:00": (6, 12),
            "☀️  Afternoon      12:00 – 17:00": (12, 17),
            "🌆  Early Evening  17:00 – 20:00": (17, 20),
            "📺  Prime Time     20:00 – 23:00": (20, 23),
            "🌙  Late Night     23:00 – 24:00": (23, 24),
            "🔧  Custom Range":                 None,
        }

        preset_choice = st.selectbox("Choose a time window:", list(TIME_PRESETS.keys()), index=3)

        if TIME_PRESETS[preset_choice] is None:
            hour_labels    = [f"{h:02d}:00" for h in range(25)]
            selected_range = st.select_slider(
                "Drag the handles to set your kick-off window:",
                options=hour_labels, value=("18:00", "23:00"),
            )
            start_hour = int(selected_range[0].split(":")[0])
            end_hour   = int(selected_range[1].split(":")[0])
        else:
            start_hour, end_hour = TIME_PRESETS[preset_choice]

        st.markdown(
            f"<div style='background:#f0f4f8;padding:12px 18px;border-radius:8px;"
            f"font-size:15px;color:#333;margin:10px 0 4px;'>"
            f"Showing matches that kick off between "
            f"<strong style='color:#1565c0;'>{start_hour:02d}:00</strong>"
            f" &nbsp;→&nbsp; "
            f"<strong style='color:#1565c0;'>{end_hour:02d}:00</strong>"
            f"&nbsp;&nbsp;<span style='color:#888;font-size:13px;'>({tz_name})</span></div>",
            unsafe_allow_html=True,
        )

        if start_hour >= end_hour:
            st.error("Start time must be earlier than end time.")
        else:
            filtered = get_games_in_time_range(future_games, start_hour, end_hour, tz)
            if not filtered:
                st.info("No matches kick off in this time window. Try a different range.")
            else:
                st.markdown(f"**{len(filtered)} match{'es' if len(filtered) != 1 else ''} found**")
                for g, dt in filtered:
                    render_game_card(g, dt, tz_name)
                render_export_options(filtered, tz_name)

    # ── By Week ────────────────────────────────────────────────────────────────
    elif view_option == "By Week":
        st.subheader("📆 Games by Week")
        weeks = get_all_weeks(future_games, tz)
        if not weeks:
            st.info("No upcoming matches found.")
        else:
            week_labels = [
                f"Week {i+1}: {w[1].strftime('%b %d')} – {w[2].strftime('%b %d')}"
                for i, w in enumerate(weeks)
            ]
            selected = st.selectbox("Week:", ["— Select a week —"] + week_labels)
            if selected != "— Select a week —":
                week_index = week_labels.index(selected) + 1
                week_games = get_games_for_week(future_games, week_index, tz)
                st.markdown(
                    f"### {selected} · {len(week_games)} match{'es' if len(week_games) != 1 else ''}"
                )
                for g, dt in week_games:
                    render_game_card(g, dt, tz_name)
                render_export_options(week_games, tz_name)

    st.markdown("---")
    st.markdown(
        "<div style='text-align:center;color:#aaa;font-size:12px;'>"
        "Data from OpenFootball · Updates hourly</div>",
        unsafe_allow_html=True,
    )


if __name__ == "__main__":
    main()
