"""
Builds report/presentation.pptx (12 slides, ~10 minutes) from our results and charts.
Each slide has speaker notes (what to say).

Screenshots in network/screenshots/ (e.g. iftop_selenium.png) are inserted automatically;
missing ones are shown as placeholder boxes. Re-run after adding them.

Run from the project folder:  python report/build_presentation.py
"""

from pathlib import Path

import pandas as pd
from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.shapes import MSO_SHAPE
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt

PROJECT = Path(__file__).resolve().parent.parent
DATA, NET, FIGS = PROJECT / "data", PROJECT / "network", PROJECT / "report" / "figures"
SHOTS = NET / "screenshots"
OUT = PROJECT / "report" / "presentation.pptx"

# ---------------- results ----------------
metrics = pd.read_csv(DATA / "metrics.csv").groupby("method").tail(1).set_index("method")
pcap = pd.read_csv(NET / "pcap_summary.csv", index_col=0)
groups = pd.read_csv(NET / "selenium_traffic_groups.csv", index_col=0)["KB"]
mae = pd.read_csv(DATA / "ml_mae.csv", index_col=0)
acc = pd.read_csv(DATA / "ml_accuracy.csv", index_col=0)
api, thr, bs4, sel = (metrics.loc[m] for m in ["api", "api_threaded", "bs4", "selenium"])
best_reg = mae.drop("Baseline (average)").index[0]
best_clf = acc.drop("Baseline (always home win)").index[0]
best_acc, base_acc = acc.loc[best_clf, "accuracy"], acc.loc["Baseline (always home win)", "accuracy"]
site_pct = 100 * groups.get("TheSportsDB (website + images)", 0) / groups.sum()
wait_pct = 100 * (1 - api.num_requests * api.avg_latency_ms / 1000 / api.total_time_s)

# ---------------- design helpers ----------------
NAVY, BLUE, GRAY = RGBColor(0x1F, 0x38, 0x64), RGBColor(0x2E, 0x55, 0x97), RGBColor(0x59, 0x59, 0x59)
prs = Presentation()
prs.slide_width, prs.slide_height = Inches(13.333), Inches(7.5)   # 16:9
BLANK = prs.slide_layouts[6]


def new_slide(title, notes=""):
    slide = prs.slides.add_slide(BLANK)
    bar = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, Inches(1.0))
    bar.fill.solid(); bar.fill.fore_color.rgb = NAVY; bar.line.fill.background()
    tf = bar.text_frame
    tf.text = title
    p = tf.paragraphs[0]; p.font.size = Pt(30); p.font.bold = True
    p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF); p.alignment = PP_ALIGN.LEFT
    tf.margin_left = Inches(0.5)
    slide.notes_slide.notes_text_frame.text = notes
    return slide


def text(slide, left, top, width, height, lines, size=18):
    """lines: list of strings; a line starting with '- ' is a sub-bullet, '#' = bold heading line."""
    box = slide.shapes.add_textbox(Inches(left), Inches(top), Inches(width), Inches(height))
    tf = box.text_frame; tf.word_wrap = True
    for i, line in enumerate(lines):
        p = tf.paragraphs[0] if i == 0 else tf.add_paragraph()
        bold = line.startswith("#")
        sub = line.startswith("- ")
        p.text = ("    – " + line[2:]) if sub else ("" if bold else "• ") + line.lstrip("# ")
        p.font.size = Pt(size - 3 if sub else size)
        p.font.bold = bold
        p.font.color.rgb = BLUE if bold else (GRAY if sub else RGBColor(0x26, 0x26, 0x26))
        p.space_after = Pt(6)
    return box


def picture(slide, path, left, top, width=None, height=None):
    kwargs = {}
    if width: kwargs["width"] = Inches(width)
    if height: kwargs["height"] = Inches(height)
    return slide.shapes.add_picture(str(path), Inches(left), Inches(top), **kwargs)


def screenshot(slide, name, label, left, top, width, height):
    path = SHOTS / name
    if path.exists():
        # Fit the screenshot inside the box (width x height) without changing its proportions
        pic = picture(slide, path, left, top, height=height)
        if pic.width > Inches(width):
            ratio = Inches(width) / pic.width
            pic.width, pic.height = Inches(width), int(pic.height * ratio)
    else:
        box = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(left), Inches(top), Inches(width), Inches(height))
        box.fill.solid(); box.fill.fore_color.rgb = RGBColor(0xEE, 0xEE, 0xEE)
        box.line.color.rgb = RGBColor(0x99, 0x99, 0x99)
        box.text_frame.text = f"[Screenshot: {label}]\nnetwork/screenshots/{name}"
        for p in box.text_frame.paragraphs:
            p.font.size = Pt(14); p.font.color.rgb = GRAY; p.alignment = PP_ALIGN.CENTER
    cap = slide.shapes.add_textbox(Inches(left), Inches(top + height + 0.05), Inches(width), Inches(0.4))
    cap.text_frame.text = label
    cap.text_frame.paragraphs[0].font.size = Pt(13); cap.text_frame.paragraphs[0].font.color.rgb = GRAY


# =========================== slides ===========================
# 1. Title
s = prs.slides.add_slide(BLANK)
bg = s.shapes.add_shape(MSO_SHAPE.RECTANGLE, 0, 0, prs.slide_width, prs.slide_height)
bg.fill.solid(); bg.fill.fore_color.rgb = NAVY; bg.line.fill.background()
t = s.shapes.add_textbox(Inches(0.8), Inches(2.0), Inches(11.7), Inches(3)).text_frame
t.word_wrap = True
t.text = "Analyzing Website Data Collection Efficiency and Network Behavior Using Multiple Web Scraping Techniques"
t.paragraphs[0].font.size = Pt(36); t.paragraphs[0].font.bold = True
t.paragraphs[0].font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
p = t.add_paragraph(); p.text = "API vs BeautifulSoup vs Selenium  •  Network analysis  •  Machine learning"
p.font.size = Pt(20); p.font.color.rgb = RGBColor(0xC9, 0xD6, 0xEA)
p = t.add_paragraph(); p.text = "\nJana Alamir & Rim Zoghbi"
p.font.size = Pt(22); p.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
s.notes_slide.notes_text_frame.text = ("Introduce yourselves and the topic: we scraped the same football data "
                                       "with three methods and compared them on the network, then used the data for ML.")

# 2. Goal
s = new_slide("Project goal", "Explain the 3 questions of the project. ~45 seconds.")
text(s, 0.6, 1.4, 12, 5.5, [
    "#Collect the SAME data with three web scraping methods",
    "API (JSON)  •  BeautifulSoup (HTML)  •  Selenium (real browser)",
    "#Compare their efficiency and network behavior",
    "time, number of requests, bandwidth, latency",
    "live tools: ss, iftop, nload, tcpdump, Wireshark — and a ufw firewall test",
    "#Use the data for machine learning",
    "predict goals (regression) and W / D / L results (classification)",
], 22)

# 3. Website and data
s = new_slide("Website and data", "Why TheSportsDB: it has both a website and an API with the same data, "
              "so the comparison is fair. Show the columns.")
text(s, 0.6, 1.4, 6.2, 5.5, [
    "#TheSportsDB.com",
    "free sports database: website + JSON API (free test key)",
    "#English Premier League 2023-2024",
    "20 teams, 38 rounds, 380 matches",
    "#7 columns for every method",
    "date, round, home_team, away_team, home_goals, away_goals, result (W/D/L for the home team)",
    "#Result: 380 matches from every method, files 100% identical",
], 19)
picture(s, FIGS / "eda_results.png", 7.1, 1.5, width=5.8)

# 4. Methods
s = new_slide("Three scraping methods",
              "Explain each column. Mention the problems: free API key limited (15 matches) -> one request per "
              "round; website page shows 100 matches -> ?all=1; Selenium window size for visible text.")
cols = [("API", ["eventsround.php: 1 request per round (38)",
                 "season endpoint: only 15 matches with free key",
                 "4 s between requests, respects Retry-After",
                 "+ threaded version: 4 threads, shared rate limiter"]),
        ("BeautifulSoup", ["requests + HTML parsing",
                           "season page with ?all=1 = all 380 matches",
                           "1 request, 1 page",
                           "reads <tr class='season-event-row'>"]),
        ("Selenium", ["headless Chrome browser",
                      "same page, waits for the table",
                      "1920x1080 window (only visible text is readable)",
                      "requests counted with the browser's Performance API"])]
for i, (title, items) in enumerate(cols):
    text(s, 0.5 + i * 4.2, 1.4, 4.0, 5.0, ["#" + title] + items, 17)
text(s, 0.5, 6.2, 12.3, 0.8, ["#Shared metrics.py: timer, request counter, bytes, latency -> data/metrics.csv  •  "
                              "User-Agent, timeouts, error handling"], 15)

# 5. Performance comparison
s = new_slide("Performance comparison",
              f"BeautifulSoup fastest: 1 request. API slowest in total but ~{wait_pct:.0f}% of its time is waiting "
              f"(rate limit + 38 requests); per request it is the fastest and downloads the least. Threads: faster "
              f"but more 429 errors.")
picture(s, FIGS / "net_metrics_comparison.png", 0.3, 1.3, height=5.6)   # 8.4 in wide
text(s, 9.0, 1.4, 4.1, 5.8, [
    f"#BeautifulSoup: {bs4.total_time_s:.2f} s",
    "1 request, whole season in one page",
    f"#Selenium: {sel.total_time_s:.0f} s",
    "browser + 60 files + slow WebDriver reading",
    f"#API: {api.total_time_s:.0f} s",
    f"~{wait_pct:.0f}% waiting (rate limit)",
    f"fastest per request ({api.avg_latency_ms:.0f} ms), least data ({api.bandwidth_kb:.0f} KB)",
    f"#Threaded API: {thr.total_time_s:.0f} s",
    f"{int(thr.num_requests) - 38} errors 429 vs {int(api.num_requests) - 38}",
], 16)

# 6. Network traces
s = new_slide("Network traces (tcpdump + scapy)",
              f"From the pcap files: API and BeautifulSoup = 1 TCP connection to 1 domain. Selenium = "
              f"{int(pcap.loc['selenium', 'tcp_connections'])} connections, {int(pcap.loc['selenium', 'domains'])} "
              f"domains. Only {site_pct:.0f}% of Selenium's traffic was the website: Selenium Manager downloads "
              f"version lists from GitHub, Chrome contacts Google services, plus ads and trackers.")
picture(s, FIGS / "net_pcap_summary.png", 0.3, 1.2, width=7.4)
picture(s, FIGS / "net_selenium_traffic_groups.png", 0.3, 4.2, width=7.4)
text(s, 8.0, 1.4, 5.0, 5.8, [
    "#API & BeautifulSoup",
    "1 TCP connection, 1 domain (www.thesportsdb.com)",
    "#Selenium",
    f"{int(pcap.loc['selenium', 'packets'])} packets, {pcap.loc['selenium', 'total_kb'] / 1024:.1f} MB",
    f"{int(pcap.loc['selenium', 'tcp_connections'])} connections, {int(pcap.loc['selenium', 'domains'])} domains",
    f"only {site_pct:.0f}% of the traffic was the website!",
    "- Selenium Manager (GitHub), Chrome services, ads / trackers",
    "#Domain names visible even with HTTPS (TLS SNI)",
], 16)

# 7. Live tools
s = new_slide("Live monitoring: ss, iftop, nload, Wireshark",
              "Show the difference between API (one connection, small regular traffic) and Selenium "
              "(many connections, big peak). Wireshark protocol hierarchy: almost everything is TLS.")
screenshot(s, "iftop_api.png", "iftop – API: one remote host", 0.4, 1.3, 6.1, 2.6)
screenshot(s, "iftop_selenium.png", "iftop – Selenium: many remote hosts", 6.8, 1.3, 6.1, 2.6)
screenshot(s, "nload_selenium.png", "nload – Selenium traffic peak", 0.4, 4.4, 6.1, 2.5)
screenshot(s, "wireshark_conversations.png", "Wireshark – Conversations", 6.8, 4.4, 6.1, 2.5)

# 8. Security
s = new_slide("Security: ufw, rate limiting, multithreading",
              "ufw: we blocked outgoing port 443 -> the scraper got 'Network is unreachable', 0 matches, no crash. "
              "Removed the rule -> 20 matches in 4.5 s. Rate limit: going too fast cost us data (210/380 on the "
              "first run). Threads: faster but more 429 errors.")
text(s, 0.6, 1.4, 6.3, 5.8, [
    "#ufw firewall test",
    "sudo ufw reject out 443/tcp",
    "API scraper: 'Network is unreachable', 0 matches, no crash",
    "rule removed: 20 matches in 4.5 s",
    "#Rate limiting",
    "2.5 s between requests -> 429 errors, only 210/380 matches",
    "4 s + Retry-After -> 380/380 matches",
    "#Multithreading (4 threads)",
    f"{100 * (1 - thr.total_time_s / api.total_time_s):.0f}% faster, but "
    f"{int(thr.num_requests) - 38} instead of {int(api.num_requests) - 38} errors 429",
], 17)
screenshot(s, "ufw.png", "ufw status + blocked API run", 7.2, 1.4, 5.7, 4.8)

# 9. ML method
s = new_slide("Machine learning: method",
              "Key point: no data leakage. Features only from matches BEFORE each game. Time-based split: "
              "train on the past, test on the last 100 matches.")
text(s, 0.6, 1.4, 6.5, 5.8, [
    "#Features from the last 5 PREVIOUS matches (no data leakage)",
    "form = points in last 5 games (0-15)",
    "average goals scored / conceded",
    "for the home team and the away team (home/away)",
    "#Train / test split by time",
    "first 5 games of each team skipped -> 329 matches",
    "train: 229 earlier matches • test: last 100 matches",
    "#Models",
    "goals: Linear Regression, Random Forest (MAE)",
    "W/D/L: Logistic Regression, Random Forest (accuracy)",
], 17)
picture(s, FIGS / "eda_home_vs_away.png", 7.3, 1.6, width=5.8)

# 10. ML results
s = new_slide("Machine learning: results",
              f"Best classifier {best_clf}: {best_acc:.0%} vs {base_acc:.0%} for always home win. Never predicts "
              f"draws. Best regression {best_reg}: MAE about {mae.loc[best_reg, 'average']:.1f} goal, close to "
              f"the average baseline: exact scores are very random.")
picture(s, FIGS / "ml_confusion_matrices.png", 0.3, 1.3, width=8.0)
text(s, 8.6, 1.4, 4.5, 5.8, [
    "#Classification (W/D/L)",
    f"{best_clf}: {best_acc:.0%}",
    f"baseline 'always home win': {base_acc:.0%}",
    f"+{(best_acc - base_acc) * 100:.0f} points",
    "draws are never predicted",
    "#Regression (goals)",
    f"{best_reg}: MAE {mae.loc[best_reg, 'average']:.2f}",
    f"baseline: MAE {mae.loc['Baseline (average)', 'average']:.2f}",
], 17)

# 11. Recommendation
s = new_slide("Which method is best?",
              "Our recommendation and why. API = most efficient; BeautifulSoup = fastest here; Selenium only "
              "when JavaScript is needed.")
text(s, 0.6, 1.4, 12.2, 5.8, [
    "#API — most efficient and most stable",
    "only the data, 1 server, 1 connection, clean JSON",
    "slow here only because of the free key (rate limit, 38 requests)",
    "#BeautifulSoup — fastest in our case",
    "1 request, under 1 second — but breaks if the HTML layout changes",
    "#Selenium — only when the page needs JavaScript",
    f"heavy: many files and domains, only {site_pct:.0f}% of its traffic was the website",
    "#Respect the rate limit: threads do not beat a server-side limit",
], 20)

# 12. Conclusion
s = new_slide("Conclusion", "Summarize in 3 sentences, then thank the audience and take questions.")
text(s, 0.6, 1.4, 12.2, 5.0, [
    "Same 380 matches from all three methods — identical data",
    "Very different network behavior: API << BeautifulSoup << Selenium in traffic",
    "Access rules (rate limits, free vs paid key) matter as much as the technology",
    f"Simple form features predict results with {best_acc:.0%} accuracy (baseline {base_acc:.0%})",
], 22)
q = s.shapes.add_textbox(Inches(0.6), Inches(5.8), Inches(12), Inches(1)).text_frame
q.text = "Thank you — questions?"
q.paragraphs[0].font.size = Pt(32); q.paragraphs[0].font.bold = True; q.paragraphs[0].font.color.rgb = NAVY

prs.save(OUT)
print(f"Saved {OUT.relative_to(PROJECT)} ({len(prs.slides)} slides)")
