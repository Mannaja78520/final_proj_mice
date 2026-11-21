"""The hub's "Check board addresses" job: find duplicate ids and map chained buses.

One cable (USB port) is the first link; bus_net.Topology walks every bus behind
it. It takes seconds to a minute on a big bus, so it runs as a background job the
page polls. Changing an id (the repair) is a separate, explicit button: checking
never writes to a board.

Routes (login needed like any other write: none of them are in hub_auth.OPEN):
  POST /api/busmap/check?port=COMx   start a check
  POST /api/busmap/fix?port=COMx     give duplicate ids a free id (by chip), then re-check
  GET  /api/busmap?port=COMx         progress, then the result
Names that live in main.py are read late through _hub.
"""
import threading
import time

import bus_ids
import bus_net

NOT_MINE = object()
_hub = None


def bind(hub):
    global _hub
    _hub = hub


def usb_link(port):
    """exchange(line, seconds) over the hub's shared handle on this cable."""
    import hub_probe
    import hub_usb

    def exchange(line, seconds):
        ent = hub_usb._usb_get(port)          # noqa: SLF001 - the shared manager
        with ent["lock"]:
            ent["last"] = time.time()
            ser = ent["ser"]
            hub_probe._drain_to_line_boundary(ser)        # noqa: SLF001
            ser.write((line + "\n").encode())
            return hub_probe._read_lines(ser, seconds + 1.0, quiet=0.3, at_least=seconds)  # noqa: SLF001
    return exchange


# QC swaps this to put a fake bus behind a port; real use is usb_link.
link_for = usb_link


class BusMapJob:
    """One check or repair of one cable, run on a thread of its own."""

    def __init__(self, port, fix):
        self.port, self.fix = port, fix
        self.state, self.step, self.error = "running", "starting", ""
        self.result = None
        self.started = time.time()
        self.finished = 0.0

    def start(self):
        threading.Thread(target=self._run, daemon=True).start()
        return self

    def _run(self):
        try:
            link = link_for(self.port)
            self.step = "looking at the cable"
            topo = bus_net.Topology(link).discover()
            moved, failed = [], []
            if self.fix and topo.duplicate_ids:
                self.step = "giving duplicate ids a free number"
                for bus, dup in sorted(topo.duplicate_ids.items()):
                    res = bus_ids.BusIds(topo.links[bus]).fix()
                    moved += [{"bus": bus, "chip": c, "to": n} for c, n in sorted(res["moved"].items())]
                    failed += [{"bus": bus, "chip": c} for c in res["failed"]]
                self.step = "checking again"
                topo = bus_net.Topology(link).discover()
            self.result = self.describe(topo, moved, failed)
            self.state = "done"
        except Exception as e:                       # noqa: BLE001
            self.state, self.error = "error", str(e)
        self.finished = time.time()

    @staticmethod
    def describe(topo, moved, failed):
        boards = sorted(topo.boards.items(), key=lambda kv: (kv[1]["bus"], kv[1]["id"]))
        buses = {}
        for chip, b in boards:
            buses.setdefault(b["bus"], {"bus": b["bus"], "boards": 0, "bridges": 0})
            buses[b["bus"]]["boards"] += 1
            buses[b["bus"]]["bridges"] += 1 if b["gateway"] else 0
        return {
            "boards": [dict(b, chip=c) for c, b in boards],
            "buses": list(buses.values()),
            "duplicates": [{"bus": bus, "id": i, "chips": chips}
                           for bus, d in sorted(topo.duplicate_ids.items())
                           for i, chips in sorted(d.items())],
            "loops": [{"chip": c, "paths": topo.routes.get(c, [])} for c in sorted({x[0] for x in topo.loops})],
            "tooDeep": topo.refused,
            "moved": moved, "failed": failed,
            "maxHops": bus_net.MAX_DEPTH,
        }

    def public(self):
        return {"ok": True, "state": self.state, "step": self.step, "error": self.error,
                "fix": self.fix, "seconds": round((self.finished or time.time()) - self.started, 1),
                "result": self.result}


class BusMapRoutes:
    _busmap_jobs = {}
    _busmap_lock = threading.Lock()

    def api_busmap(self, method, path, q):
        if path not in ("/api/busmap", "/api/busmap/check", "/api/busmap/fix"):
            return NOT_MINE
        port = (q.get("port") or [""])[0]
        jobs = BusMapRoutes._busmap_jobs
        if path == "/api/busmap":
            job = jobs.get(port)
            return self.send_json(job.public() if job else {"ok": True, "state": "none"})
        if method != "POST":
            return self.send_json({"ok": False, "error": "use POST"}, 405)
        if not port:
            return self.send_json({"ok": False, "error": "pick a cable first"}, 400)
        with BusMapRoutes._busmap_lock:
            old = jobs.get(port)
            if old and old.state == "running":
                return self.send_json(old.public())            # already on it
            job = jobs[port] = BusMapJob(port, fix=path.endswith("/fix")).start()
        return self.send_json(job.public())
