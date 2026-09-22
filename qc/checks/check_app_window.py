"""Any app opens on its own: `MiceHub.exe --open voice`, and a shortcut per app.

User 2026-09-10 (A26-6): *i just need to can run it in it own program so we
don't need to open through hub*. The hub owns every cable, so a second hub is
never the answer: --open only chooses the window. Checked without a real
browser or a real Desktop - the browser start and the shortcut writer are
passed in, and what they were ASKED to do is asserted.
"""
import json
import sys

import qc as F

AREA = "hub"
TITLE = "one app opens in its own window, and each app gets a shortcut"
SLOW = False


def run(t):
    sys.path.insert(0, str(F.HUB))
    sys.path.insert(0, str(F.CODE / "tools"))
    import app_window
    import registry
    import make_app_shortcuts as mk

    t.eq(app_window.open_arg(["--open", "voice"]), "voice", "--open voice names the app")
    t.eq(app_window.open_arg(["--open=faces"]), "faces", "and so does --open=faces")
    t.eq(app_window.open_arg(["--no-build", "studio"]), "", "other arguments open nothing")

    cfg = app_window.load_config(F.CODE / "config" / "app_window.json")
    t.ok(cfg.get("browsers") and "{url}" in json.dumps(cfg.get("args")),
         "the browser list and its arguments are DATA in config/app_window.json",
         cfg)

    started, fell = [], []
    how = app_window.open_window("http://127.0.0.1:8642/app/voice/",
                                 {"browsers": [sys.executable], "args": ["--app={url}"]},
                                 popen=started.append, fallback=fell.append)
    t.eq(how, "window", "a listed browser that exists opens its own window")
    t.ok(started and started[0][1] == "--app=http://127.0.0.1:8642/app/voice/" and not fell,
         "with the app's address, and not also in a normal tab", started)

    how = app_window.open_window("http://x/", {"browsers": [r"C:\no\such.exe"], "args": []},
                                 popen=started.append, fallback=fell.append)
    t.ok(how == "browser" and fell == ["http://x/"],
         "no listed browser on this PC: the normal browser, never nothing", (how, fell))

    # the hub's own startup uses it, for a running hub AND a fresh one
    src = F.hub_src()
    body = src[src.find("def main():"):]
    body = body[:body.find("\nif __name__")]
    t.ok(body.count("show(") >= 2 and "webbrowser.open(" not in body,
         "both start paths open what --open asked for",
         "a hub already running used to open the hub page whatever was asked")
    # main.py is NOT imported here: it must see the fake serial port first, and
    # a quick check importing it would break a later start_hub() in this worker.
    fn = src[src.find("def open_target("):]
    fn = fn[:fn.find("\ndef main():")]
    t.ok('app["path"]' in fn and "registry.app_by_id(want)" in fn,
         "--open goes to that app's own page from the registry")
    t.ok("raise SystemExit" in fn and "registry.apps()" in fn,
         "an unknown app is refused, naming the real ones",
         "a shortcut to a renamed app would otherwise open the hub and say nothing")

    specs = mk.shortcut_specs(r"C:\mice\MiceHub.exe", r"C:\out", registry.apps())
    shown = [a for a in registry.apps() if a.get("show", True)]
    t.eq(len(specs), len(shown), "one shortcut per app the hub lists")
    t.ok(all(s[2] == "--open " + a["id"] for s, a in zip(specs, shown)),
         "each one runs MiceHub.exe --open <that app>", [s[2] for s in specs])
