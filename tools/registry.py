#!/usr/bin/env python3
"""Data files that describe things, so adding a thing is one edit in one place.

Every registry in the project — web apps, servo presets, commands, module
capabilities — is a JSON file loaded through here. The point is that a person
can open one and understand it, so:

  * `//` line comments and trailing commas are allowed and stripped, because
    JSON without comments is miserable to hand-edit;
  * a broken file names the file and the line rather than raising a bare
    JSONDecodeError from somewhere deep in a request handler;
  * nothing here runs on the ESP32. Firmware tables are generated into headers
    at BUILD time (firmware/tools/gen_tables.py), so the chip parses nothing
    and pays nothing at runtime.

Stdlib only, like the rest of the hub.
"""
import json
import re
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent

_LINE_COMMENT = re.compile(r'(^|\s)//.*$', re.M)
_TRAILING_COMMA = re.compile(r",(\s*[}\]])")


class RegistryError(Exception):
    """A data file is malformed — says which file and where."""


def strip_jsonc(text: str) -> str:
    """JSON with // comments and trailing commas -> plain JSON.

    Only strips `//` that starts a token, so a URL inside a string ("http://x")
    survives. Good enough for hand-written config, and predictable.
    """
    out = []
    for line in text.splitlines():
        # keep // that sits inside a string literal
        in_str, esc, cut = False, False, None
        for i, c in enumerate(line):
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = not in_str
            elif not in_str and c == "/" and line[i:i + 2] == "//":
                cut = i
                break
        out.append(line[:cut] if cut is not None else line)
    return _TRAILING_COMMA.sub(r"\1", "\n".join(out))


def load(path, default=None):
    """Read one registry file. Missing file -> `default` (or {})."""
    p = Path(path)
    if not p.is_file():
        return {} if default is None else default
    raw = p.read_text(encoding="utf-8")
    try:
        return json.loads(strip_jsonc(raw))
    except json.JSONDecodeError as e:
        raise RegistryError("%s line %d: %s" % (p, e.lineno, e.msg)) from None


# ------------------------------------------------------------------ apps
# A web app is a folder with an app.json. Drop the folder in, and the hub
# serves it and lists it — no route to add, no button to hand-write.
APPS_DIR = CODE / "apps"

APP_DEFAULTS = {
    "name": "", "blurb": "", "icon": "", "entry": "index.html",
    "root": "", "url": "", "order": 100, "show": True,
    # Which part of the help page is about this tool. Empty means the tool has
    # no section, and then no help link is offered rather than one pointing at
    # the top of a page of a thousand lines - landing on the wrong paragraph
    # reads as an answer, which is worse than landing nowhere. Declared here
    # so a new tool brings its own help link with it, like everything else in
    # this registry.
    "help": "",
}


def apps(apps_dir=None):
    """Every registered app, sorted for display.

    `root` is where its files live, relative to code/ — so an app can point at
    a folder that already exists (Nong Studio, the help page) instead of being
    moved. `url` overrides the served path when an app must keep a historic
    address that links and QC drivers already use.
    """
    d = Path(apps_dir or APPS_DIR)
    out = []
    if not d.is_dir():
        return out
    for man in sorted(d.glob("*/app.json")):
        cfg = dict(APP_DEFAULTS)
        cfg.update(load(man))
        cfg["id"] = man.parent.name
        cfg.setdefault("name", cfg["id"])
        if not cfg["name"]:
            cfg["name"] = cfg["id"]
        # where the files are: the app's own folder unless it points elsewhere
        cfg["dir"] = (CODE / cfg["root"]) if cfg["root"] else man.parent
        cfg["path"] = cfg["url"] or ("/app/%s/" % cfg["id"])
        out.append(cfg)
    out.sort(key=lambda a: (a["order"], a["name"].lower()))
    return out


def app_by_id(app_id, apps_dir=None):
    for a in apps(apps_dir):
        if a["id"] == app_id:
            return a
    return None


# ---------------------------------------------------------------- servos
# One list of servo presets, shared by the firmware (generated into a header)
# and by Nong Studio (fetched from the hub). Two hand-kept copies used to drift.
SERVOS_FILE = CODE / "firmware" / "config" / "servos.json"


def servos(path=None):
    data = load(path or SERVOS_FILE, {})
    return data.get("servos", data if isinstance(data, dict) else {})


# -------------------------------------------------------------- commands
# What each command IS, so the firmware's HELP, COMMANDS.md and the help page
# can be checked against one declaration instead of drifting apart.
COMMANDS_FILE = CODE / "firmware" / "config" / "commands.json"


def commands(path=None):
    data = load(path or COMMANDS_FILE, {})
    return data.get("commands", [])


# -------------------------------------------------------------- modules
# What a board can BE. One entry here is a module type: the firmware
# generates its build flags, its factory and its command scope from this, and
# the hub offers it as something to flash. See firmware/config/modules.json.
MODULES_FILE = CODE / "firmware" / "config" / "modules.json"


def modules(path=None):
    data = load(path or MODULES_FILE, {})
    return data.get("modules", {})
