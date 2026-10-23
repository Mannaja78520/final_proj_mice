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

import gestures
import hub_video

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()
LINKS = None          # hub_video.Links, made on first use (QC swaps it)


def links():
    global LINKS
    if LINKS is None:
        LINKS = hub_video.Links(_hub.asset("config", "video_links.json"))
    return LINKS


def bind(hub):
    global _hub
    _hub = hub


def gesture_library(store_path=None):
    """(library as it is on this PC, this PC's own file). Read per call: an
    edit to config/gestures.json or a Studio save needs no restart."""
    path = _hub.asset("config", "gestures.json")
    shipped = (_hub.registry.load(path) if _hub.registry
               else json.loads(path.read_text(encoding="utf-8")))
    mine = (json.loads(store_path.read_text(encoding="utf-8")) if store_path.is_file() else {}) if store_path is not None else gestures.read_mine(_hub.STUDIO)
    return gestures.library(shipped, mine), mine


class StudioRoutes:
    def api_gestures(self, method, path, q):
        # ---- talk gestures (A46-1): the library, Studio's fit, a plan, play ----
        # Reading, planning and saving are Studio tools (open, like /api/save);
        # /api/gestures/play moves a robot and is gated (hub_auth GATED_POST).
        try:
            store_path = gestures.mine_path(_hub.STUDIO)
            lib, mine = gesture_library(store_path)
        except Exception as e:              # noqa: BLE001 - a broken file says so
            return self.send_err("config/gestures.json could not be read: %s" % e)
        if path == "/api/gestures" and method == "GET":
            return self.send_json({"ok": True, "lib": lib, "fit": mine.get("fit") or {},
                                   "file": str(gestures.mine_path(_hub.STUDIO).name),
                                   **gestures.character_state(_hub.STUDIO, store_path)})
        data = json.loads(self.body().decode() or "{}") if method == "POST" else {}
        if path in ("/api/gestures", "/api/gestures/fit") and method == "POST":
            change = {"fit": data} if path.endswith("/fit") else data
            if path.endswith("/fit") and not isinstance(data.get("gestures"), dict):
                return self.send_err("that does not look like a fit")
            with gestures._lock:
                state = gestures.character_state(_hub.STUDIO, store_path)
                if state["readOnly"]:
                    return self.send_err("Default is kept safe. Make a named copy in Voice first.", 409)
                if state["character"] and any(data.get(k) != state[k] for k in ("character", "gestureRevision")):
                    return self.send_err("The character changed. Reload the saved moves before saving.", 409)
                mine = gestures.merge_mine(gesture_library(store_path)[1], change)
                _hub.write_atomic(store_path, json.dumps(mine, indent=1))
            return self.send_json({"ok": True, "lib": gesture_library(store_path)[0], **gestures.character_state(_hub.STUDIO, store_path)})
        if path in ("/api/gestures/plan", "/api/gestures/play") and method == "POST":
            got = gestures.plan(lib, mine.get("fit"), data.get("text"), data.get("lang") or "",
                                data.get("manner") or "", data.get("event") or "",
                                data.get("ms") or 0, data.get("seed"))
            if path.endswith("/plan") or not got.get("ok"):
                return self.send_json(got)
            dev = str(data.get("dev") or "")
            if not dev:
                return self.send_err("which robot? (dev)")
            # Gestures never take over a show: a running one (not ours) wins.
            st = _hub.show.status()
            if st.get("running") and st.get("name") != "gestures":
                return self.send_json({"ok": False, "busy": True,
                                       "why": "the robot is playing " + str(st.get("name") or "a show")})
            try:
                _hub.show.start(dev, got["steps"], False, "gestures")
            except Exception as e:          # noqa: BLE001
                return self.send_err(e)
            return self.send_json(dict(got, playing=True))
        return self.send_err("no such gestures route", 404)

    def api_studio(self, method, path, q):
        if path.startswith("/api/gestures"):
            return self.api_gestures(method, path, q)
        # ---- studio: local storage ----
        if path == "/api/list":
            kind = (q.get("kind") or ["projects"])[0]
            folder = {"projects": _hub.PROJECTS, "sequences": _hub.SEQUENCES, "models": _hub.MODELS}.get(kind)
            if folder is None:
                return self.send_err("kind must be projects|sequences|models")
            if kind == "models" and (q.get("deep") or [""])[0] == "1":
                # A48-1: a URDF package keeps its file in <pkg>/urdf/ and its
                # meshes in <pkg>/meshes/, so the CAD look needs sub-folders
                files = sorted(p.relative_to(folder).as_posix()
                               for p in folder.rglob("*") if p.is_file())
            else:
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
            name = "character.yaml" if method == "POST" else _hub.safe_name((q.get("name") or [""])[0])
            try:
                if method == "POST":
                    length = int(self.headers.get("Content-Length") or 0)
                    if length < 0 or length > 3 * 1024 * 1024:
                        return self.send_err("that move is too large", 400)
                    text = json.loads(self.body().decode("utf-8")).get("text")
                    if not isinstance(text, str):
                        return self.send_err("that move could not be read", 400)
                else:
                    f = _hub.SEQUENCES / name
                    if not f.is_file():
                        return self.send_err("no sequence " + name, 404)
                    text = f.read_text(encoding="utf-8")
                got = _hub.seq_steps(text)
            except (ValueError, TypeError) as e:
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

        if path == "/api/rigpresets":
            # The BODIES Studio can be set to, from config/rig_presets.json
            # (A26-72). One of them is measured from the real STEP file, so
            # picking it is how somebody gets the robot's own arm lengths
            # without typing a number anywhere.
            if not _hub.registry:
                return self.send_json({"ok": False, "presets": []})
            return self.send_json({"ok": True,
                                   "presets": _hub.registry.rig_presets()})

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

        if path == "/api/rigcad" and method == "POST":
            # A48-6: "Use the CAD's sizes" (or putting the old shapes back)
            # pressed on one browser, kept here so every browser adopts it.
            # {at, parts} or {at, parts: null} for undone; a stamp per press.
            data = json.loads(self.body().decode())
            at, parts = data.get("at"), data.get("parts")
            if not isinstance(at, str) or not at or not (parts is None or isinstance(parts, dict)):
                return self.send_err("that does not look like rig parts from the CAD")
            _hub.write_atomic(_hub.RIG_CAD_FILE, json.dumps({"at": at, "parts": parts}, indent=1))
            return self.send_json({"ok": True, "at": at})

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

        r = self.api_video(method, path, q)
        if r is not NOT_MINE:
            return r
        return NOT_MINE

    def api_video(self, method, path, q):
        """Moves from a video (A44-8): a link fetched onto this PC, a picked
        file kept for its sound, and both served with Range so the page can
        seek. Fetching and keeping are gated (hub_auth): they write to this
        PC and reach the internet on someone's say-so. Reading is by an id
        nobody can guess, handed out only to whoever started the fetch."""
        if path == "/api/video/fetch" and method == "POST":
            d = json.loads(self.body().decode() or "{}")
            if d.get("cancel"):
                return self.send_json({"ok": links().cancel(str(d["cancel"]))})
            jid, why = links().start(str(d.get("url") or ""))
            if not jid:
                return self.send_err(why)
            return self.send_json({"ok": True, "id": jid, **links().status(jid)})
        if path == "/api/video/fetch":
            st = links().status((q.get("id") or [""])[0])
            if st is None:
                return self.send_err("no such video here (the hub was restarted?)", 404)
            return self.send_json({"ok": True, **st})
        if path == "/api/video/put" and method == "POST":
            try:
                n = max(0, int(self.headers.get("Content-Length") or 0))
                self._body_read = True
                jid = links().put(self.rfile.read, n, (q.get("name") or [""])[0])
            except ValueError as e:
                self.close_connection = True   # the unread body must not become a request
                return self.send_err(e, 413)
            return self.send_json({"ok": True, "id": jid})
        if path == "/api/video/sound" and method == "POST":
            d = json.loads(self.body().decode() or "{}")
            try:
                start, end = float(d.get("from") or 0), float(d.get("to") or 0)
            except (TypeError, ValueError):
                return self.send_err("from and to are seconds")
            f, why = links().sound(str(d.get("id") or ""), start, end)
            if not f:
                return self.send_err(why)
            return self.send_json({"ok": True, "size": f.stat().st_size})
        if path == "/api/video/file":
            kind = (q.get("kind") or [""])[0]
            f = links().path_of((q.get("id") or [""])[0], kind)
            if not f:
                return self.send_err("no such video here (the hub was restarted?)", 404)
            if self.command == "POST":
                self.drain()
            return hub_video.send_file(
                self, f, hub_video.TYPES.get(f.suffix.lower(), "application/octet-stream"))
        return NOT_MINE
