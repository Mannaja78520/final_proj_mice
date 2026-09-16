"""Every hub route an app page calls is still handled by the hub.

Found 2026-09-17: a promote copied an older main.py over a newer one and the
routes /api/jao/start, /api/voice/start and /api/voice/stop vanished. The All
Jao Games and Voice pages still called them, every page still loaded, and no
check noticed - the button simply stopped working.

So: collect every fetch("/api/...") literal in apps/*/index.html and app.js,
and require main.py to handle it, either by name or through a prefix it
forwards (`path.startswith("/api/voice/")` hands the rest to the voice helper).
"""
import re

import qc as F

AREA = "hub"
TITLE = "every hub route an app page calls still exists in the hub"


def run(t):
    main = (F.CODE / "main_python" / "main.py").read_text(encoding="utf-8")
    prefixes = re.findall(r'path\.startswith\(\s*"(/api/[A-Za-z0-9_/\-]+/)"', main)
    called = {}
    for f in sorted(list(F.CODE.glob("apps/*/index.html")) +
                    list(F.CODE.glob("apps/*/app.js"))):
        text = f.read_text(encoding="utf-8", errors="replace")
        for route in re.findall(r'fetch\(\s*["\'](/api/[A-Za-z0-9_/\-]+)', text):
            called.setdefault(route, set()).add(f.relative_to(F.CODE).as_posix())
    t.ok(len(called) >= 5, "the app pages call the hub (%d routes)" % len(called),
         sorted(called))
    missing = {r: sorted(pages) for r, pages in called.items()
               if '"%s"' % r not in main and not any(r.startswith(p) for p in prefixes)}
    t.ok(not missing, "and the hub still handles every one of them", missing)
    for must in ("/api/all-jao/start", "/api/partners/start", "/api/voice/start"):
        t.ok('"%s"' % must in main, "%s is handled" % must,
             "a page button calls it; without the route it silently does nothing")
