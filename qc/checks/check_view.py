"""Standard views must be FLAT — orthographic, not merely aimed.

Front/Top/Left only became true plane views once the projection changed. Under
perspective the camera pointed at the plane while near parts still rendered
bigger and parallel edges converged, so dragging in a plane did not match what
was on screen. This asserts the projection itself, not just the camera angle.
"""
import subprocess
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "view"
TITLE = "plane views are really flat (orthographic)"
SLOW = True

DRIVER = """
window.addEventListener("load", function(){ setTimeout(function(){
  try {
    var out = [];
    function probe(name){
      setView(name);
      var c = activeCam();
      out.push(name + ":" + (c.isOrthographicCamera ? "ortho" :
                             c.isPerspectiveCamera ? "persp" : "?"));
    }
    ["front","back","left","right","top","bottom","iso"].forEach(probe);

    // the live camera must be the one OrbitControls drives and the one the
    // renderer draws, or dragging targets a camera that is not on screen
    setView("front");
    out.push("controls:" + (controls.object === activeCam() ? "same" : "MISMATCH"));

    // an orthographic frustum must be non-degenerate and match the viewport
    var o = activeCam();
    var w = o.right - o.left, h = o.top - o.bottom;
    out.push("frustum:" + (w > 1 && h > 1 ? "sized" : "degenerate"));
    var vp = document.getElementById("viewport");
    var want = vp.clientWidth / vp.clientHeight, got = w / h;
    out.push("aspect:" + (Math.abs(want - got) < 0.05 ? "matches" : got.toFixed(2)));

    // switching back and forth must not move the camera
    setView("front");
    var a = activeCam().position.clone();
    setView("iso"); setView("front");
    out.push("stable:" + (activeCam().position.distanceTo(a) < 1 ? "yes" : "moved"));

    document.title = "VIEWPROJ " + out.join(" ");
  } catch(e) { document.title = "VIEWPROJ ERR " + e.message; }
}, 900); });
"""


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — run --quick")
    fake_serial.reset()
    base, main = F.start_hub()
    title = _title(base)
    if not t.ok(title.startswith("VIEWPROJ") and "ERR" not in title,
                "the view test ran", title or "(no title)"):
        return
    got = dict(p.split(":", 1) for p in title.split()[1:] if ":" in p)

    for v in ("front", "back", "left", "right", "top", "bottom"):
        t.eq(got.get(v), "ortho", "%s is a flat orthographic view" % v)
    t.eq(got.get("iso"), "persp", "iso keeps perspective — depth is the point there")
    t.eq(got.get("controls"), "same",
         "OrbitControls drives the camera that is actually rendered")
    t.eq(got.get("frustum"), "sized", "the ortho frustum is not degenerate")
    t.eq(got.get("aspect"), "matches", "the ortho frustum matches the viewport aspect")
    t.eq(got.get("stable"), "yes", "switching projection does not move the camera")


def _title(base):
    web = F.STUDIO_WEB
    drv = web / ("_qcdriver_%s.html" % browser._tag())
    drv.write_text((web / "index.html").read_text(encoding="utf-8")
                   + browser.PRELUDE + "<script>\n" + DRIVER + "\n</script>",
                   encoding="utf-8")
    browser.SCRATCH.mkdir(parents=True, exist_ok=True)
    out = str(browser.SCRATCH / "view_dom.html")
    import time
    prof = str(browser.SCRATCH / ("profile_view_%s" % browser._tag()))
    try:
        ps = ("$a=@('--headless=new','--disable-gpu','--no-sandbox','--no-first-run',"
              "'--disable-extensions','--%s','--user-data-dir=%s',"
              "'--virtual-time-budget=15000','--dump-dom','%s/studio/%s'); "
              "Start-Process -FilePath '%s' -ArgumentList $a -NoNewWindow -Wait "
              "-RedirectStandardOutput '%s' -RedirectStandardError '%s.err'"
              % (browser.TAG, prof, base, drv.name, browser.EDGE, out, out))
        subprocess.run(["powershell", "-NoProfile", "-Command", ps], timeout=200)
        dom = Path(out).read_text(encoding="utf-8", errors="replace")
    except Exception:
        dom = ""
    finally:
        drv.unlink(missing_ok=True)
        browser.kill()
        browser._rmtree(prof)
        Path(out).unlink(missing_ok=True)
        Path(out + ".err").unlink(missing_ok=True)
    return dom.split("<title>")[1].split("</title>")[0] if "<title>" in dom else ""
