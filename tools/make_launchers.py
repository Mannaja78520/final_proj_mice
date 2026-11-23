#!/usr/bin/env python3
"""Double-click starters for every app that runs alone (user 2026-11-23).

    python tools/make_launchers.py          write main_python/launchers/<App name>.bat
    python tools/make_launchers.py --check  fail if one is missing or out of date (QC)

One file per app that has an `alonePort` in its app.json, named with the app's
own name ("Voice.bat", "Prize machines.bat") so a non-engineer sees words, not
flags. A new app with an alonePort gets its launcher from this script, no code.
Each one runs dist\\MiceHub.exe (the freshly built one; the old tracked copy in
main_python does not know --alone and opened the whole hub on the PC, 2026-11-23)
or python main.py when the exe is not built with `--alone <id>`; the program opens the app's page by itself.
"""
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
import registry                                    # noqa: E402

OUT = ROOT / "main_python" / "launchers"
TEXT = ("@echo off\r\n"
        "title MICE\r\n"
        "rem Starts %(name)s by itself - no hub needed. Other MICE apps that are open\r\n"
        "rem on this PC are found automatically. Close this window to stop it.\r\n"
        "cd /d \"%%~dp0..\"\r\n"
        "if exist ..\\dist\\MiceHub.exe (..\\dist\\MiceHub.exe --alone %(id)s) else (python main.py --alone %(id)s)\r\n"
        "pause\r\n")


def wanted():
    """{file name: text} for every app that can run alone."""
    out = {}
    for a in registry.apps():
        if a.get("alonePort"):
            safe = re.sub(r'[\\/:*?"<>|]', "", a["name"]).strip() or a["id"]
            out[safe + ".bat"] = TEXT % {"name": a["name"], "id": a["id"]}
    return out


def main():
    want = wanted()
    if "--check" in sys.argv:
        have = {f.name: f.read_bytes().decode("utf-8") for f in OUT.glob("*.bat")} if OUT.is_dir() else {}
        bad = sorted(set(want) ^ set(have)) + sorted(n for n in want if n in have and have[n] != want[n])
        print("\n".join(bad) or "launchers are current")
        return 1 if bad else 0
    OUT.mkdir(exist_ok=True)
    for old in OUT.glob("*.bat"):
        old.unlink()
    for name, text in want.items():
        (OUT / name).write_bytes(text.encode("utf-8"))
    print("wrote", ", ".join(want))
    return 0


if __name__ == "__main__":
    sys.exit(main())
