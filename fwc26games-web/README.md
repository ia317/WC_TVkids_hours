# FIFA World Cup 2026 - TV Hours Web Interface

Web interface for viewing World Cup 2026 match schedule in Israel time.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the app
streamlit run web_app.py
```

Then open http://localhost:8501 in your browser.

## Project Structure

```
FifaWorldCupTVHours-Web/
├── web_app.py        # Main Streamlit application
├── requirements.txt  # Python dependencies
└── README.md         # This file
```

## Features

- View all upcoming World Cup 2026 matches
- Filter by national team
- Filter by time range (Israel time)
- Filter by week
- Beautiful, colorful interface

## Dependencies

- streamlit
- pytz
- requests