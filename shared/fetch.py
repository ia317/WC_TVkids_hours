import requests
from bs4 import BeautifulSoup
import json
import os
import re
from datetime import datetime, timedelta

OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"
WIKIPEDIA_URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
FIFA_URL = "https://www.fifa.com/fifaplus/en/tournament-calendar/2026/matchcenter/"

HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_schedule():
    """Fetch the match schedule from the internet. Returns list of game dicts, or [] on failure."""
    sources = [
        ("OpenFootball", _fetch_from_openfootball),
        ("Wikipedia", _fetch_from_wikipedia),
        ("FIFA Plus", _fetch_from_fifa_plus),
    ]

    for source_name, fetch_func in sources:
        try:
            games = fetch_func()
            if games and len(games) > 10:
                return games
        except Exception:
            continue

    return []


def _fetch_from_openfootball():
    response = requests.get(OPENFOOTBALL_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    data = response.json()
    games = []

    for match in data.get("matches", []):
        date_str = match.get("date", "")
        team1 = match.get("team1", "")
        team2 = match.get("team2", "")
        if not date_str or not team1 or not team2:
            continue

        game_date = date_str[:10] if len(date_str) >= 10 else date_str
        time_str = match.get("time", "18:00")
        game_time, utc_offset = _parse_openfootball_time(time_str)
        group_stage = match.get("group", match.get("stage", ""))
        venue = match.get("ground", match.get("venue", ""))

        games.append({
            "date": game_date,
            "time": game_time,
            "home_team": _clean_name(team1),
            "away_team": _clean_name(team2),
            "venue": _clean_name(venue),
            "utc_offset": utc_offset,
            "group": group_stage,
        })

    return games if games else None


def _fetch_from_wikipedia():
    response = requests.get(WIKIPEDIA_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    games = []

    for table in soup.find_all('table', class_='wikitable'):
        for row in table.find_all('tr')[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) < 4:
                continue
            try:
                date_text = cells[0].get_text(strip=True)
                time_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                home_team = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                away_team = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                venue = cells[4].get_text(strip=True) if len(cells) > 4 else ""

                game_date = _parse_date(date_text)
                if game_date and home_team and away_team:
                    games.append({
                        "date": game_date,
                        "time": _parse_time(time_text),
                        "home_team": _clean_name(home_team),
                        "away_team": _clean_name(away_team),
                        "venue": _clean_name(venue),
                        "utc_offset": _venue_utc_offset(venue),
                        "group": _determine_group(game_date),
                    })
            except (IndexError, AttributeError):
                continue

    return games if games else None


def _fetch_from_fifa_plus():
    response = requests.get(FIFA_URL, headers=HEADERS, timeout=30)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, 'html.parser')
    games = []

    for table in soup.find_all('table'):
        for row in table.find_all('tr')[1:]:
            cells = row.find_all(['td', 'th'])
            if len(cells) >= 4:
                try:
                    date_text = cells[0].get_text(strip=True)
                    home = cells[1].get_text(strip=True)
                    away = cells[2].get_text(strip=True)
                    game_date = _parse_date(date_text)
                    if game_date and home and away:
                        games.append({
                            "date": game_date,
                            "time": "18:00",
                            "home_team": _clean_name(home),
                            "away_team": _clean_name(away),
                            "venue": "",
                            "utc_offset": -5,
                            "group": "Unknown",
                        })
                except Exception:
                    continue

    return games if games else None


def _parse_openfootball_time(time_str):
    time_str = time_str.strip()
    utc_offset = -5  # default Eastern
    offset_match = re.search(r'UTC([+-]?\d+)', time_str)
    if offset_match:
        utc_offset = -int(offset_match.group(1))

    time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        if 'PM' in time_str.upper() and hour != 12:
            hour += 12
        elif 'AM' in time_str.upper() and hour == 12:
            hour = 0
        return f"{hour:02d}:{minute}", utc_offset

    return "18:00", -5


def _parse_date(date_str):
    date_str = date_str.strip()
    for fmt in ['%B %d, %Y', '%d %B %Y', '%Y-%m-%d', '%b %d, %Y']:
        try:
            return datetime.strptime(date_str, fmt).strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def _parse_time(time_str):
    time_str = time_str.strip()
    match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hour = int(match.group(1))
        if 'PM' in time_str.upper() and hour != 12:
            hour += 12
        elif 'AM' in time_str.upper() and hour == 12:
            hour = 0
        return f"{hour:02d}:{match.group(2)}"
    return "18:00"


def _clean_name(name):
    name = re.sub(r'\[.*?\]', '', str(name))
    return re.sub(r'\s+', ' ', name).strip()


def _venue_utc_offset(venue):
    offsets = {
        "MetLife Stadium": -4,
        "SoFi Stadium": -7,
        "Mercedes-Benz Stadium": -4,
        "AT&T Stadium": -5,
        "Levi's Stadium": -7,
        "NRG Stadium": -5,
        "GEHA Field at Arrowhead Stadium": -5,
        "State Farm Stadium": -7,
        "Gillette Stadium": -4,
        "Hard Rock Stadium": -4,
        "Lincoln Financial Field": -4,
        "Lumen Field": -7,
        "BC Place": -7,
        "Estadio Azteca": -6,
    }
    return offsets.get(venue, -5)


def _determine_group(date_str):
    try:
        d = datetime.strptime(date_str, '%Y-%m-%d')
        if d <= datetime(2026, 6, 27):
            return "Group Stage"
        elif d <= datetime(2026, 7, 3):
            return "R32"
        elif d <= datetime(2026, 7, 7):
            return "R16"
        elif d <= datetime(2026, 7, 11):
            return "QF"
        elif d <= datetime(2026, 7, 15):
            return "SF"
        elif d == datetime(2026, 7, 18):
            return "3RD"
        else:
            return "FINAL"
    except Exception:
        return "Unknown"
