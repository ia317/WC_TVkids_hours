"""
Web interface for FIFA World Cup 2026 TV Hours
Run with: streamlit run web_app.py
"""
import streamlit as st
from utils import (
    load_schedule,
    get_future_games,
    get_national_teams,
    get_games_for_team,
    convert_to_israel_time,
    get_all_weeks,
    get_games_for_week
)

# Page config
st.set_page_config(
    page_title="מונדיאל 2026 - שעות צפייה",
    page_icon="⚽",
    layout="wide"
)

# Custom CSS for Hebrew support
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Heebo:wght@400;700&display=swap');
    html, body, [class*="css"] {
        font-family: 'Heebo', sans-serif !important;
    }
    .stApp {
        background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
    }
</style>
""", unsafe_allow_html=True)

# Header
st.title("⚽ מונדיאל 2026 - לוח משחקים")
st.markdown("### 🕒 כל המשחקים בשעון ישראל")

# Load data
try:
    schedule = load_schedule()
    schedule = get_future_games(schedule)
    teams = get_national_teams(schedule)
except Exception as e:
    st.error(f"שגיאה בטעינת הנתונים: {e}")
    st.stop()

if not schedule:
    st.warning("אין משחקים עתידיים.")
    st.stop()

# Sidebar with options
st.sidebar.header("🔍 אפשרויות חיפוש")

search_mode = st.sidebar.radio(
    "בחר מצב:",
    ["כל המשחקים", "לפי נבחרת", "לפי שבוע"]
)

def display_game(game):
    """Display a single game nicely"""
    dt = convert_to_israel_time(game["date"], game["time"], game["utc_offset"])
    
    # Create expandable card
    with st.expander(f"**{game['home_team']} 🆚 {game['away_team']}**"):
        col1, col2 = st.columns(2)
        with col1:
            st.markdown(f"**📅 תאריך:** {dt.strftime('%d/%m/%Y')}")
            st.markdown(f"**🕐 שעה:** {dt.strftime('%H:%M')}")
        with col2:
            st.markdown(f"**📍 מיקום:** {game['venue']}")
            st.markdown(f"**🌍 אזור זמן:** UTC{game['utc_offset']:+d}")

if search_mode == "כל המשחקים":
    st.success(f"📊 סה\"כ {len(schedule)} משחקים קרובים")
    
    # Show in groups of 20
    for i, game in enumerate(schedule):
        display_game(game)

elif search_mode == "לפי נבחרת":
    selected_team = st.selectbox("בחר נבחרת:", ["-- בחר --"] + teams)
    
    if selected_team != "-- בחר --":
        team_games = get_games_for_team(schedule, selected_team)
        st.success(f"📊 {len(team_games)} משחקים לנבחרת {selected_team}")
        
        for game in team_games:
            display_game(game)
    else:
        st.info("בחר נבחרת מהרשימה למעלה")

elif search_mode == "לפי שבוע":
    weeks = get_all_weeks(schedule)
    
    if weeks:
        week_options = [f"שבוע {w[0]}: {w[1].strftime('%d/%m')} - {w[2].strftime('%d/%m/%Y')}" for w in weeks]
        selected_week = st.selectbox("בחר שבוע:", ["-- בחר --"] + week_options)
        
        if selected_week != "-- בחר --":
            week_idx = week_options.index(selected_week)
            week_num, monday, sunday = weeks[week_idx]
            week_games = get_games_for_week(schedule, week_num)
            
            st.success(f"📊 {len(week_games)} משחקים בשבוע {week_num}")
            st.caption(f"{monday.strftime('%d/%m/%Y')} עד {sunday.strftime('%d/%m/%Y')}")
            
            for game in week_games:
                display_game(game)
    else:
        st.info("אין נתוני שבועות.")

# Footer
st.markdown("---")
st.caption("⚡ נתונים מעודכנים אוטומטית מהאינטרנט")