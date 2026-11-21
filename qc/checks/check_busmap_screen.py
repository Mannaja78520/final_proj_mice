"""The Board numbers card: find duplicates, show the chain, fix on request, plain words.

The hub route runs bus_net/bus_ids over a link. QC puts a simulated bridged bus
behind a fake cable (hub_busmap.link_for), calls the real routes, and asserts on
what the boards ended up with (their ids), not on what the page says.
"""
import json
import sys
import time
from pathlib import Path

import qc as F

AREA = "connection"
TITLE = "Board numbers card: duplicates found and fixed by chip, chained cables shown"

ROOT = Path(F.__file__).resolve().parents[2]


def run(t):
    for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    import hub_busmap
    from bus_sim import Board, Bus, Gateway

    # 3 boards share id 3 on the first cable; a bridge (id 9) leads to 5 more
    back = Bus([Board("B0000000%04X" % i, i) for i in range(1, 6)])
    top = Bus([Board("A0000000%04X" % i, 3) for i in range(1, 4)] +
              [Board("A1000000%04X" % i, i) for i in (4, 5)] +
              [Gateway("A2000000AAAA", 9, down=back)])
    hub_busmap.link_for = lambda port: top.exchange

    class Fake:
        def __init__(self):
            self.out = None

        def send_json(self, obj, code=200):
            self.out = obj
    routes = hub_busmap.BusMapRoutes()
    routes.send_json = lambda obj, code=200: setattr(routes, "out", obj)

    def call(method, path):
        routes.api_busmap(method, path, {"port": ["COM77"]})
        return routes.out

    t.ok(call("GET", "/api/busmap").get("state") == "none", "no job yet: state none")
    t.ok(call("GET", "/api/busmap/check").get("error") == "use POST", "starting a check needs POST")
    call("POST", "/api/busmap/check")
    for _ in range(300):
        d = call("GET", "/api/busmap")
        if d["state"] != "running":
            break
        time.sleep(0.05)
    r = d["result"]
    t.ok(d["state"] == "done" and len(r["boards"]) == 11, "check finished: 11 boards seen (%s)" % d.get("state"))
    t.ok(len(r["duplicates"]) == 1 and r["duplicates"][0]["id"] == 3 and len(r["duplicates"][0]["chips"]) == 3,
         "three boards sharing number 3 are reported", json.dumps(r["duplicates"])[:100])
    t.ok(len(r["buses"]) == 2, "the board plugged into a bridge is shown as a second cable")
    ids_before = sorted(b.id for b in top.boards if not isinstance(b, Gateway))
    t.ok(ids_before.count(3) == 3, "checking changed nothing: still three boards on number 3")

    call("POST", "/api/busmap/fix")
    for _ in range(600):
        d = call("GET", "/api/busmap")
        if d["state"] != "running":
            break
        time.sleep(0.05)
    r = d["result"]
    ids_after = [b.id for b in top.boards]
    t.ok(len(set(ids_after)) == len(ids_after), "after the fix every board on the cable has its own number",
         str(sorted(ids_after)))
    t.ok(not r["duplicates"] and len(r["moved"]) == 2, "re-check shows no duplicates, 2 boards moved (%d)" % len(r["moved"]))

    # plain words: the page text a designer reads has no banned vocabulary on the surface
    html = (ROOT / "main_python" / "web" / "home" / "parts" / "busmap.html").read_text(encoding="utf-8")
    js = (ROOT / "main_python" / "web" / "home" / "parts" / "busmap.js").read_text(encoding="utf-8")
    for w in ("chip", "RS485", "gateway", "bus ", "id "):
        t.ok(w not in html.replace("class=\"tech\"", ""), "card text avoids the word '%s'" % w)
    t.ok("=>" not in js and "const " not in js and "let " not in js, "script is ES5 (Chrome 75 / Android TV)")
