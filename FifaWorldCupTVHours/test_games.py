from utils import load_schedule, convert_to_israel_time

s = load_schedule()
print(f"Total games in schedule: {len(s)}")
print()
for g in s:
    dt = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
    print(f"{dt.strftime('%Y-%m-%d %H:%M')} - {g['home_team']} vs {g['away_team']}")