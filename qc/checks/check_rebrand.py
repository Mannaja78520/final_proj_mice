"""The live MICE brand, event-host artwork and translated explanation."""

from html.parser import HTMLParser
import json
from pathlib import Path
import re

import qc as F

AREA = "hub"
TITLE = "MICE branding on live pages, translations and mascot"
SLOW = False

EXPLANATION = "MICE stands for Meetings, Incentives, Conferences and Exhibitions."
OLD_BRAND = re.compile(r"(?<![A-Za-z0-9_.-])(?:Mice|mice)(?![A-Za-z0-9_-]|\.[A-Za-z_$])|[🐭🐁🐀]")


class VisibleText(HTMLParser):
    """Check copy and labels while ignoring scripts, commands and asset identifiers."""

    def __init__(self, page):
        super().__init__()
        self.skip = None
        self.text = []
        self.feed(page)

    def handle_starttag(self, tag, attrs):
        if self.skip:
            return
        if tag in ("style", "script", "code", "pre"):
            self.skip = tag
        self.text.extend(value for attr, value in attrs if value and attr in
                         ("alt", "aria-label", "placeholder", "title"))

    def handle_endtag(self, tag):
        if tag == self.skip:
            self.skip = None

    def handle_data(self, data):
        if not self.skip:
            self.text.append(data.strip())


def run(t):
    root = Path(F.CODE)
    pages = [
        "main_python/web/hub.html", "main_python/web/help.html", "main_python/web/rgb.html",
        "apps/camera/watch.html", "apps/voice/index.legacy.html",
    ]
    pages.extend("apps/%s/index.html" % name for name in
                 ("all-jao", "camera", "faces", "gacha", "photobooth", "tv", "voice"))
    for path in pages:
        page = (root / path).read_text(encoding="utf-8")
        matches = [part for part in VisibleText(page).text if OLD_BRAND.search(part)]
        t.ok(not matches, path + " uses the MICE brand", str(matches[:3]))
        t.ok(bool(re.search(r"<title>[^<]*\bMICE\b", page)), path + " names MICE in its title")
        if path.endswith(("/hub.html", "/help.html")):
            t.contains(page, EXPLANATION, path + " explains MICE")
            t.contains(page, 'class="brand-mascot" src="/img/mascot.webp"', path + " uses the Nong mascot")

    lang = root / "shared/web/lang"
    for code in ("en", "th", "zh", "ja"):
        strings = json.loads((lang / (code + ".json")).read_text(encoding="utf-8"))["strings"]
        for label in ("About MICE", EXPLANATION):
            t.contains(strings.get(label, ""), "MICE", "%s localizes %s" % (code, label))
        for pack in (lang / (code + ".json"), lang / "help" / (code + ".json")):
            entries = json.loads(pack.read_text(encoding="utf-8"))["strings"]
            stale = [text for text in list(entries) + list(entries.values())
                     if re.search(r"(?<![A-Za-z0-9_.-])Mice(?![A-Za-z0-9_-]|\.[A-Za-z_$])", text)]
            t.ok(not stale, pack.name + " has no old brand in " + pack.parent.name, str(stale[:3]))

    img = root / "shared/web/img"
    light = (img / "mascot.webp").read_bytes()
    dark = (img / "mascot-dark.webp").read_bytes()
    t.ok(light != dark and light[8:12] == dark[8:12] == b"WEBP", "both Nong WebP variants are present")
    css = (img.parent / "img-dark.css").read_text(encoding="utf-8")
    t.contains(css, 'html[data-mode="dark"] img[src="/img/mascot.webp"]{content:url(/img/mascot-dark.webp)}',
               "dark themes select the dark Nong mascot")
