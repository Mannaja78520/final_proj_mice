"""On the nong board page the motor buttons sit ABOVE the ten joint sliders.

User 2026-11-22 (UX audit, looked at by eye at 390 px): "Go home" and "Switch
motors off" were under ten sliders, so on a phone the way to stop the arms
was off screen. The stop-ish buttons come first now; the sliders after.
"""
import re
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "board page: Go home / motors on / motors off come before the joint sliders"
SLOW = False


def run(t):
    page = (F.CODE / "firmware" / "src" / "web" / "WebUI.h").read_text(encoding="utf-8")
    nong = page[page.index("<!--#type nong-->"):]
    sliders = nong.index('id="jointRows"')
    for label in ("Go home", "Switch motors on", "Switch motors off"):
        at = nong.find(label)
        t.ok(0 <= at < sliders, "'%s' is above the sliders" % label, "at %d, sliders at %d" % (at, sliders))
