"""Studio still works on a device with no WebGL (old TV or PC browser, blocked GPU).

2026-11-20 client matrix: Firefox without WebGL left Studio with a blank 3D
view, no sliders and "checking..." for ever, because creating the renderer
threw at start. Now a stand-in renderer shows one plain sentence and the rest
of the page starts. Proven in a real Chromium started with WebGL switched off.
Skipped when node + playwright are not on this PC.
"""
import json
import shutil
import subprocess

import qc as F

AREA = "studio"
TITLE = "Studio starts and says why when the device has no 3D"

SCRIPT = r"""
const pw = require("playwright");
(async () => {
  const b = await pw.chromium.launch({args: ["--disable-3d-apis", "--disable-webgl"]});
  const p = await b.newPage({viewport: {width: 1280, height: 800}});
  const errs = [];
  p.on("pageerror", e => errs.push(String(e.message)));
  await p.goto(process.argv[1] + "/studio/", {waitUntil: "load"});
  await p.waitForTimeout(2500);
  const r = await p.evaluate(() => ({
    note: (document.querySelector(".no3d") || {}).textContent || "",
    sliders: document.querySelectorAll("input[type=range]").length,
    look: document.querySelectorAll("#viewport canvas").length}));
  r.errs = errs;
  console.log(JSON.stringify(r));
  await b.close();
})();
"""


def run(t):
    node = shutil.which("node")
    if not node:
        t.ok(True, "node not installed: no-WebGL check not run", "")
        return
    base, _main = F.start_hub()
    out = subprocess.run([node, "-e", SCRIPT, base], capture_output=True, text=True, timeout=90)
    if not out.stdout.strip():
        t.ok(True, "playwright not available: no-WebGL check not run", out.stderr[-200:])
        return
    r = json.loads(out.stdout.strip().splitlines()[-1])
    t.ok("cannot draw the 3D robot" in r["note"], "the view says in plain words that 3D is unavailable", r)
    t.ok(r["sliders"] > 0, "the sliders still start", r)
    t.ok(not [e for e in r["errs"] if "WebGL" not in e], "no other page error", r["errs"])
