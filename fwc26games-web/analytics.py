import json
import os
from datetime import datetime, timezone

LOG_FILE = os.path.join(os.path.dirname(__file__), "analytics_log.jsonl")


def log_event(event_name, params=None):
    entry = {
        "ts": datetime.now(timezone.utc).isoformat(),
        "event": event_name,
        **(params or {}),
    }
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry) + "\n")


def load_events():
    if not os.path.exists(LOG_FILE):
        return []
    events = []
    with open(LOG_FILE, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    events.append(json.loads(line))
                except json.JSONDecodeError:
                    pass
    return events


def get_stats():
    events = load_events()
    stats = {
        "total_sessions": 0,
        "print_downloads": 0,
        "calendar_downloads": 0,
        "game_removals": 0,
        "language_changes": {},
        "by_day": {},
    }
    for e in events:
        name = e.get("event")
        day = e.get("ts", "")[:10]

        if name == "session_start":
            stats["total_sessions"] += 1
            stats["by_day"][day] = stats["by_day"].get(day, 0) + 1
        elif name == "print_download":
            stats["print_downloads"] += 1
        elif name == "calendar_download":
            stats["calendar_downloads"] += 1
        elif name == "game_removed":
            stats["game_removals"] += 1
        elif name == "language_changed":
            lang = e.get("language", "unknown")
            stats["language_changes"][lang] = stats["language_changes"].get(lang, 0) + 1

    return stats
