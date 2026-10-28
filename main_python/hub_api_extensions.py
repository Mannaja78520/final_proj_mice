"""The hub's routes for this PC's apps: list, add, remove, restore, update (A51-2).

User 2026-10-27: the hub is the centre; an app is added by pointing at its
folder (or by its own installer calling the same route), removed by taking it
off this PC's list, and updated from the hub. The logic is extensions.py;
this file only checks who may ask and answers.

Changing the list needs a hub login, or the hub's own page on this PC - the
same rule as starting a partner program (hub_api_apps.start_refused). Reading
it is open like /api/apps: there is nothing secret in a folder name.
"""
import json

NOT_MINE = object()   # no route here matched: api() carries on
_hub = None           # the main module, set by bind()


def bind(hub):
    global _hub
    _hub = hub


def listing():
    """Every app the hub knows, with whether this PC shows it, plus the
    partners and the folders that hold an app not added yet."""
    ext = _hub.EXT
    partners = _hub.read_partners().get("partners") or {}
    shown = {a.get("id") for a in _hub.hub_apps()}
    apps = [{"id": a.get("id"), "name": a.get("name"), "icon": a.get("icon"),
             "blurb": a.get("blurb"), "needs": a.get("needs") or "",
             "shown": a.get("id") in shown, "added": bool(a.get("added"))}
            for a in _hub.hub_apps(everything=True)]
    outside = [{"id": k, "name": v.get("name") or k, "folder": v.get("folder") or "",
                "installed": bool(v.get("installed")),
                "update": bool(ext.update_command(k, v)[1])}
               for k, v in partners.items() if isinstance(v, dict)]
    st = ext.state()
    return {"ok": True, "apps": apps, "partners": outside, "hidden": st["hidden"],
            "added": st["added"], "found": ext.candidates()}


class ExtensionRoutes:
    def _ext_body(self):
        try:
            return json.loads(self.body(65536).decode() or "{}")
        except ValueError:
            return {}

    def api_extensions(self, method, path, q):
        if not path.startswith("/api/extensions"):
            return NOT_MINE
        if path == "/api/extensions" and method == "GET":
            return self.send_json(listing())
        refused = self.start_refused(method)       # POST, logged in or this PC
        if refused is not None:
            return refused
        d = self._ext_body()
        ext = _hub.EXT
        try:
            if path == "/api/extensions/add":
                got = ext.add(d.get("folder") or "")
                return self.send_json({"ok": True, "app": got, "list": listing()})
            if path == "/api/extensions/remove":
                ext.remove(d.get("id") or "")
                return self.send_json({"ok": True, "list": listing()})
            if path == "/api/extensions/restore":
                ext.restore(d.get("id") or "")
                return self.send_json({"ok": True, "list": listing()})
            if path == "/api/extensions/update":
                pid = d.get("id") or ""
                entry = (_hub.read_partners().get("partners") or {}).get(pid)
                return self.send_json(ext.update(pid, entry))
            if path == "/api/extensions/pick":
                return self.send_json(self._pick_folder())
        except ValueError as e:
            return self.send_json({"ok": False, "error": str(e)})
        return self.send_err("no such route: " + path, 404)

    def _pick_folder(self):
        """The PC's own folder dialog, for a person sitting at this PC. A
        phone cannot open a dialog on the PC, so it types the folder."""
        if not _hub.is_self(self.client_address[0]):
            return {"ok": False, "error": "the folder dialog opens only on the PC itself"}
        try:
            import tkinter
            from tkinter import filedialog
            root = tkinter.Tk()
            root.withdraw()
            root.attributes("-topmost", True)
            folder = filedialog.askdirectory(title="Choose the app's folder")
            root.destroy()
        except Exception as e:                              # noqa: BLE001
            return {"ok": False, "error": "no folder dialog here (%s): type the folder" % e}
        return {"ok": bool(folder), "folder": folder or ""}
