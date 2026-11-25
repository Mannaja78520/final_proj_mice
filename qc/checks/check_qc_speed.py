"""QC's own speed tools: slowest-first ordering and the live probe stay honest."""
import subprocess
import sys

import qc as F
import run_qc

AREA = "qc"
TITLE = "QC starts slow checks first and the live probe runs"
SLOW = False


def run(t):
    from pathlib import Path
    grp = [(Path(n + ".py"), None) for n in ("a", "b", "c", "d")]
    order = [f.stem for f, _m in run_qc.longest_first(grp, {"c": 50.0, "a": 2.0, "d": 9.0})]
    t.ok(order == ["c", "d", "a", "b"], "timed checks first, longest first; untimed keep order",
         str(order))
    t.ok(run_qc.longest_first(grp, {}) == grp, "no history leaves the order alone")
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "qc_live.py"), "--selftest"],
                       capture_output=True, text=True, timeout=60)
    t.ok(r.returncode == 0 and "LIVE QC PASS" in r.stdout, "live probe passes against local servers",
         r.stdout[-300:] + r.stderr[-300:])
    t.ok("not running" in r.stdout, "an app that is down is skipped, not failed")
