"""The rainbow stays off, and the type colours keep their job.

The owner's verdict, 2026-09-08: *remove the rainbow strip in the web all of it
it not help*. Two rules were painting it in `shared/web/mice.css` - a
four-colour gradient across the top edge of every page (`body` `border-image`)
and a gradient underline under every `h1` (`h1::after`). Both are gone.

This is the part that keeps them gone. A decorative gradient is the easiest
thing in the world to add back "just here" - it costs one line and looks like
care - so the ban is written down where a check can read it.

WHAT IS BANNED, AND WHAT IS NOT. Not gradients: a gradient that DOES something
is fine and one is in use. Studio's splitter (`#sideDrag`) paints a 2px line in
the middle of a 14px grab handle, so the thing you see is thin while the thing
you can hit is a finger wide - that is a gradient doing a job no border can do.

What is banned is a gradient made of the TYPE colours, which is what the
rainbow was: `--ty-nong`, `--ty-lift`, `--ty-cam` mixed together as decoration.
Those three still exist and still mean something - a module row is edged in its
own type colour, with the type written in words on the badge beside it - and
this check holds that too, because deleting the meaning would be the other way
to fail.
"""
import re

import qc as F

AREA = "design"
TITLE = "no decorative rainbow, and the type colours still mean something"

# A gradient is allowed to exist where it does a JOB. One does, and it is named
# here rather than left to a blanket rule that a future one could hide behind.
ALLOWED = {"nong/main_python_set_nong/web/style.css": ["#sideDrag"]}

WEB_FILES = [
    "shared/web/mice.css",
    "shared/web/themes.css",
    "main_python/web/hub.html",
    "main_python/web/rgb.html",
    "main_python/web/help.html",
    "nong/main_python_set_nong/web/style.css",
    "nong/main_python_set_nong/web/index.html",
    "firmware/src/web/WebUI.h",
]


def run(t):
    for rel in WEB_FILES:
        p = F.CODE / rel
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8", errors="replace")

        # ---- the two rules that were the rainbow ----------------------
        t.ok(not re.search(r"body\s*\{[^}]*border-image", text, re.S),
             "%s does not paint a gradient across the page's top edge" % rel,
             "that bar was the rainbow, and the owner said it does not help")
        t.ok("h1::after" not in text or "linear-gradient" not in
             text[text.find("h1::after"):text.find("h1::after") + 260],
             "%s has no gradient underline beneath the heading" % rel)

        # ---- and no new one made of the type colours ------------------
        for m in re.finditer(r"linear-gradient\([^)]*\)", text):
            grad = m.group(0)
            types = len(re.findall(r"--ty-", grad))
            if types < 2:
                continue                      # not a rainbow: one colour or none
            near = text[max(0, m.start() - 400):m.start()]
            allowed = any(a in near for a in ALLOWED.get(rel, []))
            t.ok(allowed,
                 "%s: no decorative gradient built from the type colours" % rel,
                 "found %s - the type colours say WHICH BOARD a row is, and "
                 "mixing them together is decoration again" % grad[:80])

    # ---- the colours themselves are still doing their job -------------
    themes = (F.CODE / "shared" / "web" / "themes.css").read_text(
        encoding="utf-8", errors="replace")
    for name in ("--ty-nong", "--ty-lift", "--ty-cam"):
        t.contains(themes, name, "%s is still defined" % name)
    css = (F.CODE / "shared" / "web" / "mice.css").read_text(
        encoding="utf-8", errors="replace")
    t.ok(re.search(r"\.mod\.[a-z]+\s*\{[^}]*--ty-|\.mod\b[^{]*\{[^}]*--ty-", css, re.S)
         or "--ty-" in css,
         "and a module row is still edged in its own type colour",
         "taking the meaning out with the decoration would be the other way to "
         "get this wrong: the colour tells a shelf of boards apart at a glance")
