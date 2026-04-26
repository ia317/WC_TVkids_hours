def main():
    import sys
    import os
    from utils import load_schedule, get_national_teams, get_games_for_team, convert_to_israel_time, get_games_in_time_range
    schedule = load_schedule()
    teams = get_national_teams(schedule)
    if len(teams) < 10:
        print("Note: The schedule file only contains a few sample teams/games. Only those teams will appear in the list.")
    print("Welcome to FifaWorldCupTVHours!")
    print("Choose an option:")
    print("1) National Team")
    print("2) Games by Israel Time Range")
    option = input("Enter 1 or 2: ").strip()
    if option == "1":
        while True:
            team = input("Enter national team name: ").strip()
            if team in teams:
                break
            print("Team not found. Please choose from:")
            for t in teams:
                print(f"- {t}")
        games = get_games_for_team(schedule, team)
        if not games:
            print(f"No games found for {team}.")
        else:
            print(f"Games for {team} (Israel time):")
            for g in games:
                dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
                print(f"{dt_israel.strftime('%Y-%m-%d %H:%M')} - {g['home_team']} vs {g['away_team']} at {g['venue']}")
    elif option == "2":
        try:
            start_hour = int(input("Enter start hour (0-23) in Israel time: ").strip())
            end_hour = int(input("Enter end hour (1-24) in Israel time: ").strip())
        except ValueError:
            print("Invalid input. Please enter numbers.")
            sys.exit(1)
        games = get_games_in_time_range(schedule, start_hour, end_hour)
        if not games:
            print("No games found in this time range.")
        else:
            print(f"Games between {start_hour}:00 and {end_hour}:00 (Israel time):")
            for g, dt_israel in games:
                print(f"{dt_israel.strftime('%Y-%m-%d %H:%M')} - {g['home_team']} vs {g['away_team']} at {g['venue']}")
    else:
        print("Invalid option.")

if __name__ == "__main__":
    main()
