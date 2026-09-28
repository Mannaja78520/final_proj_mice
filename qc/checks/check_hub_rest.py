"""The hub page rests its background loops when hidden and wakes on visible.

Asked 2026-09-21 (A26-85): one Edge renderer tab left open for 6 hours accumulated
over 10,900 CPU-seconds (~50% of a core). Investigation revealed that background
loops (periodic module scan every 15s, mods metadata refresh, and home repaint)
ran continuously even when the tab was hidden, repeatedly churning the DOM and
polling the network while unattended.

This check asserts that:
  * periodic network scan (!document.hidden && !flashActive) rests when hidden
  * modsMeta and checkVer bail out early when document.hidden
  * paintHome timer rests when document.hidden and throttles unnecessary DOM churn
  * autoUsb scan rests when document.hidden
  * visibilitychange is registered to immediately refresh state when tab becomes visible.
"""
from pathlib import Path
import re
import qc as F

AREA = "hub"
TITLE = "hub page background loops rest when hidden and wake on visible"


def run(t):
    html_file = F.HUB / "web" / "hub.html"
    t.ok(html_file.is_file(), "hub.html exists")
    src = html_file.read_text(encoding="utf-8")

    # 1. Periodic scan(false) must check !document.hidden
    m_scan = re.search(r"setInterval\(\s*\(\)\s*=>\s*\{([^}]+scan\(false\)[^}]*)\}\s*,\s*15000\s*\)", src)
    t.ok(bool(m_scan), "scan(false) interval exists at 15s")
    if m_scan:
        body = m_scan.group(1)
        t.ok("!document.hidden" in body, "scan(false) interval checks !document.hidden",
             "background scan must not poll network when tab is hidden")

    # 2. modsMeta checks document.hidden
    m_meta = re.search(r"function\s+modsMeta\s*\(\)\s*\{([^}]+)\}", src)
    t.ok(bool(m_meta), "modsMeta function exists")
    if m_meta:
        t.ok("document.hidden" in m_meta.group(1), "modsMeta bails when document.hidden",
             "metadata text updates must rest when hidden")

    # 3. checkVer checks document.hidden
    m_ver = re.search(r"async\s+function\s+checkVer\s*\(\)\s*\{([^}]+)\}", src)
    t.ok(bool(m_ver), "checkVer function exists")
    if m_ver:
        t.ok("document.hidden" in m_ver.group(1), "checkVer bails when document.hidden")

    # 4. autoUsb scan checks !document.hidden
    t.ok("!document.hidden&&!flashActive" in src or "!document.hidden && !flashActive" in src,
         "autoUsb scan checks !document.hidden")

    # 5. paintHome timer checks document.hidden
    m_paint = re.search(r"setInterval\(\s*function\s*\(\)\s*\{([^}]+paintHome\(\)[^}]*)\}\s*,\s*(\d+)\s*\)", src)
    t.ok(bool(m_paint), "paintHome interval exists")
    if m_paint:
        p_body = m_paint.group(1)
        interval_ms = int(m_paint.group(2))
        t.ok("document.hidden" in p_body, "paintHome timer checks document.hidden",
             "home panel must not repaint in hidden tab")
        t.ok(interval_ms >= 10000, f"paintHome interval throttled to at least 10s (got {interval_ms}ms)",
             "frequent 4s paint churn causes excessive renderer CPU usage")

    # 6. paintHome avoids unnecessary DOM reconstruction
    t.ok("data-errs" in src and "data-btn" in src,
         "paintHome stabilizes DOM nodes by caching error and button keys",
         "wiping innerHTML every interval triggers continuous layout and style recalc")

    # 7. visibilitychange listener wakes up and refreshes
    idx_vis = src.find("visibilitychange")
    t.ok(idx_vis >= 0, "visibilitychange event listener is registered")
    if idx_vis >= 0:
        vis_snippet = src[idx_vis:idx_vis + 500]
        t.ok("!document.hidden" in vis_snippet, "visibilitychange checks !document.hidden")
        t.ok("scan(false)" in vis_snippet, "visibilitychange triggers scan(false) on visible")
        t.ok("paintHome()" in vis_snippet, "visibilitychange triggers paintHome() on visible")
