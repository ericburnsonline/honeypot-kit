#!/usr/bin/env python3
"""
Honeypot Kit TUI
Version: 1

Full-screen terminal interface for Honeypot Kit.
Run as: hk  (or honeypot-kit menu)

Navigation:
  Arrow keys / j/k : move
  Enter / Space    : select
  q / Escape       : back / quit
  r                : refresh current screen
"""

import curses
import os
import sys
import json
import subprocess
import time
import textwrap
from pathlib import Path
from datetime import datetime

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------

HONEYPOT_HOME   = "/opt/honeypot"
COWRIE_JSON     = f"{HONEYPOT_HOME}/cowrie/var/log/cowrie/cowrie.json"
CONF_FILE       = f"{HONEYPOT_HOME}/honeypot-kit.conf"
MONITOR_STATE   = f"{HONEYPOT_HOME}/monitor-state.json"
UPDATES_LOG     = f"{HONEYPOT_HOME}/logs/updates.log"
MONITOR_LOG     = f"{HONEYPOT_HOME}/logs/monitor.log"
SMOKE_TEST      = f"{HONEYPOT_HOME}/scripts/smoke-test.sh"
AI_CONF         = f"{HONEYPOT_HOME}/integrations/openai/config.json"
AI_ANALYZER     = f"{HONEYPOT_HOME}/integrations/openai/analyzer.py"
AI_ANALYSIS_DIR = f"{HONEYPOT_HOME}/integrations/openai/analysis"

# ---------------------------------------------------------------------------
# Colors
# ---------------------------------------------------------------------------

GREEN  = 0
YELLOW = 0
RED    = 0
CYAN   = 0
NORMAL = 0
SEL    = 0

def init_colors():
    global GREEN, YELLOW, RED, CYAN, NORMAL, SEL
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_GREEN,   -1)  # good / enabled
    curses.init_pair(2, curses.COLOR_YELLOW,  -1)  # warning
    curses.init_pair(3, curses.COLOR_RED,     -1)  # error / alert
    curses.init_pair(4, curses.COLOR_CYAN,    -1)  # highlight / header
    curses.init_pair(5, curses.COLOR_WHITE,   -1)  # normal
    curses.init_pair(6, curses.COLOR_BLACK,   curses.COLOR_WHITE)  # selected row
    GREEN  = curses.A_BOLD | curses.color_pair(1)
    YELLOW = curses.A_BOLD | curses.color_pair(2)
    RED    = curses.A_BOLD | curses.color_pair(3)
    CYAN   = curses.A_BOLD | curses.color_pair(4)
    NORMAL = curses.color_pair(5)
    SEL    = curses.color_pair(6)

# ---------------------------------------------------------------------------
# Utility
# ---------------------------------------------------------------------------

def run(cmd, timeout=10):
    """Run a shell command and return stdout."""
    try:
        result = subprocess.run(
            cmd, shell=True, capture_output=True, text=True, timeout=timeout
        )
        return result.stdout.strip(), result.returncode
    except Exception as e:
        return str(e), 1


def systemctl_status(service):
    """Return True if service is active."""
    out, rc = run(f"systemctl is-active {service} 2>/dev/null")
    return out.strip() == "active"


def load_json(path):
    try:
        with open(path) as f:
            return json.load(f)
    except Exception:
        return {}


def load_config():
    import configparser
    config = configparser.ConfigParser()
    config.read(CONF_FILE)
    return config


def draw_header(win, title):
    h, w = win.getmaxyx()
    win.clear()
    header = f" Honeypot Kit  |  {title} "
    win.addstr(0, 0, " " * w, CYAN)
    win.addstr(0, max(0, (w - len(header)) // 2), header[:w], CYAN)
    win.addstr(h - 1, 0, " q:Back  r:Refresh  Arrow:Navigate  Enter:Select "[:w - 1], curses.A_DIM)


def draw_status_bar(win, msg, color=NORMAL):
    h, w = win.getmaxyx()
    win.addstr(h - 1, 0, " " * (w - 1), color)
    win.addstr(h - 1, 0, msg[:w - 1], color)


def menu(stdscr, title, items, draw_item_fn=None, on_refresh=None):
    """
    Generic scrollable menu.
    items: list of dicts with at least 'label' key.
    draw_item_fn(win, y, x, item, selected, width) - custom row renderer.
    Returns selected item or None if quit.
    """
    curses.curs_set(0)
    selected = 0
    scroll   = 0

    while True:
        if on_refresh:
            items = on_refresh()

        h, w = stdscr.getmaxyx()
        draw_header(stdscr, title)

        visible = h - 3  # header + footer
        if selected < scroll:
            scroll = selected
        if selected >= scroll + visible:
            scroll = selected - visible + 1

        for i, item in enumerate(items[scroll:scroll + visible]):
            y   = i + 1
            idx = i + scroll
            is_sel = (idx == selected)

            if draw_item_fn:
                draw_item_fn(stdscr, y, 0, item, is_sel, w)
            else:
                label = item.get("label", str(item))
                if is_sel:
                    stdscr.addstr(y, 0, f" {label:<{w-2}}", SEL)
                else:
                    stdscr.addstr(y, 0, f" {label:<{w-2}}", NORMAL)

        # Scroll indicators
        if scroll > 0:
            stdscr.addstr(1, w - 2, "▲", curses.A_DIM)
        if scroll + visible < len(items):
            stdscr.addstr(h - 2, w - 2, "▼", curses.A_DIM)

        stdscr.refresh()

        key = stdscr.getch()
        if key in (curses.KEY_UP, ord("k")):
            selected = max(0, selected - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            selected = min(len(items) - 1, selected + 1)
        elif key in (curses.KEY_ENTER, ord("\n"), ord(" ")):
            if items:
                return items[selected]
        elif key in (ord("q"), 27):  # q or Escape
            return None
        elif key == ord("r") and on_refresh:
            pass  # loop will refresh


def message_box(stdscr, title, lines, wait=True):
    """Show a scrollable message box."""
    curses.curs_set(0)
    scroll = 0

    while True:
        h, w = stdscr.getmaxyx()
        draw_header(stdscr, title)

        visible = h - 3
        for i, line in enumerate(lines[scroll:scroll + visible]):
            y = i + 1
            # Color hints
            attr = NORMAL
            if line.startswith("  [PASS]"):
                attr = GREEN
            elif line.startswith("  [FAIL]"):
                attr = RED
            elif line.startswith("  [WARN]"):
                attr = YELLOW
            elif line.startswith("INTENT"):
                attr = CYAN
            elif line.startswith("  "):
                attr = NORMAL
            stdscr.addstr(y, 0, line[:w - 1], attr)

        if scroll + visible < len(lines):
            stdscr.addstr(h - 2, w - 2, "▼", curses.A_DIM)
        if scroll > 0:
            stdscr.addstr(1, w - 2, "▲", curses.A_DIM)

        if wait:
            draw_status_bar(stdscr, " q:Back  ↑↓:Scroll ", curses.A_DIM)
        stdscr.refresh()

        if not wait:
            time.sleep(0.05)
            return

        key = stdscr.getch()
        if key in (ord("q"), 27):
            return
        elif key in (curses.KEY_UP, ord("k")):
            scroll = max(0, scroll - 1)
        elif key in (curses.KEY_DOWN, ord("j")):
            scroll = min(max(0, len(lines) - visible), scroll + 1)


# ---------------------------------------------------------------------------
# Screen: Dashboard / Status
# ---------------------------------------------------------------------------

def get_status_lines():
    lines = []

    # Cowrie
    cowrie_ok = bool(run("pgrep -u cowrie")[0])
    lines.append(("Cowrie honeypot",
                  "RUNNING" if cowrie_ok else "STOPPED",
                  GREEN if cowrie_ok else RED))

    # Real SSH
    ssh_ok = systemctl_status("ssh")
    lines.append(("Real SSH", "RUNNING" if ssh_ok else "STOPPED",
                  GREEN if ssh_ok else YELLOW))

    # Monitor
    mon_ok = systemctl_status("honeypot-monitor")
    lines.append(("Hardware monitor", "RUNNING" if mon_ok else "STOPPED",
                  GREEN if mon_ok else YELLOW))

    # Hardware modules
    config = load_config()
    oled_on = config.get("oled", "enabled", fallback="false").lower() == "true"
    led_on  = config.get("led",  "enabled", fallback="false").lower() == "true"
    lines.append(("OLED display", "enabled" if oled_on else "disabled",
                  GREEN if oled_on else YELLOW))
    lines.append(("LED indicators", "enabled" if led_on else "disabled",
                  GREEN if led_on else YELLOW))

    # Login alert
    state = load_json(MONITOR_STATE)
    alert = state.get("login_history", False)
    lines.append(("Login alert", "ACTIVE - run: sudo honeypot-kit led clear-alert" if alert else "clear",
                  RED if alert else GREEN))

    # Disk
    out, _ = run("df / --output=pcent | tail -1")
    disk_pct = int(out.strip().rstrip("%")) if out else 0
    disk_color = RED if disk_pct > 85 else (YELLOW if disk_pct > 70 else GREEN)
    lines.append(("Disk usage", f"{disk_pct}%", disk_color))

    # IP
    ip, _ = run("hostname -I | awk '{print $1}'")
    lines.append(("IP address", ip or "unknown", NORMAL))

    # OpenAI
    ai_installed = os.path.exists(AI_CONF)
    if ai_installed:
        ai_conf = load_json(AI_CONF)
        ai_enabled = ai_conf.get("enabled", False)
        ai_key     = bool(ai_conf.get("api_key", "").strip())
        ai_status  = "enabled" if ai_enabled and ai_key else \
                     "no API key" if not ai_key else "disabled"
        ai_color   = GREEN if (ai_enabled and ai_key) else YELLOW
    else:
        ai_status = "not installed"
        ai_color  = YELLOW
    lines.append(("OpenAI integration", ai_status, ai_color))

    return lines


def screen_status(stdscr):
    """Live status dashboard."""
    curses.curs_set(0)

    while True:
        h, w = stdscr.getmaxyx()
        draw_header(stdscr, "Status Dashboard")
        lines = get_status_lines()

        for i, (label, value, color) in enumerate(lines):
            y = i + 2
            if y >= h - 1:
                break
            stdscr.addstr(y, 2,  f"{label:<25}", NORMAL)
            stdscr.addstr(y, 28, value[:w - 30], color)

        draw_status_bar(stdscr, " q:Back  r:Refresh ", curses.A_DIM)
        stdscr.refresh()

        stdscr.timeout(5000)  # auto-refresh every 5s
        key = stdscr.getch()
        stdscr.timeout(-1)

        if key in (ord("q"), 27):
            return
        # any other key or timeout: refresh


# ---------------------------------------------------------------------------
# Screen: Session Browser
# ---------------------------------------------------------------------------

def load_sessions(max_age_hours=48):
    """Load completed Cowrie sessions from JSON log."""
    if not os.path.exists(COWRIE_JSON):
        return []

    sessions = {}
    closed   = set()

    try:
        with open(COWRIE_JSON) as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    event = json.loads(line)
                except Exception:
                    continue

                sid = event.get("session", "")
                if not sid:
                    continue

                if sid not in sessions:
                    sessions[sid] = {
                        "session_id":  sid,
                        "src_ip":      "",
                        "start_time":  "",
                        "duration":    0,
                        "events":      0,
                        "commands":    [],
                        "logins":      0,
                        "had_shell":   False,
                        "downloads":   0,
                    }

                s   = sessions[sid]
                eid = event.get("eventid", "")
                s["events"] += 1

                if eid == "cowrie.session.connect":
                    s["src_ip"]     = event.get("src_ip", "")
                    s["start_time"] = event.get("timestamp", "")

                elif "login.success" in eid:
                    s["had_shell"] = True
                    s["logins"]   += 1

                elif "login.failed" in eid:
                    s["logins"] += 1

                elif eid == "cowrie.command.input":
                    s["commands"].append(event.get("input", ""))

                elif "file_download" in eid:
                    s["downloads"] += 1

                elif eid in ("cowrie.session.closed", "cowrie.session.close"):
                    s["duration"] = event.get("duration", 0)
                    closed.add(sid)

    except Exception:
        pass

    # Filter to completed sessions, sort by start time descending
    result = [s for sid, s in sessions.items() if sid in closed]
    result.sort(key=lambda x: x["start_time"], reverse=True)
    return result[:100]  # cap at 100


def get_analyzed_sessions():
    """Return set of session ID prefixes that have been analyzed."""
    analyzed = set()
    if not os.path.exists(AI_ANALYSIS_DIR):
        return analyzed
    for f in Path(AI_ANALYSIS_DIR).glob("*.json"):
        analyzed.add(f.name[:16])
    return analyzed


def draw_session_row(win, y, x, item, selected, w):
    """Custom row renderer for session list."""
    s        = item
    sid      = s["session_id"][:12]
    ts       = s["start_time"][11:16] if len(s["start_time"]) > 16 else s["start_time"][:5]
    date     = s["start_time"][:10]
    cmds     = len(s["commands"])
    shell    = "✓shell" if s["had_shell"] else "      "
    analyzed = "★" if s.get("_analyzed") else " "
    ip       = s["src_ip"][:15].ljust(15)

    row = f" {analyzed} {date} {ts}  {ip}  ev:{s['events']:3d}  cmd:{cmds:3d}  {shell}"

    if selected:
        win.addstr(y, 0, row[:w - 1].ljust(w - 1), SEL)
    else:
        attr = GREEN if s["had_shell"] else NORMAL
        win.addstr(y, 0, row[:w - 1], attr)


def screen_sessions(stdscr):
    """Session browser with AI analysis."""
    curses.curs_set(0)
    sessions = load_sessions()
    analyzed = get_analyzed_sessions()

    if not sessions:
        message_box(stdscr, "Sessions", [
            "",
            "  No completed sessions found.",
            "",
            "  Sessions appear here after attackers connect and disconnect.",
            "  SSH into port 22 from another machine to create a session.",
        ])
        return

    # Mark analyzed sessions
    for s in sessions:
        s["_analyzed"] = s["session_id"][:16] in analyzed

    def refresh():
        nonlocal sessions, analyzed
        sessions = load_sessions()
        analyzed = get_analyzed_sessions()
        for s in sessions:
            s["_analyzed"] = s["session_id"][:16] in analyzed
        return sessions

    # Header legend
    stdscr.addstr(0, 0, " ★=analyzed  ✓shell=got shell  ↑↓:Navigate  a:Analyze  v:View  q:Back", curses.A_DIM)

    selected = 0
    scroll   = 0

    while True:
        h, w = stdscr.getmaxyx()
        draw_header(stdscr, "Session Browser  (★=analyzed  ✓=had shell)")

        visible = h - 3
        if selected < scroll:
            scroll = selected
        if selected >= scroll + visible:
            scroll = selected - visible + 1

        for i, s in enumerate(sessions[scroll:scroll + visible]):
            draw_session_row(stdscr, i + 1, 0, s, (i + scroll == selected), w)

        if scroll > 0:
            stdscr.addstr(1, w - 2, "▲", curses.A_DIM)
        if scroll + visible < len(sessions):
            stdscr.addstr(h - 2, w - 2, "▼", curses.A_DIM)

        draw_status_bar(stdscr, " a:Analyze with AI  v:View session  r:Refresh  q:Back ", curses.A_DIM)
        stdscr.refresh()

        key = stdscr.getch()

        if key in (curses.KEY_UP, ord("k")):
            selected = max(0, selected - 1)

        elif key in (curses.KEY_DOWN, ord("j")):
            selected = min(len(sessions) - 1, selected + 1)

        elif key == ord("r"):
            sessions = refresh()

        elif key == ord("v"):
            # View session detail
            s = sessions[selected]
            lines = [
                f"  Session ID  : {s['session_id']}",
                f"  Source IP   : {s['src_ip']}",
                f"  Started     : {s['start_time']}",
                f"  Duration    : {s['duration']:.1f}s",
                f"  Events      : {s['events']}",
                f"  Had shell   : {s['had_shell']}",
                f"  Downloads   : {s['downloads']}",
                "",
                "  Commands:",
            ]
            for cmd in s["commands"]:
                lines.append(f"    $ {cmd}")
            if not s["commands"]:
                lines.append("    (none)")
            message_box(stdscr, f"Session {s['session_id'][:12]}", lines)

        elif key == ord("a"):
            # AI analysis
            s = sessions[selected]

            if not os.path.exists(AI_ANALYZER):
                message_box(stdscr, "AI Analysis", [
                    "",
                    "  OpenAI integration is not installed.",
                    "",
                    "  Install it from the Integrations menu.",
                ])
                continue

            ai_conf = load_json(AI_CONF)
            if not ai_conf.get("enabled") or not ai_conf.get("api_key", "").strip():
                message_box(stdscr, "AI Analysis", [
                    "",
                    "  OpenAI integration is not configured.",
                    "",
                    f"  Edit: {AI_CONF}",
                    "  Set api_key and enabled: true",
                ])
                continue

            # Check cache first
            sid_prefix = s["session_id"][:16]
            if sid_prefix in analyzed:
                # Load cached result
                cached_files = sorted(
                    Path(AI_ANALYSIS_DIR).glob(f"{sid_prefix}_*.json"),
                    key=os.path.getmtime, reverse=True
                )
                if cached_files:
                    cached = load_json(str(cached_files[0]))
                    a = cached.get("analysis", {})
                    lines = _format_analysis(a, cached.get("analyzed_at", ""), cached=True)
                    message_box(stdscr, "AI Analysis (Cached)", lines)
                    continue

            # Estimate cost
            cmds_text = " ".join(s["commands"])
            est_tokens = (len(cmds_text) + 500) // 4
            est_cost   = (est_tokens / 1_000_000) * 0.15

            draw_status_bar(
                stdscr,
                f" Est: ~{est_tokens} tokens (~${est_cost:.4f})  a:Analyze  q:Cancel ",
                YELLOW
            )
            stdscr.refresh()

            key2 = stdscr.getch()
            if key2 != ord("a"):
                continue

            # Run analysis - suspend curses, run in terminal
            curses.endwin()
            print(f"\nAnalyzing session {s['session_id'][:12]}...")
            rc = subprocess.call([
                "python3", AI_ANALYZER,
                "--session", s["session_id"]
            ])
            print("\nPress Enter to return to menu...")
            input()
            stdscr = curses.initscr()
            init_colors()
            curses.curs_set(0)
            sessions = refresh()

        elif key in (ord("q"), 27):
            return


def _format_analysis(a, analyzed_at="", cached=False):
    """Format analysis dict into display lines."""
    lines = []
    if cached:
        lines.append(f"  [Cached analysis from {analyzed_at[:19]}]")
        lines.append("")

    lines += [
        f"INTENT     : {a.get('intent','?')}  (confidence: {a.get('confidence',0):.0%})",
        "",
        f"SUMMARY:",
        "",
    ]
    # Word wrap summary
    for line in textwrap.wrap(a.get("summary", ""), 70):
        lines.append(f"  {line}")

    lines.append("")
    if a.get("observed_actions"):
        lines.append("ACTIONS:")
        for action in a["observed_actions"]:
            lines.append(f"  - {action}")
        lines.append("")

    if a.get("interesting_commands"):
        lines.append("INTERESTING COMMANDS:")
        for cmd in a["interesting_commands"]:
            lines.append(f"  $ {cmd}")
        lines.append("")

    if a.get("technique_candidates"):
        lines.append("MITRE ATT&CK:")
        for t in a["technique_candidates"]:
            lines.append(f"  {t.get('technique_id','')} {t.get('technique_name','')} ({t.get('confidence','')})")
        lines.append("")

    if a.get("indicators"):
        lines.append("INDICATORS:")
        for ind in a["indicators"]:
            lines.append(f"  [{ind.get('type','')}] {ind.get('value','')} - {ind.get('context','')}")
        lines.append("")

    if a.get("educational_explanation"):
        lines.append("EDUCATIONAL NOTE:")
        for line in textwrap.wrap(a["educational_explanation"], 70):
            lines.append(f"  {line}")
        lines.append("")

    if a.get("uncertainties"):
        lines.append("UNCERTAINTIES:")
        for u in a["uncertainties"]:
            lines.append(f"  - {u}")

    return lines


# ---------------------------------------------------------------------------
# Screen: Hardware
# ---------------------------------------------------------------------------

def screen_hardware(stdscr):
    """Hardware module management."""
    def get_items():
        config = load_config()
        oled_on = config.get("oled", "enabled", fallback="false").lower() == "true"
        led_on  = config.get("led",  "enabled", fallback="false").lower() == "true"
        mon_ok  = systemctl_status("honeypot-monitor")
        state   = load_json(MONITOR_STATE)
        alert   = state.get("login_history", False)

        return [
            {"label": f"OLED Display        {'ENABLED' if oled_on else 'disabled'}",
             "action": "toggle_oled", "enabled": oled_on},
            {"label": f"LED Indicators      {'ENABLED' if led_on else 'disabled'}",
             "action": "toggle_led", "enabled": led_on},
            {"label": f"Hardware Monitor    {'RUNNING' if mon_ok else 'stopped'}",
             "action": "toggle_monitor", "running": mon_ok},
            {"label": f"Login Alert         {'ACTIVE - clear?' if alert else 'clear'}",
             "action": "clear_alert", "alert": alert},
            {"label": "Test LEDs",           "action": "test_led"},
            {"label": "Test OLED",           "action": "test_oled"},
            {"label": "← Back",              "action": "back"},
        ]

    while True:
        item = menu(stdscr, "Hardware Modules", get_items(),
                    on_refresh=get_items)
        if item is None or item["action"] == "back":
            return

        action = item["action"]

        if action == "toggle_oled":
            cmd = "sudo honeypot-kit oled disable" if item["enabled"] else "sudo honeypot-kit oled enable"
            curses.endwin()
            os.system(cmd)
            time.sleep(1)
            stdscr = curses.initscr()
            init_colors()

        elif action == "toggle_led":
            cmd = "sudo honeypot-kit led disable" if item["enabled"] else "sudo honeypot-kit led enable"
            curses.endwin()
            os.system(cmd)
            time.sleep(1)
            stdscr = curses.initscr()
            init_colors()

        elif action == "toggle_monitor":
            cmd = "sudo honeypot-kit monitor stop" if item["running"] else "sudo honeypot-kit monitor start"
            curses.endwin()
            os.system(cmd)
            time.sleep(2)
            stdscr = curses.initscr()
            init_colors()

        elif action == "clear_alert":
            if item["alert"]:
                curses.endwin()
                os.system("sudo honeypot-kit led clear-alert && sudo honeypot-kit monitor restart")
                time.sleep(2)
                stdscr = curses.initscr()
                init_colors()

        elif action in ("test_led", "test_oled"):
            module = "led" if action == "test_led" else "oled"
            curses.endwin()
            os.system(f"sudo honeypot-kit {module} test")
            print("\nPress Enter to return...")
            input()
            stdscr = curses.initscr()
            init_colors()


# ---------------------------------------------------------------------------
# Screen: Smoke Test
# ---------------------------------------------------------------------------

def screen_smoke_test(stdscr):
    """Run smoke test and display results."""
    h, w = stdscr.getmaxyx()
    draw_header(stdscr, "Smoke Test")
    stdscr.addstr(2, 2, "Running smoke test...", YELLOW)
    stdscr.refresh()

    out, rc = run(f"sudo bash {SMOKE_TEST}", timeout=30)
    lines = out.splitlines() if out else ["Smoke test script not found."]
    message_box(stdscr, "Smoke Test Results", lines)


# ---------------------------------------------------------------------------
# Screen: Logs
# ---------------------------------------------------------------------------

def screen_logs(stdscr):
    """Log viewer."""
    def get_log_items():
        return [
            {"label": "Cowrie JSON log (last 50 events)", "log": COWRIE_JSON,   "lines": 50, "json": True},
            {"label": "Monitor log",                       "log": MONITOR_LOG,  "lines": 50},
            {"label": "Updates log",                       "log": UPDATES_LOG,  "lines": 50},
            {"label": "← Back",                            "action": "back"},
        ]

    while True:
        item = menu(stdscr, "Log Viewer", get_log_items())
        if item is None or item.get("action") == "back":
            return

        log_path = item.get("log")
        if not log_path or not os.path.exists(log_path):
            message_box(stdscr, "Log", ["", "  Log file not found.", f"  {log_path}"])
            continue

        if item.get("json"):
            # Show last N events from JSON log
            out, _ = run(f"tail -50 {log_path}")
            lines = []
            for line in out.splitlines():
                try:
                    event = json.loads(line)
                    eid   = event.get("eventid", "?")
                    ts    = event.get("timestamp", "")[:19]
                    src   = event.get("src_ip", "")
                    lines.append(f"  {ts}  {eid:<35} {src}")
                except Exception:
                    lines.append(f"  {line}")
        else:
            out, _ = run(f"tail -50 {log_path}")
            lines = ["  " + l for l in out.splitlines()]

        message_box(stdscr, item["label"], lines)


# ---------------------------------------------------------------------------
# Screen: Integrations
# ---------------------------------------------------------------------------

def screen_integrations(stdscr):
    """Integration manager."""
    def get_items():
        items = [{"label": "List available integrations", "action": "list"}]

        if os.path.exists(AI_CONF):
            ai_conf = load_json(AI_CONF)
            enabled = ai_conf.get("enabled", False)
            key_set = bool(ai_conf.get("api_key", "").strip())
            status  = "enabled" if (enabled and key_set) else "installed (not configured)"
            items.append({"label": f"OpenAI AI Analysis  [{status}]", "action": "openai_status"})
            items.append({"label": "OpenAI: Run AI analysis →",        "action": "openai_sessions"})
        else:
            items.append({"label": "OpenAI: Install integration",      "action": "install_openai"})

        items.append({"label": "← Back", "action": "back"})
        return items

    while True:
        item = menu(stdscr, "Integrations", get_items(), on_refresh=get_items)
        if item is None or item.get("action") == "back":
            return

        action = item["action"]

        if action == "list":
            curses.endwin()
            os.system("honeypot-kit integration list | less")
            stdscr = curses.initscr()
            init_colors()

        elif action == "openai_status":
            ai_conf = load_json(AI_CONF)
            key     = ai_conf.get("api_key", "")
            lines   = [
                "",
                f"  Enabled   : {ai_conf.get('enabled', False)}",
                f"  API key   : {'set (' + key[:8] + '...)' if key else 'NOT SET'}",
                f"  Model     : {ai_conf.get('model', 'gpt-4o-mini')}",
                f"  Auto      : {ai_conf.get('auto_analyze', False)}",
                "",
                f"  Config    : {AI_CONF}",
                "",
                "  To configure: nano " + AI_CONF,
            ]
            message_box(stdscr, "OpenAI Status", lines)

        elif action == "openai_sessions":
            screen_sessions(stdscr)

        elif action == "install_openai":
            curses.endwin()
            os.system("sudo honeypot-kit integration install openai")
            print("\nPress Enter to return...")
            input()
            stdscr = curses.initscr()
            init_colors()


# ---------------------------------------------------------------------------
# Screen: Update
# ---------------------------------------------------------------------------

def screen_update(stdscr):
    """Run module update check."""
    h, w = stdscr.getmaxyx()
    draw_header(stdscr, "Module Updates")
    stdscr.addstr(2, 2, "Checking for updates...", YELLOW)
    stdscr.refresh()

    curses.endwin()
    os.system("sudo honeypot-kit update now")
    print("\nPress Enter to return...")
    input()
    stdscr = curses.initscr()
    init_colors()
    curses.curs_set(0)

    # Show update log
    if os.path.exists(UPDATES_LOG):
        out, _ = run(f"tail -20 {UPDATES_LOG}")
        lines = ["  " + l for l in out.splitlines()]
        message_box(stdscr, "Recent Update Log", lines)


# ---------------------------------------------------------------------------
# Main Menu
# ---------------------------------------------------------------------------

MAIN_ITEMS = [
    {"label": "📊  Status Dashboard",    "action": "status"},
    {"label": "🔍  Session Browser",     "action": "sessions"},
    {"label": "🔌  Hardware Modules",    "action": "hardware"},
    {"label": "🧩  Integrations",        "action": "integrations"},
    {"label": "✅  Run Smoke Test",      "action": "smoke"},
    {"label": "📋  View Logs",           "action": "logs"},
    {"label": "🔄  Check for Updates",   "action": "update"},
    {"label": "❌  Quit",                "action": "quit"},
]


def main(stdscr):
    init_colors()
    curses.curs_set(0)
    stdscr.keypad(True)

    while True:
        item = menu(stdscr, "Main Menu", MAIN_ITEMS)

        if item is None or item["action"] == "quit":
            break

        action = item["action"]

        if action == "status":
            screen_status(stdscr)
        elif action == "sessions":
            screen_sessions(stdscr)
        elif action == "hardware":
            screen_hardware(stdscr)
        elif action == "integrations":
            screen_integrations(stdscr)
        elif action == "smoke":
            screen_smoke_test(stdscr)
        elif action == "logs":
            screen_logs(stdscr)
        elif action == "update":
            screen_update(stdscr)


if __name__ == "__main__":
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    except Exception as e:
        print(f"TUI error: {e}")
        import traceback
        traceback.print_exc()
