"""A failure in Studio reaches the eye, wherever the operator is looking.

Studio has four side tabs, and each tab's card carries its own status line. That
is right for routine chatter and wrong for a failure, for two reasons that were
both real in this file:

  * the card belongs to ONE tab. `USB disconnected` was written into the Robot
    card while the operator was posing, so nobody saw it;
  * the monitor loop rewrites `robotStat` on every poll - twice a second - so
    even a message somebody WAS looking at vanished before it could be read.
    The five-model panel found this second one; the first was the task.

So failures also go to one line under the tab strip, visible on every tab. What
is held here is the shape of that: it is written only by `notice()`, never by a
polling loop; a repeat of the same message does not reopen a dismissed notice,
because a warning that cannot be got rid of is one people learn to ignore; and
a DIFFERENT message always shows, dismissed or not, because that is something
new going wrong.

The per-card lines stay exactly as they were. A line that shouts about
everything is a line nobody reads.
"""
import re

import qc as F

AREA = "studio"
TITLE = "a failure in Studio is visible from whichever tab you are on"

STUDIO = "nong/main_python_set_nong/web"


def run(t):
    html = (F.CODE / STUDIO / "index.html").read_text(encoding="utf-8")
    js = (F.CODE / STUDIO / "app.js").read_text(encoding="utf-8")

    # ---- there is one, and it is outside every tab ------------------
    i = html.find('id="notice"')
    if not t.ok(i > 0, "Studio has a notice line"):
        return
    t.contains(html[i - 80:i + 300], "banner err",
               "using the design system's error banner, not a new style")
    t.contains(html[i - 80:i + 300], 'role="alert"',
               "announced at once, because it is a failure")
    t.contains(html[i:i + 400], "clearNotice",
               "and it can be dismissed")

    # It must not sit inside a tab's card, which is the whole bug: an element
    # with data-stab is hidden whenever that tab is not the one showing.
    before = html[:i]
    last_stab = before.rfind("data-stab=")
    last_close = before.rfind("</div>")
    t.ok(last_stab < last_close,
         "the notice is not inside a tab's card",
         "it would be hidden exactly when the operator is somewhere else, "
         "which is the bug it exists to fix")

    # ---- only notice() writes it ------------------------------------
    # ONE writer. The element is looked up once, inside notice(); anything else
    # touching it would be a second voice on the same line, which is how the
    # per-card lines ended up being clobbered by a polling loop in the first
    # place.
    seen = re.findall(r'\$\("noticeText"\)', js)
    t.eq(len(seen), 1, "exactly one place reaches for the notice text")
    fn = js[js.find("function notice("):js.find("function clearNotice(")]
    t.ok('$("noticeText")' in fn,
         "and that place is notice()",
         "a second writer is how the per-card lines ended up being clobbered "
         "by a polling loop")
    t.contains(fn, "t.textContent = text",
               "which sets it from the message it was given")

    # ---- a repeat does not reopen a dismissed notice ----------------
    # The GUARD, not the words. Asserting that "noticeSaid" and "box.hidden"
    # appear passed with the early return deleted - the assignment and the
    # unhide still mention both.
    import re as _re
    guard = _re.search(r"if \(text === noticeSaid && box\.hidden\)\s*return", fn)
    t.ok(guard,
         "a repeat of a dismissed message does not reopen the notice",
         "the monitor polls every second and says the same thing each time; "
         "without this the dismiss button does nothing anyone can see")
    t.ok(fn.find("noticeSaid = text") > (guard.end() if guard else 0),
         "and it remembers the message only after deciding to show it",
         "remembering first makes the guard compare the text with itself")

    # ---- failures really call it ------------------------------------
    # Driven off the source rather than a browser, because the interesting
    # moment is a USB cable being pulled, which QC cannot do.
    # EVERY one, not "at least twelve". A count passed while a message was
    # taken out, because nineteen others were still there - and the one taken
    # out was `USB disconnected`, which is exactly the kind nobody can afford
    # to miss.
    missed = []
    for m in re.finditer(r'\$\("(\w*[Ss]tat\w*)"\)\.textContent\s*=', js):
        end = js.find(";", m.start())
        stmt = js[m.start():end + 1]
        if not re.search(r"could not|cannot|failed|no reply|disconnected|"
                         r"connect to the robot first|owns this cable",
                         stmt, re.I):
            continue
        if "notice(" not in js[end:end + 140]:
            missed.append(stmt.strip().replace(chr(10), " ")[:70])
    t.eq(missed, [],
         "every failure message is also shown on the notice line")

    # ---- and routine polling is NOT --------------------------------
    # The monitor loop's normal line says what the robot is doing every second.
    # Sending that to the notice would make it a second status line, and the
    # dismiss button would be useless.
    mon = js[js.find("MONITOR ${s.name}"):]
    mon = mon[:mon.find("} catch")]
    t.ok("notice(" not in mon,
         "the monitor's routine status does NOT go to the notice",
         "a line that shouts about everything is a line nobody reads")
