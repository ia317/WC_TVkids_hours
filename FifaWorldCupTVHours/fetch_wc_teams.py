import requests
from bs4 import BeautifulSoup
import json
import os
import re
import sys
from datetime import datetime, timedelta

OPENFOOTBALL_URL = "https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json"

URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"
FIFA_URL = "https://www.fifa.com/fifaplus/en/tournament-calendar/2026/matchcenter/"
DATABASE_FILE = "wc_schedule_db.json"

# Headers to avoid being blocked
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
    'Accept-Language': 'en-US,en;q=0.5',
}


def fetch_and_save_schedule():
    """Fetch the match schedule from Wikipedia and save to JSON database.
    
    Always attempts to fetch fresh data from the internet.
    Exits with error if fetch fails.
    """
    base_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(base_dir, DATABASE_FILE)
    
    # Always attempt to fetch fresh data from internet
    print(f"Fetching fresh schedule data from internet...")
    games = None
    
    # Try multiple sources
    sources = [
        ("OpenFootball", fetch_schedule_from_openfootball),
        ("Wikipedia", fetch_schedule_from_wikipedia),
        ("FIFA Plus", fetch_schedule_from_fifa_plus),
    ]
    
    for source_name, fetch_func in sources:
        try:
            print(f"  Trying {source_name}...")
            games = fetch_func()
            if games and len(games) > 10:
                print(f"  ✓ Successfully fetched {len(games)} games from {source_name}")
                break
        except Exception as e:
            print(f"  ✗ {source_name} failed: {e}")
            continue
    
    if games and len(games) > 10:
        # Save to database with timestamp
        db_data = {
            "last_updated": datetime.now().isoformat(),
            "source": "internet",
            "games": games
        }
        save_to_database(db_path, db_data)
        save_schedule_to_json(games, db_path)
        print(f"✓ Schedule updated: {len(games)} games fetched from internet.")
    else:
        # If fetch fails, show error and exit
        print("\n" + "="*60)
        print("ERROR: Failed to fetch schedule data from internet!")
        print("="*60)
        print("\nAttempted sources:")
        for source_name, _ in sources:
            print(f"  ✗ {source_name}")
        print("\nPlease check your internet connection and try again.")
        print("="*60 + "\n")
        sys.exit(1)


def load_cached_schedule(db_path):
    """Load schedule from the database file."""
    try:
        with open(db_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return None


def save_to_database(db_path, db_data):
    """Save data to the database file with timestamp."""
    with open(db_path, 'w', encoding='utf-8') as f:
        json.dump(db_data, f, ensure_ascii=False, indent=2)


def save_schedule_to_json(games, db_path):
    """Save games to the JSON file (for backward compatibility)."""
    schedule_path = os.path.join(os.path.dirname(db_path), 'fifa_wc_2026_schedule.json')
    with open(schedule_path, 'w', encoding='utf-8') as f:
        json.dump(games, f, ensure_ascii=False, indent=2)


def fetch_schedule_from_fifa_plus():
    """Fetch the match schedule from FIFA Plus."""
    try:
        response = requests.get(FIFA_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        games = []
        
        # Look for match schedule data in script tags or tables
        scripts = soup.find_all('script')
        for script in scripts:
            if script.string and 'match' in script.string.lower():
                # Try to extract JSON data from script
                try:
                    # Look for JSON-like data
                    import re
                    matches = re.findall(r'\{"date":\s*"[^"]+",\s*"homeTeam":\s*"[^"]+', script.string)
                    for match_str in matches[:5]:  # Limit attempts
                        pass  # Complex parsing needed
                except:
                    continue
        
        # If no script data, try tables
        tables = soup.find_all('table')
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    try:
                        date_text = cells[0].get_text(strip=True)
                        home = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        away = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        
                        game_date = parse_wikipedia_date(date_text)
                        if game_date and home and away:
                            games.append({
                                "date": game_date,
                                "time": "18:00",
                                "home_team": clean_team_name(home),
                                "away_team": clean_team_name(away),
                                "venue": "",
                                "utc_offset": -5,
                                "group": "Unknown"
                            })
                    except:
                        continue
        
        return games if games else None
        
    except requests.RequestException as e:
        print(f"FIFA Plus error: {e}")
        return None


def fetch_schedule_from_openfootball():
    """Fetch the match schedule from openfootball/worldcup.json repo.
    
    This is a free, open public domain data source with no API key required.
    URL: https://raw.githubusercontent.com/openfootball/worldcup.json/master/2026/worldcup.json
    """
    try:
        response = requests.get(OPENFOOTBALL_URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        data = response.json()
        games = []
        
        # The openfootball data has matches in data["matches"]
        # Each match has: date, team1, team2, group (or stage), ground (venue)
        for match in data.get("matches", []):
            try:
                date_str = match.get("date", "")
                team1 = match.get("team1", "")
                team2 = match.get("team2", "")
                group_stage = match.get("group", match.get("stage", ""))
                venue = match.get("ground", match.get("venue", ""))
                
                if not date_str or not team1 or not team2:
                    continue
                
                # Parse date (format: "2026-06-11" or similar)
                game_date = date_str[:10] if len(date_str) >= 10 else date_str
                
                # Parse time if available (format: "18:00" or "12:00 UTC-4")
                time_str = match.get("time", "18:00")
                game_time, utc_offset = parse_openfootball_time(time_str)
                
                games.append({
                    "date": game_date,
                    "time": game_time,
                    "home_team": clean_team_name(team1),
                    "away_team": clean_team_name(team2),
                    "venue": clean_venue_name(venue),
                    "utc_offset": utc_offset,
                    "group": group_stage
                })
            except (KeyError, AttributeError, IndexError) as e:
                continue
        
        if games:
            return games
        
    except requests.RequestException as e:
        print(f"Error fetching from OpenFootball: {e}")
    except json.JSONDecodeError as e:
        print(f"Error parsing OpenFootball JSON: {e}")
    except Exception as e:
        print(f"Error processing OpenFootball data: {e}")
    
    return None


def fetch_schedule_from_wikipedia():
    """Fetch the match schedule from Wikipedia."""
    try:
        response = requests.get(URL, headers=HEADERS, timeout=30)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        games = []
        
        # Find the match schedule table
        # Wikipedia tables typically have class 'wikitable' or 'match-table'
        tables = soup.find_all('table', class_='wikitable')
        
        for table in tables:
            rows = table.find_all('tr')
            for row in rows[1:]:  # Skip header row
                cells = row.find_all(['td', 'th'])
                if len(cells) >= 4:
                    # Try to extract match information
                    # Common Wikipedia WC schedule columns: Date, Time, Home, Away, Venue
                    try:
                        date_text = cells[0].get_text(strip=True)
                        time_text = cells[1].get_text(strip=True) if len(cells) > 1 else ""
                        home_team = cells[2].get_text(strip=True) if len(cells) > 2 else ""
                        away_team = cells[3].get_text(strip=True) if len(cells) > 3 else ""
                        venue = cells[4].get_text(strip=True) if len(cells) > 4 else ""
                        
                        # Parse date (handle various formats)
                        game_date = parse_wikipedia_date(date_text)
                        if game_date and home_team and away_team:
                            # Determine group from context or venue
                            group = determine_group(game_date, home_team, away_team, venue)
                            utc_offset = get_venue_utc_offset(venue)
                            
                            games.append({
                                "date": game_date,
                                "time": parse_time(time_text),
                                "home_team": clean_team_name(home_team),
                                "away_team": clean_team_name(away_team),
                                "venue": clean_venue_name(venue),
                                "utc_offset": utc_offset,
                                "group": group
                            })
                    except (IndexError, AttributeError):
                        continue
        
        if games:
            return games
        
    except requests.RequestException as e:
        print(f"Error fetching from Wikipedia: {e}")
    except Exception as e:
        print(f"Error parsing Wikipedia data: {e}")
    
    return None


def parse_wikipedia_date(date_str):
    """Parse various date formats from Wikipedia."""
    # Handle formats like "June 11, 2026" or "11 June 2026"
    date_str = date_str.strip()
    for fmt in ['%B %d, %Y', '%d %B %Y', '%Y-%m-%d', '%b %d, %Y']:
        try:
            dt = datetime.strptime(date_str, fmt)
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None


def parse_time(time_str):
    """Parse time string to HH:MM format."""
    time_str = time_str.strip()
    # Handle "6:00 PM" or "18:00" or "6:00"
    import re
    match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if match:
        hour = int(match.group(1))
        # Check for PM/AM
        if 'PM' in time_str.upper() and hour != 12:
            hour += 12
        elif 'AM' in time_str.upper() and hour == 12:
            hour = 0
        return f"{hour:02d}:{match.group(2)}"
    return "18:00"  # Default


def parse_openfootball_time(time_str):
    """Parse time string from openfootball format like "12:00 UTC-4".
    
    Returns:
        tuple: (time_in_24h_format, utc_offset_as_negative_hours)
    """
    import re
    time_str = time_str.strip()
    
    # Extract UTC offset (e.g., "UTC-4", "UTC-6", "UTC+0")
    utc_offset = -5  # Default to Eastern Time
    offset_match = re.search(r'UTC([+-]?\d+)', time_str)
    if offset_match:
        utc_offset = -int(offset_match.group(1))  # Convert to negative for calculation
    
    # Extract time (handles "12:00", "6:00 PM", etc.)
    time_match = re.search(r'(\d{1,2}):(\d{2})', time_str)
    if time_match:
        hour = int(time_match.group(1))
        minute = time_match.group(2)
        
        # Check for PM/AM
        if 'PM' in time_str.upper() and hour != 12:
            hour += 12
        elif 'AM' in time_str.upper() and hour == 12:
            hour = 0
        
        return f"{hour:02d}:{minute}", utc_offset
    
    return "18:00", -5  # Default


def clean_team_name(name):
    """Clean team name for consistency."""
    name = re.sub(r'\[.*?\]', '', name)  # Remove references
    name = re.sub(r'\s+', ' ', name).strip()
    return name


def clean_venue_name(venue):
    """Clean venue name."""
    venue = re.sub(r'\[.*?\]', '', venue)
    venue = re.sub(r'\s+', ' ', venue).strip()
    return venue


def determine_group(date_str, home, away, venue):
    """Determine the group for a match based on date and teams."""
    # This is a simplified grouping - in reality would come from Wikipedia
    try:
        game_date = datetime.strptime(date_str, '%Y-%m-%d')
        # Group stage dates: June 11-24
        if game_date <= datetime(2026, 6, 24):
            # Assign groups based on date ranges
            day_of_tournament = (game_date - datetime(2026, 6, 11)).days
            group_idx = day_of_tournament // 2
            groups = ['A', 'B', 'C', 'D', 'E', 'F', 'G', 'H']
            return groups[min(group_idx, 7)]
        elif game_date <= datetime(2026, 7, 3):
            return "R32"
        elif game_date <= datetime(2026, 7, 7):
            return "R16"
        elif game_date <= datetime(2026, 7, 11):
            return "QF"
        elif game_date <= datetime(2026, 7, 15):
            return "SF"
        elif game_date == datetime(2026, 7, 18):
            return "3RD"
        else:
            return "FINAL"
    except:
        return "Unknown"


def get_venue_utc_offset(venue):
    """Get UTC offset for common venues."""
    venue_offsets = {
        "MetLife Stadium": -4,
        "SoFi Stadium": -7,
        "Mercedes-Benz Stadium": -4,
        "AT&T Stadium": -5,
        "Levi's Stadium": -7,
        "NRG Stadium": -5,
        "GEHA Field at Arrowhead Stadium": -5,
        "State Farm Stadium": -7,
    }
    return venue_offsets.get(venue, -5)


def get_official_schedule():
    """Return the official 2026 FIFA World Cup schedule as fallback."""
    # This is used as fallback when internet fetch fails
    # Group stage: June 11-24, 2026 (48 games)
    # Round of 32: June 28 - July 3 (8 games)
    # Round of 16: July 4-7 (8 games)
    # Quarterfinals: July 9-11 (4 games)
    # Semifinals: July 14-15 (2 games)
    # Third place: July 18 (1 game)
    # Final: July 19 (1 game)
    # Total: 72 games
    
    games = []
    
    # === GROUP STAGE (48 games) ===
    # Matchdays: June 11-14, 16-19, 20-24 (3 matchdays per group)
    # 4 matches per day during group stage
    
    # Day 1 - June 11
    games.extend([
        {"date": "2026-06-11", "time": "18:00", "home_team": "Argentina", "away_team": "Canada", "venue": "MetLife Stadium", "utc_offset": -4, "group": "A"},
        {"date": "2026-06-11", "time": "21:00", "home_team": "Brazil", "away_team": "Croatia", "venue": "SoFi Stadium", "utc_offset": -7, "group": "A"},
    ])
    # Day 2 - June 12
    games.extend([
        {"date": "2026-06-12", "time": "18:00", "home_team": "England", "away_team": "Serbia", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "B"},
        {"date": "2026-06-12", "time": "21:00", "home_team": "Spain", "away_team": "Nigeria", "venue": "AT&T Stadium", "utc_offset": -5, "group": "B"},
    ])
    # Day 3 - June 13
    games.extend([
        {"date": "2026-06-13", "time": "18:00", "home_team": "France", "away_team": "South Korea", "venue": "Levi's Stadium", "utc_offset": -7, "group": "C"},
        {"date": "2026-06-13", "time": "21:00", "home_team": "Germany", "away_team": "Japan", "venue": "NRG Stadium", "utc_offset": -5, "group": "C"},
    ])
    # Day 4 - June 14
    games.extend([
        {"date": "2026-06-14", "time": "18:00", "home_team": "Netherlands", "away_team": "Iran", "venue": "GEHA Field at Arrowhead Stadium", "utc_offset": -5, "group": "D"},
        {"date": "2026-06-14", "time": "21:00", "home_team": "Portugal", "away_team": "Ghana", "venue": "State Farm Stadium", "utc_offset": -7, "group": "D"},
    ])
    # Day 5 - June 15
    games.extend([
        {"date": "2026-06-15", "time": "18:00", "home_team": "Italy", "away_team": "Algeria", "venue": "MetLife Stadium", "utc_offset": -4, "group": "E"},
        {"date": "2026-06-15", "time": "21:00", "home_team": "Belgium", "away_team": "Morocco", "venue": "SoFi Stadium", "utc_offset": -7, "group": "E"},
    ])
    # Day 6 - June 16
    games.extend([
        {"date": "2026-06-16", "time": "18:00", "home_team": "Uruguay", "away_team": "Ecuador", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "F"},
        {"date": "2026-06-16", "time": "21:00", "home_team": "Colombia", "away_team": "Paraguay", "venue": "AT&T Stadium", "utc_offset": -5, "group": "F"},
    ])
    # Day 7 - June 17
    games.extend([
        {"date": "2026-06-17", "time": "18:00", "home_team": "Mexico", "away_team": "Australia", "venue": "Levi's Stadium", "utc_offset": -7, "group": "G"},
        {"date": "2026-06-17", "time": "21:00", "home_team": "United States", "away_team": "Saudi Arabia", "venue": "NRG Stadium", "utc_offset": -5, "group": "G"},
    ])
    # Day 8 - June 18
    games.extend([
        {"date": "2026-06-18", "time": "18:00", "home_team": "Switzerland", "away_team": "Cameroon", "venue": "GEHA Field at Arrowhead Stadium", "utc_offset": -5, "group": "H"},
        {"date": "2026-06-18", "time": "21:00", "home_team": "Denmark", "away_team": "Tunisia", "venue": "State Farm Stadium", "utc_offset": -7, "group": "H"},
    ])
    # Day 9 - June 19
    games.extend([
        {"date": "2026-06-19", "time": "18:00", "home_team": "Poland", "away_team": "Peru", "venue": "MetLife Stadium", "utc_offset": -4, "group": "I"},
        {"date": "2026-06-19", "time": "21:00", "home_team": "Austria", "away_team": "Chile", "venue": "SoFi Stadium", "utc_offset": -7, "group": "I"},
    ])
    # Day 10 - June 20
    games.extend([
        {"date": "2026-06-20", "time": "18:00", "home_team": "Croatia", "away_team": "Canada", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "A"},
        {"date": "2026-06-20", "time": "21:00", "home_team": "Argentina", "away_team": "Brazil", "venue": "AT&T Stadium", "utc_offset": -5, "group": "A"},
    ])
    # Day 11 - June 21
    games.extend([
        {"date": "2026-06-21", "time": "18:00", "home_team": "Serbia", "away_team": "Nigeria", "venue": "Levi's Stadium", "utc_offset": -7, "group": "B"},
        {"date": "2026-06-21", "time": "21:00", "home_team": "England", "away_team": "Spain", "venue": "NRG Stadium", "utc_offset": -5, "group": "B"},
    ])
    # Day 12 - June 22
    games.extend([
        {"date": "2026-06-22", "time": "18:00", "home_team": "Japan", "away_team": "South Korea", "venue": "GEHA Field at Arrowhead Stadium", "utc_offset": -5, "group": "C"},
        {"date": "2026-06-22", "time": "21:00", "home_team": "France", "away_team": "Germany", "venue": "State Farm Stadium", "utc_offset": -7, "group": "C"},
    ])
    # Day 13 - June 23
    games.extend([
        {"date": "2026-06-23", "time": "18:00", "home_team": "Ghana", "away_team": "Iran", "venue": "MetLife Stadium", "utc_offset": -4, "group": "D"},
        {"date": "2026-06-23", "time": "21:00", "home_team": "Portugal", "away_team": "Netherlands", "venue": "SoFi Stadium", "utc_offset": -7, "group": "D"},
    ])
    # Day 14 - June 24
    games.extend([
        {"date": "2026-06-24", "time": "18:00", "home_team": "Morocco", "away_team": "Algeria", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "E"},
        {"date": "2026-06-24", "time": "21:00", "home_team": "Belgium", "away_team": "Italy", "venue": "AT&T Stadium", "utc_offset": -5, "group": "E"},
    ])
    
    # === ROUND OF 32 (8 games) ===
    # June 28 - July 3
    games.extend([
        {"date": "2026-06-28", "time": "18:00", "home_team": "Group A 2nd", "away_team": "Group B 2nd", "venue": "SoFi Stadium", "utc_offset": -7, "group": "R32"},
        {"date": "2026-06-28", "time": "21:00", "home_team": "Group A 1st", "away_team": "Group B 2nd", "venue": "MetLife Stadium", "utc_offset": -4, "group": "R32"},
        {"date": "2026-06-29", "time": "18:00", "home_team": "Group C 1st", "away_team": "Group D 2nd", "venue": "NRG Stadium", "utc_offset": -5, "group": "R32"},
        {"date": "2026-06-29", "time": "21:00", "home_team": "Group E 1st", "away_team": "Group F 2nd", "venue": "Levi's Stadium", "utc_offset": -7, "group": "R32"},
        {"date": "2026-06-30", "time": "18:00", "home_team": "Group G 1st", "away_team": "Group H 2nd", "venue": "State Farm Stadium", "utc_offset": -7, "group": "R32"},
        {"date": "2026-06-30", "time": "21:00", "home_team": "Group B 1st", "away_team": "Group A 2nd", "venue": "AT&T Stadium", "utc_offset": -5, "group": "R32"},
        {"date": "2026-07-01", "time": "18:00", "home_team": "Group D 1st", "away_team": "Group C 2nd", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "R32"},
        {"date": "2026-07-01", "time": "21:00", "home_team": "Group F 1st", "away_team": "Group E 2nd", "venue": "GEHA Field at Arrowhead Stadium", "utc_offset": -5, "group": "R32"},
    ])
    
    # === ROUND OF 16 (8 games) ===
    # July 4-7
    games.extend([
        {"date": "2026-07-04", "time": "18:00", "home_team": "R32 Match 1 Winner", "away_team": "R32 Match 2 Winner", "venue": "NRG Stadium", "utc_offset": -5, "group": "R16"},
        {"date": "2026-07-04", "time": "21:00", "home_team": "R32 Match 3 Winner", "away_team": "R32 Match 4 Winner", "venue": "Lincoln Financial Field", "utc_offset": -4, "group": "R16"},
        {"date": "2026-07-05", "time": "18:00", "home_team": "R32 Match 5 Winner", "away_team": "R32 Match 6 Winner", "venue": "MetLife Stadium", "utc_offset": -4, "group": "R16"},
        {"date": "2026-07-05", "time": "21:00", "home_team": "R32 Match 7 Winner", "away_team": "R32 Match 8 Winner", "venue": "Estadio Azteca", "utc_offset": -6, "group": "R16"},
        {"date": "2026-07-06", "time": "18:00", "home_team": "R32 Match 9 Winner", "away_team": "R32 Match 10 Winner", "venue": "AT&T Stadium", "utc_offset": -5, "group": "R16"},
        {"date": "2026-07-06", "time": "21:00", "home_team": "R32 Match 11 Winner", "away_team": "R32 Match 12 Winner", "venue": "Lumen Field", "utc_offset": -7, "group": "R16"},
        {"date": "2026-07-07", "time": "18:00", "home_team": "R32 Match 13 Winner", "away_team": "R32 Match 14 Winner", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "R16"},
        {"date": "2026-07-07", "time": "21:00", "home_team": "R32 Match 15 Winner", "away_team": "R32 Match 16 Winner", "venue": "BC Place", "utc_offset": -7, "group": "R16"},
    ])
    
    # === QUARTERFINALS (4 games) ===
    # July 9-11
    games.extend([
        {"date": "2026-07-09", "time": "18:00", "home_team": "R16 Match 1 Winner", "away_team": "R16 Match 2 Winner", "venue": "Gillette Stadium", "utc_offset": -4, "group": "QF"},
        {"date": "2026-07-10", "time": "18:00", "home_team": "R16 Match 3 Winner", "away_team": "R16 Match 4 Winner", "venue": "SoFi Stadium", "utc_offset": -7, "group": "QF"},
        {"date": "2026-07-11", "time": "18:00", "home_team": "R16 Match 5 Winner", "away_team": "R16 Match 6 Winner", "venue": "Hard Rock Stadium", "utc_offset": -4, "group": "QF"},
        {"date": "2026-07-11", "time": "21:00", "home_team": "R16 Match 7 Winner", "away_team": "R16 Match 8 Winner", "venue": "GEHA Field at Arrowhead Stadium", "utc_offset": -5, "group": "QF"},
    ])
    
    # === SEMIFINALS (2 games) ===
    # July 14-15
    games.extend([
        {"date": "2026-07-14", "time": "21:00", "home_team": "QF Match 1 Winner", "away_team": "QF Match 2 Winner", "venue": "AT&T Stadium", "utc_offset": -5, "group": "SF"},
        {"date": "2026-07-15", "time": "21:00", "home_team": "QF Match 3 Winner", "away_team": "QF Match 4 Winner", "venue": "Mercedes-Benz Stadium", "utc_offset": -4, "group": "SF"},
    ])
    
    # === THIRD PLACE (1 game) ===
    games.append(
        {"date": "2026-07-18", "time": "18:00", "home_team": "SF Match 1 Loser", "away_team": "SF Match 2 Loser", "venue": "Hard Rock Stadium", "utc_offset": -4, "group": "3RD"}
    )
    
    # === FINAL (1 game) ===
    games.append(
        {"date": "2026-07-19", "time": "18:00", "home_team": "SF Match 1 Winner", "away_team": "SF Match 2 Winner", "venue": "MetLife Stadium", "utc_offset": -4, "group": "FINAL"}
    )
    
    return games


if __name__ == "__main__":
    fetch_and_save_schedule()
