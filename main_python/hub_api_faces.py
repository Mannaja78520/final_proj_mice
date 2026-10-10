"""The hub's door to the face watcher's rules (system A8-1).

    GET  /api/faces/rules     the words, cameras and milestones, as the watcher has them
    POST /api/faces/rules     {rules}: save them (login - hub_auth GATED_POST)

The watcher (apps/faces/service.py) listens on this PC only and is the ONE
writer of apps/faces/rules.json: it checks the rules before it writes, and it
reads them again on the next arrival, so a save needs no restart. A page
anywhere on the WiFi saves through here, where the login is, and never talks
to the watcher itself.
"""
import json
import urllib.error
import urllib.request

NOT_MINE = object()
_hub = None


def bind(hub):
    global _hub
    _hub = hub


def watcher():
    """Where the watcher answers: config/faces.json, read per call (MICE_FACES_CONFIG
    points a check at its own watcher)."""
    import os
    from pathlib import Path
    path = Path(os.environ.get("MICE_FACES_CONFIG") or _hub.asset("config", "faces.json"))
    try:
        cfg = _hub.registry.load(path)
    except Exception:                                        # noqa: BLE001
        cfg = {}
    return str((cfg or {}).get("service") or "http://127.0.0.1:8769").rstrip("/")


def ask(method, body=None):
    """(answer, http code). The hub is a program on this PC to the watcher:
    JSON, and no Origin, which is exactly what the watcher lets in."""
    req = urllib.request.Request(watcher() + "/rules", method=method,
                                 data=json.dumps(body).encode("utf-8") if body is not None else None,
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=5) as r:
            return json.loads(r.read().decode("utf-8")), 200
    except urllib.error.HTTPError as e:
        try:
            return json.loads(e.read().decode("utf-8")), e.code
        except Exception:                                    # noqa: BLE001
            return {"ok": False, "error": "the face helper refused (%s)" % e.code}, 502
    except Exception as e:                                   # noqa: BLE001
        return {"ok": False, "watcherDown": True,
                "error": "the face helper is not running on this PC, so the rules "
                         "cannot be read or saved. Start it: python apps/faces/service.py",
                "detail": str(e)}, 503


class FacesRoutes:
    def api_faces(self, method, path, q):
        if path != "/api/faces/rules":
            return NOT_MINE
        if method == "POST":
            try:
                d = json.loads(self.body().decode() or "{}")
            except ValueError:
                return self.send_err("that request was not readable")
            got, code = ask("POST", d if isinstance(d, dict) else {})
        else:
            got, code = ask("GET")
        return self.send_json(got, code)
