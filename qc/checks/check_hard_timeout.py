"""A hung check is killed and reported, a dead one is a failure, a healthy one is untouched.

2026-11-25: three scheduled full runs stalled at ~340 of 415 checks with no word
on which check or why. qc/lib/check_pool.py gives every check its own process, a
hard time limit, and a heartbeat file. This proves, with real processes: an
answer comes back; a sleeper past its budget is killed and reported as "timed
out" without disturbing a healthy neighbour (a ProcessPoolExecutor would have
broken every pending job); a process that dies is reported, not waited on; the
heartbeat names what is running; and the budget is never below the floor or 3x the
slowest healthy time.
"""
import json
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "a hung check is killed and reported; a dead one fails; a healthy one is untouched"


def _drain(pool, want, limit=60):
    got, t0 = [], time.time()
    while len(got) < want and time.time() - t0 < limit:
        got.extend(pool.poll())
        time.sleep(0.1)
    return {k: (kind, v, s) for k, kind, v, s in got}


def run(t):
    import check_pool as cp

    t.ok(cp.budget_for("x", {"x": 10}, 600) == 600, "a quick check still gets the floor")
    t.ok(cp.budget_for("x", {"x": 400}, 600) == 1200, "a slow check gets 3x its slowest healthy time")
    t.ok(cp.budget_for("new", {}, 600) == 600, "a check never timed gets the floor")

    killed = []
    pool = cp.CheckPool(cp.selftest_work, 3, on_kill=killed.append)
    pool.submit("quick", ("quick", 0), 30)
    pool.submit("sleeper", ("sleep", 120), 3)
    pool.submit("neighbour", ("sleep", 6), 30)      # outlives the sleeper's kill
    pool.submit("dies", ("die", 0), 30)

    t0 = time.time()
    res = _drain(pool, 4)
    t.ok(res.get("quick", ("",))[0] == "done" and res["quick"][1] == ("ok", "quick"),
         "a healthy check's answer comes back", repr(res.get("quick")))
    kind = res.get("sleeper", ("missing", "", 0))
    t.ok(kind[0] == "timeout" and "timed out after" in str(kind[1]),
         "a check past its budget is reported as timed out", repr(kind))
    t.ok(kind[2] < 20, "and it was stopped near its budget, not at its natural end", "%.1f s" % kind[2])
    t.ok(len(killed) == 1, "the browser cleanup hook ran once, with the check's pid", repr(killed))
    import runlock
    time.sleep(1.0)
    t.ok(killed and not runlock.pid_alive(killed[0]),
         "the killed check's process is really gone, not left running", repr(killed))
    nb = res.get("neighbour", ("missing",))
    t.ok(nb[0] == "done", "a healthy neighbour running beside the killed check still finishes", repr(nb))
    dd = res.get("dies", ("missing", ""))
    t.ok(dd[0] == "died" and "exit code" in str(dd[1]),
         "a process that dies without answering is a failure, not a hang", repr(dd))

    # heartbeat: names what is running, with pid and age
    pool2 = cp.CheckPool(cp.selftest_work, 2)
    pool2.submit("slow-one", ("sleep", 4), 30)
    pool2.poll()
    f = Path(tempfile.mkdtemp(prefix="qc_hb_")) / "progress.json"
    hb = cp.Heartbeat(f, 10, [pool2])
    hb.finished("earlier-check")
    hb.tick(now=time.time() + 100)
    try:
        beat = json.loads(f.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        beat = {}
    names = [r.get("check") for r in beat.get("running", [])]
    t.ok(names == ["slow-one"] and beat.get("last_finished") == "earlier-check"
         and beat.get("done") == 1 and beat.get("total") == 10,
         "the heartbeat file names the running check and the last finished one", repr(beat))
    _drain(pool2, 1)

    src = (F.QC / "run_qc.py").read_text(encoding="utf-8")
    t.ok("check_pool.CheckPool(" in src and "last_progress.json" in src
         and "kind != \"timeout\"" in src,
         "run_qc.py runs every check through the pool, writes the heartbeat, never retries a timeout")
