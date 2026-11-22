"""A developer can find every hub URL: GET /api lists them, and the list is current.

User 2026-11-22: APIs others must use have to be easy for a newcomer. Before,
the only list was the 3000 lines of main.py. tools/api_index.py builds
main_python/api_index.json + docs/HUB_API.md from the route lines; this holds
that the hub serves it, that a typo'd URL points at it, and that adding an
endpoint without re-running the tool fails here (stale list = a wrong list).
"""
import json
import subprocess
import sys

import qc as F

AREA = "hub"
TITLE = "GET /api lists the endpoints and the list is current"
SLOW = False


def run(t):
    base, _main = F.start_hub()
    code, text = F.get(base + "/api/")
    data = json.loads(text) if code == 200 else {}
    paths = [e["path"] for e in data.get("endpoints", [])]
    t.ok(code == 200 and "/api/modules" in paths and "/api/usb/cmd" in paths,
         "the API list is served and has the main endpoints", "%s %d" % (code, len(paths)))
    code, text = F.get(base + "/api/zzz-typo")
    t.ok(code == 404 and "GET /api" in text, "an unknown URL says where the list is", text[:90])
    out = subprocess.run([sys.executable, str(F.CODE / "tools" / "api_index.py"), "--check"],
                         capture_output=True, text=True)
    t.ok(out.returncode == 0, "api_index.json and docs/HUB_API.md match the code",
         (out.stdout + out.stderr)[:200])
