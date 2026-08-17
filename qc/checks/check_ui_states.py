"""Every data region tells the truth, including when it cannot reach anything.

A control panel that goes blank the moment the network hiccups is a broken
panel however good it looks — and one that keeps showing modules as if they
were still there is worse, because it is confidently wrong. This is the mice
hub: the page you use to find robots.

So the failing case is driven for real. The hub page is loaded in an iframe,
the scan endpoint is then made to fail, and the check asserts the page:

  * keeps the modules it last actually found, rather than blanking,
  * marks them plainly as old instead of presenting them as live,
  * offers the one control that fixes it (retry),
  * and announces the change to a screen reader.

Also enforces the shared design contract across ALL the web apps, because four
pages that drift apart stop looking like one product: every colour a component
uses must come from a token, the focus ring must exist, and motion must respect
the reader's preference.
"""
import re

import browser
import fake_serial
import qc as F

AREA = "ui"
TITLE = "data regions degrade honestly, and every app shares one design system"
SLOW = True

APPS = [
    ("hub", "main_python/web/hub.html"),
    ("help", "main_python/web/help.html"),
    ("studio", "nong/main_python_set_nong/web/style.css"),
    ("module site", "firmware/src/web/WebUI.h"),
]

# Colours that ARE tokens. A literal copy is the bug the token contract exists
# to prevent: change the accent once and every hardcoded copy stays wrong.
TOKEN_LITERALS = ["#10141a", "#1a212b", "#2a3442", "#dce3ec", "#8b98a9",
                  "#4da3ff", "#3ecf8e", "#ffb454", "#ff6b6b", "#243040"]

PAGE = """
<style>html,body{margin:0}#f{width:1100px;height:900px;border:0}</style>
<iframe id="f" src="/"></iframe>
<script>
function done(s){ qcMark("UI " + s); qcMark("done"); }
setTimeout(function(){
  try{
    var w = document.getElementById('f').contentWindow;
    var d = w.document;
    var out = [];
    // it found something first, so there IS a last-good list to preserve
    out.push("rowsbefore=" + d.querySelectorAll('#mods .row, #mods > div').length);

    // now break the hub the way a dropped network breaks it
    w.fetch = function(u){
      if (String(u).indexOf('/api/scan') === 0) return Promise.reject(new Error('offline'));
      return Promise.resolve({json:function(){return Promise.resolve({});},
                              text:function(){return Promise.resolve("");}});
    };
    w.scan(true);
    setTimeout(function(){
      var mods = d.getElementById('mods');
      var html = mods ? mods.innerHTML : '';
      out.push("blank=" + (html.trim().length < 20 ? "yes" : "no"));
      out.push("retry=" + (/Try again/i.test(html) ? "yes" : "no"));
      out.push("stale=" + (d.querySelector('#mods .stale') ? "yes" : "no"));
      out.push("alert=" + (d.querySelector('#mods [role=alert]') ? "yes" : "no"));
      out.push("live=" + (mods && mods.getAttribute('aria-live') ? "yes" : "no"));
      done(out.join(" "));
    }, 2500);
  } catch (e) { done("ERR=" + String(e).slice(0,60)); }
}, 6000);
</script>
"""


def _nocomment(src, kind):
    """Strip comments before asserting on code.

    Assertions kept passing against the very sabotage they were written for,
    because the WORD they looked for was sitting in the explanatory comment
    right above the code. A comment is not behaviour.
    """
    nl = chr(10)
    if kind == "py":
        no_doc = re.sub(r'"""(?:.|' + nl + r')*?"""', "", src)
        return re.sub(r"#[^" + nl + r"]*", "", no_doc)
    block = re.sub(r"/\*(?:.|" + nl + r")*?\*/", "", src)
    if kind == "css":
        return block
    return re.sub(r"//[^" + nl + r"]*", "", block)


def run(t):
    # ---- no per-command spin on the cable -------------------------------
    # A wait here is paid on EVERY command, and worst exactly when the board is
    # chatty — which is normal now that every module hosts an access point. On
    # live pose streaming (~30 commands a second) it was most of the latency
    # and the arm visibly lagged the sliders. The blank-line reply marker makes
    # the wait unnecessary, so there must not be one.
    hub_py = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    i = hub_py.find("def _drain_to_line_boundary(")
    if t.ok(i >= 0, "the pre-command drain exists"):
        j = hub_py.find(chr(10) + "def ", i + 1)     # up to the next top-level def
        body = _nocomment(hub_py[i:j if j > 0 else len(hub_py)], "py")
        t.ok("while" not in body and "sleep" not in body,
             "and it never waits — clearing the buffer is O(1)",
             "a spin here is paid on every command and shows up as servo lag")
        t.contains(body, "reset_input_buffer", "it just clears what is pending")

    # ---- the 3D canvas can never cover the settings panel ---------------
    css = (F.STUDIO / "web/style.css").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"#side\{.*?\}", css, re.S)
    if t.ok(m, "the side panel has a rule"):
        body = _nocomment(m.group(0), "css")
        t.contains(body, "flex:0 0",
                   "the panel is a fixed track, so content cannot widen it")
        t.contains(body, "min-width:0",
                   "and wide content scrolls inside it instead of pushing the layout")
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    code = _nocomment(app, "js")
    # Assert on the WIRING, not just the word: `if (false) {` around it leaves
    # the name in the file while switching the behaviour off entirely.
    t.contains(code, "window.ResizeObserver",
               "the canvas follows the viewport's real size, not just window resizes")
    t.contains(code, ".observe(viewport)",
               "and it is actually watching the viewport element")

    # ---- coming back to the page must not teleport the show -------------
    # A hidden tab has its timers throttled to about once a minute. Without a
    # clamp, returning after 30s handed playTick a dt of 30000: the play head
    # jumped the whole show in one tick and every joint was re-sent at once,
    # which hung the page on return. Nothing was being sent while hidden, so
    # the robot did not advance either — clamping is the correct answer, not
    # only the safe one.
    i = code.find("function playTick(")
    if t.ok(i >= 0, "the show clock exists"):
        body = code[i:i + 700]
        t.contains(body, "Math.min",
                   "one tick can never advance the show by an unbounded jump")
        t.contains(body, "MAX_TICK_MS", "with the limit named, not a magic number")
    m = re.search(r"MAX_TICK_MS\s*=\s*(\d+)", code)
    if t.ok(m, "the limit is defined"):
        t.ok(16 <= int(m.group(1)) <= 500,
             "and is a frame-sized step (%sms)" % m.group(1),
             "too large and the jump comes back; too small and playback crawls")

    # ---- and the two playback paths are told apart ----------------------
    idx = (F.STUDIO / "web/index.html").read_text(encoding="utf-8", errors="replace")
    t.contains(idx, "keeps going with this page closed",
               "the UI says which Play survives closing the page")

    # ---- leaving the page hands the show to the robot -------------------
    # The browser clock cannot be made reliable in the background: a hidden tab
    # has rAF stopped and timers throttled to about once a minute. Observed:
    # the sequence ran at the wrong speed, or stopped and sat still. Clamping
    # the step stops the teleport but makes a hidden tab crawl instead — the
    # only real answer is to stop being the clock and let the MODULE play it.
    i = code.find("async function handOffToRobot(")
    if t.ok(i >= 0, "leaving the page hands the show to the robot"):
        body = code[i:i + 900]
        t.contains(body, "MOVE ", "by telling the module to play the sequence")
        t.contains(body, "sdUpload", "after sending it the sequence")
        t.contains(body, "playing = false",
                   "and the browser stops trying to be the clock")
        t.ok("haveUsb" in body and "haveWifi" in body,
             "only when there is actually a robot connected",
             "with no robot it would silently stop playing instead")
    # Assert the WIRING: a listener that exists but is switched off behind
    # `if (false)` still contains the word "visibilitychange".
    # ---- only ONE thing may drive the servos at a time ------------------
    # The module keeps a sequence and plays it on its own clock, which is what
    # lets a show survive the page closing. But it also means the module can
    # still be running when you come back — and if the preview then streams
    # poses too, BOTH drive the same servos and the arm fights itself. Worse,
    # Stop here only stopped the browser, so the module carried on moving.
    # Reported from the bench: "when I stop in Nong Studio the servo still
    # moves by the esp32 sequence".
    i = code.find("function stopRobotSequence(")
    if t.ok(i >= 0, "there is a way to stop the module's own sequence"):
        t.contains(code[i:i + 400], "MOVE STOP",
                   "which tells the module to stop playing")
    j = code.find("function togglePlay(")
    if t.ok(j >= 0, "the play button exists"):
        body = code[j:j + 2200]
        t.contains(body, "stopRobotSequence()",
                   "and taking control here always stops the module first",
                   )
        # it must run on BOTH edges — pressing play and pressing stop
        k = body.find("stopRobotSequence()")
        after = body[k:k + 200]
        t.contains(after, "if (!playing)",
                   "before the play/pause branch, so stopping stops the module too",
                   )

    t.contains(code, "visibilitychange",
               "triggered by the page going away, not by a timer")
    # Assert the LISTENER, not one spelling of it: this used to match the exact
    # text `document.hidden) handOffToRobot()`, so adding an early return to the
    # same branch failed a check about behaviour that had not changed.
    vis = code[code.find('addEventListener("visibilitychange"'):]
    vis = vis[:vis.find("\n});")]
    t.contains(vis, "document.hidden", "and the hidden page really is what triggers it")
    t.contains(vis, "handOffToRobot()", "which is when the module is given the show")
    # ...except when the HUB is the clock, because then nothing needs rescuing:
    # the hub is a native process and this page going away does not touch it.
    # Handing the show to the module as well would be two clocks again.
    # (check_hub_clock.py owns that path.)
    hand = code[code.find("async function handOffToRobot"):]
    hand = hand[:hand.find("\n}")]
    t.contains(hand, "hubDriven",
               "and it stands down while the hub is already playing")

    # ---- the shared design contract, across every app -------------------
    for name, rel in APPS:
        src = (F.CODE / rel).read_text(encoding="utf-8", errors="replace")
        m = re.search(r":root\s*\{.*?\}", src, re.S)
        if not t.ok(m, "%s declares design tokens" % name):
            continue
        root, body = m.group(0), src[m.end():]
        for tok in ("--on-acc", "--sunk", "--r-sm", "--sp-2"):
            t.contains(root, tok, "%s has the %s token" % (name, tok))
        stray = [lit for lit in TOKEN_LITERALS
                 if lit in body.lower() or lit.upper() in body]
        t.ok(not stray,
             "%s uses tokens, not copies of them" % name,
             "hardcoded %s — change the accent and these stay wrong" % stray)
        t.contains(src, "focus-visible",
                   "%s keeps a visible focus ring" % name)
        t.contains(src, "prefers-reduced-motion",
                   "%s respects reduced motion" % name)

    # ---- and the hub really degrades honestly ---------------------------
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    browser.raw_page(PAGE, base, seconds=22)

    marks = [m for m in fake_serial.qc_marks if m.startswith("UI ")]
    if not t.ok(marks, "the hub page reported back",
                "the page never ran: %r" % (fake_serial.qc_marks[-3:],)):
        return
    got = dict(kv.split("=", 1) for kv in marks[-1][3:].split(" ") if "=" in kv)
    if "ERR" in got:
        t.ok(False, "the page ran without throwing", got["ERR"])
        return

    t.ok(got.get("blank") == "no",
         "a failed scan does NOT blank the module list",
         "the panel went empty the moment the network dropped")
    t.eq(got.get("retry"), "yes",
         "it offers the one control that fixes it")
    t.ok(got.get("stale") == "yes",
         "and marks the modules it is still showing as old",
         "old modules were presented as if they were still there")
    t.eq(got.get("alert"), "yes", "the failure is announced, not just coloured")
    t.eq(got.get("live"), "yes", "the region is a live region for screen readers")
