#!/usr/bin/env python3
"""Save the current web app as a numbered PATCH — a preserved snapshot.

Each patch is one change (whatever was asked for that one time). Patches never
overwrite each other: the old versions stay, so you can always look back at or
restore any earlier version of the web app.

    python save_patch.py "what this change did"      # save the current web/ as the next patch
    python save_patch.py --list                       # list every saved patch
    python save_patch.py --restore 3                  # copy patch 0003 back into web/ (backs up current first)

A patch stores the source files that actually change (app.js, index.html,
style.css) — not the vendored three.js libraries, which don't change. Snapshots
live in  patches/NNNN_<slug>/  and are indexed in  PATCHES.md.

The snapshot engine is shared with the firmware's save_fw_patch.py — see
code/tools/snapshot.py. The format here is unchanged: same folder layout, same
PATCHES.md table, same numbering, so every existing patch still restores.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent.parent / "tools"))
from snapshot import Snapshots, cli  # noqa: E402

SNAP = Snapshots(
    root=ROOT / "web",
    patterns=["app.js", "index.html", "style.css"],
    # style.css is only Studio's half of the design now — the tokens and the
    # components live in shared/web/mice.css, which index.html links first. A
    # snapshot without it restores half a stylesheet.
    also=[(ROOT.parent.parent / "shared" / "web", ["*.css"], "shared")],
    patches=ROOT / "patches",
    index=ROOT / "PATCHES.md",
    what="web app",
    restore_cmd="python save_patch.py --restore",
)

if __name__ == "__main__":
    cli(SNAP, sys.argv[1:], __doc__)
