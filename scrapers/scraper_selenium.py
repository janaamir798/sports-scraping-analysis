"""
Method 3: collect Premier League 2023-2024 matches by opening the website in a real
(headless) Chrome browser with Selenium.

The data is in plain HTML, so Selenium is not strictly needed here; we use it to compare
how much more time and network traffic a full browser costs for the same table.

Run from the project folder:  python scrapers/scraper_selenium.py
"""

import re
import time
from datetime import datetime

from selenium import webdriver
from selenium.common.exceptions import TimeoutException, WebDriverException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from metrics import USER_AGENT, Metrics, match_result, save_matches

SEASON_URL = "https://www.thesportsdb.com/season/4328-english-premier-league/2023-2024?all=1"
URLS = [SEASON_URL]     # one page is enough; kept as a list so the loop + delay work for more pages
DELAY_S = 4             # rate limiting between page loads
PAGE_TIMEOUT_S = 60     # give up on a page that takes longer than this


def make_driver():
    """Start a headless Chrome (no window) that identifies itself with our User-Agent."""
    options = webdriver.ChromeOptions()
    options.add_argument("--headless=new")             # run without opening a window
    options.add_argument("--no-sandbox")               # needed to run Chrome inside WSL/containers
    options.add_argument("--disable-dev-shm-usage")    # avoid crashes from small shared memory in WSL
    # Wide window: full team names and the round column are only VISIBLE on large screens
    # (CSS class "d-lg-block"), and Selenium only reads visible text.
    options.add_argument("--window-size=1920,1080")
    options.add_argument(f"--user-agent={USER_AGENT}")
    driver = webdriver.Chrome(options=options)          # Selenium downloads ChromeDriver automatically
    driver.set_page_load_timeout(PAGE_TIMEOUT_S)
    return driver


def record_browser_requests(driver, metrics):
    """
    Ask the browser which files it downloaded (HTML, CSS, JS, images...) using the
    JavaScript Performance API, and record each one as a request in our metrics.
    """
    entries = driver.execute_script("""
        return performance.getEntriesByType('navigation')
            .concat(performance.getEntriesByType('resource'))
            .map(e => ({name: e.name, size: e.decodedBodySize, duration: e.duration}));
    """)
    for entry in entries:
        # decodedBodySize = size of the file after decompression, the same thing that
        # len(response.content) measures in the API and bs4 scrapers -> fair comparison.
        # Limitation: files from OTHER domains (team badge images, Google ads/analytics)
        # report size 0 for privacy reasons, so this total is a bit lower than reality.
        # tcpdump / Wireshark gives the exact number of bytes on the network.
        metrics.record(entry["size"], entry["duration"])
    return len(entries)


def parse_row(row):
    """
    Turn one table row (<tr class="season-event-row">) into a match dict.
    Same 5 cells as in the bs4 scraper:  date | round | home team | score | away team
    """
    cells = row.find_elements(By.TAG_NAME, "td")
    if len(cells) < 5:
        return None

    # Date: "11 Aug 23" -> "2023-08-11"
    date = datetime.strptime(cells[0].text.strip(), "%d %b %y").strftime("%Y-%m-%d")

    # Round: "r01" -> 1
    round_number = int(cells[1].text.strip().lstrip("r"))

    # Full team name is in the link with class "d-lg-block" (the other link is the short mobile name)
    home_team = cells[2].find_element(By.CSS_SELECTOR, "a.d-lg-block").text.strip()
    away_team = cells[4].find_element(By.CSS_SELECTOR, "a.d-lg-block").text.strip()

    # Score: "0 - 3" -> 0 and 3. No score (match not played) -> skip the row.
    score = re.match(r"(\d+)\s*-\s*(\d+)", cells[3].text.strip())
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


def scrape_page(driver, url):
    """Load one page in the browser, wait for the match table, and parse all rows."""
    driver.get(url)
    # Wait until at least one match row exists (in case parts of the page load late)
    WebDriverWait(driver, PAGE_TIMEOUT_S).until(
        EC.presence_of_element_located((By.CSS_SELECTOR, "tr.season-event-row")))

    matches = []
    for row in driver.find_elements(By.CSS_SELECTOR, "tr.season-event-row"):
        try:
            match = parse_row(row)
        except (WebDriverException, ValueError) as error:   # a row with an unexpected layout
            print(f"  Skipped a row that could not be parsed: {error}")
            continue
        if match is not None:
            matches.append(match)
    return matches


def main():
    metrics = Metrics("selenium")   # starts the timer (browser start-up time is included)
    matches = []
    driver = None
    try:
        driver = make_driver()
        for i, url in enumerate(URLS):
            try:
                page_matches = scrape_page(driver, url)
                print(f"Page {i + 1}: {len(page_matches)} matches")
                matches.extend(page_matches)
            except (TimeoutException, WebDriverException) as error:
                print(f"  Page {i + 1} failed: {error.msg if hasattr(error, 'msg') else error}")
            finally:
                # Count the browser's requests for this page, even if parsing failed
                n = record_browser_requests(driver, metrics)
                print(f"  The browser made {n} requests for this page")

            # Rate limiting: wait before the next page (not after the last one)
            if i < len(URLS) - 1:
                time.sleep(DELAY_S)
    except WebDriverException as error:
        print(f"Could not start Chrome: {error.msg}")
    finally:
        if driver is not None:
            driver.quit()       # always close the browser, even after an error

    save_matches(matches, "matches_selenium.csv")
    metrics.save(rows_collected=len(matches))


if __name__ == "__main__":
    main()
