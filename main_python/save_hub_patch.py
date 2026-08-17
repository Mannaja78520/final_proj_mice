#!/usr/bin/env python3
"""Save the HUB's pages as a numbered PATCH — a preserved snapshot.

Nong Studio has had this since the start; the hub did not. That gap showed up
the first time an old screenshot was wanted: Studio could be restored to any
past day and photographed, and the hub could not, because no earlier version of
`hub.html` existed anywhere. This closes it.

    python save_hub_patch.py "what this change did"   # save the current pages
    python save_hub_patch.py --list                   # list every saved patch
    python save_hub_patch.py --restore 3              # put patch 0003 back

Covers the pages the hub serves from this folder — the hub page itself, the
offline help, and the small extra pages. Not `main.py`: that is the program,
and the firmware/web patchers have always snapshotted pages rather than code.

Same engine, same folder layout and same PATCHES.md format as the other two —
see code/tools/snapshot.py.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from snapshot import Snapshots, cli  # noqa: E402

SNAP = Snapshots(
    root=ROOT / "web",
    patterns=["*.html", "*.css", "*.js"],
    patches=ROOT / "patches",
    index=ROOT / "PATCHES.md",
    what="hub pages",
    restore_cmd="python save_hub_patch.py --restore",
)

if __name__ == "__main__":
    cli(SNAP, sys.argv[1:], __doc__)
