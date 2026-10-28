"""This PC's apps as extensions: what is installed here, where, how to update (A51-2).

User 2026-10-27: the hub is the centre, and every venue PC may have a
different set - no face app, no photo booth, no prize machine - or one more
than ours. So nothing here is a fixed list:

  * an app folder says what it is with ONE file, `mice-app.json`
    (docs/extensions.md). A friend's app without that file is recognised by
    our template for it: its entry in config/partners.json and that entry's
    "detect" list, because we never write into a friend's folder;
  * what is installed on THIS PC lives in extensions.json beside
    hub_auth.json: never in git, never promoted, one per machine;
  * "remove" only takes an app off this PC's list (it hides a shipped one);
    nothing on disk is deleted;
  * a partner's folder may be written {data}/... or {parent}/... so the repo
    can move or be renamed (code -> mice_system) without breaking it.
"""
import json
import os
import re
import subprocess
import time
from pathlib import Path

MANIFEST = "mice-app.json"     # the one file an app keeps in its own folder
OUR_MANIFEST = "app.json"      # the same idea for apps inside our apps/ folder
UPDATE_TIMEOUT = 300           # a git pull over a slow venue network
# an update must not flash a console window over the venue screen
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0


def _jsonc(text):
    # registry files may carry // comments; a line comment only, never in a string
    return json.loads(re.sub(r"(?m)^\s*//.*$", "", text))


def _slug(name):
    s = re.sub(r"[^a-z0-9-]+", "-", str(name).lower()).strip("-")
    return s or "app"


class Extensions:
    """One PC's installed apps. Pure logic: the hub hands in its paths."""

    def __init__(self, store, data_root, partners=lambda: {}, apps=lambda: []):
        self.store = Path(store)
        self.data_root = Path(data_root)
        self.partners = partners       # () -> raw config/partners.json entries
        self.apps = apps               # () -> the registry's shipped apps

    # ---- this PC's list -----------------------------------------------------
    def state(self):
        try:
            got = _jsonc(self.store.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            got = {}
        return {"version": 1, "added": dict(got.get("added") or {}),
                "hidden": list(got.get("hidden") or [])}

    def _save(self, st):
        self.store.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.store.with_name(self.store.name + ".tmp")
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            json.dump(st, f, ensure_ascii=False, indent=2)
        os.replace(tmp, self.store)

    # ---- folders --------------------------------------------------------------
    def expand(self, folder):
        """{data} is the hub's own tree, {parent} the folder it sits in."""
        if not folder:
            return ""
        return (str(folder).replace("{data}", str(self.data_root))
                .replace("{parent}", str(self.data_root.parent))
                .replace("{home}", str(Path.home())))

    def detect(self, folder):
        """What app this folder holds, or None. Their own file wins over ours."""
        f = Path(self.expand(folder)).expanduser()
        if not f.is_dir():
            return None
        for name, source in ((MANIFEST, "their mice-app.json"),
                             (OUR_MANIFEST, "app.json")):
            man = f / name
            if man.is_file():
                try:
                    cfg = _jsonc(man.read_text(encoding="utf-8"))
                except (OSError, ValueError) as e:
                    return {"id": _slug(f.name), "folder": str(f), "error":
                            "%s could not be read (%s)" % (man, e)}
                return {"id": _slug(cfg.get("id") or f.name), "kind": cfg.get("kind") or "app",
                        "name": cfg.get("name") or f.name, "folder": str(f),
                        "source": source, "manifest": cfg}
        for pid, entry in (self.partners() or {}).items():
            need = entry.get("detect") if isinstance(entry, dict) else None
            if need and all((f / rel).exists() for rel in need):
                return {"id": pid, "kind": "partner", "name": entry.get("name") or pid,
                        "folder": str(f), "source": "config/partners.json"}
        return None

    # ---- add / remove / restore ---------------------------------------------------
    def add(self, folder):
        got = self.detect(folder)
        if not got:
            raise ValueError("no app found in %s" % folder)
        if got.get("error"):
            raise ValueError(got["error"])
        st = self.state()
        st["added"][got["id"]] = {"folder": got["folder"], "kind": got["kind"],
                                  "name": got["name"], "source": got["source"],
                                  "at": time.strftime("%Y-%m-%d %H:%M:%S")}
        st["hidden"] = [x for x in st["hidden"] if x != got["id"]]
        self._save(st)
        return got

    def remove(self, app_id):
        """Off this PC's list. A shipped app or a partner is hidden; nothing
        on disk is touched."""
        st = self.state()
        st["added"].pop(app_id, None)
        if app_id not in st["hidden"] and (app_id in self._shipped_ids()
                                           or app_id in (self.partners() or {})):
            st["hidden"].append(app_id)
        self._save(st)

    def restore(self, app_id):
        st = self.state()
        st["hidden"] = [x for x in st["hidden"] if x != app_id]
        self._save(st)

    def _shipped_ids(self):
        return {a.get("id") for a in (self.apps() or [])}

    # ---- what the hub shows ---------------------------------------------------------
    def partner(self, pid, entry):
        """The partner entry as THIS PC has it: its folder (this PC's choice
        first), and whether it is here at all."""
        if not isinstance(entry, dict):
            return entry
        st = self.state()
        out = dict(entry)
        mine = st["added"].get(pid) or {}
        out["folder"] = self.expand(mine.get("folder") or entry.get("folder") or "")
        out["installed"] = (pid not in st["hidden"]
                            and bool(out["folder"]) and Path(out["folder"]).is_dir())
        return out

    def visible(self, app, partners):
        """An app is listed unless this PC removed it, or the partner it
        needs ("needs" in its app.json) is not installed here."""
        if app.get("id") in self.state()["hidden"]:
            return False
        need = app.get("needs")
        if need:
            p = (partners or {}).get(need)
            return bool(isinstance(p, dict) and p.get("installed"))
        return True

    def extra_apps(self):
        """Web apps added from folders outside apps/ (kind "app" with a page)."""
        out = []
        for app_id, e in self.state()["added"].items():
            if e.get("kind") != "app":
                continue
            got = self.detect(e.get("folder"))
            if not got or got.get("error"):
                continue
            cfg = got["manifest"]
            out.append({"id": app_id, "name": cfg.get("name") or app_id,
                        "blurb": cfg.get("blurb") or "", "icon": cfg.get("icon") or "",
                        "order": cfg.get("order", 100), "help": cfg.get("help") or "",
                        "needs": cfg.get("needs") or "", "entry": cfg.get("entry") or "index.html",
                        "dir": Path(got["folder"]) / (cfg.get("root") or ""),
                        "path": cfg.get("url") or "/app/%s/" % app_id, "added": True})
        return out

    def candidates(self):
        """Folders on this PC that hold an app not on the list yet: beside
        the hub's tree, and where each partner is configured."""
        st, seen, out = self.state(), set(), []
        spots = []
        parent = self.data_root.parent
        if parent.is_dir():
            spots += [d for d in sorted(parent.iterdir()) if d.is_dir()
                      and d.resolve() != self.data_root.resolve()]
        for entry in (self.partners() or {}).values():
            if isinstance(entry, dict) and entry.get("folder"):
                spots.append(Path(self.expand(entry["folder"])))
        for d in spots:
            key = str(d).lower()
            if key in seen:
                continue
            seen.add(key)
            try:
                got = self.detect(d)
            except OSError:
                continue
            if got and not got.get("error") and got["id"] not in st["added"]:
                out.append(got)
        return out

    # ---- update -----------------------------------------------------------------------
    def update_command(self, app_id, entry=None):
        """(folder, argv) for updating an app: its own "update" list, else
        our template's, else a fast-forward git pull when it is a git folder."""
        st = self.state()
        folder = (st["added"].get(app_id) or {}).get("folder") or \
            self.expand((entry or {}).get("folder") or "")
        if not folder:
            return None, None
        got = self.detect(folder) or {}
        argv = ((got.get("manifest") or {}).get("update")
                or (entry or {}).get("update"))
        if not argv and (Path(folder) / ".git").exists():
            argv = ["git", "pull", "--ff-only"]
        return folder, argv

    def update(self, app_id, entry=None):
        folder, argv = self.update_command(app_id, entry)
        if not folder or not argv:
            return {"ok": False, "error": "no way to update %s is known" % app_id}
        try:
            r = subprocess.run(argv, cwd=folder, capture_output=True, text=True,
                               encoding="utf-8", errors="replace", timeout=UPDATE_TIMEOUT,
                               stdin=subprocess.DEVNULL, creationflags=NO_WINDOW)
        except (OSError, subprocess.SubprocessError) as e:
            return {"ok": False, "error": str(e), "command": argv}
        return {"ok": r.returncode == 0, "command": argv, "folder": folder,
                "output": ((r.stdout or "") + (r.stderr or ""))[-2000:]}
