import json
from datetime import datetime, timedelta
import pytz

ISRAEL_TZ = pytz.timezone('Asia/Jerusalem')


def load_schedule(path="fifa_wc_2026_schedule.json"):
    import os
    base_dir = os.path.dirname(os.path.abspath(__file__))
    full_path = os.path.join(base_dir, path)
    with open(full_path, encoding="utf-8") as f:
        return json.load(f)


def get_national_teams(schedule):
    teams = set()
    for game in schedule:
        teams.add(game["home_team"])
        teams.add(game["away_team"])
    return sorted(teams)


def convert_to_israel_time(date_str, time_str, utc_offset):
    # date_str: 'YYYY-MM-DD', time_str: 'HH:MM', utc_offset: int (hours)
    dt_utc = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") - timedelta(hours=utc_offset)
    dt_utc = pytz.utc.localize(dt_utc)
    dt_israel = dt_utc.astimezone(ISRAEL_TZ)
    return dt_israel


def get_games_for_team(schedule, team):
    return [g for g in schedule if g["home_team"] == team or g["away_team"] == team]


def get_games_in_time_range(schedule, start_hour, end_hour):
    games = []
    for g in schedule:
        dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
        if start_hour <= dt_israel.hour < end_hour:
            games.append((g, dt_israel))
    return games
