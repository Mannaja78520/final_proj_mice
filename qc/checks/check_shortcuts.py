"""The keyboard shortcuts work, and none of them is folklore.

A shortcut nobody can discover is a feature for whoever wrote it. So the plan's
wording for this task is the requirement: *every one of them discoverable from
that list*. That is only true while ONE array feeds both the key handler and
the visible list - two lists drift, and the one that drifts is always the
documentation.

Four properties, each a way this quietly stops being worth having:

  * **the list is generated from the handler's own array.** Hard-code the rows
    and the day someone adds a fifth shortcut it works and is undocumented;
  * **a key is never stolen from someone typing.** `/` and `?` are ordinary
    characters in a module name, a WiFi password or the search box itself. A
    shortcut that eats them turns every text field into a trap. Escape is the
    deliberate exception, because leaving a field is what it is for;
  * **there is a way in that is not a keystroke.** Everybody who does not
    already know the shortcuts exist will never press `?`. Gemini Pro's answer
    on 2026-08-20, and the reason there is a button in the tab bar;
  * **the rows are buttons.** On a phone there is no keyboard at all, so the
    same list that documents the shortcuts is also how they are run. That was
    Pro's idea too, and it is the difference between a panel that is useless on
    a phone and a menu.

Driven in a real browser, because what is under test is what a key press does.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "hub"
TITLE = "the keyboard shortcuts work, and the list shows every one of them"
SLOW = True

PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("KB " + s); qcMark("done"); }
function key(d, w, k, target){
  var ev = new w.KeyboardEvent('keydown', {key:k, bubbles:true, cancelable:true});
  (target || d.body).dispatchEvent(ev);
}
setTimeout(function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = document.getElementById('f').contentDocument;
    if (!w.SHORTCUTS) return done("missing=SHORTCUTS");
    var out = [];
    out.push("n=" + w.SHORTCUTS.length);

    // ---- "?" opens the list, and the list has a row per shortcut ----
    key(d, w, '?');
    var modal = d.getElementById('keysModal');
    out.push("opened=" + (modal && !modal.hidden ? "yes" : "no"));
    var rows = d.querySelectorAll('#keysList .keyrow');
    out.push("rows=" + rows.length);
    out.push("buttons=" + [].slice.call(rows)
              .filter(function(r){ return r.tagName === 'BUTTON'; }).length);

    // ---- Escape closes it ------------------------------------------
    key(d, w, 'Escape');
    out.push("closed=" + (modal.hidden ? "yes" : "no"));

    // ---- "/" goes to the search box ---------------------------------
    key(d, w, '/');
    var find = d.getElementById('modFind');
    out.push("focused=" + (d.activeElement === find ? "yes" : "no"));

    // ---- and typing is NEVER hijacked -------------------------------
    // The box is focused now. A "/" here is a person typing a slash, not a
    // shortcut, and the handler must leave it alone.
    find.value = '';
    key(d, w, '/', find);
    key(d, w, '?', find);
    out.push("stolen=" + (modal.hidden ? "no" : "yes"));

    // ---- Escape in a field clears the filter and leaves it ----------
    find.value = 'nong';
    key(d, w, 'Escape', find);
    out.push("cleared=" + (find.value === '' ? "yes" : "no"));

    // ---- a tap runs the action, with the dialog out of the way ------
    key(d, w, '?');
    var slash = [].slice.call(d.querySelectorAll('#keysList .keyrow'))
                  .filter(function(r){ return /^\\s*\\//.test(r.textContent); })[0];
    if (!slash) { out.push("tap=norow"); return done(out.join(" ")); }
    slash.click();
    out.push("tapclosed=" + (modal.hidden ? "yes" : "no"));
    out.push("tapfocused=" + (d.activeElement === find ? "yes" : "no"));

    // ---- there is a way in that is not a keystroke ------------------
    var opener = d.getElementById('keysOpen');
    out.push("opener=" + (opener ? "yes" : "no"));
    if (opener){
      opener.click();
      out.push("openerworks=" + (!modal.hidden ? "yes" : "no"));
    }
    done(out.join(" "));
  }catch(e){ done("ERR=" + String(e).slice(0,70)); }
}, 4000);
</script>
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")

    # ---- ONE array, read by the handler and by the list --------------
    m = re.search(r"var SHORTCUTS = \[(.*?)\n\];", hub, re.S)
    if not t.ok(m, "there is one shortcut registry"):
        return
    entries = m.group(1)
    for need in ("key:", "show:", "what:", "run:"):
        t.contains(entries, need, "each entry carries %s" % need.strip(":"))
    fn = hub[hub.find("function toggleKeys("):]
    fn = fn[:fn.find("\nif ($('keysClose'))")]
    t.contains(fn, "SHORTCUTS.forEach",
               "the visible list is generated from that same array",
               )
    t.ok("keysList" in fn,
         "into the list the dialog shows",
         "a hard-coded list is undocumented the day somebody adds the fifth "
         "shortcut - and the documentation is always the half that drifts")

    # ---- driven for real ---------------------------------------------
    fake_serial.reset()
    base, _m = F.start_hub()
    browser.raw_page(PAGE, base, seconds=30)
    marks = [x for x in fake_serial.qc_marks if x.startswith("KB ")]
    if not t.ok(marks, "the page reported back", str(fake_serial.qc_marks[-3:])):
        return
    last = marks[-1][3:]
    if "ERR=" in last or "missing=" in last:
        t.ok(False, "the shortcuts ran without throwing", last)
        return
    got = dict(kv.split("=", 1) for kv in last.split(" ") if "=" in kv)

    t.eq(got.get("opened"), "yes", "? opens the shortcut list")
    t.eq(got.get("rows"), got.get("n"),
         "and the list has exactly one row per shortcut")
    t.eq(got.get("buttons"), got.get("n"),
         "every row is a BUTTON, so a phone with no keyboard can still use it")
    t.eq(got.get("closed"), "yes", "Escape closes it")
    t.eq(got.get("focused"), "yes", "/ jumps to the module search box")

    # The one that would be a daily irritation rather than a missing feature.
    t.eq(got.get("stolen"), "no",
         "typing / or ? INTO a text box is text, not a shortcut")
    t.eq(got.get("cleared"), "yes",
         "and Escape in the search box clears the filter")

    t.eq(got.get("tapclosed"), "yes",
         "tapping a row closes the dialog before acting")
    t.eq(got.get("tapfocused"), "yes",
         "and really runs it — focusing something behind a dialog is a tap "
         "that visibly does nothing")
    t.eq(got.get("opener"), "yes",
         "there is a way in that is not a keystroke")
    t.eq(got.get("openerworks"), "yes",
         "and it opens the same list",
         )

    # ---- and the way in has a NAME, not only a picture ------------------
    # It was the one control in the tab row with no word on it: a keyboard
    # icon and a `title`, which is a tooltip - and a tooltip does not exist on
    # a touch screen at all. An icon nobody can name is a control nobody
    # presses (2026-09-08, judging the new look at 1440 and 360).
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")
    i = hub.find('id="keysOpen"')
    btn = hub[i:hub.find("</button>", i)] if i > 0 else ""
    t.ok("Shortcuts" in btn,
         "the shortcuts tab carries its name, not just an icon",
         "a title attribute is a tooltip, and there is no hover on a phone")
