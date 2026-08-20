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
import os
import subprocess
import sys
import time
from pathlib import Path

QC = Path(__file__).resolve().parent
CODE = QC.parent
sys.path.insert(0, str(QC / "lib"))
sys.path.insert(0, str(QC))

import qc as F  # noqa: E402


# ---- proof that a particular tree passed ------------------------------
# promote.py runs this suite as its gate. Running it a SECOND time on a tree
# that has not changed since a green run proves nothing, and costs another
# nine to fifteen minutes — the single biggest tax on getting work landed.
#
# So a green run leaves a receipt: the hash of every source file it could have
# read. promote.py accepts that receipt only while the tree still hashes the
# same. One changed byte and it is worthless, so this can never let something
# through that the suite has not actually seen.
RECEIPT = CODE / ".qc-receipt.json"

SKIP_PARTS = {".git", ".pio", "__pycache__", ".staging", "node_modules",
              ".vscode", "dist", "build", "patches", "generated"}


def tree_fingerprint():
    """One hash over every source file, so any edit invalidates the receipt."""
    import hashlib
    h = hashlib.sha256()
    for f in sorted(CODE.rglob("*")):
        if not f.is_file():
            continue
        rel = f.relative_to(CODE)
        if any(part in SKIP_PARTS for part in rel.parts):
            continue
        if f.suffix in (".pyc", ".pyo", ".tmp", ".exe", ".bin", ".elf"):
            continue
        # The receipt itself, and files the RUNNING system writes, are not
        # source: including them would invalidate every receipt immediately.
        if f.name in (".qc-receipt.json", "promt.md", "PLAN.html",
                      "settings_shared.json", "hub_auth.json",
                      "hub_password.txt"):
            continue
        # PATCHES.md is the INDEX of those snapshots (the snapshots themselves
        # are already skipped, above). Saving one is the last step of every web
        # change, so hashing this line threw away the twelve-minute run that had
        # just gone green and made the gate run twice for no new information.
        if f.name == "PATCHES.md":
            continue
        h.update(rel.as_posix().encode())
        h.update(f.read_bytes())
    return h.hexdigest()


def write_receipt(passed, failed):
    import json
    import time as _t
    try:
        RECEIPT.write_text(json.dumps({
            "tree": tree_fingerprint(),
            "passed": passed, "failed": failed,
            "when": _t.strftime("%Y-%m-%d %H:%M"),
            "full": True,
        }, indent=1), encoding="utf-8")
    except OSError:
        pass                      # a receipt is an optimisation, never required


def _int_arg(argv, name, default):
    """`--jobs 8` or `--jobs=8`, without pulling in argparse."""
    for i, a in enumerate(argv):
        if a == name and i + 1 < len(argv):
            try:
                return max(1, int(argv[i + 1]))
            except ValueError:
                return default
        if a.startswith(name + "="):
            try:
                return max(1, int(a.split("=", 1)[1]))
            except ValueError:
                return default
    return default


def _load(f):
    """Import one check file. Returns (module, error) - never raises.

    Split out of discover() so a pool worker can load the one check it was
    given without importing the other eighty-five.
    """
    import importlib.util
    spec = importlib.util.spec_from_file_location("qc_" + Path(f).stem, str(f))
    mod = importlib.util.module_from_spec(spec)
    try:
        spec.loader.exec_module(mod)
    except Exception as e:                           # a broken check is a failure
        return None, e
    return mod, None


def discover():
    """Every checks/check_*.py, in file order. No registry to keep in sync."""
    out = []
    for f in sorted((QC / "checks").glob("check_*.py")):
        mod, err = _load(f)
        out.append((f, mod, err) if err is None else (f, None, err))
    return out


G, R, Y, B, D = "\033[32m", "\033[31m", "\033[33m", "\033[1m", "\033[0m"
if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.kernel32.SetConsoleMode(
            ctypes.windll.kernel32.GetStdHandle(-11), 7)
    except Exception:
        G = R = Y = B = D = ""

# The Windows console codepage is cp1252, which cannot encode most of what the
# web apps actually contain — "✓", "→", "⚠", "…". Printing a FAILURE whose
# detail carries one of those raised UnicodeEncodeError inside the reporting
# loop and killed the entire run, so a single failing check took every later
# check down with it and the summary was never printed. The worst possible
# moment to lose the output is the moment something broke.
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):        # pre-3.7, or a stream that cannot be
    pass                                 # reconfigured — carry on regardless


# Checks that grab something the whole MACHINE has only one of. They cannot
# share a worker pool with anything, so they run on their own. Everything else
# is safe in parallel because a separate process gets its own fake_serial, its
# own qc_marks and its own hub - the isolation is the point, not a side effect.
SOLO = {
    "check_short_name",     # binds port 80
    "check_name_claim",     # answers mDNS on 5353
    "check_mdns",           # the same
    "check_build_split",    # writes firmware/.pio, which other checks read
    # Not a shared RESOURCE - a shared clock. It sleeps 150ms and expects the
    # hub's show thread to have advanced by then, which is true on an idle
    # machine and not true with ten workers competing for cores. It failed on
    # the first parallel gate and passed three times out of three alone, which
    # is the signature: the check is fine, the margin is not. Measuring time
    # needs a quiet machine.
    "check_hub_clock",
    # It ADDS A THEME to the real shared/web/themes.css and takes it out again -
    # which is the only honest way to prove a new theme needs no code. But that
    # file is served to every page, so while it runs, any other check reading
    # the stylesheet sees a theme that is not there, and the page-version hash
    # sees the file change twice. Raised by the panel 2026-08-20.
    "check_themes",
    # It breaks an app.json on purpose to prove a broken registry does not read
    # as an empty one, and puts it back. Any check reading the app registry
    # while that is happening sees a fault that is not theirs.
    "check_tools_list",
}


def _plan(msg):
    """Say on the plan page what QC is doing, right now.

    Asked for directly, 2026-08-20: *why it not update plan.html make update
    everytime as default when run this plan*. A gate that runs for minutes with
    the page saying nothing cannot be told from a gate that died. Best effort
    only - the plan is a convenience and must never be able to fail a run.
    """
    try:
        subprocess.run([sys.executable, str(CODE / "tools" / "plan.py"),
                        "running", msg],
                       capture_output=True, timeout=20)
    except Exception:                              # noqa: BLE001
        pass


def _one(path_str):
    """Run a single check in THIS process and return a picklable result.

    Everything it prints is captured and handed back, so a pool of workers
    cannot interleave half-lines from eight checks into unreadable soup.
    """
    import io
    import contextlib
    path = Path(path_str)
    buf = io.StringIO()
    mod, err = _load(path)
    if err:
        return (path_str, "", [], 0.0, "", err)
    with contextlib.redirect_stdout(buf):
        case, secs, crash = F.run_check(mod)
    return (path_str, getattr(mod, "TITLE", path.stem),
            [(bool(g), l, d) for g, l, d in case.results],
            secs, crash or "", "")


def main(argv):
    quick = "--quick" in argv
    listing = "--list" in argv
    # HOW MANY AT ONCE. Default is most of the machine: the suite spent 836s on
    # one core of 24 while the other 23 idled, and the user asked for the whole
    # machine to be used. Not ALL of them - each browser check starts an Edge,
    # and 24 browsers thrash a laptop rather than finishing sooner.
    jobs = _int_arg(argv, "--jobs", default=max(2, min(10, (os.cpu_count() or 4) - 2)))
    if "--serial" in argv:
        jobs = 1
    verbose = "-v" in argv or "--verbose" in argv
    # The VALUE after --jobs is not a filter. Without this, `--jobs 8` looked
    # for checks whose name contains "8" and ran none of them.
    skip_next = False
    pats = []
    for a in argv:
        if skip_next:
            skip_next = False
            continue
        if a == "--jobs":
            skip_next = True
            continue
        if not a.startswith("-"):
            pats.append(a.lower())

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

    # The generated firmware tables are built ONCE, here, before any worker
    # exists. Left to the checks, every process built them on first use and
    # they wrote the same files at the same time.
    try:
        F.generated()
    except Exception as e:                            # noqa: BLE001
        print("%sgen_tables failed:%s %s" % (R, D, e))

    # Which checks will actually run, after --quick and any filter.
    wanted = []
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
        wanted.append((f, mod))

    def report(f, mod, case_results, secs, crash, printed):
        """Print one check's block and count it. Same output, either path."""
        nonlocal total_pass, total_fail
        print("%s[%s]%s %s" % (B, getattr(mod, "AREA", "?"), D,
                               getattr(mod, "TITLE", f.stem)))
        if printed:
            sys.stdout.write(printed)
        n_fail = 0
        for good, label, detail in case_results:
            if good:
                total_pass += 1
                if verbose:
                    print("   %sok%s   %s" % (G, D, label))
            else:
                total_fail += 1
                n_fail += 1
                print("   %sFAIL%s %s" % (R, D, label))
                if detail:
                    print("        %s" % detail.replace(chr(10), chr(10) + "        "))
                failures.append("%s / %s" % (getattr(mod, "TITLE", f.stem), label))
        if crash:
            total_fail += 1
            n_fail += 1
            print("   %sCRASH%s %s" % (R, D, crash.strip().splitlines()[-1]))
            if verbose:
                print("        " + crash.replace(chr(10), chr(10) + "        "))
            failures.append("%s / crashed" % getattr(mod, "TITLE", f.stem))
        if not case_results and not crash:
            total_fail += 1
            n_fail += 1
            print("   %sFAIL%s asserted nothing — this check has gone silent"
                  % (R, D))
            failures.append("%s / asserted nothing" % getattr(mod, "TITLE", f.stem))
        print("   %s%d ok, %d failed, %.1fs%s"
              % (G if not n_fail else R,
                 len([1 for g, _l, _d in case_results if g]), n_fail, secs, D))

    solo = [(f, m) for f, m in wanted
            if f.stem in SOLO or getattr(m, "SOLO", False)]
    para = [(f, m) for f, m in wanted if (f, m) not in solo]
    if jobs > 1 and len(para) > 1:
        import concurrent.futures as _cf
        print("%srunning %d checks on %d workers, %d on their own%s"
              % (B, len(para), jobs, len(solo), D))
        done_n = 0
        by_path = {str(f): (f, m) for f, m in para}
        with _cf.ProcessPoolExecutor(max_workers=jobs) as pool:
            futs = [pool.submit(_one, str(f)) for f, _m in para]
            for fut in _cf.as_completed(futs):
                path_s, _title, results, secs, crash, err = fut.result()
                f, mod = by_path[path_s]
                if err:
                    broken.append((f.stem, err))
                    continue
                report(f, mod, results, secs, crash, "")
                done_n += 1
                if done_n % 10 == 0:
                    _plan("QC %d/%d checks" % (done_n, len(para) + len(solo)))
        for f, mod in solo:
            case, secs, crash = F.run_check(mod)
            report(f, mod, case.results, secs, crash, "")
        _plan("QC finished: %d passed, %d failed" % (total_pass, total_fail))

    else:
        # One at a time: --jobs 1, or a filter that left a single check.
        for f, mod in wanted:
            case, secs, crash = F.run_check(mod)
            report(f, mod, case.results, secs, crash, "")

    print("\n" + "=" * 62)
    for name, err in broken:
        print("%sBROKEN CHECK%s %s: %s" % (R, D, name, err))
    if skipped:
        print("%sskipped (--quick):%s %s" % (Y, D, ", ".join(skipped)))
    ok = total_fail == 0 and not broken
    print("%s%s%s  %d passed, %d failed in %.1fs"
          % (G if ok else R, "QC PASS" if ok else "QC FAIL", D,
             total_pass, total_fail, time.time() - t_all))
    # A receipt only for a FULL green run: a filtered or --quick run has not
    # seen everything, so promote must not be allowed to trust it.
    full_run = not pats and not quick
    if ok and full_run:
        write_receipt(total_pass, total_fail)
    elif RECEIPT.exists() and full_run:
        RECEIPT.unlink()          # this tree is not green any more

    if failures:
        print("\nwhat regressed:")
        for x in failures:
            print("  - " + x)
    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
