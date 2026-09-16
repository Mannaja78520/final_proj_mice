"""On the hub's own screens too: a control that acts says what happened.

The same sweep that found five faults on the module page found four here, all
verified against the code before anything changed (a fifth - that the theme
picker forces you to edit themes.css - was WRONG: the picker is built from the
stylesheet and is clickable; the note is about ADDING a theme, a developer act):

  * `fwWatch` follows a reflash and its catch was a bare `return`. The hub
    stops answering exactly when it matters - mid-write - and the quiet counter
    then never grew, so the stall line never ran: the bar sat still for ever
    with no word, three lines under a comment promising the opposite.
  * `setComplaintStatus` posted and never looked at the answer, so a refusal
    (not logged in, hub busy) closed the box as if it had saved; its catch then
    put a raw `e.message` in a blocking alert.
  * `submitReport` wrote its failure into `#stopSaid`, which lives on the
    screen BEHIND the modal - the person watching the Send button revert saw
    nothing at all.
  * the light tool threw away any command inside its 90 ms window with no
    trailing send, so the LAST value of a slider drag was lost: the strip kept
    the older colour while the slider showed the new one. It also glued the
    machine's own words onto the end of its sentences (`reply 500`, `ERR ...`,
    `e.message`), which the technical switch exists to keep one click deeper.
"""
import re

import qc as F

AREA = "hub"
TITLE = "the hub's controls say what happened, in words"


def run(t):
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")
    rgb = (F.HUB / "web" / "rgb.html").read_text(encoding="utf-8", errors="replace")

    # ---- a flash that stops answering says so --------------------------
    fw = hub[hub.find("function fwWatch("):]
    fw = fw[:fw.find("\nfunction ", 1)]
    t.ok("catch(e){ return; }" not in fw and "catch(e){return;}" not in fw,
         "a failed poll during a reflash is not swallowed")
    t.contains(fw, "stopped answering",
               "the bar says the hub went away instead of freezing")
    t.ok(re.search(r"catch\s*\(e\)\s*\{[^}]*quiet", fw, re.S),
         "and a failed poll still counts towards the stall",
         "the counter froze, so the stall line under it never ran")

    # ---- a refused change does not close as if it saved ----------------
    cs = hub[hub.find("async function setComplaintStatus("):]
    cs = cs[:cs.find("\n}") + 2]
    t.ok("r.ok" in cs, "the report status checks the answer before closing")
    t.ok("alert('Failed: '" not in cs and "e.message" not in cs,
         "and says it in the page, not in a browser box with programmer text",
         "a blocking alert carrying an exception is the opposite of plain words")
    t.contains(cs, "log in first",
               "a refusal names the one thing that would fix it")

    # ---- the report box says its own failures --------------------------
    t.contains(hub, 'id="reportSaid"',
               "the report box has a line of its own")
    sub = hub[hub.find("async function submitReport("):]
    sub = sub[:sub.find("\nfunction ", 1)]
    t.contains(sub, "reportSaid",
               "and a failed send writes there, where the person is looking")

    # ---- the light tool keeps the last value of a drag -----------------
    cmd = rgb[rgb.find("async function cmd(c,throttled,target="):]
    cmd = cmd[:cmd.find("\nfunction say(")]
    t.contains(cmd, "pending={c,target}",
               "a throttled command is remembered, not dropped")
    t.ok("setTimeout" in cmd and "if(last)cmd(last.c,0,last.target)" in cmd,
         "and sent when the window closes, so the strip ends where the slider is",
         "letting go inside the window left the strip on the previous colour")

    # ---- plain words on the surface, detail behind the switch ----------
    t.ok("t||('reply '+r.status),target" in cmd and "r.status===401||r.status===403" in cmd,
         "the sentence and the machine's own words are separate")
    said = rgb[rgb.find("function say(msg,tech,target="):]
    said = said[:said.find("\nfunction ", 1)]
    t.contains(said, "'tech mini'",
               "and the detail is put where the technical switch governs it")
