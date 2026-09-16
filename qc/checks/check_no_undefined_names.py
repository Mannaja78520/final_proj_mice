"""Every page loads and runs without throwing.

This is the bug class that hid in plain sight. `isNong` was used twice in the
module website and defined nowhere — a ReferenceError thrown in the middle of
the status handler, which silently killed the joint sliders AND everything
rendered after that line. The data was perfect the whole time; three checks
covered the area and every one of them passed, because they all tested *around*
the page instead of looking at it.

The first attempt at guarding this parsed the JavaScript looking for names with
no definition. That was the wrong instinct: a hand-rolled parser mis-handled
template literals, reported a dozen functions that plainly exist, and would
have trained everyone to ignore it. Do not reimplement a language.

Load each page in a real browser and fail on what it actually throws. No false
positives, and it catches the whole family — undefined names, null property
reads, bad JSON — at the moment they happen.

A CONNECTION THAT NEVER COMPLETED IS NOT A PAGE THAT THREW. Measured
2026-08-21: 6/6 pages clean in 18 s run alone, 4/6 in 62 s inside a full gate,
the two failures both `reject:Failed~to~fetch`. That is the hub refusing a
connection while the machine is busy, and it says nothing about undefined
names, which is the only thing this check exists to find. It cost three gates
in one day, and each red gate sends the next half hour into code that was never
wrong.

So an error is now classified before it is judged. A transport failure (failed
to fetch, a network error, a page that never loaded at all) gets the page ONE
reload, and if it still cannot be reached the page is reported as *not proven*
rather than as broken. A throw from the page's own code is never retried and
never softened.

Three probe pages keep both halves honest, because they make the two failures
happen on purpose in a real browser: `busy probe` fetches a dead port on every
attempt and must come back *busy*, `busy once` does it only on the first
attempt and must be rescued by the reload, and `throw probe` calls a name that
does not exist and must still be reported as a throw.
"""
import browser
import fake_serial
import qc as F

AREA = "ui"
TITLE = "every page loads and runs without throwing"
SLOW = True

# Each page, and a function its script must define at the very least.
#
# THE SENTINEL IS NOT DECORATION. A SYNTAX error kills the whole script before
# a single line runs - and it happens during PARSE, before the iframe's `load`
# event, so the error listener below is attached too late to ever see it. On
# 2026-08-21 hub.html carried `'PC\'s USB ports'` (an escaped BACKSLASH, so
# the string ended early), every global on the page vanished, and this check
# reported the page clean. check_advanced caught it instead, by wanting a
# function that was no longer there.
#
# So each page also names something its script must define. Missing means the
# script did not finish, whatever the error listener saw.
#
# The fourth field is a KICK: a failure the driver causes on purpose, to prove
# the busy/threw split works in the browser rather than only in a comment.
PAGES = [
    # hub's sentinel is openReport, not only showTab: openReport is called
    # from an onclick, so no load-time error ever fires for it - and on
    # 2026-08-25 a duplicate-closeReport cleanup deleted it while the page
    # still loaded clean. The 🐛 button died with nobody noticing.
    ("hub", "/", "openReport", ""),
    ("module site over USB", "/mod?dev=usb%3ACOM99", "connectWs", ""),
    ("nong studio", "/studio/", "moduleDev", ""),
    ("help", "/help", "", ""),              # a page with no script of its own
    ("rgb", "/rgb.html", "manualColor", ""),
    # The probes drive /help because it is the cheapest page here: this check
    # is the one that suffers under load, so it must not add much.
    ("busy probe", "/help", "", "busy"),
    ("busy once", "/help", "", "busy1"),
    ("throw probe", "/help", "", "throw"),
]
REAL = [p for p in PAGES if not p[3]]

PAGE = """
<style>html,body{margin:0}iframe{width:1200px;height:820px;border:0;display:block}</style>
<div id="frames"></div>
<script>
// Errors are collected per page. window.onerror inside a same-origin iframe
// reports the iframe's own throws, which is exactly what we want: a page that
// looks fine but threw halfway through building itself.
var PAGES = __PAGES__;
var SETTLE = 7000;
var errs = {}, loaded = {}, tries = {}, frames = [];

// A fetch that never completed is the machine, not the page. Kept narrow on
// purpose: anything not named here counts as the page's own fault.
function isBusy(m){
  return /failed to fetch|networkerror|load failed|net::|ERR_|aborted|abort/i.test(m);
}

function verdict(i){
  if (!loaded[i]) return 'busy:the page never loaded';
  var real = errs[i].filter(function(m){ return !isBusy(m); });
  if (real.length) return 'threw:' + real[0];
  if (errs[i].length) return 'busy:' + errs[i][0];
  return 'clean';
}

function attach(i){
  var f = frames[i], p = PAGES[i];
  loaded[i] = true;
  try{
    f.contentWindow.addEventListener('error', function(e){
      errs[i].push(String((e && e.message) || 'error').slice(0, 70));
    });
    f.contentWindow.addEventListener('unhandledrejection', function(e){
      var r = e && e.reason;
      errs[i].push('reject:' + String((r && r.message) || r).slice(0, 60));
    });
  }catch(e){ errs[i].push('cross-origin'); }
  // Did the script finish? A parse error leaves the page looking loaded and
  // completely empty of its own functions.
  try{
    if (p[2] && typeof f.contentWindow[p[2]] !== 'function')
      errs[i].push('script never ran: ' + p[2] + ' is missing');
  }catch(e){ errs[i].push('cross-origin'); }
  // The probes. setTimeout with a STRING runs in the iframe's own scope, so
  // the failure belongs to the page being watched, not to this driver.
  var kick = p[3];
  try{
    if (kick === 'throw')
      f.contentWindow.setTimeout('qcNoSuchNameXYZ()', 0);
    if (kick === 'busy' || (kick === 'busy1' && tries[i] === 1))
      f.contentWindow.setTimeout('fetch("http://127.0.0.1:1/qc-dead")', 0);
  }catch(e){ errs[i].push('probe failed: ' + e); }
}

function load(i){
  tries[i] = (tries[i] || 0) + 1;
  errs[i] = [];
  loaded[i] = false;
  var f = frames[i];
  f.onload = function(){ attach(i); };
  f.src = PAGES[i][1] + (tries[i] > 1 ? (PAGES[i][1].indexOf('?') < 0 ? '?' : '&')
                                        + 'qcretry=' + tries[i] : '');
}

PAGES.forEach(function(p, i){
  var f = document.createElement('iframe');
  frames[i] = f;
  document.getElementById('frames').appendChild(f);
  load(i);
});

// One reload for anything that could not be reached, and only for that.
setTimeout(function(){
  PAGES.forEach(function(p, i){
    if (verdict(i).indexOf('busy:') === 0) load(i);
  });
  setTimeout(function(){
    var out = [], n = [];
    PAGES.forEach(function(p, i){
      var key = p[0].replace(/ /g, '~');
      out.push(key + '=' + verdict(i).replace(/[^A-Za-z0-9:._-]/g, '~'));
      n.push(key + '=' + (tries[i] || 0));
    });
    qcMark("PAGES " + out.join(" "));
    qcMark("TRIES " + n.join(" "));
    qcMark("done");
  }, SETTLE);
}, SETTLE);
</script>
"""


def _kv(marks, head):
    """The last `head ...` mark, as a dict."""
    got = [m for m in marks if m.startswith(head + " ")]
    if not got:
        return {}
    return dict(kv.split("=", 1)
                for kv in got[-1][len(head) + 1:].split(" ") if "=" in kv)


def run(t):
    if not browser.available():
        t.ok(False, "headless Edge is available for browser checks")
        return
    fake_serial.reset()
    base, main = F.start_hub()
    js_pages = "[" + ",".join('["%s","%s","%s","%s"]' % (n, u, g, k)
                              for n, u, g, k in PAGES) + "]"
    browser.raw_page(PAGE.replace("__PAGES__", js_pages), base, seconds=40)

    marks = fake_serial.qc_marks
    got = _kv(marks, "PAGES")
    if not t.ok(got, "the pages reported back",
                "nothing ran: %r" % (marks[-3:],)):
        return
    tried = _kv(marks, "TRIES")

    proven = 0
    for name, _u, _g, kick in REAL:
        key = name.replace(" ", "~")
        res = got.get(key)
        if res is None:
            t.ok(False, "%s reported" % name, "no result for this page")
            continue
        if res.startswith("busy:"):
            # NOT a failure: the fetch never completed, so nothing was learned
            # about this page either way. Said out loud so a green run cannot
            # quietly mean nothing was tested.
            t.ok(True, "%s: NOT PROVEN — the machine was too busy (%s, %s tries)"
                 % (name, res, tried.get(key, "?")))
            continue
        proven += 1
        t.ok(res == "clean",
             "%s runs without throwing" % name,
             "it threw: %s — a throw stops everything after it, which is how "
             "the joint sliders went missing with every other check green" % res)

    t.ok(proven, "at least one page was actually reached",
         "every page came back unreachable — the hub is not answering at all, "
         "which is the machine and not the code under test")

    # ---- the split itself, proven in the browser ------------------------
    busy = got.get("busy~probe", "")
    t.ok(busy.startswith("busy:"),
         "a page that cannot be reached twice is reported busy, not broken",
         "the busy probe fetched a dead port on both attempts and came back "
         "%r — a connection failure reported as a page fault is the red gate "
         "this check cost three times on 2026-08-21" % busy)

    once = got.get("busy~once", "")
    t.ok(once == "clean",
         "a one-off connection failure is retried, and the retry is what counts",
         "the probe failed its first fetch only, so the reload should have come "
         "back clean; got %r" % once)
    t.eq(tried.get("busy~once"), "2",
         "the unreachable page was loaded a second time")
    t.eq(tried.get("throw~probe"), "1",
         "a page that threw is judged on its first load, never retried away")

    threw = got.get("throw~probe", "")
    t.ok(threw.startswith("threw:") and "qcNoSuchNameXYZ" in threw,
         "a real undefined name is still reported as a throw",
         "the throw probe called a name that does not exist and came back %r — "
         "if a real ReferenceError can be classified as busy, this check stops "
         "finding the bug it was written for" % threw)
