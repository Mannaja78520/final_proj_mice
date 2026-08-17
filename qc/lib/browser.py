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
import subprocess
import time
from pathlib import Path

import tempfile

QC = Path(__file__).resolve().parent.parent
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
TAG = "MICEQCBROWSER"          # marks our processes so we never kill the user's
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
window.qcMark=function(m){ try{ rawCmd("MOVE QCMARK " + m); }catch(e){} };
window.qcFail=function(e){ qcMark("ERROR-" + String(e && e.message || e)
  .replace(/[^A-Za-z0-9]/g,"_").slice(0,60)); };
</script>
"""


def page(driver_js, query="", seconds=20, studio_web=None):
    """Serve the real Studio index.html + a driver script, load it, wait, kill.

    The temp page lives in the studio web folder so every relative asset
    resolves, and is always removed again.
    """
    web = studio_web or (QC.parent / "nong" / "main_python_set_nong" / "web")
    src = (web / "index.html").read_text(encoding="utf-8")
    drv = web / "_qcdriver.html"
    drv.write_text(src + PRELUDE + "<script>\n" + driver_js + "\n</script>",
                   encoding="utf-8")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    # parenthesised: "/" and "%" share precedence, so without them python
    # tries Path % int
    prof = str(SCRATCH / ("profile_%d" % int(time.time() * 1000)))
    try:
        subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Start-Process -FilePath '%s' -ArgumentList "
                        "'--headless=new','--disable-gpu','--no-sandbox',"
                        "'--no-first-run','--disable-extensions','--%s',"
                        "'--user-data-dir=%s','%s' -NoNewWindow"
                        % (EDGE, TAG, prof, query)], timeout=60)
        _wait_for_done(seconds)
    finally:
        drv.unlink(missing_ok=True)
        kill()
        _rmtree(prof)


def _wait_for_done(seconds, grace=25):
    """Wait for the driver to say "done" — do not just sleep a fixed time.

    A fixed sleep is a race: when Edge starts slowly (several browser checks in
    one run, a loaded machine) the page is killed mid-way and the check fails
    with "nothing reported", even though the code under test is fine. An
    intermittently failing suite is one people learn to ignore, which is worse
    than no suite.

    So: return the moment the driver reports "done", and be patient beyond the
    nominal time if it has not. Healthy runs get FASTER, slow ones stop
    flaking.
    """
    import fake_serial
    start = len(fake_serial.qc_marks)
    deadline = time.time() + seconds + grace
    while time.time() < deadline:
        if any(m == "done" for m in fake_serial.qc_marks[start:]):
            time.sleep(0.4)          # let the last report land
            return True
        time.sleep(0.4)
    return False


def raw_page(html, base, seconds=20, name="_qcraw.html"):
    """Serve an arbitrary page from the studio web folder and load it.

    Used by checks that drive OTHER pages (in iframes) rather than the studio
    app itself. Media queries inside an iframe respond to the IFRAME's width,
    so this is a real way to test phone layouts without resizing the browser.
    """
    web = QC.parent / "nong" / "main_python_set_nong" / "web"
    f = web / name
    # NOT the studio PRELUDE: that reports via rawCmd(), which lives in app.js
    # and a raw page never loads it. Talk to the fake module directly instead.
    raw_prelude = """
<script>
window.alert=function(){}; window.confirm=function(){return true;};
window.qcMark=function(m){
  return fetch("/api/usb/cmd?port=COM99&id=0&c=" +
               encodeURIComponent("MOVE QCMARK " + m)).catch(function(){});
};
window.qcFail=function(e){ qcMark("ERROR-" + String(e && e.message || e)
  .replace(/[^A-Za-z0-9]/g,"_").slice(0,60)); };
</script>
"""
    f.write_text(raw_prelude + html, encoding="utf-8")
    SCRATCH.mkdir(parents=True, exist_ok=True)
    prof = str(SCRATCH / ("profile_%d" % int(time.time() * 1000)))
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
        _wait_for_done(seconds)
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
