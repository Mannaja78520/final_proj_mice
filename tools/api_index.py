#!/usr/bin/env python3
"""Build the hub's API list for people who write code against it.

A newcomer with a script (or a friend's app) used to have to read 3000 lines
of main.py to learn which URLs exist. This reads the route lines
(`path == "/api/..."`) and the comment above each, and writes
  main_python/api_index.json   served by the hub at GET /api
  docs/HUB_API.md              the same, as a page to read
Run after adding an endpoint:  python tools/api_index.py   (`--check` for QC).
"""
import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HUB = ROOT / "main_python"
ROUTE = re.compile(r'if path == "(/api/[^"]+)"(\s+and method == "(\w+)")?')
PARAM = re.compile(r'\bq\.get\("(\w+)"\)')


def scan():
    found = {}
    for f in sorted(HUB.glob("main.py")) + sorted(HUB.glob("hub_api_*.py")):
        lines = f.read_text(encoding="utf-8").splitlines()
        for i, ln in enumerate(lines):
            m = ROUTE.search(ln)
            if not m:
                continue
            note, j = [], i - 1
            while j >= 0 and lines[j].strip().startswith("#"):
                note.insert(0, lines[j].strip().lstrip("# ").strip())
                j -= 1
            body = "\n".join(lines[i + 1:i + 14])
            nxt = ROUTE.search(body)
            if nxt:
                body = body[:nxt.start()]
            note = [n.strip("-= ") for n in note]
            note = [n for n in note if n]
            text = " ".join(note)
            text = re.split(r"(?<=[.:])\s", text, maxsplit=1)[0][:110]
            params = sorted(set(PARAM.findall(body)))
            key = (m.group(1), m.group(3) or "GET")
            found.setdefault(key, {"path": key[0], "method": key[1],
                                   "what": text, "params": params,
                                   "file": f.name})
    return sorted(found.values(), key=lambda e: (e["path"], e["method"]))


def render(eps):
    out = ["# Hub API (generated, do not edit)", "",
           "Made by `python tools/api_index.py`. The hub also serves this list at",
           "`GET /api`. Base: `http://<hub>:8642`. Anything that moves, flashes or",
           "deletes needs a login cookie (`POST /api/login`). Errors are always",
           '`{"ok": false, "error": "<plain words>"}`; a 401 adds `"need_login": true`.', "",
           "## Start here (checked against the running hub)", "",
           "- Log in: `curl -c cookie -X POST http://127.0.0.1:8642/api/login -d '{\"password\":\"...\"}'`",
           "- What is connected: `curl http://127.0.0.1:8642/api/modules` (reading needs no login)",
           "- Cables on this PC: `curl http://127.0.0.1:8642/api/ports`",
           "- Send a board command: `curl -b cookie 'http://127.0.0.1:8642/api/usb/cmd?port=COM3&c=STATUS'`",
           "- Show progress of a play: `curl http://127.0.0.1:8642/api/play`",
           "- Pages the hub offers: `curl http://127.0.0.1:8642/api/apps`", "",
           "A `-` in the table means the code has no comment for that URL yet.", "",
           "| Method | Path | What | Query values | Defined in |", "|---|---|---|---|---|"]
    for e in eps:
        out.append("| %s | `%s` | %s | %s | %s |" % (
            e["method"], e["path"], e["what"] or "-",
            ", ".join(e["params"]) or "-", e["file"]))
    return "\n".join(out) + "\n"


def main():
    eps = scan()
    js = json.dumps({"ok": True, "about": "Mice hub API. Docs: docs/HUB_API.md. "
                     "Errors are {ok:false, error}. Moving things needs POST /api/login first.",
                     "endpoints": eps}, ensure_ascii=False, indent=1) + "\n"
    md = render(eps)
    targets = {HUB / "api_index.json": js, ROOT / "docs" / "HUB_API.md": md}
    if "--check" in sys.argv:
        stale = [t.name for t, v in targets.items()
                 if not t.exists() or t.read_bytes() != v.encode()]
        print("api index is current" if not stale else "STALE: %s - run python tools/api_index.py" % stale)
        return 1 if stale else 0
    for t, v in targets.items():
        t.write_bytes(v.encode())
    print("%d endpoints" % len(eps))
    return 0


if __name__ == "__main__":
    sys.exit(main())
