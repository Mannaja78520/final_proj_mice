"""Every app page wears one head, and an outside app is asked about BY THE HUB.

Asked 2026-10-14 (A41-1): *each web page in main goes its own way, hard to read
and hard to use - make it simple and the same everywhere, OOP so later edits are
easy*. Measured that day on the five app pages: four ways back to the hub
("🏠 Hub" left, "Hub" left, "👈 hub" link, "🏠 Hub" right), three widths, and
three hand-copied "is the outside program running" blocks.

Those copies all probed 127.0.0.1 FROM THE BROWSER. The hub shows a QR so a
phone can open it - and on a phone 127.0.0.1 is the phone, so Photobooth,
All-Jao and Reconize always read "not running" there, even while running on the
PC. The Reconize page polled localhost:8769 the same way for the watcher.

Now shared/web/mice-ui.js holds the parts (Mice.Api, Mice.Status, Mice.TopBar,
Mice.Partner) and the hub answers /api/partners/health and /api/faces/state.
This holds:

  * every app page loads mice-ui.js and has <header class="topbar">, and none
    keeps an old hand-made head;
  * no app page fetches a loopback address itself;
  * /api/partners/health says up while the program answers and down after it
    stops - asked of a real server, not of a page's words;
  * in a real browser, the Photobooth page shows the shared head and says the
    program is running when the HUB found it running.

Home joined in stage 2 (A41-3). It was one 164 KB file, so any change meant
reading all of it; it is now main_python/web/home/ (a short template and one
part per tab) built into hub.html by tools/build_web.py. Its nine-item tab row
wrapped onto a second line at 1280 px and four on a phone, with Shortcuts in
a bigger type than the rest. This also holds, in a real browser at 1280 and
390 px: Home wears the same head (STOP in it, one technical switch, no way
back because it IS the hub), and its tabs sit on one line with no sideways
scroll of the page.

Help joined in stage 5 (A41-6): its way back and its technical switch lived at
the top of its sidebar, which on a phone is a list that scrolls away. It is
now main_python/web/help/ built into help.html, on the same head.
"""
import json
import os
import re
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import browser
import fake_serial
import qc as F

AREA = "design"
TITLE = "every app page wears one head, and outside apps are checked by the hub"
SLOW = True

OLD_HEADS = ['<div class="head">', "🏠 Hub</button>", "👈 hub", ">Hub</button>"]
LOOPBACK_FETCH = re.compile(r"""fetch\(\s*["'`]https?://(127\.0\.0\.1|localhost)""")


class _Health(BaseHTTPRequestHandler):
    def do_GET(self):                                          # noqa: N802
        body = b'{"ok": true}'
        self.send_response(200 if self.path.startswith("/api/health") else 404)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, *a):
        pass


def _pages():
    """Every page an app folder serves (the built page and its template)."""
    for d in sorted((F.CODE / "apps").iterdir()):
        for name in ("index.html", "index.template.html"):
            f = d / name
            if f.is_file():
                yield f


def run(t):
    # ---- the source: one head, no browser-side loopback probe ----------
    for f in _pages():
        rel = f.relative_to(F.CODE).as_posix()
        src = f.read_text(encoding="utf-8", errors="replace")
        t.ok('src="/mice-ui.js"' in src, "%s loads the shared page parts" % rel)
        t.ok('<header class="topbar">' in src, "%s has the shared head" % rel)
        old = [h for h in OLD_HEADS if h in src]
        t.ok(not old, "%s keeps no hand-made head of its own" % rel, old)
        t.ok(not LOOPBACK_FETCH.search(src),
             "%s never asks 127.0.0.1 from the browser" % rel,
             "on a phone that is the phone itself, so the page says "
             "'not running' about a program that is running on the PC")

    # ---- Home: the same head, built from parts (A41-3) ------------------
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")
    t.ok('src="/mice-ui.js"' in hub, "Home loads the shared page parts")
    t.ok('<header class="topbar" data-home="none">' in hub,
         "Home wears the shared head, with no way back (it IS the hub)")
    t.ok("BUILT by tools/build_web.py" in hub and "<!-- part:" not in hub,
         "hub.html is built from main_python/web/home/, every part placed",
         "edit the parts, then python tools/build_web.py")
    t.ok("function setAdvanced" not in hub,
         "Home keeps no technical switch of its own (miceAdv is the one)")

    # ---- Help: the same head, built from parts (A41-6) ------------------
    hlp = (F.HUB / "web" / "help.html").read_text(encoding="utf-8", errors="replace")
    t.ok('src="/mice-ui.js"' in hlp and '<header class="topbar">' in hlp,
         "Help loads the shared page parts and wears the shared head")
    t.ok('class="back"' not in hlp and 'id="advOn"' not in hlp,
         "Help keeps no way back or technical switch of its own in its sidebar",
         "a phone scrolled both away with the rest of the list")
    t.ok("BUILT by tools/build_web.py" in hlp and "<!-- part:" not in hlp,
         "help.html is built from main_python/web/help/, every part placed",
         "edit the parts, then python tools/build_web.py")

    # ---- the hub answers whether it is up ------------------------------
    srv = ThreadingHTTPServer(("127.0.0.1", 0), _Health)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    port = srv.server_address[1]
    tmp = Path(tempfile.mkdtemp(prefix="mice_frame_"))
    cfg = tmp / "partners.json"
    cfg.write_text(json.dumps({"photobooth": {
        "name": "Photobooth", "open": "http://127.0.0.1:%d/booth" % port,
        "admin": "http://127.0.0.1:%d/admin" % port,
        "api": "http://127.0.0.1:%d" % port, "health": "/api/health",
        "folder": str(tmp)}}), encoding="utf-8")
    old_env = os.environ.get("MICE_PARTNERS")
    os.environ["MICE_PARTNERS"] = str(cfg)
    old_tmp = None
    try:
        base, _main = F.start_hub()
        old_tmp = getattr(_main.partner_launch, "TMP", None)
        _main.partner_launch.TMP = tmp
        F.logout_qc()
        code, body = F.get(base + "/api/partners/health?id=photobooth")
        got = json.loads(body or "{}")
        t.ok(code == 200 and got.get("ok") and got.get("up") is True,
             "the hub says Photobooth is up while it answers, with no login", body[:200])
        code, body = F.get(base + "/api/partners/health?id=nobody")
        t.ok(not json.loads(body or "{}").get("ok"),
             "and says so plainly about a program nobody set up", body[:200])

        # ---- in a real browser: the head, and the hub's answer on screen
        if browser.available():
            fake_serial.reset()
            browser.raw_page("""
<iframe id="f" src="/app/photobooth/" style="width:390px;height:700px"></iframe>
<script>
window.addEventListener("load", async function(){
  // Wait for the page's own answer, not a number of seconds.
  var doc = function(){ return document.getElementById("f").contentDocument; };
  await qcWaitFor(function(){
    var s = doc().getElementById("stat");
    return s && !/checking/.test(s.textContent) && doc().querySelector(".topbar-home");
  }, 15000);
  var d = doc();
  var home = d.querySelector("header.topbar .topbar-home");
  await qcMark("HOME " + (home ? home.getAttribute("href") : "none"));
  await qcMark("ADV " + d.querySelectorAll("#advOn").length);
  await qcMark("STAT " + (d.getElementById("stat").firstChild || {}).textContent);
  qcMark("done");
});
</script>""", base, seconds=25)
            marks = fake_serial.qc_marks
            t.ok("HOME /" in marks, "the page's head starts with the way back to the hub", marks)
            t.ok("ADV 1" in marks, "and carries exactly one technical switch", marks)
            stat = next((m for m in marks if m.startswith("STAT ")), "")
            t.ok(stat.startswith("STAT Photobooth is running"),
                 "and says it is running, because the hub found it", stat)
            _home(t, base)
            _help(t, base)
        else:
            t.ok(True, "browser part skipped: no headless browser here")

        srv.shutdown()
        srv.server_close()
        code, body = F.get(base + "/api/partners/health?id=photobooth")
        t.ok(json.loads(body or "{}").get("up") is False,
             "and down once it stops", body[:200])
    finally:
        if old_tmp is not None:
            _main.partner_launch.TMP = old_tmp
        srv.shutdown()
        srv.server_close()
        if old_env is None:
            os.environ.pop("MICE_PARTNERS", None)
        else:
            os.environ["MICE_PARTNERS"] = old_env


def _home(t, base):
    """Home at a PC width and a phone width: the head, and one row of tabs."""
    fake_serial.reset()
    browser.raw_page("""
<iframe id="pc" src="/" style="width:1280px;height:800px;border:0"></iframe>
<iframe id="ph" src="/" style="width:390px;height:800px;border:0"></iframe>
<script>
window.addEventListener("load", async function(){
  for (const id of ["pc", "ph"]) {
    var doc = function(){ return document.getElementById(id).contentDocument; };
    await qcWaitFor(function(){
      var d = doc();
      return d && d.querySelector("#tabs .tab") && d.querySelector(".topbar-adv");
    }, 15000);
    var d = doc();
    var tops = {};
    d.querySelectorAll("#tabs .tab").forEach(function(b){ tops[b.offsetTop] = 1; });
    var head = d.querySelector("header.topbar");
    await qcMark(id + " rows=" + Object.keys(tops).length
      + " adv=" + d.querySelectorAll("#advOn").length
      + " stop=" + (head && head.querySelector("#stopAll") ? "head" : "elsewhere")
      + " back=" + (head && head.querySelector(".topbar-home") ? "yes" : "no")
      + " wide=" + (d.documentElement.scrollWidth > d.documentElement.clientWidth ? "yes" : "no"));
  }
  qcMark("done");
});
</script>""", base, seconds=30)
    marks = fake_serial.qc_marks
    for id_, width in (("pc", "1280"), ("ph", "390")):
        got = next((m for m in marks if m.startswith(id_ + " ")), "")
        t.ok("rows=1 " in got, "Home's tabs sit on ONE line at %s px" % width, got or marks)
        t.ok("adv=1 " in got, "with exactly one technical switch (%s px)" % width, got)
        t.ok("stop=head " in got, "STOP is in the page's head (%s px)" % width, got)
        t.ok("back=no " in got, "and there is no way 'back' from the hub itself", got)
        t.ok(got.endswith("wide=no"), "the page never scrolls sideways at %s px" % width, got)


def _help(t, base):
    """Help on a phone: the shared head is on screen, not lost in the sidebar."""
    fake_serial.reset()
    browser.raw_page("""
<iframe id="f" src="/help" style="width:390px;height:800px;border:0"></iframe>
<script>
window.addEventListener("load", async function(){
  var doc = function(){ return document.getElementById("f").contentDocument; };
  await qcWaitFor(function(){
    var d = doc(); return d && d.querySelector("header.topbar .topbar-adv"); }, 15000);
  var d = doc(), head = d.querySelector("header.topbar"), home = head && head.querySelector(".topbar-home");
  await qcMark("help back=" + (home ? home.getAttribute("href") : "none")
    + " adv=" + d.querySelectorAll("#advOn").length
    + " top=" + (home ? Math.round(home.getBoundingClientRect().top) : -1));
  qcMark("done");
});
</script>""", base, seconds=25)
    got = next((m for m in fake_serial.qc_marks if m.startswith("help ")), "")
    t.ok("back=/ " in got, "Help's head starts with the way back to the hub", got or fake_serial.qc_marks)
    t.ok(" adv=1 " in got, "with exactly one technical switch", got)
    top = int(got.rsplit("top=", 1)[-1]) if "top=" in got else -1
    t.ok(0 <= top < 100, "and the way back is at the top of a phone screen (%d px)" % top, got)
