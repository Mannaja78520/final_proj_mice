"""Help must keep up with the pages (user 2026-11-22: "help must always match the new things").

tools/help_drift.py lists the buttons, tabs and headings of a page that its Help part never
mentions. qc/data/help_drift_baseline.json is today's list: it may only shrink. A new
unmentioned label fails here - describe it in the Help part (all languages, Rule 11).
When you DO describe one, delete it from the baseline (python tools/help_drift.py --baseline).
"""
import json
import sys

import qc as F

AREA = "docs"
TITLE = "Every page label is described in its Help part (ratchet)"


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import help_drift
    base = json.loads((F.CODE / "qc/data/help_drift_baseline.json").read_text(encoding="utf-8"))
    now = help_drift.drift()
    for page, miss in now.items():
        new = [m for m in miss if m not in base.get(page, [])]
        t.ok(not new, page + ": no new label missing from Help", "describe in its Help part: " + "; ".join(new[:8]))
    t.ok(set(now) >= {"apps/voice/index.html", "apps/gacha/index.html"}, "the help map covers the main apps")
