"""What Nong Studio looks like the moment it opens, including from a rig the
user saved earlier.

The saved-rig path is the dangerous one: a fresh browser has no localStorage,
so headless tests miss exactly the bugs real users hit. Both cases are checked.
"""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "boot state and saved-rig migration"
SLOW = True

NEUTRAL = [95, 85, 100, 80, 95, 85, 100, 80, 92, 88]     # nothing is 90

DRIVER = """
var want = %s;
if (location.search.indexOf("step2") < 0) {
  // an OLD saved rig: 8-long arrays, as a user who last saved before the
  // WAIST/SHRUG body joints existed would still have in localStorage
  localStorage.setItem("nong_rig", JSON.stringify({
    neutral: want, zero: [90,90,90,90,90,90,90,90]
  }));
  location.search = "?step2";
} else {
  window.addEventListener("load", function(){ setTimeout(function(){
    try {
      var vis = [];
      robot.traverse(function(o){
        if (o.isMesh) { var p = o.getWorldPosition(new THREE.Vector3());
          if (isNaN(p.x) || isNaN(p.y) || isNaN(p.z)) vis.push(o.name || "mesh"); }
      });
      document.title = "POSE=" + pose.join(",") +
        "|KEY0=" + (keys[0] ? keys[0].pose.join(",") : "none") +
        "|NEUTRAL=" + RIG.neutral.join(",") +
        "|ZERO=" + RIG.zero.join(",") +
        "|ZEROLEN=" + RIG.zero.length +
        "|NAN=" + vis.length;
    } catch(e) { document.title = "ERR " + e.message; }
  }, 900); });
}
""" % (NEUTRAL,)


def run(t):
    if not browser.available():
        t.give_up("headless Edge not found — install Edge or run --quick")
    fake_serial.reset()
    base, main = F.start_hub()

    title = _load_title(base)
    if title.startswith("ERR") or not title:
        t.ok(False, "the page booted from a saved rig", title or "(no title)")
        return
    got = dict(p.split("=", 1) for p in title.split("|") if "=" in p)
    want = ",".join(str(v) for v in NEUTRAL)

    # ---- the editor opens where the ROBOT rests ---------------------
    t.eq(got.get("NEUTRAL"), want, "a tuned neutral survives the rig merge")
    t.eq(got.get("POSE"), want, "the editor opens on the Neutral pose, not a flat 90")
    t.eq(got.get("KEY0"), want, "keyframe 0 is built from that pose")

    # neutral and zero are DIFFERENT settings: zero is the angle at which a
    # joint renders straight (a model calibration), neutral is where the robot
    # rests. Confusing them silently moves the arm.
    t.ok(got.get("ZERO") != want, "zero stays separate from neutral",
         "zero was overwritten with the neutral pose")

    # ---- the old-saved-rig trap ------------------------------------
    # An 8-long array from before WAIST/SHRUG must be padded to 10. Left short,
    # applyPose feeds undefined into the body rotation, every mesh lands on NaN
    # and the whole robot renders invisible — with no error anywhere.
    t.eq(got.get("ZEROLEN"), "10", "short arrays from an old rig are padded to 10")
    t.eq(got.get("NAN"), "0", "no mesh is at NaN (an invisible robot)")


def _load_title(base):
    web = F.STUDIO_WEB
    drv = web / ("_qcdriver_%s.html" % browser._tag())
    drv.write_text((web / "index.html").read_text(encoding="utf-8")
                   + browser.PRELUDE + "<script>\n" + DRIVER + "\n</script>",
                   encoding="utf-8")
    import subprocess
    import time
    from pathlib import Path
    browser.SCRATCH.mkdir(parents=True, exist_ok=True)   # scratch, not the repo
    out = str(browser.SCRATCH / "boot_dom.html")
    prof = str(browser.SCRATCH / ("profile_boot_%d" % int(time.time())))
    try:
        # this page goes idle (no live/monitor polling), so --dump-dom can
        # actually finish and the title is readable
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
