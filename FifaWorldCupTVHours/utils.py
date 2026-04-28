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


def get_future_games(schedule):
    """Filter schedule to only include games that haven't started yet (Israel time)."""
    now = datetime.now(ISRAEL_TZ)
    future = []
    for g in schedule:
        dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
        if dt_israel > now:
            future.append(g)
    return sorted(future, key=lambda g: (g["date"], g["time"]))


def get_national_teams(schedule):
    teams = set()
    for game in schedule:
        teams.add(game["home_team"])
        teams.add(game["away_team"])
    # Filter out placeholder teams (W97, W98, L101, etc. for knockout stages)
    real_teams = {t for t in teams if not t.startswith(('W', 'L')) or len(t) > 4}
    return sorted(real_teams)


def convert_to_israel_time(date_str, time_str, utc_offset):
    # date_str: 'YYYY-MM-DD', time_str: 'HH:MM', utc_offset: int (hours, positive = east of UTC)
    # time_str is LOCAL time at the venue, so we ADD utc_offset to get UTC
    dt_utc = datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M") + timedelta(hours=utc_offset)
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


def get_all_weeks(schedule):
    """Return sorted list of (week_number, start_date, end_date) tuples."""
    weeks = {}
    for g in schedule:
        dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
        # Get week number (1-based)
        week_num = dt_israel.isocalendar()[1]
        year = dt_israel.year
        # Store as (year, week) key for proper sorting
        if (year, week_num) not in weeks:
            # Get Monday of that week
            monday = dt_israel - timedelta(days=dt_israel.weekday())
            sunday = monday + timedelta(days=6)
            weeks[(year, week_num)] = (week_num, monday, sunday)
    sorted_keys = sorted(weeks.keys())
    return [weeks[k] for k in sorted_keys]


def get_games_for_week(schedule, week_index):
    """Return all games for a specific week by list index (1-based)."""
    weeks = get_all_weeks(schedule)
    if week_index < 1 or week_index > len(weeks):
        return []
    week_num = weeks[week_index - 1][0]  # Get the ISO week number from the tuple
    games = []
    for g in schedule:
        dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
        if dt_israel.isocalendar()[1] == week_num:
            games.append((g, dt_israel))
    return sorted(games, key=lambda x: x[1])
