"""How many people came today, the celebration at a milestone, and the two
verbs another program on this PC can use (system A6).

* THEIR COUNT IS THE TRUTH (A6-1). Their dashboard field is distinct
  recognised people since midnight (their api/reports.py:25). Ours - who this
  watcher saw - is the fallback and must say it is ours, because it forgets on
  a restart and never saw the morning before it started.
* A MILESTONE FIRES ONCE A DAY (A6-2), and still once after the watcher
  restarts: the fired list is its own file with one writer. Kept inside
  rules.json, the screen's next save would carry an old list back and the rig
  would celebrate the same hundred twice. A celebration the rig could not say
  is not marked fired, so it is said when it can be.
* ONE ADDRESS, ONE VERB (A6-3). POST /count and POST /act on the watcher.
  It listens on this PC only; a web page open on this PC is refused too.
"""
import importlib.util
import json
import sys
import tempfile
import threading
import urllib.error
import urllib.request
from datetime import datetime
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F


AREA = "hub"
TITLE = "today's count is theirs, a milestone fires once, and a program has one verb"


def _load(name, rel):
    sys.path.insert(0, str(F.CODE / "apps" / "faces"))
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Theirs(BaseHTTPRequestHandler):
    today = 7
    up = True

    def do_GET(self):                                        # noqa: N802
        if not Theirs.up:
            self.send_response(500)
            self.end_headers()
            return
        raw = json.dumps({"detected_today": Theirs.today}).encode()
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, *a):
        pass


def _post(url, body, headers):
    req = urllib.request.Request(url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return r.status, json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read().decode() or "{}")


def run(t):
    R = _load("_faces_rules_count", "apps/faces/rules.py")
    S = _load("_faces_service_count", "apps/faces/service.py")

    theirs = ThreadingHTTPServer(("127.0.0.1", 0), Theirs)
    threading.Thread(target=theirs.serve_forever, daemon=True).start()
    st = S.State("reconize")
    entry = st.partner()
    t.ok(entry.get("count", {}).get("field"), "the registry says where their count is")
    st._live = dict(entry, api="http://127.0.0.1:%d" % theirs.server_port)
    st._live_at = 10 ** 12          # keep the fake address: no re-probe
    st.token_now = lambda: ("tok", "")

    got = st.count_today()
    t.ok(got == {"today": 7, "from": "theirs", "means": entry["count"]["means"]},
         "their count is used, and named as theirs", got)

    Theirs.up = False
    st._count = None
    today = datetime.now().isoformat(timespec="seconds")
    for e in ({"who": "Ann", "id": "P1", "known": True, "when": today, "source": "ws"},
              {"who": "Ann", "id": "P1", "known": True, "when": today, "source": "poll"},
              {"who": "", "id": "", "known": False, "when": today, "source": "poll"},
              {"who": "Old", "id": "P0", "known": True, "when": "2020-01-01T10:00:00",
               "source": "poll"}):
        st.people.append(e)
    got = st.count_today()
    t.ok(got["from"] == "ours" and got["today"] == 1,
         "with their app down ours stands in, says so, and counts distinct known "
         "people today - not strangers, not yesterday", got)

    # ---- milestones -----------------------------------------------------
    rules, why = R.load()
    t.ok(not why and rules.get("milestones"), "the shipped rules carry a milestone", why)
    rules = json.loads(json.dumps(rules))
    rules["greet"] = True
    rules["milestones"] = [{"at": 100, "text": "hundred"}, {"at": 200, "text": "two hundred"}]
    fired = Path(tempfile.mkdtemp(prefix="mice_fired_")) / "fired.json"
    sent = []
    post = lambda g: (sent.append(g), ("queued", ""))[1]     # noqa: E731
    m = R.Milestones(fired, post)
    t.eq(m.tick(99, rules, "2026-10-10"), [], "99 people is not yet a hundred")
    m.tick(100, rules, "2026-10-10")
    t.ok(len(sent) == 1 and sent[0]["text"] == "hundred" and sent[0]["whenBusy"] == "queue",
         "a hundred celebrates once, and waits its turn rather than being dropped", sent)
    m.tick(150, rules, "2026-10-10")
    R.Milestones(fired, post).tick(160, rules, "2026-10-10")
    t.eq(len(sent), 1, "not again that day, even after the watcher restarts")
    R.Milestones(fired, post).tick(100, rules, "2026-10-11")
    t.eq(len(sent), 2, "and again the next day, when their count starts from zero")

    sent.clear()
    replies = ["skipped", "queued"]
    busy = lambda g: (sent.append(g), (replies.pop(0), "full"))[1]   # noqa: E731
    fired2 = fired.with_name("fired2.json")
    R.Milestones(fired2, busy).tick(100, rules, "2026-10-10")
    R.Milestones(fired2, busy).tick(100, rules, "2026-10-10")
    t.eq(len(sent), 2, "a celebration the rig could not say is said on the next try")
    rules["greet"] = False
    sent.clear()
    R.Milestones(fired.with_name("f3.json"), post).tick(500, rules, "2026-10-10")
    t.eq(sent, [], "with greeting off nothing celebrates either")
    t.ok("{name}" in R.milestones_check([{"at": 5, "text": "hi {name}"}]),
         "a milestone may not name anybody: it is about a crowd")

    # ---- the two verbs --------------------------------------------------
    calls = []
    st.greeter = R.Greeter(post=lambda g: (calls.append(g), ("queued", ""))[1])
    st._count = None
    S.Handler.state = st
    srv = ThreadingHTTPServer(("127.0.0.1", 0), S.Handler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_port
    js = {"Content-Type": "application/json"}
    code, got = _post(base + "/count", b"{}", js)
    t.ok(code == 200 and got.get("today") == 1, "POST /count answers today's count", got)
    code, got = _post(base + "/act", json.dumps({"say": "party", "module": "nong"}).encode(), js)
    t.ok(code == 200 and calls and calls[-1]["text"] == "party"
         and calls[-1]["module"] == "nong" and calls[-1]["whenBusy"] == "queue",
         "POST /act puts it in the rig's one speaking queue", (code, got, calls[-1:]))
    n = len(calls)
    code, _ = _post(base + "/act", json.dumps({"say": "x"}).encode(),
                    dict(js, Origin="https://evil.example"))
    t.ok(code == 403 and len(calls) == n, "a web page open on this PC is refused", code)
    code, _ = _post(base + "/act", b'{"say": "x"}', {"Content-Type": "text/plain"})
    t.ok(code == 403 and len(calls) == n,
         "and so is a form-like post, which a page can send without asking", code)
    code, got = _post(base + "/act", b"{}", js)
    t.ok(code == 400 and len(calls) == n, "an empty act says what to send", got)
    srv.shutdown()
    theirs.shutdown()
