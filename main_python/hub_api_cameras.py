"""The hub's one list of cameras (user 2026-11-23), and adding / removing them.

    GET  /api/cameras                every camera: ESP32-CAM boards, this PC's
                                     webcams, links and demo cameras people added
         ?face=1                     only the ones the face watcher reads
    GET  /api/cameras/kinds          what kinds can be added (config/cameras.json)
    POST /api/cameras/add            {name, kind, value}  (login)
    POST /api/cameras/remove         {id}                 (login)
    POST /api/cameras/face           {dev, on}            (login)

Pictures are not here: any camera in the list is watched at
/api/dev/cam.stream?dev=<dev> (live) and /api/dev/cam.jpg?dev=<dev> (one
picture), the same URLs boards always had, so every page and program reads
every camera the same way.
"""
import json

import cam_relay
import cam_sources

NOT_MINE = object()
_hub = None


def bind(hub):
    global _hub
    _hub = hub
    cam_sources.bind(hub)


def boards():
    """ESP32 cameras by WiFi, and the ones only a cable reaches."""
    out, seen = [], set()
    try:
        mods = _hub.scan_modules(False)
    except Exception:                                        # noqa: BLE001
        mods = []
    for m in mods:
        if m.get("type") == "cam" and m.get("ip"):
            seen.add(str(m.get("chip") or m.get("id")))
            out.append({"dev": "wifi:" + m["ip"], "name": m.get("name"), "id": m.get("id")})
    try:
        for u in _hub.probe_usb_all(False):
            m = u.get("module")
            if m and m.get("type") == "cam" and str(m.get("chip") or m.get("id")) not in seen:
                out.append({"dev": "usb:" + u["port"], "name": m.get("name"), "id": m.get("id")})
    except Exception:                                        # noqa: BLE001
        pass
    return out


class CamerasRoutes:
    def api_cameras(self, method, path, q):
        if not path.startswith("/api/cameras"):
            return NOT_MINE
        if path == "/api/cameras" and method == "GET":
            rows = cam_sources.listing(
                boards(), cam_relay.pc_devices(_hub.hub_api_faces.pc_camera()))
            if (q.get("face") or [""])[0] == "1":
                rows = [r for r in rows if r["face"]]
            return self.send_json({"ok": True, "cameras": rows})
        if path == "/api/cameras/kinds" and method == "GET":
            kinds = cam_sources.config().get("kinds") or {}
            return self.send_json({"ok": True, "kinds": [
                {"kind": k, "label": v.get("label", k), "hint": v.get("hint", ""),
                 "needs": v.get("needs", "")} for k, v in kinds.items()]})
        if method != "POST" or path not in ("/api/cameras/add", "/api/cameras/remove",
                                             "/api/cameras/face"):
            return NOT_MINE
        try:
            d = json.loads(self.body().decode() or "{}")
        except ValueError:
            return self.send_err("that request was not readable")
        if not isinstance(d, dict):
            return self.send_err("that request was not readable")
        if path == "/api/cameras/add":
            src, why = cam_sources.add(d.get("name"), str(d.get("kind") or ""),
                                       str(d.get("value") or ""))
            if why:
                return self.send_err(why)
            return self.send_json({"ok": True, "dev": "cam:" + src["id"], "id": src["id"]})
        if path == "/api/cameras/remove":
            if not cam_sources.remove(str(d.get("id") or "")):
                return self.send_err("no added camera has that id", 404)
            return self.send_json({"ok": True})
        dev = str(d.get("dev") or "")
        if not dev or len(dev) > 200:
            return self.send_err("which camera?")
        cam_sources.set_face(dev, bool(d.get("on")))
        return self.send_json({"ok": True})
