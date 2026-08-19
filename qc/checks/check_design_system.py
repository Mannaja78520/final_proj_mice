"""One design system, in ONE file, that every surface really reads.

The project had six copies of the same `:root` block — hub.html, module.html,
rgb.html, help.html, Studio's style.css and the module website inside
firmware/src/web/WebUI.h — each one commented "the SHARED design system" and
none of them shared with anything. They had already drifted into three radius
scales and four names for the same grey caption, and colours had been copied
as raw hex that stayed behind whenever a token moved.

`shared/web/mice.css` is now the only place those values exist. Nothing here
trusts a comment saying so:

  * exactly one file declares the tokens, and it is that one;
  * every page really LINKS it, and the hub really SERVES it at that URL;
  * the board carries the SAME BYTES in flash, generated from the same file,
    so a module reached over WiFi cannot look like a different product from
    the same module reached over USB;
  * no surface has quietly copied a token value back in as raw hex.

The one deliberate copy is docs/PLAN.html, which has to open from a USB stick
with no server at all and so cannot link anything.
"""
import re
import urllib.parse

import fake_serial
import qc as F

AREA = "design"
TITLE = "one design system, one file, and every surface reads it"
SLOW = False

CSS = F.CODE / "shared" / "web" / "mice.css"

# Every web surface a person looks at. style.css is Studio's own sheet: it does
# not link anything itself, its page does.
SURFACES = [
    ("hub", "main_python/web/hub.html", True),
    ("help", "main_python/web/help.html", True),
    ("rgb", "main_python/web/rgb.html", True),
    ("module site", "firmware/src/web/WebUI.h", True),
    ("studio page", "nong/main_python_set_nong/web/index.html", True),
    ("studio css", "nong/main_python_set_nong/web/style.css", False),
]

# Colours that ARE tokens. A literal copy is the bug this check exists to
# prevent: change the accent once and every hardcoded copy stays wrong.
TOKEN_LITERALS = ["#10141a", "#1a212b", "#0d1117", "#2a3442", "#dce3ec",
                  "#8b98a9", "#4da3ff", "#06121f", "#243040", "#3ecf8e",
                  "#ffb454", "#ff6b6b"]

# What the system has to define for a page to be able to stop defining it.
# The tokens, split the way the two files are (2026-08-19): colour lives in
# themes.css so a theme is one block in one small file, and shape lives in
# mice.css. Each list is checked against ITS file, and against the other one
# NOT having it - a colour that creeps back into mice.css is invisible until
# someone adds a theme and finds half the palette ignores it.
COLOUR_TOKENS = ["--bg", "--card", "--sunk", "--line", "--txt", "--mut",
                 "--acc", "--on-acc", "--btn", "--ok", "--warn", "--err",
                 "--ty-nong", "--ty-lift", "--ty-cam", "--ty-other"]
SHAPE_TOKENS = ["--r-sm", "--r-md", "--r-lg", "--r-pill",
                "--sp-1", "--sp-2", "--sp-3", "--sp-4", "--sp-6",
                "--sans", "--mono"]
REQUIRED_TOKENS = COLOUR_TOKENS + SHAPE_TOKENS


def run(t):
    if not t.ok(CSS.is_file(), "shared/web/mice.css exists",
                "the one design system is missing: %s" % CSS):
        return
    css = CSS.read_text(encoding="utf-8")

    # ---- it really is a design system ---------------------------------
    themes_file = CSS.parent / "themes.css"
    t.ok(themes_file.is_file(), "the palette has a file of its own",
         "shared/web/themes.css is where a theme is added, in one block")
    themes = themes_file.read_text(encoding="utf-8") if themes_file.is_file() else ""

    root = re.search(r":root\s*\{.*?\}", css, re.S)
    if t.ok(root, "mice.css declares the shape tokens"):
        for tok in SHAPE_TOKENS:
            t.contains(root.group(0), tok + ":", "mice.css defines %s" % tok)

    # Every colour token, in every theme. A theme that forgets one inherits it
    # from the default and looks almost right, which is the hardest kind of
    # wrong to see.
    blocks = re.findall(r':root(?:\[data-theme="([\w-]+)"\])?\s*\{(.*?)\}',
                        themes, re.S)
    named = [(n or "midnight", b) for n, b in blocks if "--txt:" in b or "--bg:" in b]
    t.ok(len(named) >= 2, "there is more than one theme to choose from",
         "found: %r" % [n for n, _b in named])
    for name, body in named:
        missing = [tok for tok in COLOUR_TOKENS if tok + ":" not in body]
        t.ok(not missing, "the %s theme defines every colour" % name,
             "missing %r - it would inherit them and look almost right" % missing)

    # ...and mice.css no longer names any of them.
    leaked = [tok for tok in COLOUR_TOKENS
              if re.search(r"^\s*" + re.escape(tok) + r"\s*:", css, re.M)]
    t.ok(not leaked, "and mice.css names no colour at all",
         "%r are still declared there, so a theme cannot change them" % leaked)

    # The floor every app used to repeat, now stated once. Keyboard users need
    # to see where they are, and motion is a preference, not a decoration.
    t.contains(css, "focus-visible", "mice.css keeps a visible focus ring")
    t.contains(css, "prefers-reduced-motion", "mice.css respects reduced motion")
    t.contains(css, "pointer:coarse", "mice.css sizes controls for a finger")

    # ---- and it is the ONLY one ---------------------------------------
    for name, rel, is_page in SURFACES:
        src = (F.CODE / rel).read_text(encoding="utf-8", errors="replace")

        t.ok(not re.search(r":root\s*\{", src),
             "%s does not declare its own tokens" % name,
             "a second :root block is how six copies happened the first time")

        stray = [lit for lit in TOKEN_LITERALS
                 if lit in src.lower() or lit.upper() in src]
        t.ok(not stray, "%s uses tokens, not copies of them" % name,
             "hardcoded %s — change the accent and these stay wrong" % stray)

        if is_page:
            t.ok(re.search(r'<link[^>]+href="/mice\.css"', src),
                 "%s links the shared stylesheet" % name,
                 "the page carries no design system at all now, so a missing "
                 "link renders it unstyled")

    # ---- the board carries the same bytes, not a copy someone edited ---
    # gen_tables.py compiles mice.css into flash. F.generated() runs the very
    # generator the firmware build runs, so this is what the board really gets.
    flash = F.generated("web/MiceCss.h")
    body = None
    if t.ok(flash.is_file(), "the board's stylesheet is generated into flash",
            "gen_tables.py wrote no web/MiceCss.h, so the board would serve "
            "nothing at /mice.css and its page would render unstyled"):
        gen = flash.read_text(encoding="utf-8")
        body = re.search(r'R"rawliteral\((.*)\)rawliteral"', gen, re.S)
    if t.ok(body, "the generated header carries the stylesheet"):
        # The served stylesheet is the palette and the components joined
        # (themes.css then mice.css, since 2026-08-19). Rather than writing
        # that join a THIRD time here, this asserts what actually matters:
        # both files are in it, whole.
        for part, name in ((themes, "themes.css"), (css, "mice.css")):
            t.ok(part and part.strip() in body.group(1),
                 "the board's stylesheet carries all of %s" % name,
                 "rerun gen_tables.py - the board would render with half a "
                 "design system, which looks like a broken page rather than "
                 "a stale build")

    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(portal, '"/mice.css"',
               "the board serves it at the same URL the hub does")
    t.contains(portal, "MICE_CSS",
               "and serves the generated stylesheet, not a second copy")

    # ---- the hub really serves it, at that URL, as CSS ----------------
    fake_serial.reset()
    base, main = F.start_hub()

    st, got = F.get(base + "/mice.css")
    t.eq(st, 200, "the hub serves /mice.css")
    for part, name in ((themes, "themes.css"), (css, "mice.css")):
        t.ok(part and part.strip() in got,
             "and serves all of %s in it" % name,
             "the hub answered %d bytes" % len(got))

    # The two producers must agree with EACH OTHER, or a board looks one way
    # over WiFi and another through the hub - the exact fault the one design
    # system was built to end. Compared directly, so neither the hub nor the
    # generator can quietly change the join and still pass.
    if body:
        t.ok(got.strip() == body.group(1).strip(),
             "and the board and the hub serve the same bytes",
             "hub %d bytes, board %d - one of them has been changed alone"
             % (len(got.strip()), len(body.group(1).strip())))

    # The shared script travels the same way, or the theme works on one
    # surface and not the others.
    stj, js = F.get(base + "/mice.js")
    t.eq(stj, 200, "the hub serves /mice.js")
    t.contains(js, "miceTheme", "carrying the shared theme handling")
    flashjs = F.generated("web/MiceJs.h")
    t.ok(flashjs.is_file(), "and the board has it in flash too",
         "a board reached over WiFi would have no theme at all")

    # Every page the hub hands out has to reach it. A link that 404s leaves an
    # unstyled page, which is worse than the six copies were.
    dev = "usb:" + urllib.parse.quote(fake_serial.PORT)
    for name, url in (("hub", "/"), ("help", "/help"), ("rgb", "/rgb.html"),
                      ("studio", "/studio/"),
                      ("module site", "/mod?dev=" + dev)):
        st, page = F.get(base + url)
        t.eq(st, 200, "the hub serves the %s page" % name)
        t.ok('href="/mice.css"' in page,
             "the %s page links /mice.css" % name,
             "served page carries no link to the design system")
