#!/usr/bin/env python3
"""QC — re-check every part of the mice project after any change.

    python qc/run_qc.py              everything (browser checks included, ~2 min)
    python qc/run_qc.py --quick      skip the browser checks (~10 s)
    python qc/run_qc.py connection   only areas/files matching "connection"
    python qc/run_qc.py --list       what is covered today

Nothing is registered by hand. Every `checks/check_*.py` is discovered, so
covering a NEW part of the project means dropping a new file in `checks/` —
see qc/README.md. That is the point: the suite grows with the project instead
of going stale.

Exit code 0 = everything green, 1 = something regressed.
"""
import sys
import time
from pathlib import Path

QC = Path(__file__).resolve().parent
sys.path.insert(0, str(QC / "lib"))
sys.path.insert(0, str(QC))

import qc as F  # noqa: E402


def discover():
    """Every checks/check_*.py, in file order. No registry to keep in sync."""
    import importlib.util
    out = []
    for f in sorted((QC / "checks").glob("check_*.py")):
        spec = importlib.util.spec_from_file_location("qc_" + f.stem, f)
        mod = importlib.util.module_from_spec(spec)
        try:
            spec.loader.exec_module(mod)
        except Exception as e:                       # a broken check is a failure
            mod = None
            out.append((f, None, e))
            continue
        out.append((f, mod, None))
    return out


G, R, Y, B, D = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        G = R = Y = B = D = ""


def main(argv):
    quick = "--quick" in argv
    listing = "--list" in argv
    verbose = "-v" in argv or "--verbose" in argv
    pats = [a.lower() for a in argv if not a.startswith("-")]

    found = discover()
    if listing:
        print("%sQC coverage%s — %d checks\n" % (B, D, len(found)))
        for f, mod, err in found:
            if err:
                print("  %s%-28s BROKEN: %s%s" % (R, f.stem, err, D))
                continue
            print("  %-14s %-30s %s" % (getattr(mod, "AREA", "?"),
                                        getattr(mod, "TITLE", f.stem),
                                        "(slow)" if getattr(mod, "SLOW", False) else ""))
        return 0

    try:                       # clear anything a killed run left behind
        import browser
        browser.sweep()
    except Exception:
        pass

    t_all = time.time()
    total_pass = total_fail = 0
    broken, skipped = [], []
    failures = []

    for f, mod, err in found:
        if err:
            broken.append((f.stem, err))
            continue
        area = getattr(mod, "AREA", "?")
        title = getattr(mod, "TITLE", f.stem)
        if pats and not any(p in area.lower() or p in f.stem.lower()
                            or p in title.lower() for p in pats):
            continue
        if quick and getattr(mod, "SLOW", False):
            skipped.append(title)
            continue

        print("%s[%s]%s %s" % (B, area, D, title))
        case, secs, crash = F.run_check(mod)
        for good, label, detail in case.results:
            if good:
                total_pass += 1
                if verbose:
                    print("   %sok%s   %s" % (G, D, label))
            else:
                total_fail += 1
                print("   %sFAIL%s %s" % (R, D, label))
                if detail:
                    print("        %s" % detail.replace("\n", "\n        "))
                failures.append("%s / %s" % (title, label))
        if crash:
            total_fail += 1
            print("   %sCRASH%s %s" % (R, D, crash.strip().splitlines()[-1]))
            if verbose:
                print("        " + crash.replace("\n", "\n        "))
            failures.append("%s / crashed" % title)
        if not case.results and not crash:
            print("   %s(no assertions)%s" % (Y, D))
        print("   %s%d ok, %d failed, %.1fs%s"
              % (G if not case.failed and not crash else R,
                 len(case.passed), len(case.failed) + (1 if crash else 0), secs, D))

    print("\n" + "=" * 62)
    for name, err in broken:
        print("%sBROKEN CHECK%s %s: %s" % (R, D, name, err))
    if skipped:
        print("%sskipped (--quick):%s %s" % (Y, D, ", ".join(skipped)))
    ok = total_fail == 0 and not broken
    print("%s%s%s  %d passed, %d failed in %.1fs"
          % (G if ok else R, "QC PASS" if ok else "QC FAIL", D,
             total_pass, total_fail, time.time() - t_all))
    if failures:
        print("\nwhat regressed:")
        for x in failures:
            print("  - " + x)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
