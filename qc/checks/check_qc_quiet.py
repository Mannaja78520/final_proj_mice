"""run_qc.py --quiet shows only what an agent must act on.

Asked 2026-10-21 (tokens): an agent's context keeps every line QC prints and
pays for it again on every later call; a full run printed ~2,000 lines, almost
all "ok". --quiet writes the whole run to qc/last_run.log and lets only the
failures (with their indented detail), the flaky list and the summary reach
the screen. This drives the filter with a fake screen and a temp log.
"""
import importlib.util
import io
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "run_qc --quiet: failures and the summary on screen, everything in the log"

RUN = [
    "\x1b[1m[tools]\x1b[0m some check\n",
    "   \x1b[32m11 ok, 0 failed, 0.2s\x1b[0m\n",
    "\x1b[1m[hub]\x1b[0m another check\n",
    "   \x1b[31mFAIL\x1b[0m the door stays shut\n",
    "        expected open, got shut\n",
    "   \x1b[31m3 ok, 1 failed, 0.4s\x1b[0m\n",
    "\x1b[31mQC FAIL\x1b[0m  14 passed, 1 failed in 1.0s\n",
    "\nwhat regressed:\n",
    "  - another check / the door stays shut\n",
]


def run(t):
    spec = importlib.util.spec_from_file_location("run_qc_under_test", str(F.CODE / "qc" / "run_qc.py"))
    R = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(R)
    with tempfile.TemporaryDirectory() as tmp:
        screen, log = io.StringIO(), Path(tmp) / "last_run.log"
        q = R._Quiet(screen, log)
        for chunk in RUN:
            q.write(chunk)
        q.close()
        shown, kept = screen.getvalue(), log.read_text(encoding="utf-8")
    t.ok("FAIL\x1b[0m the door stays shut" in shown and "expected open, got shut" in shown,
         "a failure and its detail line reach the screen", shown)
    t.ok("QC FAIL" in shown and "  - another check" in shown,
         "the summary and the regressed list reach the screen", shown)
    t.ok("some check" not in shown and "11 ok" not in shown,
         "passing checks stay off the screen", shown)
    t.ok(kept == "".join(RUN), "the log keeps every line", kept[-200:])
    t.ok("last_run.log" in shown, "the screen says where the full log is", shown[-120:])
