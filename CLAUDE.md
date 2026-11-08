# Project: Sports Web Scraping, Network Analysis & ML

Course project (groups of 2): Jana Alamir and Rim Zoghbi.
Full title: Analyzing Website Data Collection Efficiency and Network Behavior Using Multiple Web Scraping Techniques.

## Goal
Scrape the SAME football match data with three methods (Selenium, BeautifulSoup, API), compare their
performance and network behavior, then use the data for ML predictions.

## Data source
- Website: https://www.thesportsdb.com
- API: TheSportsDB V1 JSON API, free test key in the URL path
  (base: https://www.thesportsdb.com/api/v1/json/{key}/...)
- League: English Premier League (20 teams, 38 rounds, 380 matches per season)
- Season: one full season (start with 2023-2024)
- Note: the free key is rate-limited (~30 requests/min) and may return limited results on some endpoints.
  Always check how many matches each method actually returns and report it.

## Data to collect (same columns for all three scrapers)
date, round, home_team, away_team, home_goals, away_goals, result
- result is from the HOME team's view: W / D / L
- Save to data/matches_api.csv, data/matches_bs4.csv, data/matches_selenium.csv

## Performance metrics (every scraper must record these)
method, total_time_s, num_requests, bandwidth_kb, avg_latency_ms, rows_collected
- Append one row per run to data/metrics.csv
- Shared helper code for timing/counting goes in scrapers/metrics.py

## Responsible scraping rules
- Rate limiting: delay between requests (respect ~30 req/min on the API)
- Set a clear User-Agent
- Handle errors and timeouts gracefully (no crashes on a failed request)
- Optional: multithreaded version to compare speed vs. stability

## Project structure
scrapers/   scraper_api.py, scraper_bs4.py, scraper_selenium.py, metrics.py
data/       CSV outputs
network/    pcap files and screenshots (ss, iftop, nload, tcpdump, Wireshark, ufw)
notebooks/  network_analysis.ipynb, ml_analysis.ipynb
report/     final PDF report and presentation

## Environment
- Ubuntu on WSL2 (Windows host), Python 3 in a virtual environment (.venv)
- Network tools: ss, iftop, nload, tcpdump, ufw; Wireshark on Windows to open .pcap files

## ML plan
- Sort matches by date
- Features calculated ONLY from matches before each game (no data leakage):
  form (points in last 5), avg goals scored (last 5), avg goals conceded (last 5), home/away
- Train on the first ~280 matches, predict the last 60-100 matches
- Regression: predict goals (score) -> evaluate with MAE
- Classification: predict W / D / L -> evaluate with accuracy + confusion matrix, compare with
  "always home win" baseline

## How to help
- Work one step at a time; keep code simple and readable for students
- Explain what the code does after writing it, since we must present and defend it
- Comment the important parts of the code
