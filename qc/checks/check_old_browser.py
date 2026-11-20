"""Old TV browsers: nothing the hub serves uses syntax Chrome 75 cannot parse, and missing features are filled in.

2026-11-20, an Android-x86 VM with Chrome 75 (the browser an older Android TV
ships): Studio died on `RIG.extraClearanceMm ?? 0` (77 such spots), Home on
`replaceChildren`, and a blank page said nothing. Now the built scripts are
lowered at build time (tools/web_compat.py), the missing features are filled
in (mice-ui.js), and a page that still cannot start says so in one sentence.

Proof, on the real pages: every inline script and every shared script parses
for an old browser (no `?.` / `??`); in a real Chromium with those features
REMOVED the pages still get them back; and the plain-words banner appears on
a start-up syntax error. Skipped when node + playwright are not on this PC.
"""
import json
import re
import shutil
import subprocess
import sys
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "served pages run on an old browser: no new syntax, features filled in, plain words if not"

PAGES = ["main_python/web/hub.html", "main_python/web/help.html", "main_python/web/rgb.html",
         "apps/voice/index.legacy.html", "apps/camera/index.html", "apps/faces/index.html",
         "apps/gacha/index.html", "apps/tv/index.html", "apps/all-jao/index.html",
         "apps/photobooth/index.html", "nong/main_python_set_nong/web/index.html"]
SCRIPTS = ["nong/main_python_set_nong/web/app.legacy.js", "shared/web/mice.js", "shared/web/mice-ui.js",
           "shared/web/cast.js", "shared/web/resources.js", "apps/gacha/motion.js",
           "apps/gacha/presets.js", "apps/all-jao/link.js"]

BROWSER = r"""
const pw = require("playwright");
(async () => {
  const b = await pw.chromium.launch();
  const p = await b.newPage();
  await p.addInitScript(() => {            // an old browser: these do not exist yet
    delete Element.prototype.replaceChildren; delete Promise.allSettled;
    delete Array.prototype.at; delete String.prototype.replaceAll; delete AbortSignal.timeout;
  });
  await p.goto(process.argv[1] + "/app/tv/", {waitUntil: "load"});
  const r = await p.evaluate(async () => {
    const d = document.createElement("div"); d.innerHTML = "<i></i>";
    d.replaceChildren(document.createElement("b"));
    const s = await Promise.allSettled([Promise.resolve(1), Promise.reject(2)]);
    window.dispatchEvent(new ErrorEvent("error", {message: "Uncaught SyntaxError: Unexpected token ?"}));
    return {rc: d.innerHTML, at: [1, 2, 3].at(-1), ra: "a-b-c".replaceAll("-", "+"),
            settled: s.map(x => x.status).join(), timeout: typeof AbortSignal.timeout,
            banner: /too old/.test((document.getElementById("miceOldBrowser") || {}).textContent || "")};
  });
  console.log(JSON.stringify(r));
  await b.close();
})();
"""


def scripts_of(path):
    text = path.read_text(encoding="utf-8")
    if path.suffix == ".js":
        return [text]
    return [m.group(2) for m in re.finditer(r"<script(?![^>]*\bsrc=)([^>]*)>(.*?)</script>", text, re.S)
            if not re.search(r"type=[\"'](?!text/javascript|module)", m.group(1))]


def run(t):
    node = shutil.which("node")
    sys.path.insert(0, str(F.CODE / "tools"))
    import web_compat                                           # noqa: E402
    if not node or not web_compat._ready(node):
        t.ok(True, "node/esbuild not installed: old-browser check not run", "")
        return
    for rel in PAGES + SCRIPTS:
        path = F.CODE / rel
        if not path.exists():
            continue
        bad = [i for i, s in enumerate(scripts_of(path)) if not web_compat.parses_for_old(s, node)]
        t.ok(not bad, "%s has no syntax Chrome 75 cannot parse" % rel, "script(s) %s" % bad)
    base, _main = F.start_hub()
    import urllib.request

    def fetch(path, ua):
        req = urllib.request.Request(base + path, headers={"User-Agent": ua})
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.read().decode("utf-8", "replace")
    old_ua = "Mozilla/5.0 (Linux; Android 9) AppleWebKit/537.36 Chrome/75.0.3770.101 Safari/537.36"
    new_ua = "Mozilla/5.0 (Linux; Android 13) AppleWebKit/537.36 Chrome/126.0.0.0 Safari/537.36"
    for path in ("/app.js", "/app/voice/"):
        old, new = fetch(path, old_ua), fetch(path, new_ua)
        body = lambda s: re.findall(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", s, re.S) or [s]
        t.ok(all(web_compat.parses_for_old(x, node) for x in body(old)),
             "%s: a Chrome 75 browser is sent a script it can parse" % path, len(old))
        t.ok(not all(web_compat.parses_for_old(x, node) for x in body(new)),
             "%s: a modern browser keeps the readable original" % path, len(new))
    out = subprocess.run([node, "-e", BROWSER, base], capture_output=True, text=True, timeout=90)
    if not out.stdout.strip():
        if "Cannot find module" in out.stderr:
            t.ok(True, "playwright not available: browser part not run", out.stderr[-200:])
        else:
            t.ok(False, "the old-browser page test ran", out.stderr[-300:])
        return
    r = json.loads(out.stdout.strip().splitlines()[-1])
    t.ok(r["rc"] == "<b></b>" and r["at"] == 3 and r["ra"] == "a+b+c" and r["settled"] == "fulfilled,rejected"
         and r["timeout"] == "function", "missing browser features are filled in", r)
    t.ok(r["banner"], "a start-up syntax error shows the plain 'browser too old' sentence", r)
