"""The hub's routes for theme packs: list, install, remove, and a pack's pictures.

User 2026-11-23: themes work like VS Code extensions. The logic is
theme_packs.py; this file checks who may change the list and answers.
Reading the list and the pictures is open (a login page needs its colours);
installing or removing needs a hub login or the hub's own page on this PC, the
same rule as hub_api_extensions.
"""
import json

import theme_packs

NOT_MINE = object()
_hub = None
PACK_LIMIT = theme_packs.MAX_PACK + 4096


def bind(hub):
    global _hub
    _hub = hub


def packs():
    return _hub.THEME_PACKS


def shared_css_extra():
    """The packs as CSS, appended to /mice.css (hub only, never in a board's flash)."""
    return packs().css().encode("utf-8")


def version():
    """Changes whenever a pack is installed or removed: pages refetch the CSS."""
    return str(len(packs().css()))


class ThemeRoutes:
    def api_themes(self, method, path, q):
        if not path.startswith("/api/themes"):
            return NOT_MINE
        if path == "/api/themes" and method == "GET":
            return self.send_json({"ok": True, "themes": packs().listing()})
        if path == "/api/themes/images" and method == "GET":
            return self.send_json({"ok": True, "images": packs().images((q.get("id") or [""])[0])})
        refused = self.start_refused(method)
        if refused is not None:
            return refused
        try:
            if path == "/api/themes/install":
                new_id = packs().install(self.body(PACK_LIMIT))
                return self.send_json({"ok": True, "id": new_id, "themes": packs().listing()})
            if path == "/api/themes/remove":
                d = json.loads(self.body(65536).decode() or "{}")
                packs().remove(str(d.get("id") or ""))
                return self.send_json({"ok": True, "themes": packs().listing()})
        except (ValueError, theme_packs.ThemePackError) as e:   # ThemePackError is a ValueError
            return self.send_json({"ok": False, "error": str(e)})
        return self.send_err("no such route: " + path, 404)

    def theme_file(self, path):
        """GET /themes/<id>/<file>: a picture a pack names. None when not this route."""
        if not path.startswith("/themes/"):
            return NOT_MINE
        parts = path.split("/")
        got = packs().file(parts[2], parts[3]) if len(parts) == 4 else None
        if not got:
            return self.send_err("no such picture", 404)
        data, ext = got
        return self.send_bytes(data, _hub.MIME.get(ext, "application/octet-stream"))
