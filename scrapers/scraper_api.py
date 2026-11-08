"""
Method 1: collect Premier League 2023-2024 matches from TheSportsDB JSON API.

The "whole season" endpoint (eventsseason.php) only returns 15 matches with the
free key, so we ask for one round at a time instead (eventsround.php):
38 rounds x 10 matches = 380 matches.

Run from the project folder:  python scrapers/scraper_api.py
"""

import time

from metrics import Metrics, make_session, match_result, save_matches

BASE_URL = "https://www.thesportsdb.com/api/v1/json/123"   # 123 = free test key
LEAGUE_ID = 4328            # English Premier League
SEASON = "2023-2024"
NUM_ROUNDS = 38
# Pause between requests -> 15 requests/min. With 2.5s the API started answering
# "429 Too Many Requests" after ~11 requests, so the real limit is stricter than 30/min.
DELAY_S = 4


def parse_event(event):
    """Turn one API event (a dict with ~30 fields) into a row with our 7 columns."""
    # Skip matches without a score (e.g. not played / postponed)
    if event.get("intHomeScore") is None or event.get("intAwayScore") is None:
        return None

    # The API returns scores as text ("3"), so convert them to numbers
    home_goals = int(event["intHomeScore"])
    away_goals = int(event["intAwayScore"])
    return {
        "date": event["dateEvent"],
        "round": int(event["intRound"]),
        "home_team": event["strHomeTeam"],
        "away_team": event["strAwayTeam"],
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": match_result(home_goals, away_goals),
    }


def main():
    metrics = Metrics("api")        # starts the timer
    session = make_session()
    matches = []

    for round_number in range(1, NUM_ROUNDS + 1):
        url = f"{BASE_URL}/eventsround.php?id={LEAGUE_ID}&r={round_number}&s={SEASON}"
        response = metrics.get(session, url)

        events = []
        if response is not None:
            try:
                events = response.json().get("events") or []   # "events" can be null
            except ValueError:
                print(f"  Round {round_number}: response was not valid JSON")

        for event in events:
            row = parse_event(event)
            if row is not None:
                matches.append(row)
        print(f"Round {round_number:2}: {len(events)} matches")

        # Rate limiting: wait before the next request (no need after the last one)
        if round_number < NUM_ROUNDS:
            time.sleep(DELAY_S)

    save_matches(matches, "matches_api.csv")
    metrics.save(rows_collected=len(matches))


if __name__ == "__main__":
    main()
