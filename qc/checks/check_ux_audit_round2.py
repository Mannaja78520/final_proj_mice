"""Things the 2026-11-22 by-eye audit found, held so they stay fixed.

- Prize page: an empty Kind box says what to do (it looked broken, empty).
- The login strip is slim (it took a third of a phone screen).
- TV mode buttons carry one language, not Thai with English in brackets.
- Studio's "L on edge"/palm words have Thai/zh/ja entries.
"""
import json

import qc as F

AREA = "hub"
TITLE = "by-eye audit round 2: empty Kind hint, slim login, one-language TV tabs, Studio hand words"
SLOW = False


def run(t):
    root = F.CODE
    gacha = (root / "apps" / "gacha" / "index.html").read_text(encoding="utf-8")
    t.ok("no prize kinds yet" in gacha, "an empty Kind list says what to do")
    css = (root / "shared" / "web" / "mice.css").read_text(encoding="utf-8")
    t.ok(".mlogin" in css and "padding: 8px 14px" in css, "the login strip is slim")
    tv = (root / "apps" / "tv" / "index.html").read_text(encoding="utf-8")
    t.ok("(Mobile Controller)" not in tv and "(Stage Display)" not in tv, "TV tabs are one language")
    for code in ("th", "zh", "ja"):
        s = json.loads((root / "shared" / "web" / "lang" / (code + ".json")).read_text(encoding="utf-8"))["strings"]
        for key in ("L on edge", "R ✋ palm up", "no prize kinds yet - add one under Machines and kinds"):
            t.ok(bool(s.get(key)), "%s has '%s'" % (code, key))
