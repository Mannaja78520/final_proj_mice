"""An open page notices when the app behind it has changed.

Asked on 2026-08-20: *in web why i need to refresh by my self to see the
change*. The answer was that two different things were being confused. The DATA
on the hub page refreshes itself - modules every 5 seconds, a rescan every 15 -
so a board coming and going is seen. But `hub.html` and the stylesheets are
fetched once, when the tab opens, so a change to the INTERFACE is invisible
until somebody reloads, and nothing on screen says so.

So the hub publishes a version of the pages it is serving, and a page that
notices the version move says so. Three properties, and the second is the one
that makes it usable rather than annoying:

  * the version changes when a served file changes, and only then;
  * the page NEVER reloads itself. Somebody may be dragging a joint or halfway
    through typing a WiFi password, and losing that to a surprise refresh is
    worse than reading an old screen for a minute;
  * `/api/version` needs no login, because the login screen is one of the pages
    that can go stale, and a version nobody may read until they log in would
    not help there.
"""
import json
import re
import os
import time
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "an open page is told when the hub it came from has changed"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    # ---- the version follows the files, not a hand-written number ---
    first = main.web_version(ttl=0)
    t.ok(first, "the hub can say which version of the pages it serves")
    t.eq(main.web_version(ttl=0), first,
         "and says the same thing when nothing has changed")

    page = F.HUB / "web" / "hub.html"
    was = page.stat()
    try:
        os.utime(page, (was.st_atime, was.st_mtime + 61))
        moved = main.web_version(ttl=0)
    finally:
        os.utime(page, (was.st_atime, was.st_mtime))
    t.ok(moved != first,
         "a changed page really moves the version",
         "hub.html was touched and the version stayed %s - an open tab would "
         "never learn that the interface had changed" % first)
    t.eq(main.web_version(ttl=0), first,
         "and it goes back when the file does, so it is the FILES that decide")

    # ---- a changed PICTURE counts too -------------------------------
    # Raised by the panel 2026-08-20 and true: the hash looked only at html,
    # css and js, so a redrawn pinout or a new icon was invisible to an open
    # tab. That is exactly the change somebody makes and then wonders why
    # nothing moved.
    pic = F.HUB / "web" / "pinout.svg"
    if pic.is_file():
        st = pic.stat()
        try:
            os.utime(pic, (st.st_atime, st.st_mtime + 61))
            t.ok(main.web_version(ttl=0) != first,
                 "a changed picture moves the version too",
                 "images were skipped, so a redrawn diagram never reached an "
                 "open page")
        finally:
            os.utime(pic, (st.st_atime, st.st_mtime))

    # A ONE-FILE BUILD must not appear to change just by restarting: PyInstaller
    # unpacks to a new temp folder each launch, so every mtime is new. Frozen
    # builds therefore use size and path only.
    src_v = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src_v.find("def web_version")
    body_v = src_v[i:src_v.find(chr(10) + "def ", i)]
    t.contains(body_v, "if not frozen:",
               "a frozen build ignores mtimes, which change on every launch")
    t.ok("relative_to" in body_v,
         "files are keyed by path, not by name alone",
         "two folders each hold an index.html; keying on the name meant moving "
         "a file between them changed nothing")

    # ---- scratch files do not count as a new version ----------------
    # Found by this check failing in the first parallel gate: QC writes its
    # driver page into the studio web folder while a browser check runs, so the
    # version moved several times a minute and every open tab would have
    # announced an update because a temporary file appeared.
    scratch = F.CODE / "nong" / "main_python_set_nong" / "web" / "_qcver.html"
    try:
        scratch.write_text("<p>scratch</p>", encoding="utf-8")
        t.eq(main.web_version(ttl=0), first,
             "a temporary file next to the pages is not a new version")
    finally:
        scratch.unlink(missing_ok=True)

    # A cache, because every open tab asks. Without it a laptop with three tabs
    # open stats a megabyte of Studio several times a minute forever.
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src.find("def web_version")
    t.contains(src[i:src.find(chr(10) + "def ", i)], "ttl",
               "the answer is cached for a moment, since every tab asks")

    # ---- and it is readable WITHOUT logging in ----------------------
    base, _m = F.start_hub()
    with urllib.request.urlopen(base + "/api/version", timeout=8) as r:
        got = json.loads(r.read())
    t.ok(got.get("ok") and got.get("version"),
         "a page that is not logged in can still ask",
         "got %r - the login screen is one of the pages that goes stale, so a "
         "version behind the login would not help the case that needs it" % (got,))
    t.eq(got["version"], main.web_version(ttl=0),
         "and it is the same version the hub computed")

    j = src.find('"/api/login", "/api/logout"')
    t.contains(src[j - 200:j + 300], "/api/version",
               "the route is listed with the open ones on purpose")

    # ---- the page asks, and never reloads itself --------------------
    html = page.read_text(encoding="utf-8")
    t.contains(html, "/api/version", "the page asks for the version")
    k = html.find("async function checkVer")
    body = html[k:k + 900]
    t.contains(body, "document.hidden",
               "and stops asking while the tab is in the background")
    # The baseline must STORE WHAT IT WAS TOLD. Asserting that the words
    # "myVer === null" appear proves nothing: the sabotage tool broke the
    # assignment, left the words in place, and this check still passed - which
    # is the exact failure the sabotage rule exists to catch.
    base_line = re.search(r"myVer\s*===\s*null\s*\)\s*\{([^}]*)\}", body)
    t.ok(base_line and "myVer = r.version" in base_line.group(1),
         "the first answer is kept as the baseline, not a change",
         "the baseline branch reads %r - if it stores anything other than the "
         "version it was given, every page announces an update the moment it "
         "loads" % (base_line.group(1).strip() if base_line else None))

    # The banner exists, is hidden until there is something to say, and is
    # built from the design system rather than a second kind of button.
    b = html.find('id="newVer"')
    if not t.ok(b > 0, "there is a banner to show"):
        return
    banner = html[b - 120:b + 400]
    t.contains(banner, "hidden", "hidden until the version really moves")
    t.contains(banner, 'aria-live="polite"',
               "and announced politely, since it appears on its own")
    t.contains(banner, "banner info",
               "using the banner component that already exists")
    t.ok('class="btn' not in banner,
         "and the buttons the stylesheet really defines",
         "mice.css styles button by element with .primary and .danger; a .btn "
         "class would be a second button system that nothing styles")

    t.ok("location.reload()" in banner,
         "reloading is offered")
    auto = html[k:k + 900]
    t.ok("location.reload" not in auto,
         "but the page never reloads itself",
         "someone may be mid-drag or typing a password; a surprise refresh "
         "loses that, which is worse than an old screen")
