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
    try:
        base, _main = F.start_hub()
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
        else:
            t.ok(True, "browser part skipped: no headless browser here")

        srv.shutdown()
        srv.server_close()
        code, body = F.get(base + "/api/partners/health?id=photobooth")
        t.ok(json.loads(body or "{}").get("up") is False,
             "and down once it stops", body[:200])
    finally:
        srv.shutdown()
        srv.server_close()
        if old_env is None:
            os.environ.pop("MICE_PARTNERS", None)
        else:
            os.environ["MICE_PARTNERS"] = old_env

