"""How long ago reads as hours or days, never thousands of minutes.

The Home card said *last opened 2026-09-18 13:35 (4470 min ago)* on
2026-09-21 - the user pasted it back. Nobody reads 4470 minutes as three days,
and the pages are for designers, not programmers. The function is run for real
(node), so the words are checked, not the source text.
"""
import re
import shutil
import subprocess

import qc as F

AREA = "hub"
TITLE = "'last opened' says minutes, hours or days - whichever reads"

CASES = [(3, "just now"), (40, "40s ago"), (600, "10 min ago"),
         (3 * 3600, "3 hours ago"), (4470 * 60, "3 days ago")]


def run(t):
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    m = re.search(r"function agoText\(ms\)\{.*?\n\}", hub, re.S)
    if not t.ok(m, "hub.html has agoText"):
        return
    node = shutil.which("node")
    if not t.ok(node, "node is available to run it", "install Node.js"):
        return
    script = m.group(0) + (
        "\nconst now=Date.now();for(const s of %s){console.log(agoText(now-s*1000));}"
        % [c[0] for c in CASES])
    out = subprocess.run([node, "-e", script], capture_output=True, text=True,
                         timeout=20).stdout.split("\n")
    for (secs, want), got in zip(CASES, out):
        t.ok(got.strip() == want, "%d s ago reads '%s'" % (secs, want),
             "got '%s'" % got.strip())

    # ---- A26-87: each row says when THAT board was last opened ----------
    fns = []
    for name in ("stamp", "agoText", "openedTimes", "rememberOpened", "openedText"):
        f = re.search(r"function %s\(.*?\n\}" % name, hub, re.S)
        if not t.ok(f, "hub.html has %s" % name):
            return
        fns.append(f.group(0))
    script = "\n".join(fns) + """
const store = {};
globalThis.localStorage = {getItem: k => store[k] || null, setItem: (k, v) => { store[k] = v; }};
rememberOpened('usb:COM21:67', 'nong', 'chip/AAA');
rememberOpened('wifi:10.0.0.9', 'other');          // an opener with no key
console.log(openedText({key: 'chip/AAA', routes: []}));
console.log(openedText({key: 'chip/BBB', routes: [{dev: 'wifi:10.0.0.9'}]}));
console.log(openedText({key: 'chip/CCC', routes: [{dev: 'usb:COM9'}]}) || 'none');
"""
    got = subprocess.run([node, "-e", script], capture_output=True, text=True,
                         timeout=20).stdout.split("\n")
    t.ok(got[0].startswith("last opened ") and "just now" in got[0],
         "a board opened now says so on its own row", repr(got[:1]))
    t.ok(got[1].startswith("last opened "),
         "found by any of its routes when the opener had no board key", repr(got[1:2]))
    t.eq(got[2].strip(), "none", "a board never opened says nothing")
