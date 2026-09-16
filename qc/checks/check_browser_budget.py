"""A browser check must be given longer than the waits it can actually spend.

The explanation for one of three intermittents on 2026-08-20, and the only one
with a mechanical cause.

`check_flash_confirm` waited up to 20 s for a row, then 20 s for a dialog, then
20 s for its details - 60 s of waiting inside a page window of 40 s. On an idle
machine every wait returned in under a second and nothing was ever noticed. In
a parallel gate the first wait alone outlasted the window, the page was killed
before it reported anything, and the check announced *"clicking Flash ASKS
instead of flashing"* - which reads as the safety gate being gone. It was not.
Nothing had been clicked at all.

That is the worst shape a failure can take: alarming, wrong, and only under
load, so it looks like a flake and gets re-run instead of read.

The invariant is arithmetic, so it can be checked rather than remembered: for
every driver page, the window `raw_page(seconds=)` must cover the WORST CASE -
every `qcWaitFor` timing out end to end, plus the startup delay - with room for
the hub to start and the browser to launch.

Waits usually return early. That is exactly why this needs checking: the budget
is only ever wrong on the slow day, and on the slow day the message is a lie.
"""
import pathlib
import re

import qc as F

AREA = "qc"
TITLE = "every browser check is given longer than its own waits can take"

# The hub starts, Edge launches with a fresh profile, and the page loads before
# the driver's first line runs. Measured at several seconds on this machine.
OVERHEAD = 8


def budget(src: str):
    """(window, worst-case seconds of waiting) for one check file."""
    wins = [int(m) for m in re.findall(r"raw_page\([^)]*seconds\s*=\s*(\d+)", src)]
    waits = []
    for m in re.finditer(r"qcWaitFor\(", src):
        seg = src[m.end():m.end() + 900]
        n = re.search(r"\}\s*,\s*(\d{3,})\s*\)", seg)
        if n:
            waits.append(int(n.group(1)) / 1000.0)
    # the driver's own setTimeout(..., N) before it starts
    start = [int(m) / 1000.0
             for m in re.findall(r"\},\s*(\d{3,})\)\s*;?\s*\n</script>", src)]
    return wins, sum(waits) + sum(start)


def run(t):
    checks = sorted(pathlib.Path(F.QC / "checks").glob("check_*.py"))
    t.ok(checks, "there are checks to inspect")

    looked = 0
    for f in checks:
        if f.name == "check_browser_budget.py":
            continue
        src = f.read_text(encoding="utf-8", errors="replace")
        wins, need = budget(src)
        if not wins:
            continue
        looked += 1
        name = f.stem[6:]
        for w in wins:
            t.ok(w >= need + OVERHEAD,
                 "%s: %ds window covers %.0fs of waits" % (name, w, need),
                 "the page is killed at %ds while its own waits can spend "
                 "%.0fs plus about %ds of startup - so on a loaded machine it "
                 "reports nothing, and whatever the check says about the "
                 "missing marks is not about the code under test"
                 % (w, need, OVERHEAD))
    t.ok(looked >= 8,
         "and it looked at every browser check (%d)" % looked,
         "if this suddenly inspects two, the pattern it matches on has stopped "
         "matching and it is guarding nothing")

    # The one that was actually wrong keeps its own guard, so a later tidy-up
    # cannot quietly take the margin back.
    fc = (F.QC / "checks" / "check_flash_confirm.py").read_text(encoding="utf-8")
    wins, need = budget(fc)
    t.ok(wins and min(wins) >= need + OVERHEAD,
         "check_flash_confirm has room for its own worst case",
         "it is the one this was written for: 60s of waits in a 40s window, "
         "which failed only under load and blamed the safety gate")
