"""Cleaning up scratch never deletes what a running process owns.

2026-11-26: a nested QC run (check_dev_tools -> tools/sabotage.py -> run_qc.py)
called browser.sweep() at its start, which deleted every driver page and browser
profile in the shared folders - including those of the OUTER run's browser checks
that were running right then. Their page got a 404 for its own driver ("QC DIAG:
page GET yes (404) ... login POST NO"), reported nothing, waited out its grace
(175-478 s) and failed, and passed alone: the QC SILENT flake, in 7 of 8 full runs.
Files named for a live pid are kept; files named for a dead pid are removed.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "sweep keeps the driver pages and profiles of live processes and removes dead ones"


def run(t):
    import browser
    d = Path(tempfile.mkdtemp(prefix="qc_sweep_"))
    scratch, web = d / "scratch", d / "web"
    scratch.mkdir()
    web.mkdir()
    gone = subprocess.Popen([sys.executable, "-c", "pass"])
    gone.wait()
    live, dead = os.getpid(), gone.pid

    def pages(pid):
        return [web.joinpath("_qcdriver_%d_111.html" % pid), web.joinpath("_qcraw_%d_222.html" % pid),
                web.joinpath("_qctalk_%d_333.html" % pid), scratch / ("profile_%d_444" % pid),
                scratch / ("profile_%d_555.edge.log" % pid)]

    keep = pages(live)
    drop = pages(dead) + [web.joinpath("_qcmod_legacy.html")]
    for p in keep + drop:
        if p.name.startswith("profile_") and not p.name.endswith(".log"):
            (p / "x").mkdir(parents=True)
        else:
            p.write_text("x", encoding="utf-8")

    browser.sweep(scratch=scratch, webs=(web,))
    t.ok(all(p.exists() for p in keep), "files and profiles of a live process are kept",
         str([p.name for p in keep if not p.exists()]))
    t.ok(not any(p.exists() for p in drop), "files and profiles of a dead process, and legacy names, are removed",
         str([p.name for p in drop if p.exists()]))
