#!/usr/bin/env python3
"""Save the PROJECT'S CODE as a numbered PATCH - every area, one command.

Nong Studio has been snapshotted since week one, and the pages and firmware
have their own patchers; the code did not. Asked 2026-08-24: *save other thing
too not only nong studio*. This covers what the others do not: the hub's
Python, the shared design system, the QC suite, the tools and promote itself.

    python tools/save_code_patch.py "what this change did"   # snapshot
    python tools/save_code_patch.py --list                   # every patch
    python tools/save_code_patch.py --restore 3              # put 0003 back

A WHITELIST, not a blacklist: only the globs below are ever saved, so a
runtime file cannot sneak in by appearing somewhere new. Deliberately outside:
docs/PLAN.html and promt.md (written by the running system), MiceHub.exe and
dist/ (build output), hub_password.txt and any *cookie* file (secrets), and
the areas with their own patchers.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
from snapshot import Snapshots, cli  # noqa: E402

SNAP = Snapshots(
    root=ROOT,
    patterns=["main_python/*.py", "main_python/web/*", "shared/web/*",
              "qc/*.py", "qc/checks/*.py", "qc/lib/*.py", "qc/data/*.json",
              "tools/*.py", "promote.py", "MiceHub.spec"],
    patches=ROOT / "patches_code",
    index=ROOT / "PATCHES.md",
    what="project code",
    restore_cmd="python tools/save_code_patch.py --restore",
)

if __name__ == "__main__":
    cli(SNAP, sys.argv[1:], __doc__)
