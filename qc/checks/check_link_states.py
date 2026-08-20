"""Every screen answers "can I drive the robot?" from one list, with a next step.

Three screens show whether the robot is reachable - the hub page on a PC, the
board's own website served from its flash, and Nong Studio - and each used to
decide for itself and say it differently: a coloured dot, a badge of channel
names, a status line reading `not connected`. Three vocabularies for one
question, and only one of them ever said what to DO about it.

`not connected` is the example worth keeping: it tells an operator exactly what
they already know. It was also used for four different situations - nothing
plugged in, a board that has not booted, a port held by another program, and a
hub that wants a password - each of which needs a different next action.

So the states live in `shared/web/mice.js`, which every screen already loads:
served at /mice.js by the hub, and compiled into the board's flash by
gen_tables.py, so it works with no hub in sight.

Two things this deliberately does NOT require:

  * that every screen use the shared SENTENCE. The hub page knows it is a PC
    with cables and says *plug a board into this PC*, which is better than
    anything a shared string can say. Screens may be more specific; they may
    not invent a different set of states;
  * that the board page depend on the script being there. It is served from
    flash and must still work if the shared file is ever missing, so its use of
    it is guarded.
"""
import re

import qc as F

AREA = "connection"
SLOW = True
TITLE = "one list of connection states, and every one says what to do next"

SHARED = "shared/web/mice.js"
STUDIO = "nong/main_python_set_nong/web"


def run(t):
    js = (F.CODE / SHARED).read_text(encoding="utf-8")

    # ---- the list exists, and is reachable from every page ----------
    t.contains(js, "window.miceLink",
               "the shared script publishes the connection states")
    # The message may be built (the stale one counts seconds), so match the
    # state name and take the rest of its call for the next-step text.
    states = []
    for m in re.finditer(r'st\("(\w+)",', js):
        call = js[m.start():js.find(");", m.start()) + 2]
        quoted = re.findall(r'"([^"]*)"', call)[1:]
        states.append((m.group(1), quoted[0] if quoted else "",
                       " ".join(quoted[1:])))
    t.ok(len(states) >= 8,
         "there are states for the situations that differ (%d)" % len(states),
         "found %s" % [s[0] for s in states])

    named = {s[0] for s in states}
    for want, why in (("busy", "a port held by another program"),
                      ("login", "reachable but refusing until you log in"),
                      ("none", "nothing plugged in and nothing on WiFi"),
                      ("waiting", "never heard from it yet"),
                      ("stale", "heard from it, but not lately")):
        t.ok(want in named, "there is a state for %s" % why,
             "these four used to be the same two words: not connected")

    # ---- EVERY state that is not OK says what to do next ------------
    # This is the whole task. A state that only names the problem is the thing
    # being replaced, so one without a next step must not be able to creep in.
    silent = [s[0] for s in states if not s[2].strip() and s[0] not in
              ("cable", "wifi", "hub")]
    t.eq(silent, [],
         "every state that is not working tells the operator what to do")
    for name, says, nxt in states:
        if nxt.strip():
            t.ok(len(nxt) < 90,
                 "%s: the next step is one short sentence" % name,
                 "it is read standing next to a robot, not sitting down: %r"
                 % nxt)

    # ---- and no screen still says the empty phrase ------------------
    app = (F.CODE / STUDIO / "app.js").read_text(encoding="utf-8")
    idx = (F.CODE / STUDIO / "index.html").read_text(encoding="utf-8")
    t.contains(idx, "/mice.js",
               "Studio loads the shared script")
    badge = app[app.find("function linkBadge"):]
    badge = badge[:badge.find("\n}") + 2]
    t.contains(badge, "miceLink",
               "and asks it rather than inventing an answer")
    code = re.sub(r"//[^\n]*", "", badge)
    t.ok('"not connected"' not in code or "window.miceLink" in code,
         "the bare phrase is only a fallback for a page opened with no hub",
         "Studio can be opened straight from a file, where /mice.js is not "
         "served - but that is the only case it may be used for")

    # ---- the board page uses it, and survives without it ------------
    page = (F.FIRMWARE / "src" / "web" / "WebUI.h").read_text(encoding="utf-8")
    tick = page[page.find("function staleTick"):]
    tick = tick[:tick.find("setInterval(staleTick")]
    t.contains(tick, "window.miceLink",
               "the board's own page takes its wording from the shared list")
    t.ok(":" in tick and "window.miceLink" in tick and "Math.round" in tick,
         "and still works if the shared script is ever missing",
         "this page is served from flash; a hard dependency on a file the hub "
         "serves would break it exactly when the hub is not there")

    # ---- and the shared script really RUNS ---------------------------
    # A syntax error here is silent and total: every page loads it, so the
    # theme picker dies with it. One was introduced while writing this very
    # feature - two string literals side by side, which is fine in Python and
    # a parse error in JavaScript - and nothing but a browser would have said
    # so. The page asks the script a question and puts the answer in its title.
    import browser  # noqa: PLC0415
    if browser.available():
        base, _m = F.start_hub()
        said = _ask_browser(base)
        t.ok(said.startswith("OK "),
             "the shared script parses and answers in a real browser",
             "the page reported %r - a parse error takes the theme picker "
             "down on every screen with it" % said)
        t.eq(said, "OK none",
             "and with nothing connected it says so, from the shared list")

    # And the board really carries the shared script, not just the master.
    mjs = F.generated("web/MiceJs.h").read_text(encoding="utf-8")
    t.contains(mjs, "miceLink",
               "the copy compiled into flash has the states too",
               )


def _ask_browser(base):
    """Load a tiny page that asks miceLink one question, and read its title."""
    import subprocess
    from pathlib import Path as _P
    import browser
    web = F.CODE / STUDIO
    probe = web / ("_qclink_%s.html" % browser._tag())
    probe.write_text(
        "<!doctype html><meta charset=utf-8><title>t</title>"
        "<script src='/mice.js'></script>"
        "<script>document.title = window.miceLink ? "
        "('OK ' + window.miceLink.read({}).state) : 'BROKEN';</script>",
        encoding="utf-8")
    out = str(browser.SCRATCH / ("linkprobe_%s.html" % browser._tag()))
    prof = str(browser.SCRATCH / ("profile_link_%s" % browser._tag()))
    ps = ("$a=@('--headless=new','--disable-gpu','--no-sandbox','--no-first-run',"
          "'--disable-extensions','--%s','--user-data-dir=%s',"
          "'--virtual-time-budget=6000','--dump-dom','%s/studio/%s'); "
          "Start-Process -FilePath '%s' -ArgumentList $a -NoNewWindow -Wait "
          "-RedirectStandardOutput '%s'"
          % (browser.TAG, prof, base, probe.name, browser.EDGE, out))
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=150)
        dom = _P(out).read_text(encoding="utf-8", errors="replace")
        m = re.search(r"<title>([^<]*)</title>", dom)
        return m.group(1) if m else "(no answer)"
    except Exception as e:                                   # noqa: BLE001
        return "(browser failed: %s)" % e
    finally:
        probe.unlink(missing_ok=True)
