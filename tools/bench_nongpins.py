"""Every nong the hub can see answers PIN? with its servo pins SET.

    python tools/bench_nongpins.py [hub-url]

A24-7. Asks each module of type nong for its pin map and names every joint
that would stay silent (arm pins unset = a servo nobody drives). Exit 0 only
when every reachable nong's arm is fully mapped, so a flash flow can call it
as a gate.

Runs against the LIVE hub — this is the bench half; the law itself lives in
qc/lib/nongpins.py and is unit-checked by check_bench_nongpins.
"""
import json
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "qc" / "lib"))
import nongpins                                            # noqa: E402

HUB = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8642"
# The shipped demo login — the convention everywhere in this project.
USER, PASSWORD = "manny", "12345678"


def _post(path: str, data: dict):
    req = urllib.request.Request(
        HUB + path, json.dumps(data).encode(),
        {"Content-Type": "application/json"})
    return urllib.request.urlopen(req, timeout=15).read().decode()


def _get(path: str):
    try:
        return urllib.request.urlopen(HUB + path, timeout=30).read().decode()
    except urllib.error.HTTPError as e:
        return e.read().decode()


opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor())
req = urllib.request.Request(HUB + "/api/login",
                             json.dumps({"user": USER, "password": PASSWORD}
                                        ).encode(),
                             {"Content-Type": "application/json"})
opener.open(req, timeout=15)


def ask(dev: str, c: str) -> str:
    u = "%s/api/dev/cmd?dev=%s&c=%s" % (
        HUB, urllib.parse.quote(dev), urllib.parse.quote(c))
    try:
        return opener.open(u, timeout=30).read().decode()
    except urllib.error.HTTPError as e:
        return ""


mods = json.loads(_get("/api/modules/all")).get("modules") or []
nongs = [m for m in mods if m.get("type") == "nong"]
if not nongs:
    print("no nong module is visible to the hub - nothing to audit")
    sys.exit(1)

bad = 0
for m in nongs:
    routes = m.get("routes") or []
    dev = routes[0].get("dev", "") if routes else ""
    label = "%-4s %-12s %s" % (m.get("id"), m.get("name"), dev or "?")
    if not dev:
        print("%s  NO WAY IN" % label)
        bad += 1
        continue
    raw = ask(dev, "PIN?")
    try:
        arm, body = nongpins.missing(json.loads(raw))
    except ValueError:
        print("%s  no PIN? reply (%r...)" % (label, raw[:40]))
        bad += 1
        continue
    if arm:
        print("%s  SILENT ARM JOINTS: %s"
              % (label, ", ".join("%s=%s" % kv for kv in arm)))
        bad += 1
    else:
        note = ("  (body unset: %s)" % ", ".join(p for p, _ in body)) \
            if body else ""
        print("%s  ok%s" % (label, note))

sys.exit(1 if bad else 0)
