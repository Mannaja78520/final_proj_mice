"""The hub's routes for Nong Studio's files, shared settings and the list of hubs.

Moved out of main.py's Handler.api() on 2026-09-22 (A26-93). Handler inherits
StudioRoutes, and api() asks it before carrying on down its own chain. Names
that live in main.py are read late through _hub, so a check that swaps
main.<name> reaches this code too.
"""
import json
import socket
import time
import urllib.request

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


class StudioRoutes:
    def api_studio(self, method, path, q):
        # ---- studio: local storage ----
        if path == "/api/list":
            kind = (q.get("kind") or ["projects"])[0]
            folder = {"projects": _hub.PROJECTS, "sequences": _hub.SEQUENCES, "models": _hub.MODELS}.get(kind)
            if folder is None:
                return self.send_err("kind must be projects|sequences|models")
            files = sorted(p.name for p in folder.iterdir() if p.is_file())
            return self.send_json({"ok": True, "files": files})

        if path == "/api/load":
            name = _hub.safe_name((q.get("name") or [""])[0])
            f = _hub.PROJECTS / name
            if not f.is_file():
                return self.send_err("no project " + name, 404)
            return self.send_bytes(f.read_bytes())

        if path == "/api/loadseq":
            name = _hub.safe_name((q.get("name") or [""])[0])
            f = _hub.SEQUENCES / name
            if not f.is_file():
                return self.send_err("no sequence " + name, 404)
            return self.send_bytes(f.read_bytes(), "text/yaml; charset=utf-8")

        if path == "/api/seqdelete" and method == "POST":
            # Asked 2026-09-17: *make can edit and delete the yaml too*. Moved
            # into sequences/.deleted/ with a time stamp, never erased: a show
            # is a person's work and a mis-click must be recoverable by hand.
            data = json.loads(self.body().decode() or "{}")
            try:
                name = _hub.safe_name(str(data.get("name") or ""))
            except ValueError:
                name = ""
            f = _hub.SEQUENCES / name
            if not name or not f.is_file():
                return self.send_err("no saved sequence called " + name, 404)
            bin_ = _hub.SEQUENCES / ".deleted"
            bin_.mkdir(exist_ok=True)
            dest = bin_ / (time.strftime("%Y%m%d-%H%M%S_") + name)
            f.replace(dest)
            return self.send_json({"ok": True, "file": name,
                                   "kept": ".deleted/" + dest.name})

        if path == "/api/seqsteps":
            # The same file loadseq serves, PARSED for POST /api/play - the
            # voice answer that moves a robot needs steps, not yaml text.
            # Reads only, so it is ungated like loadseq; starting the show
            # still goes through gated /api/play.
            name = _hub.safe_name((q.get("name") or [""])[0])
            f = _hub.SEQUENCES / name
            if not f.is_file():
                return self.send_err("no sequence " + name, 404)
            try:
                got = _hub.seq_steps(f.read_text(encoding="utf-8"))
            except ValueError as e:
                return self.send_err("cannot play %s: %s" % (name, e))
            if len(got["steps"]) < 2:
                return self.send_err(
                    "%s has fewer than two poses - nothing to play" % name)
            return self.send_json({"ok": True, "file": name, **got})

        if path == "/api/save" and method == "POST":
            data = json.loads(self.body().decode())
            name = _hub.safe_name(data["name"])
            if not name.endswith(".json"):
                name += ".json"
            existed = (_hub.PROJECTS / name).exists()
            _hub.write_atomic(_hub.PROJECTS / name,
                         json.dumps(data["project"], indent=1))
            # `existed` goes back so the editor can say "replaced my_move.json"
            # rather than letting a name collision pass in silence. The default
            # name in the editor is "my_move", so saving over someone else's
            # project is one careless click.
            return self.send_json({"ok": True, "file": name, "replaced": existed})

        if path == "/api/model/upload" and method == "POST":
            name = _hub.safe_name((q.get("name") or [""])[0])
            if not name.lower().endswith(_hub.UPLOAD_EXT):
                return self.send_err("allowed: " + " ".join(_hub.UPLOAD_EXT))
            (_hub.MODELS / name).write_bytes(self.body())
            return self.send_json({"ok": True, "file": name})

        if path == "/api/rigdefault" and method == "POST":
            # "Make this the factory default": the browser is the ONLY place the
            # live rig exists, so it posts it here to be written into the repo.
            # Every fresh browser then starts on it, and Reset returns to it.
            data = json.loads(self.body().decode())
            rig = data.get("rig")
            if not isinstance(rig, dict) or "min" not in rig:
                return self.send_err("that does not look like a rig")
            # The tuned rig is the most expensive thing in this project to
            # rebuild by hand, so it never gets truncated in place.
            _hub.write_atomic(_hub.STUDIO / "rig_default.json", json.dumps(rig, indent=1))
            return self.send_json({"ok": True, "file": "rig_default.json",
                                   "keys": len(rig)})

        if path == "/api/settings" and method == "POST":
            # Studio's whole setup, parked on THIS hub so another PC can pull
            # it. The browser is the only place these settings live (they are
            # localStorage keys), so the page has to hand them over.
            data = json.loads(self.body().decode())
            bundle = data.get("bundle")
            if not isinstance(bundle, dict) or "rig" not in bundle:
                return self.send_err("that does not look like a settings bundle")
            bundle["savedAt"] = time.strftime("%Y-%m-%d %H:%M:%S")
            bundle["savedBy"] = socket.gethostname()
            _hub.write_atomic(_hub.SETTINGS_FILE, json.dumps(bundle, indent=1))
            return self.send_json({"ok": True, "savedAt": bundle["savedAt"]})

        if path == "/api/settings":
            if not _hub.SETTINGS_FILE.is_file():
                return self.send_json({"ok": False,
                                       "why": "no settings have been shared from this PC yet"})
            return self.send_bytes(_hub.SETTINGS_FILE.read_bytes(), _hub.MIME[".json"])

        if path == "/api/settings/peer":
            # Fetch another PC's settings THROUGH this hub, not from the
            # browser. A page served by this hub cannot read another hub's
            # response directly — that is a cross-origin request and the
            # browser blocks it. The hub has no such rule, so it does the
            # fetching and hands the result back same-origin.
            host = (q.get("host") or [""])[0].strip()
            if not host:
                return self.send_err("need host=<ip or name of the other PC>")
            if ":" not in host:
                host += ":%d" % _hub.PORT
            try:
                with urllib.request.urlopen("http://%s/api/settings" % host, timeout=6) as r:
                    body = r.read()
            except Exception as e:  # noqa: BLE001
                return self.send_err("cannot reach %s (%s)" % (host, type(e).__name__))
            return self.send_bytes(body, _hub.MIME[".json"])

        # A hub the sweep cannot reach, named by a person. Gated: it changes
        # what this hub talks to.
        if path in ("/api/hubs/add", "/api/hubs/forget") and method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
                have = _hub.remember_hub(d.get("ip"), forget=path.endswith("forget"))
                return self.send_json({"ok": True, "hubs": have})
            except Exception as e:                 # noqa: BLE001
                return self.send_err(e)

        if path == "/api/hubs":
            # Other mice hubs on this network, so nobody has to type an IP.
            return self.send_json({"ok": True, "known": _hub.known_hubs(),
                                   "hubs": _hub.scan_hubs(
                                       (q.get("force") or ["0"])[0] == "1")})

        return NOT_MINE
