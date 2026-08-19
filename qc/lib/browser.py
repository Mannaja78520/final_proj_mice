"""Drive the real web app in headless Edge, for checks that must prove what
the BROWSER does (not what a python copy of the logic would do).

Everything here is a lesson that cost time to learn — read before changing:

* Edge's launcher hands the URL to a child process and exits. A bare Popen
  returns with nothing loaded, and subprocess pipes never close. Start-Process
  is the only reliable launcher.
* A user-data-dir is used by ONE Edge at a time. Reuse a profile that a
  leftover instance still holds and the new URL is silently swallowed — the
  page never loads and nothing says why. Always a fresh profile per run, and
  always kill the tree afterwards (they are tagged so QC only kills its own).
* `--virtual-time-budget` advances time in huge jumps, so an animation loop
  steps straight over whole segments. Anything that measures playback timing
  must run in REAL time.
* `--dump-dom` never completes while the page keeps issuing fetches, so a page
  in live/monitor mode cannot be read that way. Such checks report through the
  fake module instead (see marker()).
* `alert()` blocks a headless browser forever. The driver stubs it.
"""
import os
import subprocess
import time
from pathlib import Path

import tempfile

QC = Path(__file__).resolve().parent.parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
# Marks our processes so we never kill the user's own browser — and carries
# this RUN's process id, so two QC runs (two staging trees, verified at the
# same time) cannot kill each other's browsers. kill() matches on the whole
# tag, so a second run is invisible to the first.
TAG = "MICEQCBROWSER%d" % os.getpid()
# Browser profiles live in the system temp dir, NOT the repo: Edge keeps file
# locks for a while after it is killed, so a profile written into qc/ survives
# the cleanup and litters the project. Scratch belongs outside the source tree.
SCRATCH = Path(tempfile.gettempdir()) / "mice_qc"


def available():
    return Path(EDGE).is_file()


# The driver stub every page gets: silence modal dialogs, and give the check a
# way to report back over the module wire (which the fake records).
PRELUDE = """
<script>
window.alert=function(){}; window.confirm=function(){return true;};
// Reporting a mark, for BOTH preludes. One copy: A0-11 hardened the raw page's
// version and left this one bare, and the check that kept failing under load
// was the one using the bare copy.
//
// A mark can genuinely fail: fake_serial refuses two writers at once by design
// (two commands on the wire at once), and under load that happens. A dropped
// mark fails the check for a reason that has nothing to do with the code under
// test, so it retries. A mark that never lands after all the tries still fails
// the check, which is what should happen.
window.qcMark=function(m, tries){
  tries = tries || 0;
  return fetch("/api/usb/cmd?port=COM99&id=0&c=" +
               encodeURIComponent("MOVE QCMARK " + m))
    .then(function(r){ if (!r || !r.ok) throw new Error("mark refused"); })
    .catch(function(){
      if (tries >= 4) return;
      return new Promise(function(go){ setTimeout(go, 150); })
        .then(function(){ return window.qcMark(m, tries + 1); });
    });
};
window.qcFail=function(e){ qcMark("ERROR-" + String(e && e.message || e)
  .replace(/[^A-Za-z0-9]/g,"_").slice(0,60)); };
// Wait for something to BE TRUE, not for a number of milliseconds. A fixed
// sleep is a bet on how fast the machine is today: under load the page has not
// finished, the driver measures an empty list, and the check reports a bug
// that does not exist. Returns true if the condition came good, false if the
// deadline passed, so the caller can say what it was waiting for and a real
// failure still fails.
window.qcWaitFor = function(cond, ms, step){
  ms = ms || 8000; step = step || 100;
  return new Promise(function(done){
    var until = Date.now() + ms;
    (function poll(){
      var ok = false;
      try{ ok = !!cond(); }catch(e){ ok = false; }
      if (ok) return done(true);
      if (Date.now() > until) return done(false);
      setTimeout(poll, step);
    })();
  });
};
</script>
"""


def _quiet_start():
    """Begin a browser run from a known-silent state.

    Every check shares ONE list of marks (fake_serial.qc_marks) and every hub a
    check starts stays alive for the rest of the process — start_hub runs it on
    a daemon thread and nothing ever stops it. So a page from the PREVIOUS
    check, killed a moment ago but with a request already in flight, can still
    be recorded into THIS check's marks. Its stray "done" then ends this
    check's wait before the real page has said anything, and the check fails
    with "nothing reported" while the code it tests is fine.

    That is not hypothetical: it is exactly what a stray measurement script did
    to check_responsive on 2026-08-18, and it explains why a different browser
    check failed on each full run and every one of them passed alone.

    So: kill anything left over, let the last request land, and only then clear
    the marks. Cheap, and it makes each browser check independent of the one
    before it.
    """
    import fake_serial
    kill()
    _wait_until_gone()
    del fake_serial.qc_marks[:]


def _running():
    """How many of OUR browsers are still alive (never the user's own)."""
    r = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "@(Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                        "Where-Object { $_.CommandLine -like '*%s*' }).Count" % TAG],
                       capture_output=True, text=True, timeout=60)
    try:
        return int((r.stdout or "0").strip() or 0)
    except ValueError:
        return 0


def _wait_until_gone(timeout=20):
    """Wait for the last browser to actually die before starting another.

    kill() sends taskkill and returns; the processes take a moment. Starting
    the next check while several are still shutting down is how a page ends up
    launching slowly, missing its window and reporting nothing — the failure
    that has hit five different browser checks, each of which passed when run
    on its own.
    """
    end = time.time() + timeout
    while time.time() < end:
        if _running() == 0:
            return True
        time.sleep(0.3)
    return False


def _login_js():
    """A script that logs the browser in before anything else runs.

    Synchronous on purpose. An async login is a race: the driver script runs on
    load and fires its first fetch immediately, and if the cookie has not landed
    yet that call comes back 401 and the check fails for a reason that is not
    the code under test. This is a test harness talking to a hub on loopback, so
    the one blocking request costs nothing and removes the race entirely.
    """
    import qc as _F
    return ("""
<script>
(function(){
  try{
    var x = new XMLHttpRequest();
    x.open("POST", "/api/login", false);          // false = synchronous
    x.setRequestHeader("Content-Type", "application/json");
    x.send(JSON.stringify({password: "%s"}));
  }catch(e){ /* the gate check drives a logged-OUT page on purpose */ }
})();
</script>
""" % _F.HUB_PASSWORD)


def _tag():
    """A suffix nothing else can be using.

    Every temporary file and browser profile carries it. Before the checks ran
    in parallel they did not have to: one process, one driver page, one profile
    at a time. With a pool, two workers wrote `_qcdriver.html` into the SAME
    studio folder and each loaded the other's test - which does not fail, it
    passes the wrong test. The millisecond timestamp the profiles used was not
    enough either: workers start together, and two of them landed in the same
    millisecond. The pid is what actually differs.
    """
    return "%d_%d" % (os.getpid(), int(time.time() * 1000) % 100000)


def page(driver_js, query="", seconds=20, studio_web=None):
    """Serve the real Studio index.html + a driver script, load it, wait, kill.

    The temp page lives in the studio web folder so every relative asset
    resolves, and is always removed again.
    """
    _quiet_start()
    web = studio_web or (QC.parent / "nong" / "main_python_set_nong" / "web")
    src = (web / "index.html").read_text(encoding="utf-8")
    drv = web / ("_qcdriver_%s.html" % _tag())
    # Callers name the driver page in their URL as `_qcdriver.html`, because
    # that is what it is CALLED, not where it happens to live this run. The
    # real file carries a per-process suffix so two workers cannot load each
    # other's test, and the URL is corrected here rather than in ten checks.
    query = query.replace("_qcdriver.html", drv.name)
    drv.write_text(src + _login_js() + PRELUDE + "<script>\n" + driver_js + "\n</script>",
                   encoding="utf-8")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # parenthesised: "/" and "%" share precedence, so without them python
    # tries Path % int
    prof = str(SCRATCH / ("profile_%s" % _tag()))
    import fake_serial
    _before = len(fake_serial.qc_marks)      # before the browser can say anything
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Start-Process -FilePath '%s' -ArgumentList "
                        "'--headless=new','--disable-gpu','--no-sandbox',"
                        "'--no-first-run','--disable-extensions','--%s',"
                        "'--user-data-dir=%s','%s' -NoNewWindow"
                        % (EDGE, TAG, prof, query)], timeout=60)
        _wait_for_done(seconds, start=_before)
    finally:
        drv.unlink(missing_ok=True)
        kill()
        _rmtree(prof)


def _wait_for_done(seconds, grace=150, start=None):
    """Wait for the driver to say "done" — do not just sleep a fixed time.

    A fixed sleep is a race: when Edge starts slowly (several browser checks in
    one run, a loaded machine) the page is killed mid-way and the check fails
    with "nothing reported", even though the code under test is fine. An
    intermittently failing suite is one people learn to ignore, which is worse
    than no suite.

    So: return the moment the driver reports "done", and be patient beyond the
    nominal time if it has not. Healthy runs get FASTER, slow ones stop
    flaking.

    The grace is deliberately LARGE. It costs nothing when things are well —
    the wait ends the instant "done" arrives — and it is the whole defence
    when they are not. It was 25s, which was still a bet on machine speed: with
    every page now logging in first, three separate full runs failed on three
    different browser checks, each passing alone. A check that genuinely hangs
    still fails, just later.
    """
    import fake_serial
    # The caller captures this BEFORE launching the browser. Capturing it here
    # meant a page that reported before this line ran was invisible: its marks
    # were already in the list, so the wait sat until the deadline and the
    # check reported nothing.
    if start is None:
        start = len(fake_serial.qc_marks)
    deadline = time.time() + seconds + grace
    while time.time() < deadline:
        if any(m == "done" for m in fake_serial.qc_marks[start:]):
            time.sleep(0.4)          # let the last report land
            return True
        time.sleep(0.4)
    return False


def raw_page(html, base, seconds=20, name=None):
    """Serve an arbitrary page from the studio web folder and load it.

    Used by checks that drive OTHER pages (in iframes) rather than the studio
    app itself. Media queries inside an iframe respond to the IFRAME's width,
    so this is a real way to test phone layouts without resizing the browser.
    """
    _quiet_start()
    web = QC.parent / "nong" / "main_python_set_nong" / "web"
    name = name or ("_qcraw_%s.html" % _tag())
    f = web / name
    # NOT the studio PRELUDE: that reports via rawCmd(), which lives in app.js
    # and a raw page never loads it. Talk to the fake module directly instead.
    raw_prelude = """
<script>
window.alert=function(){}; window.confirm=function(){return true;};
// A report that does not arrive fails the check for a reason that has nothing
// to do with the code under test. This used to be a bare .catch(){} — one
// dropped fetch and a measurement simply vanished, so the suite failed at
// random under load and passed when run alone. A suite that fails randomly is
// one people learn to ignore.
//
// So a mark RETRIES. The port behind it is a single fake serial line shared by
// every mark, and under load a request can be refused; four attempts spaced
// 150 ms apart cover that without hiding a real failure, because a mark that
// never lands after all four still fails the check.
window.qcMark=function(m, tries){
  tries = tries || 0;
  return fetch("/api/usb/cmd?port=COM99&id=0&c=" +
               encodeURIComponent("MOVE QCMARK " + m))
    .then(function(r){ if (!r || !r.ok) throw new Error("mark refused"); })
    .catch(function(){
      if (tries >= 4) return;                 // give up, and let the check fail
      return new Promise(function(go){ setTimeout(go, 150); })
        .then(function(){ return window.qcMark(m, tries + 1); });
    });
};
window.qcFail=function(e){ qcMark("ERROR-" + String(e && e.message || e)
  .replace(/[^A-Za-z0-9]/g,"_").slice(0,60)); };
// Wait for something to BE TRUE, not for a number of milliseconds. A fixed
// sleep is a bet on how fast the machine is today: under load the page has not
// finished, the driver measures an empty list, and the check reports a bug
// that does not exist. Returns true if the condition came good, false if the
// deadline passed, so the caller can say what it was waiting for and a real
// failure still fails.
window.qcWaitFor = function(cond, ms, step){
  ms = ms || 8000; step = step || 100;
  return new Promise(function(done){
    var until = Date.now() + ms;
    (function poll(){
      var ok = false;
      try{ ok = !!cond(); }catch(e){ ok = false; }
      if (ok) return done(true);
      if (Date.now() > until) return done(false);
      setTimeout(poll, step);
    })();
  });
};
</script>
"""
    f.write_text(_login_js() + raw_prelude + html, encoding="utf-8")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    prof = str(SCRATCH / ("profile_%s" % _tag()))
    import fake_serial
    _before = len(fake_serial.qc_marks)      # before the browser can say anything
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Start-Process -FilePath '%s' -ArgumentList "
                        "'--headless=new','--disable-gpu','--no-sandbox',"
                        "'--no-first-run','--disable-extensions','--%s',"
                        "'--user-data-dir=%s','%s/studio/%s' -NoNewWindow"
                        % (EDGE, TAG, prof, base, name)], timeout=60)
        # Wait for the page to SAY it is finished, exactly like page() does.
        # A fixed sleep is a race: with several browser checks in one run the
        # machine is loaded, Edge starts slowly, and the page gets killed
        # mid-measurement — the suite then fails on checks that pass fine on
        # their own. An intermittently failing suite is one people learn to
        # ignore, which is worse than no suite. A driver that never marks
        # "done" simply waits the full time as before.
        _wait_for_done(seconds, start=_before)
    finally:
        f.unlink(missing_ok=True)
        kill()
        _rmtree(prof)


def kill():
    """Kill only the Edge processes QC started (matched by our tag)."""
    subprocess.run(["powershell", "-NoProfile", "-Command",
                    "Get-CimInstance Win32_Process -Filter \"Name='msedge.exe'\" | "
                    "Where-Object { $_.CommandLine -like '*%s*' } | "
                    "ForEach-Object { taskkill /F /T /PID $_.ProcessId }" % TAG],
                   stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)


def _rmtree(p):
    """Edge still holds file locks for a moment after taskkill, so a single
    rmtree leaves a profile dir behind. Retry briefly, then give up quietly —
    sweep() clears any stragglers on the next run."""
    import shutil
    for _ in range(6):
        shutil.rmtree(p, ignore_errors=True)
        if not Path(p).exists():
            return
        time.sleep(0.4)


def sweep():
    """Delete scratch left by earlier runs (including any from older versions
    that still wrote into the repo)."""
    for p in list(SCRATCH.glob("profile_*")) + list(QC.glob("_profile_*")):
        _rmtree(str(p))
    for p in list(QC.glob("_boot_dom.html*")) + list(SCRATCH.glob("*.html*")):
        try:
            p.unlink()
        except OSError:
            pass


def marks(fake_serial):
    """The markers the page sent, in order (see qcMark in PRELUDE)."""
    return [m for m in fake_serial.qc_marks]
