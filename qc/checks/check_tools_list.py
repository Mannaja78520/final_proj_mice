"""The Tools list on the hub page actually draws the tools.

Found by the five-model panel on 2026-08-20 and confirmed in a browser: the
list rendered NOTHING. The row-building loop had been copied from the module
list and still read `m.type`, but the loop variable there is `a` and an app has
no module type at all - so `m` was undefined, the exception left `loadApps`
half-finished, and the card stayed empty.

It survived because an empty list is a PLAUSIBLE state. The page has a careful
empty message - *No tools yet. A tool is a folder with an app.json* - so a
broken list and a genuinely empty one looked identical, and every check that
asked about the app registry asked the SERVER, which was answering perfectly.

So this check drives the real page in a real browser and counts rows against
what `/api/apps` returned. That is the only way the two can be told apart: the
registry being right is exactly what the old checks proved while the screen
showed nothing.
"""
import json
import re
import subprocess
import urllib.request

import browser
import qc as F

AREA = "hub"
TITLE = "the Tools list draws one row per tool, and knows when there are none"
SLOW = True


def run(t):
    if not browser.available():
        t.give_up("Edge is not installed on this machine")
        return

    base, _main = F.start_hub()
    with urllib.request.urlopen(base + "/api/apps", timeout=10) as r:
        apps = (json.loads(r.read()) or {}).get("apps", [])
    if not t.ok(apps, "the hub has tools to show",
                "code/apps/*/app.json is where they come from"):
        return

    dom = _load(base + "/")
    if not t.ok(dom, "the hub page loads"):
        return

    # The Tools card, not the whole page: module rows use the same class, and
    # counting those would have hidden this bug just as well as the old checks
    # did.
    card = dom[dom.find('id="tools"'):]
    card = card[:card.find("</div>", card.find("</div>") + 6) + 6] if "</div>" in card else card
    names = re.findall(r'class="nm">([^<]*)<', card)
    t.eq(len(names), len(apps),
         "every tool the hub reports has a row on the page")
    # The DOM carries escaped text - an app called "Features & help" appears as
    # "Features &amp; help" - so the comparison has to speak the same language.
    import html as _html
    names = [_html.unescape(n) for n in names]
    for a in apps:
        t.ok(any(a["name"] in n for n in names),
             "%s is on the page" % a["name"],
             "the hub lists it in /api/apps but the page drew %r" % (names,))

    # ---- and the empty state is still reachable ---------------------
    # It is the state a broken list imitates, so it has to be real: if the card
    # can never say "no tools yet" then the message is decoration, and if the
    # list breaks again it will look like this instead.
    src = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    fn = src[src.find("async function loadApps"):]
    fn = fn[:fn.find("\nasync function", 10)]
    t.contains(fn, "No tools yet",
               "the card can say that there are none")
    t.ok("!apps.length" in fn,
         "and says it only when there really are none",
         "an empty state that shows on an error is how a broken list hides")

    # ---- BROKEN is not EMPTY ----------------------------------------
    # A malformed app.json used to be reported three different wrong ways: the
    # hub answered 200 with an empty list, so the page said *No tools yet* and
    # told the operator to go and ADD a tool; or registry.apps() raised, the
    # request became a 500, and the page said *the hub may have stopped*, which
    # is false and throws away the file and line that RegistryError already
    # knew. Both hid a real fault behind a tidy state.
    man = F.CODE / "apps" / "help" / "app.json"
    keep = man.read_text(encoding="utf-8")
    try:
        man.write_text(keep.replace("{", "{,", 1), encoding="utf-8")
        with urllib.request.urlopen(base + "/api/apps", timeout=10) as r:
            broke = json.loads(r.read())
            code = r.status
        t.eq(code, 200, "a broken registry is still an answer, not a 500")
        t.ok(broke.get("ok") is False,
             "and the answer says it failed",
             "an empty list with ok:true is indistinguishable from having no "
             "tools, which is what made this invisible")
        t.contains(str(broke.get("error", "")), "app.json",
                   "naming the file that could not be read")
        t.contains(str(broke.get("error", "")), "line",
                   "and where in it")

        dom2 = _load(base + "/")
        card2 = dom2[dom2.find('id="tools"'):]
        card2 = card2[:card2.find("</div>", card2.find("</div>") + 6) + 6]
        t.ok("could not be read" in card2,
             "the page says the list could not be read")
        t.ok("No tools yet" not in card2,
             "and does NOT tell the operator to go and add one",
             "that is advice for a different situation, and it hides a fault "
             "somebody could fix in ten seconds if they were told which file")
    finally:
        man.write_text(keep, encoding="utf-8", newline="")

    # The specific mistake, kept out by name: the loop variable is `a`, and
    # anything reaching for a module's fields here is the same bug again.
    body = fn[fn.find("apps.forEach"):]
    body = body[:body.find("});") + 3]
    # Comments stripped first: the fix's own comment EXPLAINS the m.type
    # that used to be there, and the first version of this assertion failed
    # on that explanation - the same trap as three other checks here.
    body = re.sub(r"//[^\n]*", "", body)
    t.ok(not re.search(r"\bm\.", body),
         "the row builder does not reach for a module's fields",
         "`m.type` here was undefined and threw, which drew no rows at all: %s"
         % re.findall(r"\bm\.\w+", body))


def _load(url):
    """The page after its scripts have run, as the browser sees it."""
    prof = str(browser.SCRATCH / ("profile_tools_%s" % browser._tag()))
    out = str(browser.SCRATCH / ("tools_dom_%s.html" % browser._tag()))
    ps = ("$a=@('--headless=new','--disable-gpu','--no-sandbox','--no-first-run',"
          "'--disable-extensions','--%s','--user-data-dir=%s',"
          "'--virtual-time-budget=9000','--dump-dom','%s'); "
          "Start-Process -FilePath '%s' -ArgumentList $a -NoNewWindow -Wait "
          "-RedirectStandardOutput '%s' -RedirectStandardError '%s.err'"
          % (browser.TAG, prof, url, browser.EDGE, out, out))
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=200)
        from pathlib import Path
        return Path(out).read_text(encoding="utf-8", errors="replace")
    except Exception:                                        # noqa: BLE001
        return ""
