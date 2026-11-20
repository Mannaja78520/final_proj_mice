"""Pages leave the hub small and are not re-sent when unchanged; failures read as plain words.

Asked 2026-11-20: customers may open the hub on a low-spec Android TV and the
people using it are not engineers. Measured that day: Studio's app.js left the
hub as 653 KB plain text, no-store, on every open; a failed call printed the
browser's own "Failed to fetch" on screen in 40+ places.

Proven on the real hub: gzip only when asked for, a smaller body, an ETag that
earns a body-less 304, and live /api data that stays no-store. The wording
table (Mice.Words in mice-ui.js) is run in node when node exists.
"""
import gzip
import shutil
import subprocess
import urllib.error
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "pages are gzipped and revalidated; failures are worded for people"


def get(base, path, headers=None):
    req = urllib.request.Request(base + path, headers=headers or {})

    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def run(t):
    base, _main = F.start_hub()
    c1, h1, plain = get(base, "/app.js")
    c2, h2, packed = get(base, "/app.js", {"Accept-Encoding": "gzip"})
    t.ok(c1 == 200 and "Content-Encoding" not in h1,
         "a browser that does not ask for gzip gets plain text", h1)
    t.ok(c2 == 200 and h2.get("Content-Encoding") == "gzip"
         and len(packed) < len(plain) / 2 and gzip.decompress(packed) == plain,
         "a browser that asks gets gzip, under half the size, same bytes",
         "%d -> %d" % (len(plain), len(packed)))
    tag = h2.get("ETag")
    t.ok(bool(tag) and h2.get("Cache-Control") == "no-cache",
         "pages carry an ETag and must be re-asked (never stale after an update)", h2)
    c3, _h3, body3 = get(base, "/app.js", {"If-None-Match": tag or "x"})
    t.ok(c3 == 304 and body3 == b"", "an unchanged page is a 304 with no body", c3)
    _c5, h5, _ = get(base, "/api/apps")
    t.ok(h5.get("Cache-Control") == "no-store" and "ETag" not in h5,
         "live /api data is never cached", h5)

    _c6, h6, _b6 = get(base, "/docs/shots/hub-tools-card.png")
    t.ok(h6.get("Cache-Control") == "no-cache" and h6.get("ETag") and "Content-Encoding" not in h6,
         "screenshots are revalidated (304), not re-sent, and not pointlessly gzipped", h6)
    help_html = get(base, "/help")[2].decode("utf-8", "replace")
    t.ok("<img " in help_html and "<img src=" not in help_html,
         "Help pictures load lazily (only the ones scrolled to)", help_html.count("<img "))

    node = shutil.which("node")
    if not node:
        t.ok(True, "node not installed: wording table not run", "")
        return
    js = (Path(F.CODE) / "shared/web/mice-ui.js").as_posix()
    prog = ("global.window={};global.document={readyState:'complete',addEventListener(){},"
            "querySelectorAll(){return[]},getElementById(){return null}};"
            "global.localStorage={};global.location={href:'http://x/',hostname:'x'};"
            "require(%r);const W=window.Mice.Words;"
            "const o=[W.plain('Failed to fetch').says,W.plain('x is undefined').says,"
            "W.plain('the arm is not powered').says,W.plain(new Error('timed out: /a')).says];"
            "console.log(JSON.stringify(o))" % js)
    out = subprocess.run([node, "-e", prog], capture_output=True, text=True, timeout=30).stdout
    import json
    got = json.loads(out or "[]")
    t.ok(len(got) == 4 and "hub did not answer" in got[0] and "went wrong" in got[1]
         and got[2] == "the arm is not powered" and "took too long" in got[3]
         and "fetch" not in got[0].lower() and "undefined" not in got[1],
         "browser wording becomes plain sentences, a person-written reply is kept", out)
