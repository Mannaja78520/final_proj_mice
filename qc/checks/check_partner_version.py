"""Which version of the face app is installed, and does it still send what we
read (system A9).

* READ, NEVER RUN (A9-1). The commit comes from files in their .git: HEAD,
  then the branch file, then packed-refs - after a `git gc` the branch file is
  gone and the commit lives only in packed-refs. Running git in their folder
  would take locks under their own updater.
* CHECKED ON WHAT THEY SENT (A9-2). Their OpenAPI page lists HTTP paths and
  nothing else, so it is used for paths only; the fields of a live frame or a
  history row are checked on the real payload as it arrives.
* IT TELLS, AND CHANGES NOTHING (A9-3). A frame missing a field is still
  handled exactly as before; only the screen says so.
"""
import importlib.util
import json
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "the face app's version is read from files and only reported"
SHA = "f27a9d5" + "0" * 33


class Spec(BaseHTTPRequestHandler):
    def do_GET(self):                                        # noqa: N802
        raw = json.dumps({"paths": {"/api/health": {}, "/api/auth/login": {},
                                    "/api/history": {}}}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / rel.rsplit("/", 1)[0]))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    V = _load("_partner_version", "main_python/partner_version.py")
    src = (F.CODE / "main_python" / "partner_version.py").read_text(encoding="utf-8")
    t.ok("subprocess" not in src and "os.system" not in src,
         "it never runs a program (git) in their folder")

    root = Path(tempfile.mkdtemp(prefix="mice_ver_"))
    g = root / ".git"
    (g / "refs" / "heads").mkdir(parents=True)
    (g / "HEAD").write_text("ref: refs/heads/main\n", encoding="utf-8")
    (g / "refs" / "heads" / "main").write_text(SHA + "\n", encoding="utf-8")
    t.eq(V.commit(root)[:2], (SHA, "main"), "the commit is read through the branch file")
    (g / "refs" / "heads" / "main").unlink()
    (g / "packed-refs").write_text("# pack-refs with: peeled\n%s refs/heads/main\n" % SHA,
                                   encoding="utf-8")
    t.eq(V.commit(root)[0], SHA, "and through packed-refs once that file is gone")
    (g / "HEAD").write_text("abc1234def\n", encoding="utf-8")
    t.eq(V.commit(root)[:2], ("abc1234def", ""),
         "a detached HEAD, as their updater leaves it, is the commit itself")
    sha, _, why = V.commit(root / "nowhere")
    t.ok(sha == "" and why, "no .git is a reason, not a crash", why)

    srv = ThreadingHTTPServer(("127.0.0.1", 0), Spec)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    entry = {"name": "Reconize", "folder": str(root), "testedWith": ["abc1234"],
             "api": "http://127.0.0.1:%d" % srv.server_port, "health": "/api/health",
             "login": {"path": "/api/auth/login"},
             "count": {"path": "/api/reports/dashboard"},
             "events": [{"kind": "ws", "path": "/api/node/events-feed?token={token}"},
                        {"kind": "poll", "path": "/api/history?page={page}"}]}
    got = V.report(entry)
    t.ok(got["same"] and "tested with" in got["words"], "the tested commit is called that", got)
    t.ok(got["spec"]["checked"] and got["spec"]["missing"] == ["/api/reports/dashboard"],
         "an address we call that their list no longer has is named; the websocket "
         "is not judged by a list that cannot describe it", got["spec"])
    (g / "HEAD").write_text("ffff000\n", encoding="utf-8")
    got = V.report(entry)
    t.ok(not got["same"] and "updated" in got["words"] and "keeps working" in got["words"],
         "a newer version is reported, and the words say nothing turned off", got["words"])
    srv.shutdown()

    # ---- the watcher checks what really arrived ------------------------------
    S = _load("_faces_service_contract", "apps/faces/service.py")
    st = S.State("reconize")
    ws = st.ws_source()
    ev = st.from_ws(ws, {"name": "Ann", "participant_id": "P1", "at": "2026-10-10T10:00:00",
                         "checkin": "new"})
    t.ok(st.contract["ws"]["missing"] == ["node_id"],
         "a live frame without its camera field is noticed", st.contract)
    t.ok(ev["who"] == "Ann" and ev["camera"] == "",
         "and handled exactly as before - it only tells", ev)
    st.from_ws(ws, {"name": "Ann", "participant_id": "P1", "at": "x", "node_id": "door-1"})
    t.eq(st.snapshot()["contract"]["ws"]["missing"], [],
         "a complete frame clears it, and the screen reads it from /state")

    # ---- through the hub, with no login ------------------------------------
    base, _main = F.start_hub()
    F.logout_qc()
    code, body = F.get(base + "/api/partners/version?id=reconize")
    got = json.loads(body or "{}")
    t.ok(code == 200 and got.get("ok") and got.get("words"),
         "the hub answers which version is installed, no login needed", (code, body[:200]))
    code, page = F.get(base + "/app/faces/")
    t.contains(page, '"/api/partners/version?id="', "the Reconize screen shows it")
