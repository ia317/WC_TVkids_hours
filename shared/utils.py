import json
import re
from datetime import datetime, timedelta
import pytz

ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')

TIMEZONES = {
    # North America
    "Eastern (ET)":          pytz.timezone("America/New_York"),
    "Central (CT)":          pytz.timezone("America/Chicago"),
    "Mountain (MT)":         pytz.timezone("America/Denver"),
    "Pacific (PT)":          pytz.timezone("America/Los_Angeles"),
    "Mexico City (CT)":      pytz.timezone("America/Mexico_City"),
    "Canada/Vancouver (PT)": pytz.timezone("America/Vancouver"),
    # South America
    "Brazil (BRT)":          pytz.timezone("America/Sao_Paulo"),
    "Argentina (ART)":       pytz.timezone("America/Argentina/Buenos_Aires"),
    # Europe
    "UK (GMT/BST)":          pytz.timezone("Europe/London"),
    "Central Europe (CET)":  pytz.timezone("Europe/Paris"),
    "Eastern Europe (EET)":  pytz.timezone("Europe/Athens"),
    # Middle East
    "Israel (IST)":          pytz.timezone("Asia/Jerusalem"),
    "Gulf (GST)":            pytz.timezone("Asia/Dubai"),
    # Asia / Pacific
    "India (IST)":           pytz.timezone("Asia/Kolkata"),
    "Japan/Korea (JST)":     pytz.timezone("Asia/Tokyo"),
    "Australia East (AEST)": pytz.timezone("Australia/Sydney"),
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


# ISO 3166-1 alpha-2 codes for flagcdn.com image URLs
COUNTRY_CODES = {
    "Algeria": "dz", "Argentina": "ar", "Australia": "au", "Austria": "at",
    "Belgium": "be", "Bolivia": "bo", "Brazil": "br", "Cameroon": "cm",
    "Canada": "ca", "Chile": "cl", "China": "cn", "Colombia": "co",
    "Costa Rica": "cr", "Croatia": "hr", "Czech Republic": "cz", "Czechia": "cz",
    "Denmark": "dk", "DR Congo": "cd", "Ecuador": "ec", "Egypt": "eg",
    "England": "gb-eng", "France": "fr", "Germany": "de", "Ghana": "gh",
    "Greece": "gr", "Honduras": "hn", "Hungary": "hu", "Indonesia": "id",
    "Iran": "ir", "Iraq": "iq", "Ireland": "ie", "Israel": "il",
    "Italy": "it", "Ivory Coast": "ci", "Côte d'Ivoire": "ci", "Japan": "jp",
    "Jordan": "jo", "Kenya": "ke", "Mali": "ml", "Mexico": "mx",
    "Morocco": "ma", "Netherlands": "nl", "New Zealand": "nz", "Nigeria": "ng",
    "Northern Ireland": "gb-nir", "Oman": "om", "Panama": "pa", "Paraguay": "py",
    "Peru": "pe", "Poland": "pl", "Portugal": "pt", "Qatar": "qa",
    "Romania": "ro", "Saudi Arabia": "sa", "Scotland": "gb-sct", "Senegal": "sn",
    "Serbia": "rs", "Slovakia": "sk", "Slovenia": "si", "South Africa": "za",
    "South Korea": "kr", "Spain": "es", "Switzerland": "ch", "Tunisia": "tn",
    "Turkey": "tr", "Türkiye": "tr", "UAE": "ae", "Ukraine": "ua",
    "United States": "us", "USA": "us", "Uruguay": "uy", "Uzbekistan": "uz",
    "Venezuela": "ve", "Wales": "gb-wls",
}


def get_flag_img(team_name, height=24):
    code = COUNTRY_CODES.get(team_name)
    if code:
        return (
            f'<img src="https://flagcdn.com/w40/{code}.png" '
            f'height="{height}" style="vertical-align:middle; border-radius:2px; margin:0 4px;">'
        )
    return ""


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
