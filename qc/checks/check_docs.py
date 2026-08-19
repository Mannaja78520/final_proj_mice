"""The offline help page must not go stale.

Docs rot silently: a command is added, the page still describes last month's
system, and nobody notices until someone trusts it. So adding a feature without
documenting it is a QC FAILURE here, not a note for later.

If this fails, add the missing thing to `main_python/web/help.html`.
"""
import re

import qc as F

AREA = "docs"
TITLE = "help page covers the whole system"
SLOW = False

HELP = F.HUB / "web" / "help.html"

# Not module commands: HTTP verbs from the REST table in the same document.
NOT_COMMANDS = {"GET", "POST"}
# Real commands, but noise as separate feature rows — the file-transfer verbs
# are described as one capability rather than one line each.
GROUPED = {"FDATA", "FEND", "FREAD", "FDEL", "FBEGIN", "ZERO"} | NOT_COMMANDS


def run(t):
    if not t.ok(HELP.is_file(), "the help page exists", str(HELP)):
        return
    help_txt = HELP.read_text(encoding="utf-8", errors="replace")
    low = help_txt.lower()

    # ---- it is actually reachable, not just present on disk ---------
    base, main = F.start_hub()
    for path in ("/help", "/help.html"):
        s, b = F.get(base + path)
        t.eq(s, 200, "the hub serves %s" % path)
    # The hub's tool list is rendered from the app registry now, so assert what
    # the user actually gets — the help app is registered and offered — rather
    # than a literal "/help" string in the HTML, which only tested how the link
    # happened to be written.
    import json as _json
    s, b = F.get(base + "/api/apps")
    listed = _json.loads(b).get("apps", []) if s == 200 else []
    helps = [a for a in listed if a.get("path", "").rstrip("/") == "/help"]
    t.ok(helps, "the help page is offered by the hub", listed)
    s, b = F.get(base + "/")
    t.contains(b, "/api/apps", "the hub's main page renders that list")

    # ---- every command in COMMANDS.md is described ------------------
    cmds = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    documented = set()
    for m in re.finditer(r"^\|\s*`([A-Z][A-Z0-9]*)", cmds, re.M):
        documented.add(m.group(1))
    missing = sorted(c for c in documented - GROUPED if c not in help_txt)
    t.eq(missing, [], "every command in COMMANDS.md appears on the help page")

    # ---- every nong joint ------------------------------------------
    for j in ("L_SH_P", "L_EL_R", "R_SH_R", "WAIST", "SHRUG"):
        t.contains(help_txt, j, "help page lists joint %s" % j)

    # ---- every module type -----------------------------------------
    for ty in ("lift", "nong", "blank"):
        t.contains(low, ty, "help page covers the %s module type" % ty)

    # ---- every servo preset the firmware offers ---------------------
    # Read from config/servos.json, the ONE place a preset is declared.
    #
    # This used to grep NongModule.cpp for `t == "<name>"` — an if-chain that
    # was deliberately deleted when presets moved into the registry, and whose
    # removal check_registries.py now ASSERTS. So one check enforced the
    # removal of the very thing this one grepped for: the regex returned [],
    # the loop below ran zero times, and a servo preset added without being
    # documented shipped green. Nothing failed, because nothing was asked.
    import sys
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry
    presets = sorted(registry.servos().keys())
    # the guard, so this can never quietly go empty again
    t.ok(len(presets) >= 4,
         "the servo presets were really read (%d)" % len(presets),
         "an empty list here means the loop below checks nothing")
    for p in presets:
        t.contains(help_txt, p, "help page lists the %s servo preset" % p)

    # ---- every QC area is described (this file included) ------------
    for f in sorted((F.QC / "checks").glob("check_*.py")):
        m = re.search(r'^AREA\s*=\s*"(\w+)"', f.read_text(encoding="utf-8"), re.M)
        if m:
            t.contains(low, m.group(1), "help page mentions QC area '%s'" % m.group(1))

    # ---- the transports, which are the thing users ask about most ---
    for w in ("wifi", "usb", "rs485"):
        t.contains(low, w, "help page covers the %s transport" % w)

    # ---- offline: no external requests, or it breaks with no internet
    for bad in ("http://fonts.", "https://fonts.", "cdn.", "unpkg.com", "jsdelivr"):
        t.ok(bad not in low, "help page loads nothing from the internet (%s)" % bad)
