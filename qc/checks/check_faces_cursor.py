"""Committed history delivery never loses a burst or revives an old sighting."""
import importlib.util
import json
import sys
import threading
from datetime import datetime, timedelta, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

import qc as F

AREA = "hub"
TITLE = "face history follows sequences and keeps camera observations honest"
SOLO = True


def _module(name, path):
    spec = importlib.util.spec_from_file_location(name, F.CODE / path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def run(t):
    faces = _module("cursor_faces_check", "apps/faces/service.py")
    voice = _module("cursor_voice_check", "apps/voice/service.py")
    from face_history import HistoryCursor, local_when
    stamp = datetime.now(timezone.utc)
    t.eq(local_when(stamp.isoformat()), local_when(stamp.astimezone(
        timezone(timedelta(hours=7))).isoformat()), "UTC and +07 identify the same local instant")
    t.eq(local_when(stamp.isoformat().replace("+00:00", "Z")),
         local_when(stamp.isoformat()), "Z denotes UTC rather than naive local time")
    naive = datetime.now()
    t.eq(local_when(naive.isoformat()), naive, "legacy naive times stay local")

    rows = [{"id": "legacy", "seq": None, "name": "Old Name"}]
    fail_after = [None]
    malformed = [False]
    requests = []

    class Handler(BaseHTTPRequestHandler):
        def log_message(self, *args):
            pass

        def do_GET(self):
            query = parse_qs(urlparse(self.path).query)
            after = int(query["after_seq"][0]) if "after_seq" in query else None
            requests.append(after)
            if after is not None and after == fail_after[0]:
                self.send_error(503)
                return
            selected = [r for r in rows if r["seq"] is not None
                        and (after is None or r["seq"] > after)]
            latest = max((r["seq"] for r in selected), default=after)
            batch = selected[:2] if after is not None else rows[-2:]
            doc = {"items": batch, "total": len(selected), "page_size": 2,
                   "latest_seq": latest}
            if after is not None:
                doc["next_after_seq"] = (batch[-1]["seq"] if batch else after) + int(malformed[0])
            body = json.dumps(doc).encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    entry = voice.registry.load(F.CODE / "config/partners.json")["reconize"]
    source = next(s for s in entry["events"] if s["kind"] == "poll")
    t.ok(bool(source.get("cursor")), "shipped Reconize registry enables sequence polling")
    entry["api"] = "http://127.0.0.1:%s" % server.server_port
    entry["events"] = [source]

    def add(seq, name=None, node="door", ago=0):
        rows.append({"id": "row-%s" % seq, "seq": seq, "name": name,
                     "participant_id": name, "call_as": name,
                     "status": "matched" if name else "unknown", "node_id": node,
                     "source": "camera_node", "detected_at": (datetime.now().astimezone()
                         - timedelta(seconds=ago)).isoformat()})

    try:
        state = faces.State("reconize")
        state.partners = {"reconize": entry}
        state.partner = lambda: entry
        state.entry = lambda: entry
        state.token_now = lambda: ("fake", "")
        fresh, why = state.poll_once()
        t.eq((fresh, why, state._history_cursor.after_seq), ([], "", 0),
             "null watermark bootstraps at zero without replaying legacy rows")
        for n in range(1, 6):
            add(n, "Person%s" % n)
        fresh, why = state.poll_once(max_pages=1)
        t.eq([e["seq"] for e in fresh], [1, 2], "page cap delivers the first page")
        t.eq(state._history_cursor.after_seq, 2, "partial burst never jumps to latest_seq")
        fresh, why = state.poll_once()
        t.eq([e["seq"] for e in fresh], [3, 4, 5], "next poll drains the remaining burst")
        add(6, "Delayed", ago=10000)
        add(7, node="door")
        add(8, "NoCamera", node=None)
        add(9, "Kiosk", node="kiosk")
        fresh, why = state.poll_once()
        by = {e["seq"]: e for e in fresh}
        t.eq(sorted(by), [6, 7, 8, 9], "old timestamps and strangers still count exactly once")
        t.eq((by[6]["node_id"], by[6]["camera"], by[6]["hasCamera"]),
             ("door", "", False), "delayed rows retain provenance without greeting")
        t.ok(by[7]["hasCamera"] and not by[7]["known"], "fresh unknown carries its real node")
        t.ok(not by[8]["hasCamera"] and not by[9]["hasCamera"], "null and kiosk are not physical cameras")
        add(10, "FutureHistory", ago=-600)
        state.poll_once()
        present = state.present(theirs=False)["people"]
        t.ok(not any(p["who"] in {"Delayed", "NoCamera", "Kiosk", "FutureHistory"} for p in present),
             "present excludes stale, future and non-camera history even without a camera filter")
        # A live kiosk copy may arrive before persistence knows the real node.
        state.note({"who": "Upgrade", "id": "Upgrade", "known": True,
                    "when": datetime.now().isoformat(), "camera": "kiosk", "source": "ws"})
        before_count = len(state.people)
        add(11, "Upgrade", node="real-door")
        fresh, why = state.poll_once()
        t.eq([e["who"] for e in fresh], ["Upgrade"], "real-node history hands an upgraded arrival to the greeter")
        t.eq(len(state.people), before_count, "camera upgrade does not recount the person")
        t.eq(fresh[0]["camera"], "real-door", "upgraded greeting uses the real station")
        for n in range(12, 17):
            add(n, "Person%s" % n)
        fail_after[0] = 13
        fresh, why = state.poll_once()
        t.eq([e["seq"] for e in fresh], [12, 13], "completed page is retained when next request fails")
        t.ok(bool(why), "HTTP failure is reported")
        t.eq(state._history_cursor.after_seq, 13, "HTTP error leaves cursor at last consumed row")
        fail_after[0] = None
        fresh, why = state.poll_once()
        t.eq([e["seq"] for e in fresh], [14, 15, 16], "retry does not skip or duplicate rows")
        add(17, "Later")
        malformed[0] = True
        fresh, why = state.poll_once()
        t.ok(bool(why) and not fresh and state._history_cursor.after_seq == 16,
             "malformed next cursor refuses the page without a time-window fallback")
        malformed[0] = False
        fresh, why = state.poll_once()
        t.eq([e["seq"] for e in fresh], [17], "valid retry recovers the refused row")

        reader = HistoryCursor()
        reader.after_seq = 0
        doc = {"items": [{"seq": 1}], "next_after_seq": 1}
        why = reader.poll(source, lambda path: (doc, ""),
                          lambda row: (_ for _ in ()).throw(ValueError("consumer failed")))
        t.ok(bool(why) and reader.after_seq == 0, "processing failure cannot advance the cursor")

        brain = voice.Brain.__new__(voice.Brain)
        brain.cfg = {"face": {"rememberSeconds": 120}}
        brain._reconize_entry = lambda: entry
        brain._reconize_login = lambda timeout=0: "fake"
        t.eq(brain._query_reconize_direct(), "", "Voice also bootstraps without replaying people")
        add(18, "Alice", node="A")
        add(19, "Bob", node="B")
        names = brain._query_reconize_direct()
        t.ok("Alice" in names and "Bob" in names, "Voice consumes both fresh real-node observations")
        add(20, node="A")
        names = brain._query_reconize_direct()
        t.ok("Alice" in names and "Bob" in names, "one unknown face cannot erase known companions")
        add(21, "Carol", node="A")
        rows[-1]["upload_id"] = "group-A"
        add(22, "Dan", node="A")
        rows[-1]["upload_id"] = "group-A"
        names = brain._query_reconize_direct()
        t.ok("Carol" in names and "Dan" in names, "separate face timestamps in one upload retain both people")
        brain._direct_observations = {key: obs for key, obs in brain._direct_observations.items() if key[0] == "B"}
        add(23, "OldAlice", node="A", ago=1000)
        add(24, "Future", node="A", ago=-600)
        t.eq(brain._query_reconize_direct(), "Bob", "late and future rows cannot revive a badge")
        fail_after[0] = 24
        t.eq(brain._query_reconize_direct(), "Bob", "outage preserves a valid observation")
        brain._direct_observations[("B", "Bob")]["when"] -= timedelta(seconds=121)
        t.eq(brain._query_reconize_direct(), "", "outage cannot extend observation expiry")
        fail_after[0] = None
        entry["api"] += "/new-database"
        t.eq(brain._query_reconize_direct(), "", "endpoint change bootstraps a different database")
        t.ok(requests[-1] is None, "new endpoint does not reuse the former sequence")
    finally:
        server.shutdown()
        server.server_close()
