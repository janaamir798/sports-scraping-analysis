"""
Method 1b: the API scraper, but MULTITHREADED.

Several threads download different rounds at the same time. A shared rate limiter
makes sure all threads together never send more than 1 request every MIN_INTERVAL_S
seconds, so we stay responsible even with many threads.

Question we want to answer: is it faster than the normal API scraper, and is it as stable
(how many "429 Too Many Requests" errors)?

Run from the project folder:  python scrapers/scraper_api_threaded.py
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

from metrics import Metrics, make_session, save_matches
# Reuse the settings and the parsing code of the normal API scraper (no copy-paste)
from scraper_api import BASE_URL, LEAGUE_ID, NUM_ROUNDS, SEASON, parse_event

NUM_THREADS = 4
# Shared by ALL threads: at most 1 new request every 2 s = 30 requests/min,
# the limit documented for the free key (the sequential scraper uses 4 s).
MIN_INTERVAL_S = 2.0


class RateLimiter:
    """Gives each thread a 'time slot' so requests are spaced MIN_INTERVAL_S apart."""

    def __init__(self, interval_s):
        self.interval_s = interval_s
        self.lock = threading.Lock()
        self.next_slot = time.perf_counter()

    def wait(self):
        # Inside the lock, reserve the next free slot (only one thread at a time can do this)
        with self.lock:
            now = time.perf_counter()
            my_slot = max(now, self.next_slot)
            self.next_slot = my_slot + self.interval_s
        # Outside the lock, sleep until our slot (other threads can reserve theirs meanwhile)
        time.sleep(my_slot - now)


# Each thread gets its own requests.Session (sessions are not guaranteed thread-safe)
thread_data = threading.local()


def get_session():
    if not hasattr(thread_data, "session"):
        thread_data.session = make_session()
    return thread_data.session


def fetch_round(round_number, metrics, limiter):
    """Download and parse one round. This function runs inside a worker thread."""
    limiter.wait()                                   # rate limiting shared by all threads
    url = f"{BASE_URL}/eventsround.php?id={LEAGUE_ID}&r={round_number}&s={SEASON}"
    # Note: if the server answers 429, metrics.get() waits Retry-After and retries by itself
    response = metrics.get(get_session(), url)

    rows = []
    if response is not None:
        try:
            events = response.json().get("events") or []
        except ValueError:
            events = []
        rows = [row for row in (parse_event(e) for e in events) if row is not None]
    return round_number, rows


def main():
    metrics = Metrics("api_threaded")    # starts the timer
    limiter = RateLimiter(MIN_INTERVAL_S)
    matches = []

    # The pool runs fetch_round() for the 38 rounds using NUM_THREADS threads in parallel
    with ThreadPoolExecutor(max_workers=NUM_THREADS) as pool:
        futures = [pool.submit(fetch_round, r, metrics, limiter)
                   for r in range(1, NUM_ROUNDS + 1)]
        # as_completed gives each result as soon as its thread finishes (any order)
        for future in as_completed(futures):
            round_number, rows = future.result()
            print(f"Round {round_number:2}: {len(rows)} matches")
            matches.extend(rows)

    save_matches(matches, "matches_api_threaded.csv")
    metrics.save(rows_collected=len(matches))


if __name__ == "__main__":
    main()
