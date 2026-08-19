"""Two QC runs can happen at once without ruining each other.

Every change queued behind one 12-minute suite, so the user asked for more than
one working copy. Two staging trees are two PROCESSES, so the shared-state
collision that bit us inside one process does not apply — but three things did,
and all three fail silently rather than loudly, which is the dangerous kind:

  * browser.TAG was a constant and kill() matches on it, so one run killed the
    other run's browser in the middle of a measurement. That looks exactly like
    a flaky check;
  * qc._hub_port started at 8700 in both runs, so two trees fought over ports —
    or worse, one tree's hub answered the other tree's request, which does not
    fail at all, it just tests the wrong tree;
  * promote.py hardcoded MAIN/.staging, so a second tree could not be promoted.

This asserts each run takes an identity from its own process, and that the
identity really differs between processes — checked by starting a second
Python and comparing, not by reading the source and hoping.
"""
import subprocess
import sys

import qc as F

AREA = "qc"
TITLE = "two working copies can be verified at the same time"
SLOW = False

# Ask another process what IT computed. Reading the source cannot tell you
# whether two processes actually differ.
PROBE = (
    "import sys, os; sys.path.insert(0, r'%s'); sys.path.insert(0, r'%s');"
    "import browser, qc;"
    "print(browser.TAG); print(qc._hub_port[0]); print(os.getpid())"
)


def _ask_another_process():
    r = subprocess.run(
        [sys.executable, "-c", PROBE % (F.QC / "lib", F.QC)],
        capture_output=True, text=True, timeout=120, cwd=str(F.CODE))
    if r.returncode != 0:
        return None
    parts = (r.stdout or "").strip().splitlines()
    return parts if len(parts) == 3 else None


def run(t):
    import browser

    # ---- this run has its own identity --------------------------------
    t.ok(browser.TAG.startswith("MICEQCBROWSER") and browser.TAG != "MICEQCBROWSER",
         "the browser tag is particular to this run",
         "kill() matches on the tag, so a shared one means one run kills the "
         "other run's browser: %r" % browser.TAG)
    t.ok(F._hub_port[0] != 8700,     # noqa: SLF001 - the value under test
         "and so is the port range it starts hubs on",
         "two runs both starting at 8700 can answer each other's requests, "
         "which does not fail — it tests the wrong tree")

    # ---- and another process really gets a different one --------------
    other = _ask_another_process()
    if not t.ok(other, "a second process could be asked what it computed"):
        return
    tag, port, pid = other[0], other[1], other[2]
    t.ok(tag != browser.TAG,
         "a second run gets a DIFFERENT browser tag",
         "same tag in both (%s) — one run's kill() would take the other's "
         "browser down mid-measurement" % tag)
    t.ok(port != str(F._hub_port[0]),   # noqa: SLF001
         "and a different port range",
         "both runs would start hubs at %s" % port)

    # ---- promote can be pointed at another tree -----------------------
    import importlib.util
    spec = importlib.util.spec_from_file_location("qc_promote", F.CODE / "promote.py")
    pr = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(pr)
    t.ok(hasattr(pr, "_pick_staging"), "promote.py can be pointed at a tree")
    if hasattr(pr, "_pick_staging"):
        t.eq(pr._pick_staging(".staging").name, ".staging",
             "the default is still .staging")
        t.eq(pr._pick_staging(".staging-ui").name, ".staging-ui",
             "and a second tree can be named")
        t.ok(pr._pick_staging(r"E:/somewhere/else").as_posix().endswith("somewhere/else"),
             "including one outside the repo")
