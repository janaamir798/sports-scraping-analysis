#!/usr/bin/env bash
# =============================================================================
# Network measurements for the three scraping methods + a ufw firewall test.
#
# Run it as your normal user (NOT with sudo in front), from the project folder:
#     bash network/run_measurements.sh                  (all steps)
#     bash network/run_measurements.sh bs4 selenium ufw (only some steps)
# Steps: api, bs4, selenium, ufw. It asks for your sudo password once (tcpdump and ufw).
#
# For each method (api, bs4, selenium) it:
#   1. starts tcpdump on ports 80/443        -> network/<method>.pcap
#   2. runs the scraper with `time`          -> network/<method>_output.txt
#   3. saves `ss` snapshots during the run   -> network/<method>_ss.txt
#   4. stops tcpdump
# Then the ufw test: block outgoing port 443, run the API scraper (fails),
# remove the rule, run it again (works)     -> network/ufw_blocked.txt, ufw_allowed.txt
# =============================================================================

set -u
cd "$(dirname "$0")/.." || exit 1        # always work from the project folder
PY=".venv/bin/python"
NET="network"
IFACE="eth0"                             # WSL2's network interface
STEPS=" ${*:-api bs4 selenium ufw} "     # steps given on the command line, or all of them
want() { [[ "$STEPS" == *" $1 "* ]]; }   # is this step selected?

TCPDUMP_RUNNING=0
SS_PID=""
UFW_RULE_ADDED=0
UFW_WAS_ACTIVE=1

# ---------- small helpers for clear messages ----------
banner()     { echo; echo "=================================================================="; echo "  $1"; echo "=================================================================="; }
screenshot() { echo; echo ">>>>>>>>>>  TAKE SCREENSHOT NOW: $1  <<<<<<<<<<"; echo; }
pause()      { echo; read -r -p "$1  [press Enter to continue] " _; }

# ---------- cleanup: runs at the end, or if you press Ctrl+C ----------
# Makes sure tcpdump is stopped and the firewall rule is removed, even after an error.
cleanup() {
    [ -n "$SS_PID" ] && kill "$SS_PID" 2>/dev/null
    if [ "$TCPDUMP_RUNNING" = 1 ]; then sudo pkill -INT -x tcpdump; fi
    if [ "$UFW_RULE_ADDED" = 1 ]; then
        echo "Cleanup: removing the ufw rule that blocks port 443"
        sudo ufw delete reject out 443/tcp >/dev/null
    fi
    if [ "$UFW_WAS_ACTIVE" = 0 ]; then sudo ufw --force disable >/dev/null; fi
    [ -n "${KEEPALIVE_PID:-}" ] && kill "$KEEPALIVE_PID" 2>/dev/null
}
trap cleanup EXIT
trap 'echo; echo "Stopped by user."; exit 1' INT TERM

# ---------- checks before starting ----------
for tool in tcpdump ss ufw; do
    command -v "$tool" >/dev/null || { echo "ERROR: $tool is not installed. Run: sudo apt install $tool"; exit 1; }
done
[ -x "$PY" ] || { echo "ERROR: virtual environment not found at $PY"; exit 1; }

echo "This script needs sudo for tcpdump and ufw."
sudo -v || exit 1
# Keep sudo's password "remembered" during the long API run (it normally expires after 15 min)
( while true; do sudo -n true; sleep 60; done ) 2>/dev/null &
KEEPALIVE_PID=$!

banner "BEFORE STARTING"
echo "Open TWO more Ubuntu terminals and run (leave them open):"
echo "    Terminal 2:  sudo iftop -i $IFACE -P      (live connections and speed)"
echo "    Terminal 3:  nload $IFACE                  (live bandwidth graph)"
pause "When iftop and nload are running,"

# ---------- one measurement = tcpdump + ss + scraper ----------
measure() {
    local method=$1 script=$2
    local pcap="$NET/$method.pcap" ss_file="$NET/${method}_ss.txt" out="$NET/${method}_output.txt"

    banner "METHOD: $method   ($script)"

    # 1. Start tcpdump in the background (only web traffic: ports 80 and 443).
    #    -U writes packets immediately, -Z $USER makes the .pcap file owned by you.
    sudo tcpdump -i "$IFACE" -n -U -Z "$USER" -w "$pcap" 'tcp port 80 or tcp port 443' \
        > "$NET/${method}_tcpdump_log.txt" 2>&1 &
    local tcpdump_pid=$!
    TCPDUMP_RUNNING=1
    sleep 2                                  # give tcpdump time to start

    # 2. Save `ss` snapshots every 0.5 s while the scraper runs
    ( while true; do
          echo "=== $(date +%H:%M:%S.%3N) ==="
          ss -tunp state established
          sleep 0.5
      done ) > "$ss_file" 2>&1 &
    SS_PID=$!

    # 3. Run the scraper with `time` (in the background, so we can show screenshot prompts)
    ( time "$PY" -u "scrapers/$script" ) 2>&1 | tee "$out" &
    local run_pid=$!

    if [ "$method" = "bs4" ]; then
        echo "(bs4 finishes in about 1 second: too fast for live screenshots, that is normal)"
    else
        sleep 6
        screenshot "nload (terminal 3) and iftop (terminal 2) while $method is running"
        echo "--- ss -tunp state established (live) ---"
        ss -tunp state established
        screenshot "this terminal (the ss output above)"
    fi

    wait "$run_pid"                          # wait until the scraper finishes

    # 4. Stop ss and tcpdump
    kill "$SS_PID" 2>/dev/null; SS_PID=""
    sleep 2                                  # catch the last packets (connection closing)
    sudo pkill -INT -x tcpdump
    # Wait only for tcpdump to finish writing. (A plain `wait` would also wait for the
    # sudo keep-alive loop, which never ends -> the script would hang here.)
    wait "$tcpdump_pid" 2>/dev/null
    TCPDUMP_RUNNING=0

    local packets
    packets=$(tcpdump -r "$pcap" -n 2>/dev/null | wc -l)
    echo
    echo "Saved: $pcap ($packets packets, $(du -h "$pcap" | cut -f1)), $ss_file, $out"
    echo "--- first 15 packets of $pcap ---"
    tcpdump -r "$pcap" -n 2>/dev/null | head -15
    screenshot "tcpdump packets above ($method)"
    pause "Done with $method."
}

want api      && measure api      scraper_api.py
want bs4      && measure bs4      scraper_bs4.py
want selenium && measure selenium scraper_selenium.py

# ---------- ufw firewall test ----------
if want ufw; then
banner "UFW FIREWALL TEST: block outgoing HTTPS (port 443)"
sudo ufw status | grep -q "Status: active" && UFW_WAS_ACTIVE=1 || UFW_WAS_ACTIVE=0
sudo ufw --force enable

# "reject" instead of "deny": deny silently drops packets, so every request would hang
# until its 30 s timeout. reject answers immediately "connection refused" -> faster test.
sudo ufw reject out 443/tcp
UFW_RULE_ADDED=1
sudo ufw status verbose | tee "$NET/ufw_status.txt"
screenshot "ufw status above (rule: REJECT OUT 443/tcp)"

echo "Running the API scraper with port 443 BLOCKED (2 test rounds, saves nothing)..."
{ echo "### ufw rule active: reject out 443/tcp"
  ( time "$PY" -u scrapers/scraper_api.py --test-rounds 2 ) 2>&1
} | tee "$NET/ufw_blocked.txt"
screenshot "the failed API run above (connection refused)"

sudo ufw delete reject out 443/tcp
UFW_RULE_ADDED=0
echo
echo "Rule removed. Running the API scraper again (2 test rounds)..."
{ echo "### ufw rule removed"
  ( time "$PY" -u scrapers/scraper_api.py --test-rounds 2 ) 2>&1
} | tee "$NET/ufw_allowed.txt"
screenshot "the successful API run above"
fi

banner "ALL DONE"
echo "Files in $NET/:"
ls -lh "$NET" | grep -v gitkeep
echo
echo "Next: open the .pcap files in Wireshark (Windows) from:"
echo "    \\\\wsl.localhost\\Ubuntu$(pwd)/$NET/"
echo "and take screenshots of: Statistics > Conversations, and Statistics > Protocol Hierarchy."
