"""The module page stops presenting old numbers as if they were current.

The board pushes its status twice a second. When that stops - the WiFi drops,
the cable is pulled, the board reboots - every value on the page keeps its last
reading and goes on looking live. On a page that shows where an ARM IS, that is
the state that hurts somebody: an angle is read, a hand goes in, and the arm is
somewhere else entirely.

This is the fifth state from the design rules, the one everybody skips: not
loading, not empty, not error, but STALE - data shown while known to be old. It
is also the one this project has a standing rule about, that the UI is always
right about itself while the arm sits somewhere else.

What is held here:

  * silence for three seconds - six missed pushes - is called out;
  * a page that has NEVER heard from the board is not called stale. That is
    loading, and saying "these numbers are old" about numbers that were never
    there is a lie in the other direction;
  * the numbers are NOT blanked. The last known pose is still the most useful
    thing on the screen, as long as nobody mistakes it for the current one;
  * the warning goes away by itself the moment a message arrives, without a
    reload - a warning that has to be dismissed by hand gets dismissed by
    habit.
"""
import re

import qc as F

AREA = "connection"
TITLE = "the module page says when its numbers have gone old"


def run(t):
    page = (F.FIRMWARE / "src" / "web" / "WebUI.h").read_text(encoding="utf-8")

    # ---- there is something to say it with -------------------------
    i = page.find('id="staleWarn"')
    if not t.ok(i > 0, "the page has a stale warning to show"):
        return
    banner = page[i - 200:i + 420]
    t.contains(banner, "banner warn",
               "in the warning colour of the design system, not a new one")
    t.contains(banner, "hidden",
               "hidden while the board is answering")
    t.contains(banner, 'aria-live="polite"',
               "and announced, since it appears with nobody pressing anything")
    t.ok("last ones it sent" in banner or "not what it is doing now" in banner,
         "it says what the numbers ARE, not just that something is wrong",
         "'connection lost' does not tell anyone whether the angle on screen "
         "can be trusted, which is the only question being asked")

    # ---- and it is driven by silence, not by the socket alone -------
    # A closed socket is not the same as a silent board: the socket can stay
    # open through a board that has stopped answering, which is exactly the
    # case that used to show live numbers for a robot that had rebooted.
    t.contains(page, "lastHeard",
               "the page remembers when the board last said anything")
    t.contains(page, "STALE_MS",
               "and has a named threshold rather than a number in three places")
    m = re.search(r"var STALE_MS=(\d+)", page)
    if t.ok(m, "the threshold is readable"):
        ms = int(m.group(1))
        t.ok(1000 <= ms <= 10000,
             "it is between one and ten seconds (%d ms)" % ms,
             "shorter than a second calls a busy board dead; longer than ten "
             "leaves somebody reading an old angle for too long")

    tick = page[page.find("function staleTick"):]
    tick = tick[:tick.find("setInterval(staleTick")]
    t.contains(tick, "lastHeard===null",
               "a page that has NEVER heard from the board is not called stale")
    t.ok("hidden" in tick and "age <" in tick.replace("< ", "<"),
         "the warning appears and disappears with the age of the data",
         "one that only ever appears has to be dismissed by hand, and a "
         "warning dismissed by habit is not a warning")

    # It must not blank the readouts: the last pose is the most useful thing on
    # the screen as long as it is labelled.
    t.ok("innerHTML=''" not in tick and "textContent=''" not in tick,
         "and the last known numbers stay on screen, labelled",
         "blanking them replaces a known-old pose with no pose at all, which "
         "is worse for somebody standing next to the arm")

    # ---- hearing anything clears it, by both routes -----------------
    # Inside the SOCKET handler specifically. The same words appear in the
    # first fetch below, so asserting on the whole file passed while the push
    # path stopped counting - the sabotage tool caught that.
    ws = page[page.find("function connectWs"):]
    ws = ws[:ws.find("var lastHeard")]
    t.contains(ws, "heard()",
               "a pushed status counts as hearing from the board")
    first = page[page.find("fetch('/api/status')"):]
    t.contains(first[:200], "heard()",
               "and so does the first status the page asks for itself")
    h = page[page.find("function heard()"):]
    h = h[:h.find("function staleTick")]
    t.contains(h, "hidden=true",
               "hearing from the board takes the warning away at once")

    # ---- and the generated page really carries it -------------------
    # WebUI.h is the master; the board serves the GENERATED copy. A change that
    # lives only in the master reaches nobody.
    gen = F.generated("web/ModuleUI.h").read_text(encoding="utf-8")
    t.contains(gen, "staleWarn",
               "the generated page the board serves has it too")
    t.contains(gen, "STALE_MS",
               "including the timer that drives it")
