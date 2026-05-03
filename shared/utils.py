import json
import re
from datetime import datetime, timedelta
import pytz

ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

TIMEZONES = {
    "Eastern (ET)": pytz.timezone("America/New_York"),
    "Central (CT)": pytz.timezone("America/Chicago"),
    "Mountain (MT)": pytz.timezone("America/Denver"),
    "Pacific (PT)": pytz.timezone("America/Los_Angeles"),
    "Israel (IST)": pytz.timezone("Asia/Jerusalem"),
}

DEFAULT_TZ_NAME = "Eastern (ET)"

FLAGS = {
    "Algeria": "🇩🇿",
    "Argentina": "🇦🇷",
    "Australia": "🇦🇺",
    "Austria": "🇦🇹",
    "Belgium": "🇧🇪",
    "Bolivia": "🇧🇴",
    "Brazil": "🇧🇷",
    "Cameroon": "🇨🇲",
    "Canada": "🇨🇦",
    "Chile": "🇨🇱",
    "China": "🇨🇳",
    "Colombia": "🇨🇴",
    "Costa Rica": "🇨🇷",
    "Croatia": "🇭🇷",
    "Czech Republic": "🇨🇿",
    "Czechia": "🇨🇿",
    "Denmark": "🇩🇰",
    "DR Congo": "🇨🇩",
    "Ecuador": "🇪🇨",
    "Egypt": "🇪🇬",
    "England": "🏴󠁧󠁢󠁥󠁮󠁧󠁿",
    "France": "🇫🇷",
    "Germany": "🇩🇪",
    "Ghana": "🇬🇭",
    "Greece": "🇬🇷",
    "Honduras": "🇭🇳",
    "Hungary": "🇭🇺",
    "Indonesia": "🇮🇩",
    "Iran": "🇮🇷",
    "Iraq": "🇮🇶",
    "Ireland": "🇮🇪",
    "Israel": "🇮🇱",
    "Italy": "🇮🇹",
    "Ivory Coast": "🇨🇮",
    "Côte d'Ivoire": "🇨🇮",
    "Japan": "🇯🇵",
    "Jordan": "🇯🇴",
    "Kenya": "🇰🇪",
    "Mali": "🇲🇱",
    "Mexico": "🇲🇽",
    "Morocco": "🇲🇦",
    "Netherlands": "🇳🇱",
    "New Zealand": "🇳🇿",
    "Nigeria": "🇳🇬",
    "Northern Ireland": "🇬🇧",
    "Oman": "🇴🇲",
    "Panama": "🇵🇦",
    "Paraguay": "🇵🇾",
    "Peru": "🇵🇪",
    "Poland": "🇵🇱",
    "Portugal": "🇵🇹",
    "Qatar": "🇶🇦",
    "Romania": "🇷🇴",
    "Saudi Arabia": "🇸🇦",
    "Scotland": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "Senegal": "🇸🇳",
    "Serbia": "🇷🇸",
    "Slovakia": "🇸🇰",
    "Slovenia": "🇸🇮",
    "South Africa": "🇿🇦",
    "South Korea": "🇰🇷",
    "Spain": "🇪🇸",
    "Switzerland": "🇨🇭",
    "Tunisia": "🇹🇳",
    "Turkey": "🇹🇷",
    "Türkiye": "🇹🇷",
    "UAE": "🇦🇪",
    "Ukraine": "🇺🇦",
    "United States": "🇺🇸",
    "USA": "🇺🇸",
    "Uruguay": "🇺🇾",
    "Uzbekistan": "🇺🇿",
    "Venezuela": "🇻🇪",
    "Wales": "🏴󠁧󠁢󠁷󠁬󠁳󠁿",
}


def get_flag(team_name):
    return FLAGS.get(team_name, "🏳️")


def load_schedule(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def convert_to_tz(date_str, time_str, utc_offset, tz):
    dt_utc = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") + timedelta(hours=utc_offset)
    dt_utc = pytz.utc.localize(dt_utc)
    return dt_utc.astimezone(tz)


def convert_to_israel_time(date_str, time_str, utc_offset):
    return convert_to_tz(date_str, time_str, utc_offset, ISRAEL_TZ)


def get_future_games(schedule):
    now = datetime.now(pytz.utc)
    future = []
    for g in schedule:
        dt_utc = datetime.strptime(f"{g['date']} {g['time']}", "%Y-%m-%d %H:%M") + timedelta(hours=g["utc_offset"])
        dt_utc = pytz.utc.localize(dt_utc)
        if dt_utc > now:
            future.append(g)
    return sorted(future, key=lambda g: (g["date"], g["time"]))


def get_national_teams(schedule):
    teams = set()
    for game in schedule:
        teams.add(game["home_team"])
        teams.add(game["away_team"])
    real_teams = {t for t in teams if re.match(r"^[A-Za-z\s&'-]+$", t)}
    return sorted(real_teams)


def get_games_for_team(schedule, team):
    return [g for g in schedule if g["home_team"] == team or g["away_team"] == team]


def get_games_in_time_range(schedule, start_hour, end_hour, tz):
    games = []
    for g in schedule:
        dt = convert_to_tz(g["date"], g["time"], g["utc_offset"], tz)
        if start_hour <= dt.hour < end_hour:
            games.append((g, dt))
    return games


def get_all_weeks(schedule, tz):
    weeks = {}
    for g in schedule:
        dt = convert_to_tz(g["date"], g["time"], g["utc_offset"], tz)
        week_num = dt.isocalendar()[1]
        year = dt.year
        if (year, week_num) not in weeks:
            monday = dt - timedelta(days=dt.weekday())
            sunday = monday + timedelta(days=6)
            weeks[(year, week_num)] = (week_num, monday, sunday)
    return [weeks[k] for k in sorted(weeks.keys())]


def get_games_for_week(schedule, week_index, tz):
    weeks = get_all_weeks(schedule, tz)
    if week_index < 1 or week_index > len(weeks):
        return []
    week_num = weeks[week_index - 1][0]
    games = []
    for g in schedule:
        dt = convert_to_tz(g["date"], g["time"], g["utc_offset"], tz)
        if dt.isocalendar()[1] == week_num:
            games.append((g, dt))
    return sorted(games, key=lambda x: x[1])
