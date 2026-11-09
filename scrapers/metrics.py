"""
Shared helper code used by all three scrapers (API, BeautifulSoup, Selenium).

It measures, for one scraper run:
  - total_time_s    : wall-clock time of the whole run (including rate-limit delays)
  - num_requests    : how many HTTP requests were made
  - bandwidth_kb    : total size of all responses, in kilobytes
  - avg_latency_ms  : average time per request (send request -> full response received)
  - rows_collected  : how many matches the scraper saved

and appends one row per run to data/metrics.csv.
"""

import csv
import threading
import time
from pathlib import Path

import requests

# Paths are built from this file's location, so the scrapers work
# no matter which folder you run them from.
PROJECT_DIR = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_DIR / "data"
METRICS_FILE = DATA_DIR / "metrics.csv"

# A clear User-Agent tells the website who is making the requests (responsible scraping).
USER_AGENT = "sports-scraping-analysis/1.0 (university course project, educational use)"

METRICS_COLUMNS = ["method", "total_time_s", "num_requests", "bandwidth_kb",
                   "avg_latency_ms", "rows_collected"]
MATCH_COLUMNS = ["date", "round", "home_team", "away_team",
                 "home_goals", "away_goals", "result"]


class Metrics:
    """Counts requests, bytes and latency for one scraper run."""

    def __init__(self, method):
        self.method = method              # "api", "bs4" or "selenium"
        self.num_requests = 0
        self.failed_requests = 0
        self.total_bytes = 0
        self.latencies_ms = []
        self.start_time = time.perf_counter()   # the clock starts when the object is created
        # A lock so that several threads (threaded scraper) never update the counters
        # at the same moment, which could lose a count.
        self.lock = threading.Lock()

    def record(self, num_bytes, latency_ms):
        """Record one request. Selenium calls this directly; API/bs4 use get() below."""
        with self.lock:
            self.num_requests += 1
            self.total_bytes += num_bytes
            self.latencies_ms.append(latency_ms)

    def get(self, session, url, timeout=30, retries=4, retry_wait_s=5):
        """
        Download a URL with requests, record its size and latency,
        and return the response (or None if it failed).
        Errors and timeouts are caught, so a failed request never crashes the scraper.
        If the server says "429 Too Many Requests", we wait as long as it asks
        (the Retry-After header) before trying again.
        """
        for attempt in range(1, retries + 2):
            start = time.perf_counter()
            response = None
            try:
                response = session.get(url, timeout=timeout)
                response.raise_for_status()      # turns HTTP errors (404, 429, 500...) into exceptions
                ok = True
            except requests.RequestException as error:
                print(f"  Request failed (attempt {attempt}): {error}")
                ok = False
            latency_ms = (time.perf_counter() - start) * 1000

            # Every attempt counts as a request, even a failed one, because it still used the network.
            size = len(response.content) if response is not None else 0
            self.record(size, latency_ms)

            if ok:
                return response
            with self.lock:
                self.failed_requests += 1
            if attempt <= retries:
                wait_s = retry_wait_s
                # Rate limited: respect the server's Retry-After value (in seconds) + 1s margin
                if response is not None and response.status_code == 429:
                    retry_after = response.headers.get("Retry-After", "")
                    if retry_after.isdigit():
                        wait_s = int(retry_after) + 1
                time.sleep(wait_s)               # wait before trying again
        return None

    def save(self, rows_collected):
        """Compute the final numbers, append them to data/metrics.csv and print a summary."""
        total_time_s = time.perf_counter() - self.start_time
        avg_latency_ms = (sum(self.latencies_ms) / len(self.latencies_ms)
                          if self.latencies_ms else 0)

        row = {
            "method": self.method,
            "total_time_s": round(total_time_s, 2),
            "num_requests": self.num_requests,
            "bandwidth_kb": round(self.total_bytes / 1024, 1),
            "avg_latency_ms": round(avg_latency_ms, 1),
            "rows_collected": rows_collected,
        }

        DATA_DIR.mkdir(exist_ok=True)
        write_header = not METRICS_FILE.exists()     # only write the header the first time
        with open(METRICS_FILE, "a", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=METRICS_COLUMNS)
            if write_header:
                writer.writeheader()
            writer.writerow(row)

        print("\nMetrics:")
        for key, value in row.items():
            print(f"  {key:15} {value}")
        if self.failed_requests:
            print(f"  ({self.failed_requests} request attempts failed)")
        return row


# ---- Small helpers shared by all scrapers (same session and same CSV format) ----

def make_session():
    """A requests Session reuses the TCP connection and always sends our User-Agent."""
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    return session


def match_result(home_goals, away_goals):
    """Result from the HOME team's point of view: W, D or L."""
    if home_goals > away_goals:
        return "W"
    if home_goals == away_goals:
        return "D"
    return "L"


def save_matches(matches, filename):
    """Sort matches by date and save them to data/<filename> with the standard columns."""
    matches = sorted(matches, key=lambda m: (m["date"], m["home_team"]))
    DATA_DIR.mkdir(exist_ok=True)
    path = DATA_DIR / filename
    with open(path, "w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=MATCH_COLUMNS)
        writer.writeheader()
        writer.writerows(matches)
    print(f"Saved {len(matches)} matches to {path.relative_to(PROJECT_DIR)}")
