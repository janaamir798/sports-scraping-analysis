"""
Method 2: collect Premier League 2023-2024 matches from the website HTML
using requests + BeautifulSoup.

The season page normally shows only the first 100 matches, but adding "?all=1"
to the URL shows all 380 matches in one plain-HTML table (no JavaScript needed).

Run from the project folder:  python scrapers/scraper_bs4.py
"""

import re
import time
from datetime import datetime

from bs4 import BeautifulSoup

from metrics import Metrics, make_session, match_result, save_matches

SEASON_URL = "https://www.thesportsdb.com/season/4328-english-premier-league/2023-2024?all=1"
URLS = [SEASON_URL]     # one page is enough; kept as a list so the loop + delay work for more pages
DELAY_S = 4             # rate limiting between page requests (same polite pace as the API scraper)


def parse_row(row):
    """
    Turn one table row (<tr class="season-event-row">) into a match dict.
    The row has 5 cells:  date | round | home team | score | away team
    Example text:        "11 Aug 23" | "r01" | "Burnley" | "0 - 3" | "Manchester City"
    """
    cells = row.find_all("td")
    if len(cells) < 5:
        return None

    # Date: "11 Aug 23" -> "2023-08-11"
    date_text = cells[0].get_text(" ", strip=True)
    date = datetime.strptime(date_text, "%d %b %y").strftime("%Y-%m-%d")

    # Round: "r01" -> 1
    round_number = int(cells[1].get_text(strip=True).lstrip("r"))

    # Each team name appears twice (full name for desktop, shortened for mobile).
    # The full name is in the link with class "d-lg-block" -> take that one.
    home_team = cells[2].find("a", class_="d-lg-block").get_text(strip=True)
    away_team = cells[4].find("a", class_="d-lg-block").get_text(strip=True)

    # Score: "0 - 3" -> 0 and 3. If there is no score (match not played), skip the row.
    score = re.match(r"(\d+)\s*-\s*(\d+)", cells[3].get_text(strip=True))
    if score is None:
        return None
    home_goals, away_goals = int(score.group(1)), int(score.group(2))

    return {
        "date": date,
        "round": round_number,
        "home_team": home_team,
        "away_team": away_team,
        "home_goals": home_goals,
        "away_goals": away_goals,
        "result": match_result(home_goals, away_goals),
    }


def parse_page(html):
    """Find every match row in the page and parse it."""
    soup = BeautifulSoup(html, "html.parser")       # build a tree from the raw HTML text
    matches = []
    for row in soup.find_all("tr", class_="season-event-row"):
        try:
            match = parse_row(row)
        except (AttributeError, ValueError) as error:  # a row with an unexpected layout
            print(f"  Skipped a row that could not be parsed: {error}")
            continue
        if match is not None:
            matches.append(match)
    return matches


def main():
    metrics = Metrics("bs4")        # starts the timer
    session = make_session()
    matches = []

    for i, url in enumerate(URLS):
        response = metrics.get(session, url)
        if response is not None:
            page_matches = parse_page(response.text)
            print(f"Page {i + 1}: {len(page_matches)} matches")
            matches.extend(page_matches)

        # Rate limiting: wait before the next page (not after the last one)
        if i < len(URLS) - 1:
            time.sleep(DELAY_S)

    save_matches(matches, "matches_bs4.csv")
    metrics.save(rows_collected=len(matches))


if __name__ == "__main__":
    main()
