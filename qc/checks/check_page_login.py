"""Tools work with nobody logged in; everything else asks first.

Asked 2026-09-09: *make our app except the TOOL and module can use with out
login, other thing need to be login same as face reconize, because i need to
use the tool some time with no login in site.* A tool has to be usable at a
venue with nobody signed in. Everything else shows a sign-in box instead of
its controls.

THE ONE THING TO UNDERSTAND BEFORE CHANGING ANY OF THIS

  This is NOT a lock, and must never be mistaken for one. The lock is
  `hub_auth.GATED`, which answers `401 log in first` to every route that moves
  a robot, writes a file, replaces firmware or takes a port - and
  `check_hub_auth` proves that. What is here decides only what a person SEES
  and can press. A card the data file forgets is a card a stranger can press
  and be refused by the hub; it is never a way in.

WHAT THIS HOLDS

  * the rule is DATA (`config/page_access.json`), read per request, so a
    designer changing which cards ask for a login edits one file and no code;
  * `/api/access` is OPEN. It has to be: a page draws itself before anybody
    has signed in, so gating it would put the sign-in box behind a sign-in box;
  * a BROKEN file gates NOTHING and says why. Failing the other way hides the
    whole hub behind a box that cannot be passed, because the file describing
    the box is the broken one;
  * the shared script reads the list from the hub rather than carrying its own
    copy - two lists disagree the first time one is edited;
  * and the words on the box come out of the file, put in with textContent, so
    a file a person edits is never markup.
"""
import json
import os
import tempfile

import browser
import fake_serial
import qc as F


AREA = "hub"
TITLE = "tools open with no login, everything else asks first"
SLOW = True

CFG = "config/page_access.json"

# Drive the real hub page in a real browser. Asserting on the FILES would only
# say the attributes are spelled right; what matters is what a person sees.
DRIVER = """
<style>html,body{margin:0}#f{width:1200px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function nap(ms){ return new Promise(function(r){ setTimeout(r, ms); }); }
setTimeout(async function(){
  var out = [];
  try{
    var d = document.getElementById('f').contentDocument;
    var off = d.getElementById('logoutBtn');

    // Start signed OUT. The browser profile is reused between runs and a
    // cookie ignores the port, so a session from an earlier run reaches this
    // hub and the whole check would measure the wrong half.
    if (off && !off.hidden){ off.click(); await nap(1200); }
    await nap(900);

    var flash = d.querySelector('[data-needs-login="flash"]');
    var tools = d.querySelector('[data-tab="tools"]');
    out.push("boxShown:" + (d.querySelector('.mg-gate') ? "yes" : "no"));
    out.push("flashAway:" + (flash && flash.classList.contains('mg-off') ? "yes" : "no"));
    out.push("toolsStay:" + (tools && !tools.classList.contains('mg-off') ? "yes" : "no"));
    // THE box for this card, not merely the first one on the page - the home
    // tab's card is gated too and comes first in the document.
    var box = d.querySelector('[data-gate-for="flash"]');
    out.push("boxSameTab:" + (box && box.getAttribute('data-tab') ===
                              flash.getAttribute('data-tab') ? "yes" : "no"));
    out.push("boxHasWay:" + (box && box.querySelector('button') ? "yes" : "no"));

    // ...now sign in, on this page, and the cards come back.
    d.getElementById('loginPass').value = "%s";
    d.getElementById('loginBtn').click();
    await nap(1800);
    out.push("boxGone:" + (d.querySelector('.mg-gate') ? "no" : "yes"));
    out.push("flashBack:" + (flash && !flash.classList.contains('mg-off') ? "yes" : "no"));

    // A card may already be hidden for its OWN reason. Gating and ungating it
    // must give that state back untouched - which is the whole reason the gate
    // uses a class instead of writing el.hidden. Driven on a card of our own,
    // because every real one on this page is legitimately revealed at login.
    var probe = d.createElement('div');
    probe.setAttribute('data-needs-login', 'lights');
    probe.hidden = true;
    d.body.appendChild(probe);
    // A second card of the SAME kind: the lights page has four, and four
    // identical sign-in boxes stacked up is noise, not an explanation.
    var twin = d.createElement('div');
    twin.setAttribute('data-needs-login', 'lights');
    d.body.appendChild(twin);

    var w = document.getElementById('f').contentWindow;
    w.miceGate.apply(false); await nap(400);
    out.push("probeGated:" + (probe.classList.contains('mg-off') ? "yes" : "no"));
    out.push("boxesForKind:" +
             d.querySelectorAll('[data-gate-for="lights"]').length);
    w.miceGate.apply(true); await nap(400);
    out.push("probeOwnState:" + (probe.hidden ? "kept" : "clobbered"));
    out.push("boxesCleared:" +
             d.querySelectorAll('[data-gate-for="lights"]').length);
    probe.remove(); twin.remove();

    qcMark(out.join(" ").replace(/ /g, "~"));
  }catch(e){ qcMark("ERR~" + String(e.message || e).replace(/ /g, "~")); }
  qcMark("done");
}, 1800);
</script>
"""


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "main_python"))
    import hub_auth                                          # noqa: E402

    # ---- the rule is data, and the hub reads it ------------------------
    raw = (F.CODE / CFG).read_text(encoding="utf-8")
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                          # noqa: E402
    cfg = json.loads(registry.strip_jsonc(raw))

    for key in ("openPages", "needLogin", "words"):
        t.ok(key in cfg, "%s says what is %s" % (CFG, key), sorted(cfg))
    for want in ("/app/", "/mod"):
        t.ok(want in cfg.get("openPages", []),
             "%s works with no login" % want,
             "a tool has to be usable on site with nobody signed in - that is "
             "the whole reason this file exists")

    # ---- and the hub hands it to a page, without a login ---------------
    t.ok("/api/access" in hub_auth.OPEN,
         "/api/access is open, and listed as open on purpose",
         "a page draws itself before anybody has signed in, so gating this "
         "would put the sign-in box behind a sign-in box")
    t.ok(not hub_auth.gated("/api/access", "GET"),
         "and the gate really lets it through")

    base, _main = F.start_hub()
    code, body = F.get(base + "/api/access")
    t.eq(code, 200, "the hub answers it with nobody logged in")
    got = json.loads(body)
    t.eq(got.get("openPages"), cfg["openPages"], "with the file's own list")
    t.eq(got.get("needLogin"), cfg["needLogin"], "and the cards that ask first")
    t.eq(got.get("words", {}).get("title"), cfg["words"]["title"],
         "and the words a designer wrote")

    # ---- a broken file fails OPEN, and says so -------------------------
    # Which way to fail is the whole decision here. Gating everything when the
    # file cannot be read locks the hub behind a box nobody can pass, and the
    # reason is invisible. Gating nothing costs a stranger the sight of a card
    # the hub will refuse them anyway.
    broken = os.path.join(tempfile.mkdtemp(prefix="qc_access_"), "bad.json")
    with open(broken, "w", encoding="utf-8") as fh:
        fh.write("{ this is not json")
    # Swapped on the RUNNING hub, which also proves the other half of the
    # promise: the file is read per request, so editing it needs no restart.
    os.environ["MICE_PAGE_ACCESS"] = broken
    try:
        code, body = F.get(base + "/api/access")
        t.eq(code, 200, "a broken rules file still answers, rather than a 500")
        bad = json.loads(body)
        t.eq(bad.get("needLogin"), [],
             "and gates nothing, so nobody is locked out by a typo")
        t.ok(bad.get("ok") is False and CFG in (bad.get("error") or ""),
             "while naming the file that needs fixing",
             "silence here means a designer edits the file, sees no change, "
             "and has nothing to read: %r" % bad.get("error"))
        t.ok(bad.get("words") == {} or "title" not in (bad.get("words") or {}),
             "and it does not invent words it could not read")
    finally:
        os.environ.pop("MICE_PAGE_ACCESS", None)

    code, body = F.get(base + "/api/access")
    t.eq(json.loads(body).get("needLogin"), cfg["needLogin"],
         "putting the file back needs no restart - it is read per request")

    # ---- one list, not two --------------------------------------------
    js = (F.CODE / "shared/web/mice.js").read_text(encoding="utf-8")
    t.contains(js, "window.miceGate", "the gate is in the shared script")
    t.contains(js, '"/api/access"',
               "and it asks the hub for the list rather than carrying a copy")
    t.contains(js, "data-needs-login",
               "a card opts in by naming itself, so the page stays readable")
    t.ok("innerHTML" not in js.split("miceGate")[-1],
         "the box is built with textContent, never innerHTML",
         "the words come out of a file a person edits, and a file a person "
         "edits is not markup")

    # ---- it fails open in the browser too ------------------------------
    t.contains(js, "needLogin: []",
               "and when the hub cannot be reached the page gates nothing")

    # ---- the box is a real component, in the shared stylesheet ---------
    css = (F.CODE / "shared/web/mice.css").read_text(encoding="utf-8")
    t.contains(css, ".mg-gate", "the sign-in box is one shared component")
    block = css[css.find(".mg-gate"):]
    block = block[:block.find("\n\n") if "\n\n" in block else len(block)]
    t.ok("#" not in block,
         "built from tokens, with no colour written into it",
         "a hardcoded colour is a copy that stays wrong when the accent "
         "changes: %r" % block[:200])
    t.ok("var(--" in block, "and it really uses the tokens")
    t.contains(css, ".mg-off{display:none",
               "and hiding is a class, not the hidden attribute")

    # ---- the lights page too, not only the hub -------------------------
    # It drives real hardware, it is not a tool under /app/, and it already
    # mounts miceLogin - so marking its controls is all it needs.
    # EVERY control card, not merely a couple of them. Counting *at least two*
    # was the first version of this, and unmarking one card left three - which
    # still passed. A count is not a rule.
    import re
    rgb = (F.CODE / "main_python/web/rgb.html").read_text(encoding="utf-8")
    cards = re.findall(r'<(?:div|details) class="card[^"]*"[^>]*>', rgb)
    open_cards = [c for c in cards
                  if "data-needs-login" not in c and "loginHere" not in c]
    t.ok(not open_cards,
         "every control card on the lights page asks first",
         "the lights turn real lamps on and off, and this page is not a tool "
         "under /app/ - so a card here that is not marked is offered to a "
         "stranger and refused only after they press it: %s" % open_cards)
    t.contains(rgb, "miceLogin.mount",
               "and carries a login of its own to answer with")

    # ---- and now what a person actually sees ---------------------------
    if not browser.available():
        t.give_up("headless Edge not found - run --quick")
    fake_serial.reset()
    browser.raw_page(DRIVER % F.HUB_PASSWORD, base, seconds=30)
    marks = [m.replace("~", " ") for m in fake_serial.qc_marks]
    line = next((m for m in marks if "boxShown:" in m), "")
    if not t.ok(line and "ERR" not in " ".join(marks),
                "the hub page ran and reported", marks or "(nothing)"):
        return
    saw = dict(p.split(":", 1) for p in line.split() if ":" in p)

    t.eq(saw.get("boxShown"), "yes",
         "signed out, a gated card is replaced by the sign-in box")
    t.eq(saw.get("flashAway"), "yes", "and the card itself is out of the way")
    t.eq(saw.get("toolsStay"), "yes",
         "while the Tools list stays, with nobody signed in")
    t.eq(saw.get("boxSameTab"), "yes",
         "the box stands on the card's own tab, not on every tab")
    t.eq(saw.get("boxHasWay"), "yes", "and it offers the way in, not just a no")
    t.eq(saw.get("boxGone"), "yes", "signing in on that page removes the box")
    t.eq(saw.get("flashBack"), "yes", "and gives the card back")
    t.eq(saw.get("probeGated"), "yes", "the gate really hides a marked card")
    t.eq(saw.get("boxesForKind"), "1",
         "two cards of one kind get ONE sign-in box between them")
    t.eq(saw.get("boxesCleared"), "0", "and signing in clears it")
    t.ok(saw.get("probeOwnState") == "kept",
         "a card hidden for its OWN reason is still hidden after signing in",
         "the gate hides with a class so it can give the element's own state "
         "back; writing el.hidden would have revealed the pairing card at "
         "login - got %r" % saw.get("probeOwnState"))
