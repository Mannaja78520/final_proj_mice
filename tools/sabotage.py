"""Break a fix on purpose, prove its check screams, put it back.

    python tools/sabotage.py --check page_version --spec - <<'JSON'
    [{"file": "main_python/main.py",
      "find": "if f.name.startswith(chr(95)):",
      "replace": "if False:",
      "why": "scratch files counted as a new version again"}]
    JSON

The project's rule is that a check only counts once you have broken the thing it
guards and watched it fail - a check that passes before and after guards
nothing. Doing that by hand is six shell commands per attempt (copy the file,
patch it, run the check, read the result, copy it back, run it again to be
sure), and it has been written out by hand more than a dozen times in one day.
It is the same six commands every time, so it belongs here.

What this adds beyond convenience, and the reason it is not just a shortcut:

  * the file is ALWAYS restored, including when the check crashes, the patch
    does not apply, or the run is interrupted - a hand-written cycle that dies
    in the middle leaves sabotaged code on disk, and that has happened;
  * a sabotage whose text is not found is an ERROR, not a pass. Silently
    patching nothing and then watching the check pass would read as *the check
    is weak* when the truth is *the sabotage missed*;
  * it says which assertion caught it, so the output is one line to read rather
    than a screen of QC to skim.

Exit code is 0 only when EVERY sabotage was caught.
"""
import argparse
import json
import re
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def run_check(name):
    """Run one QC check and return (passed, [failed assertion labels])."""
    r = subprocess.run([sys.executable, str(ROOT / "qc" / "run_qc.py"),
                        "--only", name],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace", cwd=str(ROOT))
    out = (r.stdout or "") + (r.stderr or "")
    plain = re.sub(r"\x1b\[[0-9;]*m", "", out)
    bad = [l.strip()[2:].strip() for l in plain.splitlines()
           if l.strip().startswith("- ")]
    return ("QC PASS" in plain and r.returncode == 0), bad, plain


def apply(spec):
    """Patch one file. Returns the original text, or raises if it did not bite."""
    f = ROOT / spec["file"]
    was = f.read_text(encoding="utf-8")
    find, repl = spec["find"], spec.get("replace", "")
    if find not in was:
        raise SystemExit("sabotage %r does not appear in %s - nothing would "
                         "have changed, and the check would have passed for "
                         "the wrong reason" % (find[:60], spec["file"]))
    f.write_text(was.replace(find, repl, 1), encoding="utf-8", newline="")
    return f, was


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--check", required=True, help="the QC check that must catch it")
    ap.add_argument("--spec", required=True,
                    help="a JSON file of sabotages, or - to read stdin")
    a = ap.parse_args(argv)

    text = sys.stdin.read() if a.spec == "-" else Path(a.spec).read_text(encoding="utf-8")
    specs = json.loads(text)
    if isinstance(specs, dict):
        specs = [specs]

    ok, _bad, _ = run_check(a.check)
    if not ok:
        print("the check is ALREADY failing - fix that before sabotaging it")
        return 2

    caught = 0
    for i, spec in enumerate(specs, 1):
        f, was = apply(spec)
        try:
            passed, bad, _out = run_check(a.check)
        finally:
            f.write_text(was, encoding="utf-8", newline="")   # always
        why = spec.get("why") or spec["find"][:50]
        if passed:
            print("%d. SILENT  %s" % (i, why))
            print("      the check passed with the fix broken - it is not "
                  "testing what it claims")
        else:
            caught += 1
            print("%d. caught  %s" % (i, why))
            for b in bad[:2]:
                print("      by: %s" % b.split(" / ")[-1])

    passed, _bad, _ = run_check(a.check)
    print("restored and green" if passed else "RESTORED BUT STILL RED - look now")
    print("%d of %d sabotages were caught" % (caught, len(specs)))
    return 0 if (caught == len(specs) and passed) else 1


if __name__ == "__main__":
    sys.exit(main())
