#!/usr/bin/env python3
"""Save the current FIRMWARE source as a numbered patch — a preserved snapshot.

The firmware is the part that cannot be rolled back by reloading a browser: a
bad flash means a robot that does not move. So every firmware change gets a
snapshot first, exactly like the web app has always had.

    python save_fw_patch.py "what this change did"   # snapshot src/, config/, ini, COMMANDS.md
    python save_fw_patch.py --list                    # every saved firmware patch
    python save_fw_patch.py --restore 3               # put patch 0003 back (backs up current first)

Covers the hand-written firmware: `src/**`, `config/**` (headers AND the JSON
registries), `tools/*.py`, `platformio.ini` and `COMMANDS.md`. Build output
(`.pio/`, `generated/`) and downloaded libraries are never snapshotted — they
are rebuilt, not authored. The registries and the generator are in because
since the per-type build they decide what a binary actually contains: a
snapshot without them could not be rebuilt into the same firmware.
"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT.parent / "tools"))
from snapshot import Snapshots, cli  # noqa: E402

SNAP = Snapshots(
    root=ROOT,
    patterns=["src/**/*.cpp", "src/**/*.h", "config/**/*.h", "config/**/*.json",
              "tools/*.py", "platformio.ini", "COMMANDS.md"],
    patches=ROOT / "patches",
    index=ROOT / "PATCHES.md",
    what="firmware",
    restore_cmd="python save_fw_patch.py --restore",
)

if __name__ == "__main__":
    cli(SNAP, sys.argv[1:], __doc__)
