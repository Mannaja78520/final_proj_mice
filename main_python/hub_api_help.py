"""Read-only help for the apps currently shown in the Hub's Tools list."""
import json
from pathlib import Path
import re

LANGS = ("th", "en", "zh", "ja")
GROUPS = {"start", "use", "build", "wrong"}
SLUG = re.compile(r"[a-z0-9][a-z0-9_-]*")
SHOT = re.compile(r"(th|en|zh|ja)-(light|dark)-[a-z0-9][a-z0-9_-]*\.webp")
NOT_MINE = object()


class AppHelp:
    def __init__(self, hub):
        self.hub = hub

    @staticmethod
    def read(root, anchor):
        try:
            data = json.loads((root / "help.json").read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                return None
            titles, summaries = data.get("title"), data.get("summary")
            if not all(isinstance(x, dict) and all(isinstance(x.get(code), str)
                       and x[code].strip() for code in LANGS) for x in (titles, summaries)):
                return None
            if data.get("group") not in GROUPS or type(data.get("order")) is not int:
                return None
            if not all((root / (code + ".html")).is_file() for code in LANGS):
                return None
            return dict(anchor=anchor, title=titles, summary=summaries,
                        group=data["group"], order=data["order"])
        except (OSError, ValueError, TypeError):
            return None

    def available(self):
        partners = self.hub.read_partners().get("partners") or {}
        found = {}
        for app in self.hub.hub_apps():
            app_id = app["id"]
            anchor = app.get("help") or app_id
            if not app.get("show", True) or not SLUG.fullmatch(app_id):
                continue
            if not isinstance(anchor, str) or not SLUG.fullmatch(anchor):
                continue
            partner = partners.get(app.get("needs")) or {}
            folder = partner.get("folder")
            roots = [app["manifest_dir"] / "help"]
            if folder:
                roots.insert(0, Path(folder) / "help")
            for root in roots:
                meta = self.read(root, anchor)
                if meta:
                    found[app_id] = (root, dict(meta, id=app_id))
                    break
        return found

    @staticmethod
    def asset(root, rel):
        if rel in {code + ".html" for code in LANGS}:
            mime = "text/plain; charset=utf-8"
        elif rel.startswith("img/") and SHOT.fullmatch(rel[4:]):
            mime = "image/webp"
        else:
            return None
        try:
            resolved = (root / rel).resolve()
            if resolved.is_relative_to(root.resolve()):
                return resolved.read_bytes(), mime
        except (OSError, ValueError, RuntimeError):
            pass
        return None


class HelpRoutes:
    def api_help(self, method, path, q):
        if path == "/api/help/apps" and method == "GET":
            apps = [meta for _, meta in self.app_help.available().values()]
            apps.sort(key=lambda app: (app["order"], app["id"]))
            return self.send_json({"ok": True, "apps": apps})
        if method != "GET" or not path.startswith("/api/help/apps/"):
            return NOT_MINE
        app_id, _, rel = path[len("/api/help/apps/"):].partition("/")
        match = self.app_help.available().get(app_id)
        asset = match and self.app_help.asset(match[0], rel)
        if asset is None:
            return self.send_err("Help file not found", 404)
        return self.send_bytes(*asset, headers=[("X-Content-Type-Options", "nosniff")])
