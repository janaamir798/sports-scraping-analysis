# Sports Web Scraping, Network Analysis & Machine Learning

**Analyzing Website Data Collection Efficiency and Network Behavior Using Multiple Web Scraping Techniques**

Course project by **Jana Alamir** and **Rim Zoghbi**.

We collect the same football data (English Premier League 2023-2024, 20 teams, 380 matches) from
[TheSportsDB](https://www.thesportsdb.com) with three scraping methods (API, BeautifulSoup, Selenium),
compare their performance and network behavior, and then use the data to predict match results
with machine learning.

## Folder structure

```
scrapers/                    the scrapers
  metrics.py                 shared helper: timing, request counting, bandwidth, latency, CSV saving
  scraper_api.py             method 1: TheSportsDB JSON API (one request per round)
  scraper_api_threaded.py    method 1b: same API with 4 threads and a shared rate limiter
  scraper_bs4.py             method 2: requests + BeautifulSoup on the season HTML page
  scraper_selenium.py        method 3: headless Chrome with Selenium
data/
  matches_*.csv              380 matches per method: date, round, home_team, away_team, home_goals, away_goals, result
  metrics.csv                one row per scraper run: method, total_time_s, num_requests, bandwidth_kb, avg_latency_ms, rows_collected
  ml_mae.csv, ml_accuracy.csv, predictions_last100.csv   ML results
network/
  run_measurements.sh        tcpdump + ss + timed scraper runs + ufw firewall test
  *_ss.txt, *_output.txt     ss snapshots and scraper output for each method
  ufw_*.txt                  firewall test results
  pcap_summary.csv           packets / bytes / servers / domains per method (from the .pcap files)
  screenshots/               screenshots of ss, nload, iftop, tcpdump, Wireshark, ufw
  *.pcap                     packet captures (NOT on GitHub, too large: re-create with run_measurements.sh)
notebooks/
  network_analysis.ipynb     comparison of the methods, pcap analysis, ss / ufw results
  ml_analysis.ipynb          EDA, features, regression (goals) and classification (W/D/L)
report/
  figures/                   charts used in the report and presentation
  build_report.py            creates final_report.pdf
  build_presentation.py      creates presentation.pptx
  final_report.pdf
  presentation.pptx
```

## Setup (Ubuntu / WSL2)

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Selenium needs Google Chrome installed (`google-chrome --version`); the matching ChromeDriver is
downloaded automatically by Selenium. The network tools come from apt:
`sudo apt install tcpdump iftop nload ufw`.

## Running the scrapers

Run from the project folder (with the virtual environment activated):

```bash
python scrapers/scraper_api.py            # ~9 min (API rate limit: 4 s between requests)
python scrapers/scraper_api_threaded.py   # 4 threads, shared rate limiter
python scrapers/scraper_bs4.py            # ~1 s
python scrapers/scraper_selenium.py       # ~40 s
python scrapers/scraper_api.py --test-rounds 2   # quick test, saves nothing
```

Each scraper writes `data/matches_<method>.csv` and appends one row to `data/metrics.csv`.

## Network measurements

Run as your normal user (it asks for the sudo password for tcpdump and ufw):

```bash
bash network/run_measurements.sh                    # all steps: api, bs4, selenium, ufw
bash network/run_measurements.sh bs4 selenium ufw   # only some steps
```

Before starting, open two more terminals with `sudo iftop -i eth0 -P` and `nload eth0`.
The script prints `TAKE SCREENSHOT NOW: ...` when it is time for a screenshot.
The `.pcap` files can be opened in Wireshark on Windows from
`\\wsl.localhost\Ubuntu\home\<user>\sports-scraping-analysis\network\`.

## Notebooks

```bash
jupyter notebook notebooks/                     # open and run interactively
# or run them from the terminal (outputs are saved in the notebook):
jupyter nbconvert --to notebook --execute --inplace notebooks/network_analysis.ipynb
jupyter nbconvert --to notebook --execute --inplace notebooks/ml_analysis.ipynb
```

The network notebook reads the `.pcap` files if they exist, otherwise `network/pcap_summary.csv`.

## Report and presentation

```bash
python report/build_report.py         # -> report/final_report.pdf
python report/build_presentation.py   # -> report/presentation.pptx
```

Both scripts read the numbers from the CSV files and the charts from `report/figures/`.
Screenshots saved in `network/screenshots/` (names listed in the network notebook, e.g. `nload_api.png`)
are inserted automatically; missing ones appear as placeholders.

## Responsible scraping

- Clear User-Agent identifying the project
- Rate limiting (4 s between API requests; the server's `Retry-After` is respected after a 429)
- Timeouts and error handling: a failed request never crashes a scraper
- One reused HTTP connection (`requests.Session`)
