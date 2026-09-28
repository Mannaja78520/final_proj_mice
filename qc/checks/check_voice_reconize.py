"""Open Reconize on the Voice page opens THEIR camera page, from data.

A26-60 (user 2026-09-18): *Add the Open Reconize button inside the Voice
page - open the service, detect the face and data to voice*. The face only
reaches the Voice badge when someone is in front of Reconize's live camera,
so the button must land on that page, not on their dashboard.

What it guards:
  * config/partners.json names the camera page (`camera`) - no address in
    apps/voice/app.js; the first version hardcoded http://localhost:5173 and
    opened a second tab whenever the real address differed;
  * the tab opens inside the click (a tab opened after the start wait is a
    blocked pop-up), then goes to open + camera;
  * the page starts Reconize through /api/partners/start and waits for ready;
  * from a phone, "localhost" is swapped for the hub's host.
Measured 2026-09-18 against the live hub: localhost:5173/recognition from the
PC, 192.168.3.108:5173/recognition from the network.
"""
import re
import sys

import qc as F

AREA = "tools"
TITLE = "Open Reconize on the Voice page lands on the live face camera"


def run(t):
    sys_path = F.CODE / "main_python"
    if str(sys_path) not in sys.path:
        sys.path.insert(0, str(sys_path))
    import main as hub
    rec = (hub.read_partners().get("partners") or {}).get("reconize") or {}
    t.ok(str(rec.get("camera", "")).startswith("/"),
         "partners.json names Reconize's camera page",
         "reconize.camera = %r" % rec.get("camera"))

    js = (F.CODE / "apps" / "voice" / "app.js").read_text(encoding="utf-8")
    a = js.find("async openReconize(){")           # with the async, or node cannot run it
    body = js[a:js.find("\n  detectLang", a)] if a >= 0 else ""
    t.ok(bool(body), "app.js has openReconize", "not found")
    t.ok(":5173" not in js and "localhost:" not in body,
         "no Reconize address is written in the Voice page", "found a hardcoded address")
    first_await = body.find("await ")
    blank = body.find('window.open("about:blank"')
    t.ok(0 <= blank < first_await,
         "the tab opens inside the click, before any wait",
         "about:blank at %d, first await at %d" % (blank, first_await))
    t.ok("links.camera" in body and "/api/partners\"" in body,
         "the camera page comes from /api/partners", "links.camera or /api/partners missing")
    t.ok("/api/partners/start?id=reconize" in body and "got.ready" in body,
         "Reconize is started and waited for", "start/ready loop missing")
    t.ok(re.search(r"url\.hostname\s*=\s*location\.hostname", body) is not None,
         "a phone gets the hub's host, not localhost", "hostname swap missing")

    page = (F.CODE / "apps" / "voice" / "index.html").read_text(encoding="utf-8")
    t.ok('id="btnOpenReconize"' in page and "links.camera" in page,
         "the built Voice page carries the button and the new code",
         "run tools/build_web.py")
    t.ok('onclick="openReconize()"' in page and "window.openReconize" in page,
         "the button is really wired to the function",
         "onclick or the window.openReconize bridge is missing")

    _run_it(t, body)


def _run_it(t, body):
    """Runs the REAL function under node with the hub stubbed out.

    A page that merely CONTAINS the right words can still open the wrong
    address: the first version read like this one and sent every browser to
    localhost:5173. So the function itself is called twice - once as the PC,
    once as a phone - and the address it puts in the tab is what is asserted.
    """
    import json
    import shutil
    import subprocess
    import tempfile
    node = shutil.which("node")
    if not node:                                  # no node on this machine
        return
    harness = """
const body = %s;
const stub = {
  "/api/partners": {ok: true, partners: {reconize: {open: "http://localhost:5173", camera: "/recognition"}}},
  "/api/partners/start?id=reconize": {ok: true, ready: true, open: "http://localhost:5173"},
};
const out = [];
for (const host of ["127.0.0.1", "10.0.0.5"]) {
  const els = {stat: {textContent: ""}, btnOpenReconize: {disabled: false}};
  const tab = {closed: false, location: {href: "about:blank"}, close() { this.closed = true; }};
  globalThis.window = {open: () => tab};
  globalThis.location = {hostname: host};
  globalThis.fetch = async (u) => ({json: async () => stub[u]});
  const app = eval("({ $: id => els[id], say(m){ els.stat.textContent = m; }, pollFace(){}, " + body + "})");
  await app.openReconize();
  out.push(tab.location.href + (tab.closed ? " CLOSED" : ""));
}
console.log(JSON.stringify(out));
""" % json.dumps(body)
    with tempfile.TemporaryDirectory() as d:
        f = __import__("pathlib").Path(d) / "open_reconize.mjs"
        f.write_text(harness, encoding="utf-8")
        r = subprocess.run([node, str(f)], capture_output=True, text=True, timeout=60)
    got = (r.stdout or "").strip().splitlines()[-1:] or [""]
    try:
        pc, phone = json.loads(got[0])
    except Exception:
        return t.ok(False, "the real function runs and opens a tab",
                    "node said: %s %s" % (r.stdout[-200:], r.stderr[-200:]))
    t.eq(pc, "http://localhost:5173/recognition", "from this PC the tab lands on the camera page")
    t.eq(phone, "http://10.0.0.5:5173/recognition", "from a phone the tab lands on the hub's host")
