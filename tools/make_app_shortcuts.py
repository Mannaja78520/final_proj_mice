"""Make one Windows shortcut per app: double-click it, get only that app (A26-6).

    python tools/make_app_shortcuts.py              -> dist/Apps/<name>.lnk
    python tools/make_app_shortcuts.py --desktop    -> on this user's Desktop

Each shortcut runs `MiceHub.exe --open <id>`. The list comes from apps/*/app.json,
so a new app gets its shortcut by running this again - nothing to edit here.
"""
import argparse
import os
import subprocess
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(CODE / "tools"))
import registry  # noqa: E402


def shortcut_specs(exe, out_dir, apps):
    """[(lnk path, target, arguments, working dir)] - pure, so QC can read it."""
    return [(Path(out_dir) / ("Mice %s.lnk" % a["name"]), str(exe),
             "--open %s" % a["id"], str(Path(exe).parent))
            for a in apps if a.get("show", True)]


def write_lnk(lnk, target, args, workdir):
    # WScript.Shell is the one shortcut writer every Windows has. Single quotes
    # are doubled for PowerShell; no other character in these values is special.
    q = lambda s: "'" + str(s).replace("'", "''") + "'"
    ps = ("$s=(New-Object -ComObject WScript.Shell).CreateShortcut(%s);"
          "$s.TargetPath=%s;$s.Arguments=%s;$s.WorkingDirectory=%s;"
          "$s.IconLocation=%s;$s.Save()"
          % (q(lnk), q(target), q(args), q(workdir), q(target + ",0")))
    subprocess.run(["powershell", "-NoProfile", "-Command", ps], check=True,
                   capture_output=True, timeout=60)


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--desktop", action="store_true", help="put them on the Desktop")
    ap.add_argument("--exe", default=str(CODE / "dist" / "MiceHub.exe"))
    a = ap.parse_args(argv)
    exe = Path(a.exe)
    if not exe.is_file():
        print("no hub program at %s - build it first: "
              "python -m PyInstaller --clean MiceHub.spec" % exe)
        return 1
    out = (Path(os.environ.get("USERPROFILE", "~")).expanduser() / "Desktop"
           if a.desktop else exe.parent / "Apps")
    out.mkdir(parents=True, exist_ok=True)
    for lnk, target, args, wd in shortcut_specs(exe, out, registry.apps()):
        write_lnk(lnk, target, args, wd)
        print("made", lnk)
    return 0


if __name__ == "__main__":
    sys.exit(main())
