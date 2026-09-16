"""Stop from anywhere, find by typing, and get back to the last robot.

Three things a person standing at the bench needs and did not have:

  * a STOP. There was none on this page at all - the only one was inside Nong
    Studio, on another screen, behind a tab. Somebody next to a moving arm does
    not navigate. It sits with the title, so it is on every tab; it never asks,
    because a stop that needs confirming arrives after the thing you were
    trying to prevent; and it is NOT disabled while it works - Gemini Pro
    proposed disabling it, which is right for an ordinary button and wrong for
    this one, since a press that did not land has to be repeatable;
  * a search. Four boards fit on a screen and twenty do not, and scrolling a
    list looking for a name is how the wrong robot gets opened;
  * the last board opened. Coming back to the same robot is the commonest
    thing anybody does here and it took a tab, a scroll and a click.

The stop route is deliberately NOT behind the login, for the reason hub_auth
already gives about /api/play/stop: a password prompt in that moment is a
safety failure, not security. That is asserted here too, because it is exactly
the kind of thing a later tidy-up "fixes".
"""
import json
import re
import urllib.request

import qc as F

AREA = "hub"
TITLE = "stop is reachable from every screen, and a module can be found by name"


def run(t):
    page = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")

    # ---- the stop is outside every tab ------------------------------
    i = page.find('id="stopAll"')
    if not t.ok(i > 0, "there is a stop control"):
        return
    before = page[:i]
    last_tab = before.rfind("data-tab=")
    last_h1 = before.rfind("<h1")
    t.ok(last_h1 > last_tab,
         "it sits with the title, not inside a tab's card",
         "a control inside a tab is missing from five screens out of six")
    t.contains(page[i - 200:i + 200], "danger",
               "and it looks like what it does")

    fn = page[page.find("async function stopEverything"):]
    fn = fn[:fn.find("\n}") + 2]
    t.ok("confirm(" not in fn,
         "it never asks first",
         "a stop that needs confirming arrives after the thing it was meant "
         "to prevent")
    t.ok("disabled" not in fn,
         "and it is not disabled while it works",
         "if the first press did not land, the operator has to be able to "
         "press again - that is what makes it a stop and not a button")
    t.contains(fn, "STOPPING",
               "it says it is working, since several boards take a moment")
    t.contains(fn, "power switch",
             "and if it fails it says what to do instead")

    # ---- the route exists, stops the clock first, and needs no login -
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    route = src[src.find('if path == "/api/stopall"'):]
    # cut at the NEXT section, not N chars into the answer line: the reply
    # grew ("slow") and the old slice ended before its own tail
    route = route[:route.find("# ---- studio")]
    t.contains(route, "show.stop",
               "the show clock is stopped as well as the boards")
    i_show = route.find("show.stop")
    i_mod = route.find("modules_here()")
    t.ok(0 < i_show < i_mod,
         "and the clock goes first",
         "stopping the boards while the clock runs means the next tick starts "
         "them moving again")
    t.contains(route, "MOVE STOP", "each board is told to stop")
    # in a row, each stop queues behind whatever that cable was already
    # doing - a flash holds its port lock for up to 30s (FWEND)
    t.ok("threading.Thread(" in route,
         "boards are stopped at the same time, not one after another")
    # a board still being reached when the answer goes out must be named,
    # not silently dropped - silence would read as stopped
    t.contains(route, '"slow": slow',
               "a board still being reached when the answer goes out is named")

    auth = (F.HUB / "hub_auth.py").read_text(encoding="utf-8")
    t.contains(auth, '"/api/stopall"',
               "and stopping never waits for a password")
    m = re.search(r"NEVER_GATED = \{([^}]*)\}", auth)
    t.ok(m and "stopall" in m.group(1),
         "it is in NEVER_GATED, listed rather than merely absent",
         "this is the one control where a login prompt could cause an injury "
         "rather than prevent one")

    # It really answers without a cookie.
    base, _m = F.start_hub()
    req = urllib.request.Request(base + "/api/stopall", data=b"", method="POST")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            got = json.loads(r.read())
            code = r.status
    except urllib.error.HTTPError as e:
        print(e.read().decode())
        raise
    t.eq(code, 200, "an unauthenticated stop is answered, not refused")
    t.ok("stopped" in got, "and it says what it stopped", str(got)[:120])

    # ---- find by typing ---------------------------------------------
    t.contains(page, 'id="modFind"', "there is a box to type a name into")
    ff = page[page.find("function filterMods"):]
    ff = ff[:ff.find("\n}") + 2]
    t.contains(ff, "toLowerCase",
               "matching ignores case, because nobody types the case")
    t.contains(ff, "modFindNone",
               "and it says when a word matched nothing")
    t.ok("still connected" in page,
         "saying the modules are still there, only filtered",
         "the empty state of a SEARCH is not the empty state of a list, and "
         "confusing them makes people think boards dropped off")

    # ---- the last one opened ----------------------------------------
    t.contains(page, "function rememberOpened",
               "opening a module is remembered")
    # EACH SITE, not a count. "at least as many minus one" passed with one
    # route stripped, which is exactly the route that would then be missing
    # from the shortcut - proved with tools/sabotage.py.
    forgot = []
    for m in re.finditer(r"window\.open\('/mod\?dev=", page):
        near = page[max(0, m.start() - 260):m.start()]
        # the last-opened button itself opens the remembered one; it does not
        # need to record what it just read back
        if "rememberOpened(" in near or "raw.dev" in page[m.start():m.start() + 60]:
            continue
        forgot.append(page[max(0, m.start() - 70):m.start() + 40]
                      .strip().replace(chr(10), " ")[-70:])
    t.eq(forgot, [],
         "every way of opening a module records it")
    t.contains(page, 'id="lastOpened"', "and Home has somewhere to show it")
    ph = page[page.find("function paintHome(){"):]
    t.contains(ph[:200], "paintLastOpened",
               "which is painted when Home is drawn")
