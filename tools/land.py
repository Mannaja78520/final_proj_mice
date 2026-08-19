"""Take finished work through the gate and into the real tree, in one command.

    python tools/land.py --done A17-3 A15-2      quick, then the full gate
    python tools/land.py --skip-quick            straight to the gate

Every landing in this project is the same four steps: run the quick suite, run
the full gate through promote.py, say what happened, and move the plan. Written
out by hand each time that is four commands plus a grep to find the verdict in
three hundred lines of output, and the grep pattern has been mistyped more than
once - which reads as *the gate said nothing* when the gate said plenty.

Three things it does that the four commands do not:

  * the plan is updated at each STEP, not only at the end, so the page says
    "quick suite" then "full gate" then the verdict while it runs. The user
    asked for exactly that: a page that goes quiet cannot be told from a run
    that died;
  * the quick suite runs FIRST and stops the gate if it fails. A full gate
    takes five minutes to tell you what the quick one says in thirty seconds;
  * `--done` only marks tasks when the gate is actually green. Marking work
    done because the command finished is how a plan starts lying.
"""
import argparse
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def plan(*args):
    """Move the plan. Never fatal: it is a page, not a gate."""
    try:
        subprocess.run([sys.executable, str(ROOT / "tools" / "plan.py")] + list(args),
                       capture_output=True, timeout=30)
    except Exception:                                  # noqa: BLE001
        pass


def run(cmd, **kw):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT), **kw)
    return r.returncode, re.sub(r"\x1b\[[0-9;]*m", "", (r.stdout or "") + (r.stderr or ""))


def verdict(text):
    """The one line worth reading out of a few hundred."""
    m = re.search(r"QC (PASS|FAIL)\s+(\d+) passed, (\d+) failed in ([\d.]+)s", text)
    if not m:
        return None, text.strip().splitlines()[-1:] or ["(no verdict in the output)"]
    bad = [l.strip()[2:].strip() for l in text.splitlines()
           if l.strip().startswith("- ")]
    return (m.group(1) == "PASS", ["%s passed, %s failed in %ss"
                                   % (m.group(2), m.group(3), m.group(4))] + bad[:6])


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--done", nargs="*", default=[],
                    help="task ids to mark done IF the gate is green")
    ap.add_argument("--skip-quick", action="store_true")
    a = ap.parse_args(argv)

    if not a.skip_quick:
        plan("running", "quick suite before the gate")
        code, out = run([sys.executable, str(ROOT / "qc" / "run_qc.py"), "--quick"])
        ok, lines = verdict(out)
        print("quick: " + (lines[0] if lines else "?"))
        for l in lines[1:]:
            print("   - " + l)
        if not ok:
            plan("running", "quick suite FAILED - not gating")
            return 1

    plan("running", "full gate, then promote")
    code, out = run([sys.executable, str(ROOT.parent / "promote.py")]
                    if (ROOT.parent / "promote.py").is_file()
                    else [sys.executable, str(ROOT / "promote.py")])
    ok, lines = verdict(out)
    print("gate:  " + (lines[0] if lines else "?"))
    for l in lines[1:]:
        print("   - " + l)

    landed = "promoted" in out
    print("promote: " + ("landed in the real tree" if landed
                         else "REFUSED - nothing was copied"))
    if ok and landed:
        for tid in a.done:
            plan("done", tid)
        plan("running", "--clear")
    else:
        plan("running", "gate red - staging holds unpromoted work")
    return 0 if (ok and landed) else 1


if __name__ == "__main__":
    sys.exit(main())
