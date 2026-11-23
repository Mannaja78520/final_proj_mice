"""Module controls stay hidden until identified, then motor buttons precede nong sliders.

User 2026-11-22 (UX audit, looked at by eye at 390 px): "Go home" and "Switch
motors off" were under ten sliders, so on a phone the way to stop the arms
was off screen. The stop-ish buttons come first now; the sliders after.
"""
import re
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "board page: controls wait for identification and nong motor buttons come first"
SLOW = False


def run(t):
    page = (F.CODE / "firmware" / "src" / "web" / "WebUI.h").read_text(encoding="utf-8")
    capabilities = re.findall(r"showCard\('([^']+)',has\(", page)
    t.ok(bool(capabilities), "the module has capability cards")
    t.contains(page, '.card[data-cap="0"]{display:none}',
               "CSS hides unavailable cards before scripts run")
    for card_id in capabilities:
        card = re.search(r'<div\b[^>]*\bid="' + re.escape(card_id) + r'"[^>]*>', page)
        t.ok(card and 'data-cap="0"' in card[0], card_id + " starts unavailable")
    nong = page[page.index("<!--#type nong-->"):]
    sliders = nong.index('id="jointRows"')
    for label in ("Go home", "Switch motors on", "Switch motors off"):
        at = nong.find(label)
        t.ok(0 <= at < sliders, "'%s' is above the sliders" % label, "at %d, sliders at %d" % (at, sliders))
