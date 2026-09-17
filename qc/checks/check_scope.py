"""A small change gets a small gate; a wide one still gets the whole suite.

Asked 2026-09-16: *if we change some thing we can gate and qc about that ...
full check when edit the whole system or more than 1 system*. promote.py now
runs `run_qc.py --changed`, and qc/lib/scope.py decides from qc/data/scope.json.

The danger of a scoped gate is a change that SHOULD have run everything and
did not. So the cases that must stay full are asserted first:
  * a shared core file (main.py, mice.css, qc/lib) -> full;
  * two systems at once (apps/voice + apps/faces) -> full;
and the ones that may be small:
  * one app's files -> exactly the checks that name them, and they include the
    check written for that change;
  * a changed check -> that check runs;
  * only the plan and notes -> the quick suite, never nothing at all.
"""
import sys

import qc as F


AREA = "tools"
TITLE = "a one-system change runs its own checks; core or two systems run all"


def run(t):
    sys.path.insert(0, str(F.CODE / "qc" / "lib"))
    import scope                                            # noqa: E402

    def d(*paths):
        return scope.decide(F.CODE, list(paths))

    t.eq(d("main_python/main.py")[0], "full", "the hub core runs the full suite")
    t.eq(d("shared/web/mice.css")[0], "full", "the shared stylesheet runs the full suite")
    t.eq(d("qc/lib/browser.py")[0], "full", "the QC library runs the full suite")
    got = d("apps/voice/app.js", "apps/faces/index.html")
    t.ok(got[0] == "full", "two systems at once run the full suite", got)

    got = d("apps/faces/index.html", "main_python/partner_launch.py")
    t.ok(got[0] == "full", "a web app plus a hub file is two systems", got)

    got = d("main_python/partner_launch.py")
    t.ok(got[0] == "checks" and "check_partner_launch" in got[1],
         "one hub file runs the checks that name it", got)
    t.ok(got[0] == "checks" and len(got[1]) < 20,
         "and not the whole suite", got[:2])

    got = d("apps/faces/index.html")
    t.ok(got[0] == "checks" and "check_faces_app" in got[1],
         "a generic name (index.html) is found by its folder", got)
    t.ok(got[0] == "checks" and "check_voice" not in got[1],
         "and does not drag in every other index.html", got)

    got = d("qc/checks/check_crash_gate.py")
    t.ok(got[0] == "checks" and "check_crash_gate" in got[1],
         "a changed check runs itself", got)

    t.eq(d("docs/PLAN.html", "promt.md")[0], "quick",
         "only the plan changed: the quick suite, never nothing")

    # promote.py --only scopes the gate to the landed files, not to whatever
    # else the shared staging carries (2026-09-17: a receipt file and a QC
    # leftover turned a 3-file land into a full gate).
    got = d("main_python/web/hub.html", ".qc-receipt.json",
            "nong/main_python_set_nong/settings_shared.json")
    t.ok(got[0] == "checks",
         "files QC or the hub write never widen a one-page change to the full gate", got)
    run_src = (F.CODE / "qc" / "run_qc.py").read_text(encoding="utf-8")
    prom = (F.CODE / "promote.py").read_text(encoding="utf-8")
    t.ok('os.environ.get("MICE_QC_ONLY")' in run_src and 'env["MICE_QC_ONLY"]' in prom,
         "a promote --only gate is scoped to exactly the files it lands")
