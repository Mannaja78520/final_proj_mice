"""A browser check that fails only in the crowd is retried alone, and SAID.

User decision 2026-09-22 (A26-93): four full gates that night - the unsplit
main tree included - each went red on a DIFFERENT browser check, and every
one passed alone (check_identity, check_ui_states, check_link_states,
check_hub_nav at 200 s instead of 11 s, check_studio_playback). Nothing could
land. So run_qc.py reruns such a check alone `browserRetriesAlone` times:

  * all green  -> counted passed, printed FLAKY in red, listed at the end;
  * any red    -> the ORIGINAL failure is reported and the gate stays red.

What must not happen: a plain (non-browser) check retried, a single green
rerun excusing a failure, or a flaky check passing without a word.
"""
import json
import re

import qc as F

AREA = "tooling"
TITLE = "a browser check that fails only in the parallel run is retried alone, and named"


def run(t):
    src = (F.CODE / "qc" / "run_qc.py").read_text(encoding="utf-8")
    raw = (F.CODE / "qc" / "data" / "qc_speed.json").read_text(encoding="utf-8")
    cfg = json.loads(re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*',
                            lambda m: m.group(1) or "", raw))
    t.ok(int(cfg.get("browserRetriesAlone") or 0) >= 2,
         "the retry count is data, and at least two runs alone",
         "one green rerun is a coin toss, not evidence: %r" % cfg.get("browserRetriesAlone"))
    t.ok("path_s in heavy_paths and retries and _red(results, crash)" in src,
         "only a BROWSER check that failed is held back for a retry",
         "a plain check that fails in the pool is a real failure")
    t.ok("all(not _red(r[2], r[4]) and not r[5] for r in again)" in src,
         "it passes only if EVERY run alone was green",
         "any() here would let one lucky run excuse a real bug")
    t.ok("# real: it blocks" in src and
         "report(f, mod, results, secs, crash, _said(results, crash, printed))" in src,
         "a check that also fails alone reports its original failure, with what it printed")
    t.ok("sFLAKY%s" in src and "flaky.append(f.stem)" in src and "if flaky:" in src,
         "a retried check is printed FLAKY and listed at the end, never silent")
    t.ok("for good, label, detail in results:\n                    if not good:" in src
         and 'print("        in the crowd: %s%s"' in src
         and "if printed:\n                    sys.stdout.write(printed)" in src,
         "and it prints WHAT failed in the crowd, plus what the check printed",
         "a name with no evidence means reproducing the race to learn anything")
