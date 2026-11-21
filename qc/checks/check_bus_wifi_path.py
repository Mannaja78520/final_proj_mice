"""A board behind a bridge is commanded over WiFi: wifi:<ip>:>12>7.

The bridge board's /api/cmd answers "-> sent"; the real reply is read from its
/api/busreplies list. This fake board mimics exactly that contract (see
RS485Bus::repliesSince) in front of a simulated bus; the hub side is the real
dev_cmd / parse_dev / wifi_path_cmd. Files and status must refuse, not hit the
wrong board.
"""
import http.server
import socketserver
import sys
import threading
import urllib.parse
from pathlib import Path

import qc as F

AREA = "connection"
TITLE = "commands reach a board behind a bridge over WiFi (wifi:IP:>12>7)"

ROOT = Path(F.__file__).resolve().parents[2]


def run(t):
    for p in (ROOT / "qc" / "lib", ROOT / "main_python"):
        if str(p) not in sys.path:
            sys.path.insert(0, str(p))
    from bus_sim import Board, Bus, Gateway
    import main as hub

    back = Bus([Board("B0000000%04X" % i, i) for i in range(1, 11)])
    top = Bus([Board("A0000000%04X" % i, i) for i in range(1, 4)] + [Gateway("A1000000AAAA", 12, down=back)])
    state = {"seq": 0, "rows": [], "cmds": []}
    lock = threading.Lock()

    class H(http.server.BaseHTTPRequestHandler):
        def log_message(self, *a):
            pass

        def do_GET(self):
            u = urllib.parse.urlparse(self.path)
            q = urllib.parse.parse_qs(u.query)
            body = ""
            if u.path == "/api/cmd":
                c = q["c"][0]
                state["cmds"].append(c)
                for d, tx in sorted(top.frames(c)):
                    if tx.startswith("@"):
                        with lock:
                            state["seq"] += 1
                            state["rows"].append((state["seq"], tx))
                body = "-> sent, the reply appears when it answers"
            elif u.path == "/api/busreplies":
                after = int(q.get("after", ["0"])[0])
                with lock:
                    body = "".join("%d %s\n" % (n, tx) for n, tx in state["rows"][-8:] if n > after)
            data = body.encode()
            self.send_response(200)
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

    srv = socketserver.ThreadingTCPServer(("127.0.0.1", 0), H)
    srv.daemon_threads = True
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    ip = "127.0.0.1:%d" % srv.server_address[1]
    try:
        kind, host, bus, peer = hub.parse_dev("wifi:%s:>12>7" % ip)
        t.ok((kind, host, bus) == ("wifi", ip, ">12>7"), "wifi:ip:>12>7 parses to a path", str((kind, host, bus)))
        t.ok(hub.parse_dev("wifi:%s" % ip)[2] == 0, "a plain wifi address is unchanged")
        r = hub.dev_cmd("wifi:%s:>12>7" % ip, "SET ID 7", wait=3)
        t.ok(r == "OK id=7", "the board behind the bridge answered over WiFi (%r)" % r)
        t.ok(state["cmds"][-1] == "#>12>7 SET ID 7", "the bridge board was handed a path line", state["cmds"][-1])
        r = hub.dev_cmd("wifi:%s:>12>7" % ip, "SET ID 7", wait=3)
        t.ok(r == "OK id=7", "a second command is not answered by the first one's reply")
        try:
            hub.dev_cmd("wifi:%s:>12>99" % ip, "SET ID 7", wait=0.5)
            t.ok(False, "a path to nothing times out")
        except TimeoutError as e:
            t.ok(">12>99" in str(e), "a path to nothing times out and names the path", str(e))
        for fn, args in ((hub.dev_status, ()), (hub.dev_files, ("/",))):
            try:
                fn("wifi:%s:>12>7" % ip, *args)
                t.ok(False, "%s refuses a path over WiFi" % fn.__name__)
            except ValueError:
                t.ok(True, "%s refuses a path over WiFi instead of reading the wrong board" % fn.__name__)
    finally:
        srv.shutdown()

    cpp = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    web = (F.FIRMWARE / "src" / "core" / "WebPortal.cpp").read_text(encoding="utf-8")
    t.contains(cpp, "String RS485Bus::repliesSince", "firmware keeps the last replies")
    t.contains(web, '"/api/busreplies"', "firmware serves them at /api/busreplies")
