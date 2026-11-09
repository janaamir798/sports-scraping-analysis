"""
Builds report/final_report.pdf from our results (CSV files) and charts (report/figures).

Screenshots: save them in network/screenshots/ with the names used below
(e.g. nload_api.png). Then run this script again and they appear in the PDF;
missing screenshots are shown as grey placeholder boxes.

Run from the project folder:  python report/build_report.py
"""

from datetime import date
from pathlib import Path

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import (CondPageBreak, Image, KeepTogether, PageBreak, Paragraph,
                                SimpleDocTemplate, Spacer, Table, TableStyle)
from reportlab.lib.utils import ImageReader

PROJECT = Path(__file__).resolve().parent.parent
DATA, NET, FIGS = PROJECT / "data", PROJECT / "network", PROJECT / "report" / "figures"
SHOTS = NET / "screenshots"
OUT = PROJECT / "report" / "final_report.pdf"

# ---------------- load our results ----------------
metrics = pd.read_csv(DATA / "metrics.csv").groupby("method").tail(1).set_index("method")
pcap = pd.read_csv(NET / "pcap_summary.csv", index_col=0)
groups = pd.read_csv(NET / "selenium_traffic_groups.csv", index_col=0)["KB"]
mae = pd.read_csv(DATA / "ml_mae.csv", index_col=0)
acc = pd.read_csv(DATA / "ml_accuracy.csv", index_col=0)
pred = pd.read_csv(DATA / "predictions_last100.csv")

api, thr, bs4, sel = (metrics.loc[m] for m in ["api", "api_threaded", "bs4", "selenium"])
retries = {m: int(metrics.loc[m, "num_requests"]) - 38 for m in ["api", "api_threaded"]}  # 38 rounds
api_network_s = api.num_requests * api.avg_latency_ms / 1000
best_reg = mae.drop("Baseline (average)").index[0]
best_clf = acc.drop("Baseline (always home win)").index[0]
best_acc, base_acc = acc.loc[best_clf, "accuracy"], acc.loc["Baseline (always home win)", "accuracy"]
n_correct = int((pred["correct"] == "yes").sum())
n_exact = int((pred["predicted_score"] == pred["real_score"]).sum())
sel_total_kb = groups.sum()
site_kb = groups.get("TheSportsDB (website + images)", 0)

# ---------------- styles and helpers ----------------
styles = getSampleStyleSheet()
body = ParagraphStyle("body", parent=styles["BodyText"], fontSize=10.5, leading=14.5, spaceAfter=6)
small = ParagraphStyle("small", parent=body, fontSize=9, leading=12, textColor=colors.HexColor("#444444"))
caption = ParagraphStyle("caption", parent=small, alignment=TA_CENTER, spaceAfter=12)
# keepWithNext: a heading is never left alone at the bottom of a page
h1 = ParagraphStyle("h1", parent=styles["Heading1"], fontSize=16, spaceBefore=6, spaceAfter=8,
                    textColor=colors.HexColor("#1F3864"), keepWithNext=1)
h2 = ParagraphStyle("h2", parent=styles["Heading2"], fontSize=12.5, spaceBefore=8, spaceAfter=4,
                    textColor=colors.HexColor("#2E5597"), keepWithNext=1)
story = []
P = lambda text, style=body: story.append(Paragraph(text, style))
H1 = lambda text: story.append(Paragraph(text, h1))
H2 = lambda text: story.append(Paragraph(text, h2))
gap = lambda h=0.3: story.append(Spacer(1, h * cm))
WIDTH = A4[0] - 4 * cm


def bullets(items):
    for item in items:
        story.append(Paragraph(item, body, bulletText="•"))


def table(rows, col_widths=None, header=True):
    t = Table(rows, colWidths=col_widths, hAlign="CENTER")
    style = [("GRID", (0, 0), (-1, -1), 0.4, colors.HexColor("#999999")),
             ("FONTSIZE", (0, 0), (-1, -1), 9),
             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
             ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#F2F5FA")])]
    if header:
        style += [("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#2E5597")),
                  ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                  ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold")]
    t.setStyle(TableStyle(style))
    story.append(t)
    gap(0.4)


def picture(path, text, width=WIDTH):
    iw, ih = ImageReader(str(path)).getSize()
    height = width * ih / iw
    if height > 11 * cm:                       # keep very tall pictures on one page
        width, height = width * 11 * cm / height, 11 * cm
    story.append(KeepTogether([Image(str(path), width=width, height=height),
                               Paragraph(text, caption)]))


def figure(name, text, width=WIDTH):
    picture(FIGS / name, text, width)


def screenshot(name, text):
    """Insert network/screenshots/<name> if it exists, otherwise a placeholder box."""
    path = SHOTS / name
    if path.exists():
        picture(path, text, WIDTH * 0.85)
        return
    box = Table([[Paragraph(f"<b>[SCREENSHOT PLACEHOLDER]</b><br/>Save the screenshot as "
                            f"<b>network/screenshots/{name}</b> and run "
                            f"<i>python report/build_report.py</i> again.", small)]],
                colWidths=[WIDTH * 0.85], rowHeights=[3 * cm])
    box.setStyle(TableStyle([("BOX", (0, 0), (-1, -1), 1, colors.HexColor("#888888")),
                             ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#EEEEEE")),
                             ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
                             ("ALIGN", (0, 0), (-1, -1), "CENTER")]))
    story.append(KeepTogether([box, Paragraph(text, caption)]))


f1 = lambda x: f"{x:,.1f}"

# =================================================================
# Title page
# =================================================================
gap(5)
story.append(Paragraph("Analyzing Website Data Collection Efficiency and Network Behavior "
                       "Using Multiple Web Scraping Techniques",
                       ParagraphStyle("title", parent=h1, fontSize=22, leading=28, alignment=TA_CENTER)))
gap(1)
P("Web scraping, network analysis and machine learning on Premier League 2023-2024 data",
  ParagraphStyle("sub", parent=body, fontSize=13, alignment=TA_CENTER))
gap(2)
P("<b>Jana Alamir</b> and <b>Rim Zoghbi</b>", ParagraphStyle("names", parent=body, fontSize=13,
                                                             alignment=TA_CENTER))
P(date.today().strftime("%B %Y"), ParagraphStyle("date", parent=body, alignment=TA_CENTER))
story.append(PageBreak())

# =================================================================
# 1. Introduction
# =================================================================
H1("1. Introduction")
P("The goal of this project is to collect the <b>same data with three different web scraping "
  "methods</b>, compare how efficient they are and how they behave on the network, and then use "
  "the collected data to make <b>predictions with machine learning</b>.")
P("The three methods are:")
bullets(["<b>API</b>: asking the website's official JSON API for the data,",
         "<b>BeautifulSoup</b>: downloading the HTML page with <i>requests</i> and extracting the "
         "data from it,",
         "<b>Selenium</b>: opening the page in a real (headless) Chrome browser and reading it."])
P("For each method we measured the time, the number of requests, the downloaded data and the "
  "latency, and we observed the network traffic with <i>ss, iftop, nload, tcpdump</i> and "
  "<i>Wireshark</i>. We also tested a firewall rule with <i>ufw</i> and a multithreaded version of the "
  "API scraper.")

H2("Website choice")
P("We chose <b>TheSportsDB</b> (www.thesportsdb.com), a free sports database that offers both a "
  "website and a JSON API with a free test key. This is important for our project because we can "
  "scrape <b>exactly the same data</b> from the API and from the website, so the comparison is fair.")
P("We used the <b>English Premier League, season 2023-2024</b>: 20 teams, 38 rounds, "
  "<b>380 matches</b>. Football results are also a good dataset for machine learning "
  "(predicting goals and results).")

# =================================================================
# 2. Data collected
# =================================================================
H1("2. Data collected")
P("Every scraper saves the matches in a CSV file with the same 7 columns:")
table([["Column", "Meaning", "Example"],
       ["date", "date of the match", "2023-08-11"],
       ["round", "round number (1-38)", "1"],
       ["home_team / away_team", "the two teams", "Burnley / Manchester City"],
       ["home_goals / away_goals", "final score", "0 / 3"],
       ["result", "result for the HOME team: W, D or L", "L"]],
      [4.5 * cm, 6.5 * cm, 4.5 * cm])
P(f"All methods collected <b>380 matches</b>, and we checked that the files are <b>exactly "
  f"identical</b> (same dates, teams, scores and results). In the season there were 46% home wins, "
  f"22% draws and 32% away wins, and an average of 3.28 goals per match.")

# =================================================================
# 3. The scrapers
# =================================================================
H1("3. The three scrapers")
P("All scrapers use a shared helper file, <b>metrics.py</b>, which starts a timer, counts every "
  "request, adds up the size of every response (bandwidth) and measures the time of each request "
  "(latency). At the end it adds one row to <b>data/metrics.csv</b>. It also makes sure that a failed "
  "request never crashes the program (try/except, timeout of 30 s, retries).")

H2("3.1 API scraper (scraper_api.py)")
P("The API returns JSON data. The endpoint for a whole season only returns 15 matches with the free "
  "key, so we ask for <b>one round at a time</b> (eventsround.php): 38 requests of 10 matches. "
  "From the ~30 fields of each match we keep only our 7 columns. Between two requests the scraper "
  "waits 4 seconds (rate limiting), and if the server answers <i>429 Too Many Requests</i>, it waits the "
  "number of seconds given in the <i>Retry-After</i> header before trying again.")

H2("3.2 Multithreaded API scraper (scraper_api_threaded.py)")
P("The same API requests, but made by <b>4 threads at the same time</b>. A shared rate limiter "
  "gives each thread a time slot so that all threads together send at most one request every 2 "
  "seconds (30 per minute, the documented limit). Each thread has its own HTTP session, and the "
  "counters in metrics.py are protected with a lock.")

H2("3.3 BeautifulSoup scraper (scraper_bs4.py)")
P("The season page of the website normally shows 100 matches, but with <b>?all=1</b> in the URL it "
  "shows all 380 matches in <b>one plain HTML table</b>, without JavaScript. The scraper downloads "
  "this page with one request, then BeautifulSoup finds every row "
  "(&lt;tr class=\"season-event-row\"&gt;) and reads the 5 cells: date, round, home team, score, "
  "away team.")

H2("3.4 Selenium scraper (scraper_selenium.py)")
P("Selenium starts a headless Chrome browser (no window), opens the same page, waits until the "
  "table is there, and reads the same cells as BeautifulSoup. Because the browser downloads many files "
  "by itself, we ask Chrome for the list of all downloaded files (JavaScript Performance API) to count "
  "the requests and bytes.")

H2("Responsible scraping")
bullets(["a clear <b>User-Agent</b> that says this is a university project,",
         "<b>rate limiting</b> (4 s between API requests, respect of Retry-After),",
         "<b>timeouts and error handling</b> (no crash on a failed request),",
         "one reused connection (<i>requests.Session</i>) instead of a new one for every request."])

# =================================================================
# 4. Problems
# =================================================================
H1("4. Problems we faced and how we solved them")
table([["Problem", "Solution"],
       [Paragraph("The API's whole-season endpoint returns only 15 matches with the free key.", small),
        Paragraph("Ask one round at a time: 38 requests, 380 matches.", small)],
       [Paragraph("With 2.5 s between requests, the API answered <i>429 Too Many Requests</i> after ~11 "
                  "requests; our first run got only 210 of 380 matches. Our retries (5 s) came before "
                  "the 6 s the server asked for.", small),
        Paragraph("4 s between requests and wait the <i>Retry-After</i> time after a 429. Result: "
                  "380 of 380 matches.", small)],
       [Paragraph("The website season page shows only 100 matches.", small),
        Paragraph("Found that <b>?all=1</b> shows all 380 matches in one page.", small)],
       [Paragraph("Each team name appears twice in the HTML (full name for computers, short name "
                  "like 'Manchester Ci' for phones).", small),
        Paragraph("Take only the link with the CSS class <i>d-lg-block</i> (desktop version).", small)],
       [Paragraph("Selenium only reads <i>visible</i> text, and the full names and the round column "
                  "are hidden on small screens.", small),
        Paragraph("Open the browser with a large window (1920x1080).", small)],
       [Paragraph("The browser cannot tell us the size of files from other domains (images, Google "
                  "ads): they count as 0.", small),
        Paragraph("We use the tcpdump capture to measure the real traffic.", small)],
       [Paragraph("Our measurement script hung after the API run (bash <i>wait</i> waited for a "
                  "background loop that never ends).", small),
        Paragraph("Wait only for the tcpdump process; allow running only some steps again.", small)]],
      [8 * cm, 8 * cm])

# =================================================================
# 5. Network results
# =================================================================
story.append(CondPageBreak(10 * cm))      # new page only if less than 10 cm are left
H1("5. Network results")
H2("5.1 Performance metrics")
rows = [["Method", "Total time (s)", "Requests", "Data (KB)", "Avg latency (ms)", "Matches"]]
for name, m in [("API", api), ("API threaded", thr), ("BeautifulSoup", bs4), ("Selenium", sel)]:
    rows.append([name, f"{m.total_time_s:.2f}", int(m.num_requests), f1(m.bandwidth_kb),
                 f1(m.avg_latency_ms), int(m.rows_collected)])
table(rows)
figure("net_metrics_comparison.png", "Figure 1: comparison of the four scrapers (time is on a log scale).")
bullets([f"<b>BeautifulSoup is the fastest</b> ({bs4.total_time_s:.2f} s): one request is enough "
         f"because the website shows the whole season in one page.",
         f"<b>Selenium</b> needs {sel.total_time_s:.0f} s: starting the browser, loading all the "
         f"page's files, and reading 380 rows through the WebDriver (each cell is a separate command).",
         f"<b>The API is the slowest in total</b> ({api.total_time_s:.0f} s), but not because the API is "
         f"slow: the time spent inside the requests is only about {api_network_s:.1f} s. About "
         f"{100 * (1 - api_network_s / api.total_time_s):.0f}% of the time is <b>waiting</b> because of the "
         f"rate limit of the free key and the 38 separate requests.",
         f"Per request, the API is the fastest ({api.avg_latency_ms:.0f} ms against "
         f"{bs4.avg_latency_ms:.0f} ms for the HTML page) and it downloads the least data "
         f"({api.bandwidth_kb:.0f} KB): only the JSON data we need.",
         f"The <b>threaded API</b> scraper was about {100 * (1 - thr.total_time_s / api.total_time_s):.0f}% "
         f"faster ({thr.total_time_s:.0f} s), but needed {int(thr.num_requests)} requests because it got "
         f"{retries['api_threaded']} <i>429</i> errors (the normal API scraper: {retries['api']})."])

H2("5.2 Packet captures (tcpdump)")
P("During each run we captured all TCP traffic on ports 80 and 443 with tcpdump and analyzed the "
  ".pcap files with Python (scapy). Even with HTTPS, the first message of every connection "
  "(the TLS <i>ClientHello</i>) contains the server name in clear text (SNI), so we can see "
  "<b>which domains</b> each method contacted.")
rows = [["Method", "Packets", "Bytes on network (KB)", "TCP connections", "Domains", "Duration (s)"]]
for m, name in [("api", "API"), ("bs4", "BeautifulSoup"), ("selenium", "Selenium")]:
    r = pcap.loc[m]
    rows.append([name, int(r.packets), f1(r.total_kb), int(r.tcp_connections), int(r.domains),
                 f1(r.duration_s)])
table(rows)
figure("net_pcap_summary.png", "Figure 2: what tcpdump captured for each method.")
P("The API and BeautifulSoup use <b>only one TCP connection</b> to www.thesportsdb.com. "
  f"Selenium opened <b>{int(pcap.loc['selenium', 'tcp_connections'])} connections</b> to "
  f"<b>{int(pcap.loc['selenium', 'domains'])} different domains</b>.")
figure("net_selenium_traffic_groups.png",
       "Figure 3: where Selenium's captured traffic went.", WIDTH * 0.9)
P(f"<b>Only {site_kb:.0f} KB of the {sel_total_kb:.0f} KB ({100 * site_kb / sel_total_kb:.0f}%) captured "
  f"during the Selenium run came from TheSportsDB.</b> Most of the traffic was "
  f"<b>Selenium Manager</b> (it downloads version lists from GitHub to choose the right ChromeDriver, "
  f"at every start) and <b>Chrome's background services</b> (updates, Google account, optimization "
  f"guide). The page also loads <b>ads and trackers</b> (Google Tag Manager, Cloudflare Insights, "
  f"Plausible). Note: Chrome also uses QUIC (HTTP/3 over UDP), which our TCP-only capture did not "
  f"include, so the real traffic was even bigger.")
figure("net_packets_over_time.png",
       "Figure 4: packets over time. API: small regular bursts (one per round); "
       "BeautifulSoup: one short burst; Selenium: one big burst then background traffic.")

H2("5.3 Live monitoring (screenshots)")
screenshot("ss_api.png", "ss during the API run: a single HTTPS connection (python to TheSportsDB).")
screenshot("ss_selenium.png", "ss during the Selenium run: many parallel connections from Chrome "
                              "(TCP and QUIC/UDP on port 443).")
screenshot("nload_api.png", "nload during the API run: small, regular traffic peaks.")
screenshot("nload_selenium.png", "nload during the Selenium run: a much bigger peak.")
screenshot("iftop_api.png", "iftop during the API run: only one remote host.")
screenshot("iftop_selenium.png", "iftop during the Selenium run: many remote hosts at the same time.")
screenshot("tcpdump.png", "tcpdump: the TCP three-way handshake (SYN, SYN-ACK, ACK) and then encrypted "
                          "TLS traffic.")
screenshot("wireshark_conversations.png", "Wireshark - Statistics > Conversations (Selenium capture).")
screenshot("wireshark_protocols.png", "Wireshark - Statistics > Protocol Hierarchy: almost all data is "
                                      "TLS (encrypted HTTPS).")

# =================================================================
# 6. Security
# =================================================================
H1("6. Security part")
H2("6.1 Firewall test with ufw")
P("To show how a firewall can control scraping traffic, we blocked all outgoing HTTPS traffic with "
  "<b>sudo ufw reject out 443/tcp</b> and ran the API scraper (2 test rounds). We used <i>reject</i> "
  "instead of <i>deny</i> so that the connection is refused immediately (with <i>deny</i>, packets are "
  "silently dropped and every request waits for its 30 s timeout).")
table([["", "Rule active (443 blocked)", "Rule removed"],
       ["Result", "every request failed: 'Network is unreachable'", "requests work normally"],
       ["Matches collected", "0", "20"],
       ["Time", "44.5 s (5 attempts x 2 rounds, waiting between retries)", "4.5 s"],
       ["Did the program crash?", "No: errors are caught, it retries and continues", "-"]],
      [3.5 * cm, 7.5 * cm, 5 * cm])
screenshot("ufw.png", "ufw status with the REJECT OUT rule, and the failed API run.")

H2("6.2 Rate limiting")
P("Rate limiting protects the server, and also protects us: when we went too fast, the server "
  "blocked us (429 errors) and we lost data. With 4 s between requests and respecting the "
  "<i>Retry-After</i> header, we got all 380 matches. The real limit of the free key was stricter than "
  "the documented ~30 requests per minute, so rate limits must be <b>tested, not assumed</b>.")

H2("6.3 Multithreading: speed vs. stability")
P(f"With 4 threads the API scraper was {100 * (1 - thr.total_time_s / api.total_time_s):.0f}% faster, "
  f"but it received {retries['api_threaded']} <i>429</i> errors instead of {retries['api']}. When the "
  f"server limits the number of requests, threads mainly make us hit the limit faster. They give a "
  f"small gain in speed but less stability and less politeness towards the server.")

# =================================================================
# 7. Machine learning
# =================================================================
story.append(CondPageBreak(10 * cm))
H1("7. Machine learning results")
H2("7.1 Method")
bullets(["Matches sorted by date; no missing values and no duplicates.",
         "Features calculated <b>only from previous matches</b> (no data leakage), for the home team and "
         "the away team: <b>form</b> (points in the last 5 matches), <b>average goals scored</b> and "
         "<b>average goals conceded</b> in the last 5 matches. The first 3 features describe the home team "
         "and the last 3 the away team, so the model can learn the home advantage.",
         "Matches where a team had fewer than 5 previous games were skipped: 329 matches remain.",
         "<b>Training</b> on the 229 earlier matches, <b>test</b> on the <b>last 100 matches</b> of the season "
         "(all 20 teams)."])
figure("eda_home_vs_away.png", "Figure 5: home teams score more goals than away teams (home advantage).",
       WIDTH * 0.9)

H2("7.2 Regression: predicting goals (MAE)")
rows = [["Model", "MAE home goals", "MAE away goals", "Average MAE"]]
for model, r in mae.iterrows():
    rows.append([model, f"{r.home_goals:.2f}", f"{r.away_goals:.2f}", f"{r.average:.2f}"])
table(rows)
P(f"<b>{best_reg}</b> is the best model: on average our predicted number of goals is about "
  f"<b>{mae.loc[best_reg, 'average']:.1f} goal</b> away from the real number. This is only a little "
  f"better than always predicting the average, because football scores are very random. Only "
  f"{n_exact} of the 100 exact scores were predicted correctly.")

H2("7.3 Classification: predicting W / D / L (accuracy)")
rows = [["Model", "Accuracy on the last 100 matches"]]
for model, r in acc.iterrows():
    rows.append([model, f"{r['accuracy'] * 100:.0f}%"])
table(rows, [8 * cm, 6 * cm])
figure("ml_confusion_matrices.png", "Figure 6: confusion matrices (rows = real result, columns = "
                                    "predicted result).")
P(f"<b>{best_clf}</b> reached <b>{best_acc:.0%}</b> accuracy, against <b>{base_acc:.0%}</b> for the "
  f"simple baseline that always predicts a home win (+{(best_acc - base_acc) * 100:.0f} percentage points). "
  f"So the form features really help. The models are good at home wins and home losses, but "
  f"<b>never predict a draw</b>: a draw looks like 'two similar teams', which can also end in a win "
  f"or a loss.")

H2("7.4 Predictions for the last 100 matches")
P(f"The full table (home team, away team, predicted score, real score, predicted result, real result, "
  f"correct or not) is in <b>data/predictions_last100.csv</b> and in the ML notebook. Summary: "
  f"<b>{n_correct} of 100 results correct</b>, {n_exact} exact scores. The first 10 matches:")
rows = [["Home team", "Away team", "Pred. score", "Real score", "Pred.", "Real", "OK"]]
for _, r in pred.head(10).iterrows():
    rows.append([r.home_team, r.away_team, r.predicted_score, r.real_score, r.predicted_result,
                 r.real_result, r.correct])
table(rows, [3.6 * cm, 3.6 * cm, 2 * cm, 2 * cm, 1.4 * cm, 1.4 * cm, 1.2 * cm])
P("Limitations: only one season, only 6 simple features, and a small test set (1 match = 1%). We chose "
  "the best model by looking at the test results, which makes the result a little optimistic.", small)

# =================================================================
# 8. Recommendation
# =================================================================
H1("8. Optimization recommendation: which method is best?")
table([["", "API", "BeautifulSoup", "Selenium"],
       ["Network efficiency", "best (only data)", "good (1 page)", "worst (many files, domains)"],
       ["Total speed (our case)", "slow (rate limit)", "fastest", "medium"],
       ["Stability", "high (official format)", "breaks if the HTML changes", "most fragile"],
       ["Data quality", "clean JSON fields", "needs careful parsing", "needs careful parsing"],
       ["Needed when...", "an API exists", "data is in plain HTML", "page needs JavaScript"]],
      [4 * cm, 4 * cm, 4 * cm, 4.5 * cm])
P("<b>Our recommendation:</b>")
bullets(["Use the <b>API</b> when it gives all the data: it is the most efficient for the network, the most "
         "stable and gives the cleanest data. With a paid key (whole season in one request) it would also "
         "be the fastest.",
         "Use <b>BeautifulSoup</b> when the data is in plain HTML and the API is limited. On TheSportsDB it was "
         "the best compromise: 1 request, under 1 second, same data.",
         "Use <b>Selenium only when the page needs JavaScript</b>: a full browser downloads a lot of "
         "traffic that has nothing to do with the data (Selenium Manager, Chrome services, ads, trackers).",
         "Always respect the rate limit; adding threads does not help when the server limits the request rate."])

# =================================================================
# 9. Conclusion
# =================================================================
H1("9. Conclusion")
P("We collected the same 380 Premier League matches with three scraping methods and got identical "
  "data from all of them. The methods are very different on the network: the API sends only the data, "
  "BeautifulSoup needs one HTML page, and Selenium generates much more traffic to many servers. In "
  "our case the free API key's limits made the API the slowest method in total time, even though it is "
  "the most efficient per request. The network tools (ss, iftop, nload, tcpdump, Wireshark) confirmed "
  "these differences, and the ufw test showed how a firewall rule can stop scraping traffic completely.")
P(f"With machine learning, simple features based on the last 5 matches predicted the result of the "
  f"last 100 matches with {best_acc:.0%} accuracy, better than the {base_acc:.0%} of always predicting "
  f"a home win, and predicted goals with an error of about one goal. More seasons and more features "
  f"would be needed to do better.")


# ---------------- build the PDF ----------------
def page_number(canvas, doc):
    canvas.setFont("Helvetica", 8)
    canvas.drawRightString(A4[0] - 2 * cm, 1.2 * cm, f"Page {doc.page}")


doc = SimpleDocTemplate(str(OUT), pagesize=A4, leftMargin=2 * cm, rightMargin=2 * cm,
                        topMargin=2 * cm, bottomMargin=2 * cm,
                        title="Web Scraping, Network Analysis and ML - Final Report",
                        author="Jana Alamir, Rim Zoghbi")
doc.build(story, onFirstPage=page_number, onLaterPages=page_number)
missing = [p for p in ["ss_api.png", "ss_selenium.png", "nload_api.png", "nload_selenium.png",
                       "iftop_api.png", "iftop_selenium.png", "tcpdump.png", "wireshark_conversations.png",
                       "wireshark_protocols.png", "ufw.png"] if not (SHOTS / p).exists()]
print(f"Saved {OUT.relative_to(PROJECT)}")
if missing:
    print(f"{len(missing)} screenshot placeholders (add them to network/screenshots/): {', '.join(missing)}")
