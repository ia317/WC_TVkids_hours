import requests
from bs4 import BeautifulSoup
import json

URL = "https://en.wikipedia.org/wiki/2026_FIFA_World_Cup"

response = requests.get(URL)
soup = BeautifulSoup(response.text, 'html.parser')

# Find the section with the teams
teams = set()
for ul in soup.find_all('ul'):
    if any('AFC' in (li.text or '') for li in ul.find_all('li')):
        for li in ul.find_all('li'):
            if '•' in li.text:
                team = li.text.split('•')[-1].strip()
                if team:
                    teams.add(team)

# Save to JSON
with open('wc_2026_teams.json', 'w', encoding='utf-8') as f:
    json.dump(sorted(list(teams)), f, ensure_ascii=False, indent=2)

print(f"Extracted {len(teams)} teams.")
