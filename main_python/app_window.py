"""One app in its own window: `MiceHub.exe --open voice` (A26-6).

User 2026-09-10: *i just need to can run it in it own program so we don't need
to open through hub*. One hub must stay one hub (it owns every cable), so the
app is still served by the hub; --open only decides what window appears. If a
hub is already running, that hub serves it and no second one starts.

Which browser and how: config/app_window.json, so a PC without Edge is an edit
there, not here.
"""
import json
import os
import re
import subprocess
import webbrowser
from pathlib import Path


def open_arg(argv):
    """The app id asked for with `--open <id>` or `--open=<id>`, else ""."""
    for i, a in enumerate(argv):
        if a == "--open" and i + 1 < len(argv):
            return argv[i + 1].strip()
        if a.startswith("--open="):
            return a[len("--open="):].strip()
    return ""


def load_config(path):
    try:
        raw = Path(path).read_text(encoding="utf-8")
    except OSError:
        return {}
    raw = re.sub(r"^\s*//.*$", "", raw, flags=re.M)   # the file explains itself in comments
    try:
        return json.loads(raw)
    except ValueError:
        return {}


def browser_command(url, cfg, exists=os.path.isfile):
    """[exe, args...] for the first configured browser on this PC, or None."""
    for b in cfg.get("browsers") or []:
        exe = os.path.expandvars(str(b))
        if "%" not in exe and exists(exe):
            return [exe] + [str(a).replace("{url}", url) for a in cfg.get("args") or []]
    return None


def open_window(url, cfg, popen=subprocess.Popen, fallback=webbrowser.open):
    """Show `url` in an app window. -> "window" or "browser" (what happened)."""
    cmd = browser_command(url, cfg)
    if cmd:
        try:
            popen(cmd)
            return "window"
        except OSError:
            pass                     # listed but will not start: plain browser
    fallback(url)
    return "browser"
