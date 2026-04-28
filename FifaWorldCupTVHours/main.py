def main():
    import sys
    import os
    from utils import load_schedule, get_national_teams, get_games_for_team, convert_to_israel_time, get_games_in_time_range, get_all_weeks, get_games_for_week, get_future_games
    from fetch_wc_teams import fetch_and_save_schedule
    
    # Remove old database files to force fresh fetch
    base_dir = os.path.dirname(os.path.abspath(__file__))
    for db_file in ["wc_schedule_db.json", "fifa_wc_2026_schedule.json"]:
        db_path = os.path.join(base_dir, db_file)
        if os.path.exists(db_path):
            os.remove(db_path)
            print(f"Removed old database: {db_file}")
    
    # Always fetch fresh data from internet on every run
    print("Fetching latest schedule data...")
    fetch_and_save_schedule()
    print("Data updated successfully!\n")
    
    # Load schedule and filter to future games only
    schedule = load_schedule()
    schedule = get_future_games(schedule)
    
    if not schedule:
        print("No upcoming games found.")
        sys.exit(0)
    
    print(f"Showing {len(schedule)} upcoming game(s)\n")
    
    teams = get_national_teams(schedule)
    if len(teams) < 10:
        print("Note: The schedule file only contains a few sample teams/games. Only those teams will appear in the list.")
    print("Welcome to FifaWorldCupTVHours!")
    print("Choose an option:")
    print("1) National Team")
    print("2) Games by Israel Time Range")
    print("3) All Games by Week")
    option = input("Enter 1, 2, or 3: ").strip()
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
    elif option == "3":
        weeks = get_all_weeks(schedule)
        if not weeks:
            print("No games found.")
        else:
            print("Available weeks:")
            for i, (week_num, monday, sunday) in enumerate(weeks, 1):
                print(f"  {i}) Week {week_num}: {monday.strftime('%Y-%m-%d')} to {sunday.strftime('%Y-%m-%d')}")
            print(f"  0) All games")
            while True:
                try:
                    week_choice = int(input("Enter week number to view (0 for all): ").strip())
                    if 0 <= week_choice <= len(weeks):
                        break
                    print(f"Please enter a number between 0 and {len(weeks)}.")
                except ValueError:
                    print("Invalid input. Please enter a number.")
            if week_choice == 0:
                # Show all games across all weeks
                all_games = []
                for g in schedule:
                    dt_israel = convert_to_israel_time(g["date"], g["time"], g["utc_offset"])
                    all_games.append((g, dt_israel))
                all_games.sort(key=lambda x: x[1])
                if not all_games:
                    print("No games found.")
                else:
                    print(f"\nAll Games (Israel time):")
                    for g, dt_israel in all_games:
                        print(f"{dt_israel.strftime('%Y-%m-%d %H:%M')} - {g['home_team']} vs {g['away_team']} at {g['venue']}")
                    print(f"\nTotal: {len(all_games)} game(s)")
            else:
                games = get_games_for_week(schedule, week_choice)
                if not games:
                    print(f"No games found for week {week_choice}.")
                else:
                    week_num = weeks[week_choice - 1][0]
                    print(f"\nGames for Week {week_num} (Israel time):")
                    for g, dt_israel in games:
                        print(f"{dt_israel.strftime('%Y-%m-%d %H:%M')} - {g['home_team']} vs {g['away_team']} at {g['venue']}")
                    print(f"\nTotal: {len(games)} game(s)")
    else:
        print("Invalid option.")

if __name__ == "__main__":
    main()
