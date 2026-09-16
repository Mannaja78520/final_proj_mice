"""docs/ref.html says which equation each part uses, and it cannot go stale.

Asked for 2026-08-28: *find the ref to ref.html for me please which thing have
use which equation or other ref for everything in my project alway update this
ref too if we add something new or edit it*.

The second half is the hard half. A reference page that is updated when
somebody remembers is a page that is wrong within a month, and a wrong
reference is worse than none: it is believed. So three things are held here.

**Every entry is complete and points at something real.** An entry naming a
file that does not exist is the normal way this kind of page dies — code moves,
the page does not. The file must be there, and the line must be inside it.

**Every equation in the code has an entry.** `NongMath.h` is the project's one
pure-maths file: every function in it is a formula the robot runs on, so every
one of them must be named by some entry. Add a formula there and this check
fails until the reference learns about it. That is the rule the user asked for,
expressed as a test rather than as a promise.

**The page draws the data and nothing else.** The entries live in
`docs/ref_data.js` so adding the next one costs no page code — the same shape
as every other registry here. If someone hardcodes an entry into ref.html, the
count stops matching and this says so.

Both files travel in `docs/`, beside PLAN.html, and open from the file system
with no server: the page loads its data with a <script> tag, because a file://
page has a null origin and is refused when it fetches its own neighbours.
"""
import re

import qc as F

AREA = "docs"
TITLE = "the equation reference is complete, and points at real code"

# Every field an entry must carry. `from` and `watch` are optional: not every
# formula has an outside source or a trap worth naming.
NEEDED = ("id", "group", "name", "where", "eq", "why")


def entries(text):
    """Split ref_data.js into one string per entry. Not a JS parser - the file
    is written by this project in one known shape, and a real parser here would
    be a second thing to keep right."""
    out, depth, buf = [], 0, ""
    started = False
    for ch in text.split("window.REF", 1)[-1]:
        if ch == "{":
            depth += 1
            started = True
        if started:
            buf += ch
        if ch == "}":
            depth -= 1
            if depth == 0 and started:
                out.append(buf)
                buf, started = "", False
    return out


def run(t):
    docs = F.CODE / "docs"
    page = docs / "ref.html"
    data = docs / "ref_data.js"
    if not t.ok(page.is_file(), "docs/ref.html is there", str(page)):
        return
    if not t.ok(data.is_file(), "docs/ref_data.js is there", str(data)):
        return

    html = page.read_text(encoding="utf-8", errors="replace")
    js = data.read_text(encoding="utf-8", errors="replace")

    # ---- it opens with no server -------------------------------------
    t.contains(html, 'src="ref_data.js"',
               "the page loads its data with a script tag, not fetch")
    t.ok("fetch(" not in html,
         "and never fetches, which a file:// page is refused",
         "a page opened from disk has a null origin")
    t.ok("<link" not in html,
         "nor links a stylesheet it would not find from a USB stick")

    # ---- the entries -------------------------------------------------
    es = entries(js)
    t.ok(len(es) >= 10, "the reference has real content", "%d entries" % len(es))

    ids, seen_files = set(), 0
    for e in es:
        m = re.search(r"id:\s*\"([^\"]+)\"", e)
        who = m.group(1) if m else e[:40]
        for field in NEEDED:
            t.ok(re.search(r"\b%s:\s*\S" % field, e) is not None,
                 "%s has %s" % (who, field))
        if m:
            t.ok(m.group(1) not in ids, "%s is used once" % who)
            ids.add(m.group(1))

        # Every place an entry points at must exist, at that line. file, line
        # and what are taken TOGETHER: an entry may name two places (a formula
        # that lives in the firmware and again in Studio), and pairing the
        # first name with the second file is how this check first failed.
        for f, line, what in re.findall(
                r"file:\s*\"([^\"]+)\",\s*line:\s*(\d+),\s*what:\s*\"([^\"]*)\"",
                e, re.S):
            seen_files += 1
            p = F.CODE / f
            if not t.ok(p.is_file(), "%s names a real file (%s)" % (who, f)):
                continue
            body = p.read_text(encoding="utf-8", errors="replace")
            n = len(body.splitlines())
            t.ok(1 <= int(line) <= n,
                 "%s points inside %s" % (who, f),
                 "line %s of %d - the code moved and the reference did not"
                 % (line, n))
            # A line number alone rots quietly: code moves and the number stays
            # valid while pointing at nothing. When `what` names a function,
            # that name must still be in the file it is claimed to live in,
            # which survives the line drifting a little.
            wm = re.match(r"(\w+)\(\)", what.strip())
            if wm:
                t.contains(body, wm.group(1) + "(",
                           "%s: %s() is really in %s" % (who, wm.group(1), f))
    t.ok(seen_files >= len(es),
         "every entry points at somewhere in the code", seen_files)

    # ---- ALWAYS UPDATE IT: the maths file may not outgrow the page ----
    # NongMath.h is the one file that is nothing but formulas, so it is the
    # honest tripwire: a function there with no entry means the reference is
    # already behind the code.
    math = (F.FIRMWARE / "src/modules/nong/NongMath.h").read_text(
        encoding="utf-8", errors="replace")
    funcs = set(re.findall(r"^inline\s+\w[\w:<>\s\*&]*?\b(\w+)\s*\(", math, re.M))
    # the chain helper is the two named functions performed one after the other
    funcs -= {"jointToUs", "maxDelta"}
    for fn in sorted(funcs):
        t.ok(fn in js,
             "NongMath's %s() is in the reference" % fn,
             "a formula the robot runs on that the reference does not mention - "
             "add an entry to docs/ref_data.js")
