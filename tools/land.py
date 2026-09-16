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

# THAI, OR ANY OTHER LANGUAGE, MUST NOT KILL A TOOL. Windows hands python a
# cp1252 console here, which cannot encode Thai at all: printing one Thai word
# raised UnicodeEncodeError and the command died after it had already changed
# the file. Measured 2026-08-22. UTF-8 out, and never crash on a character.
for _out in (sys.stdout, sys.stderr):
    try:
        _out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass        # a check that IMPORTS this tool has replaced stdout
                    # with a StringIO, which has no reconfigure at all

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


def snap(desc):
    """Numbered patch of the whole code tree once the work IS in the real
    tree - A24-1: every landed change gets a number without anyone remembering
    to ask. Never fatal: a missing patcher must not fail a green gate."""
    try:
        r = subprocess.run([sys.executable, str(ROOT / "tools" / "save_code_patch.py"), desc],
                           capture_output=True, text=True, encoding="utf-8",
                           errors="replace", cwd=str(ROOT), timeout=300)
        line = (r.stdout or "").strip().splitlines()
        if line:
            print("patch: " + line[-1])
    except Exception:                                   # noqa: BLE001
        pass


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

    def finish(good, why=""):
        # The LAST line decides. On 2026-08-23 the deciding word sat at the end
        # of hundreds of lines that a truncated read never reached, and a landed
        # promote was reported as REFUSED. Whoever reads only the tail now
        # reads the truth.
        print("LAND RESULT: %s%s%s" % ("LANDED" if good else "NOT LANDED",
                                       (" - " + why) if why else "",
                                       (" (" + " ".join(a.done) + ")") if a.done else ""))
        return 0 if good else 1

    if not a.skip_quick:
        plan("running", "quick suite before the gate")
        code, out = run([sys.executable, str(ROOT / "qc" / "run_qc.py"), "--quick"])
        ok, lines = verdict(out)
        print("quick: " + (lines[0] if lines else "?"))
        for l in lines[1:]:
            print("   - " + l)
        if not ok:
            plan("running", "quick suite FAILED - not gating")
            return finish(False, "quick suite failed")

    # Numbered patch BEFORE the gate copies anything: promote carries the
    # whole tree INCLUDING this patch into the real tree, so the rollback
    # point for THIS landing is IN the real tree the moment it lands. Taken
    # after the snapshot the other way round left patch 0003 stranded in
    # staging - the one landing someone might need to undo was the one main
    # had no patch for.
    snap(("landing " + " ".join(a.done)) if a.done
         else "landing - no task ids given")

    plan("running", "full gate, then promote")
    code, out = run([sys.executable, str(ROOT.parent / "promote.py")]
                    if (ROOT.parent / "promote.py").is_file()
                    else [sys.executable, str(ROOT / "promote.py")])
    ok, lines = verdict(out)
    print("gate:  " + (lines[0] if lines else "?"))
    for l in lines[1:]:
        print("   - " + l)
    # KEEP THE EVIDENCE. Printing only the verdict threw away the crash text
    # twice - once for a check that never reproduced, once for a timing failure
    # whose numbers would have named the cause. A red gate now leaves the whole
    # run on disk, and says where.
    if not ok:
        from pathlib import Path as _P
        import tempfile as _tf
        keep = _P(_tf.gettempdir()) / "mice_last_gate.log"
        try:
            keep.write_text(out, encoding="utf-8")
            print("   full output kept: %s" % keep)
        except OSError:
            pass

    # Staging byte-identical to the real tree means the work IS in the real
    # tree - promote copies nothing and prints "nothing to promote". Calling
    # that REFUSED left finished work marked doing forever (A22-2, A20-1).
    synced = "nothing to promote" in out
    landed = "promoted" in out
    if synced and not landed:
        print("promote: already in the real tree - nothing was copied")
        for tid in a.done:
            plan("done", tid)
        plan("running", "--clear")
        return finish(True, "already in the real tree")

    print("promote: " + ("landed in the real tree" if landed
                         else "REFUSED - nothing was copied"))
    # A promote that reused the RECEIPT prints no verdict at all - the suite did
    # not run because the tree had not changed since it last went green. That is
    # a success, and reading it as a red gate marked finished work as still in
    # flight and left the plan saying the opposite of the truth.
    if landed and ok is None:
        ok = True
        print("gate:  no QC verdict found - assuming a reused green receipt")
    if ok and landed:
        for tid in a.done:
            plan("done", tid)
        plan("running", "--clear")
        return finish(True)
    plan("running", "gate red - staging holds unpromoted work")
    return finish(False, "promote refused or gate red")


if __name__ == "__main__":
    sys.exit(main())
