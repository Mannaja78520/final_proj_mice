#!/usr/bin/env python3
"""Write one entry to docs/BRIDGE.md, under the shared lock. One command.

    set MICE_AGENT=claude:5a33
    python tools/bridge.py NOTICE "what happened" "what is true now" "next"
    python tools/bridge.py CLAIM "Task: A0-31" "Files: tools/bridge.py"

Replaces a hand-typed PowerShell mutex block (2026-09-16/17: long to type,
and one was blocked by a path in its text). Same lock and format as
promote.py's bridge(), which this calls, so the two can never disagree.
Always the REAL tree's BRIDGE, even when run from a .staging copy.
"""
import importlib.util
import os
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REAL = HERE.parent if HERE.name.startswith(".staging") else HERE


def main(argv):
    if len(argv) < 2:
        print(__doc__)
        return 2
    if not os.environ.get("MICE_AGENT"):
        print("set MICE_AGENT=provider:session first (python tools/plan.py session <provider>)")
        return 2
    spec = importlib.util.spec_from_file_location("promote_bridge", str(HERE / "promote.py"))
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    P.MAIN = REAL
    P.bridge(argv[0].upper(), argv[1:])
    print("BRIDGE: %s written" % argv[0].upper())
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
