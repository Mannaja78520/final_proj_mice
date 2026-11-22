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

    # round 4 (hub tabs, Studio phone Stop, prize machines with none)
    modjs = (root / "main_python" / "web" / "home" / "parts" / "modules.js").read_text(encoding="utf-8")
    t.ok("'RS485 #' +" not in modjs.replace(" ' · RS485 #'", ""),
         "a module's way in is plain words; RS485 / COM port sit behind the technical switch")
    t.ok("by cable · '" in modjs and "tech(' · RS485 #'" in modjs, "plain 'by cable' line with the code inside .tech")
    studio = (root / "nong" / "main_python_set_nong" / "web" / "index.html").read_text(encoding="utf-8")
    t.ok('id="fabStop"' in studio, "Studio has an always-visible Stop for phones")
    t.ok("No prize machines found" in gacha, "Prize machines with none says so, not a green '0 of 0'")
    home = (root / "main_python" / "web" / "home" / "style.css").read_text(encoding="utf-8")
    t.ok("mask-image" in home, "the phone tab row fades at the edge so it reads as slidable")

    # round 5
    topics = (root / "main_python" / "web" / "help" / "parts" / "topics.js").read_text(encoding="utf-8")
    t.ok("saved === null && window.innerWidth <= 860" in topics, "Help on a first phone visit opens only 'Start here'")
    t.ok('"Robot commands"' in topics and "QC suite" not in topics, "Help topic names are everyday words")
    tv = (root / "apps" / "tv" / "index.html").read_text(encoding="utf-8")
    t.ok('.replace(/_+/g, " ")' in tv, "TV shows are named without .yaml and underscores")
    style = (root / "main_python" / "web" / "home" / "style.css").read_text(encoding="utf-8")
    t.ok("#homeTools.js-tools{grid-template-columns:repeat(2" in style, "phone Home shows tools as small tiles so robots come sooner")
