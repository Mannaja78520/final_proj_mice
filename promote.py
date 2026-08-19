#!/usr/bin/env python3
"""Staging workspace: work in a copy, promote to the real tree only when QC is green.

    python promote.py --init      make/refresh code/.staging/ from the real tree
    python promote.py --check     run the FULL QC suite inside .staging
    python promote.py             --check, and copy back only if it passes
    python promote.py --diff      what would move, without moving it

Why a plain copy and not a git worktree: the real tree usually has uncommitted
work, and a worktree branches from the last COMMIT — it would silently start
from a tree missing everything not yet committed. A copy always mirrors what is
actually there.

`code/` keeps running the whole time, so the robot and MiceHub stay usable
while work is in progress. Nothing reaches it until QC passes.
"""
import argparse
import filecmp
import shutil
import subprocess
import sys
import time
from pathlib import Path

MAIN = Path(__file__).resolve().parent
# Which working copy to promote. `.staging` unless told otherwise, so two trees
# can be worked and verified at the same time:
#
#     python promote.py --staging .staging-ui
#
# Promoting stays SERIAL even so: both trees copy into the same real tree, and
# two promotes touching one file is a lost edit.
STAGING = MAIN / ".staging"


def _pick_staging(name):
    """Where the working copy is. A bare name is relative to the repo."""
    if not name:
        return MAIN / ".staging"
    p = Path(name)
    return p if p.is_absolute() else MAIN / name

# Never copied either way: build output, VCS, caches, the built exe (QC runs
# main.py directly; the exe is rebuilt after promotion when main.py moved), and
# the LIVE LOGS.
#
# promt.md is appended to by the UserPromptSubmit hook in the REAL tree while
# work happens in staging, so staging's copy is stale the moment it is made.
# Promoting it copied a 2.7 KB snapshot over a 23 KB log and would have thrown
# the prompt history away. A file the running system writes to is not source,
# and must not travel with the source.
SKIP_DIRS = {".git", ".pio", "__pycache__", ".staging", "node_modules",
             ".vscode", "dist", "build"}
# docs/PLAN.html is here for the same reason: its STATE block records progress
# and is edited in the REAL tree as work lands, by whoever or whatever is doing
# the work. Promoting a staging copy would roll that progress backwards.
# Two more the RUNNING system writes:
#   settings_shared.json  the hub rewrites it whenever a browser saves a
#     shared setting, and QC starts the hub — so staging's copy carries a
#     QC run's timestamp and would overwrite the real one.
#   hub_auth.json  THIS machine's password hash. Promoting a staging copy
#     would replace the real password with a test one and lock the user
#     out of their own hub.
SKIP_FILES = {"MiceHub.exe", "promt.md", "PLAN.html",
              "settings_shared.json", "hub_auth.json", "hub_password.txt",
              ".qc-receipt.json"}   # proof about ONE tree; meaningless in another
SKIP_SUFFIX = {".pyc", ".pyo", ".tmp"}


def skip(p: Path) -> bool:
    if any(part in SKIP_DIRS for part in p.parts):
        return True
    return p.name in SKIP_FILES or p.suffix in SKIP_SUFFIX


def walk(root: Path):
    """Every file worth copying, as paths relative to root."""
    for f in root.rglob("*"):
        if f.is_file():
            rel = f.relative_to(root)
            if not skip(rel):
                yield rel


def init(force=False):
    if STAGING.exists() and not force:
        n = sum(1 for _ in walk(STAGING))
        print("staging already exists (%d files) — refreshing changed files" % n)
    STAGING.mkdir(parents=True, exist_ok=True)
    copied = 0
    for rel in walk(MAIN):
        src, dst = MAIN / rel, STAGING / rel
        if dst.exists() and filecmp.cmp(src, dst, shallow=False):
            continue
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        copied += 1
    print("staging ready at %s (%d file(s) copied)" % (STAGING, copied))
    print("work in there; `python promote.py` moves it back once QC is green.")


def already_green(where: Path):
    """True when a FULL green run has already covered this exact tree.

    run_qc.py leaves a receipt naming the hash of every source file it could
    have read. If that hash still matches, running the suite again proves
    nothing the first run did not — it just costs another nine to fifteen
    minutes, which was the biggest single tax on landing work.

    This can never let something through unseen: change one byte and the hash
    no longer matches, so the suite runs. A filtered or --quick run leaves no
    receipt at all.
    """
    import json
    receipt = where / ".qc-receipt.json"
    if not receipt.is_file():
        return False
    try:
        got = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if not got.get("full"):
        return False

    import subprocess as sp
    r = sp.run([sys.executable, "-c",
                "import sys; sys.path.insert(0, r'%s'); "
                "import run_qc; print(run_qc.tree_fingerprint())" % (where / "qc")],
               cwd=str(where), capture_output=True, text=True, timeout=300)
    now = (r.stdout or "").strip().splitlines()[-1:] or [""]
    if now[0] != got.get("tree"):
        return False
    print("QC already passed on this exact tree at %s (%s checks) — not running "
          "it again.\nChange any file and it runs in full."
          % (got.get("when", "?"), got.get("passed", "?")))
    return True


def _plan(msg):
    """Tell the plan page what the promote is doing. Best effort, never fatal.

    Asked for 2026-08-20: *make update everytime as default when run this
    plan*. A gate takes minutes, and a page that says nothing for that long
    cannot be told from a run that died. run_qc.py reports its own progress;
    this covers the steps around it - the fingerprint check and the copy.
    """
    try:
        subprocess.run([sys.executable, str(MAIN / "tools" / "plan.py"),
                        "running", msg], capture_output=True, timeout=20)
    except Exception:                                  # noqa: BLE001
        pass


def run_qc(where: Path):
    qc = where / "qc" / "run_qc.py"
    if not qc.is_file():
        print("no QC suite at %s" % qc)
        return False
    print("running the FULL QC suite in %s ...\n" % where)
    t0 = time.time()
    r = subprocess.run([sys.executable, str(qc)], cwd=str(where))
    print("\nQC finished in %.0fs, exit %d" % (time.time() - t0, r.returncode))
    return r.returncode == 0


def changes():
    """(changed, added, only_in_main) between staging and the real tree."""
    changed, added = [], []
    stage = set(walk(STAGING))
    for rel in sorted(stage):
        src, dst = STAGING / rel, MAIN / rel
        if not dst.exists():
            added.append(rel)
        elif not filecmp.cmp(src, dst, shallow=False):
            changed.append(rel)
    gone = sorted(set(walk(MAIN)) - stage)
    return changed, added, gone


def show(changed, added, gone):
    for label, group in (("changed", changed), ("new", added)):
        if group:
            print("\n%s (%d):" % (label, len(group)))
            for rel in group:
                print("   ", rel.as_posix())
    if gone:
        # Files removed or MOVED in staging still exist here. Promotion never
        # deletes, so a moved file quietly comes back on the next --init and
        # can break a build that was green (the ESP32 test sketches did exactly
        # that). Loud, and with the command to finish the job.
        print("\n\033[33m!! %d file(s) exist here but NOT in staging\033[0m" % len(gone))
        print("   If you MOVED or deleted them, remove them here too or the next")
        print("   `--init` copies them back:")
        for rel in gone:
            print("     del %s" % rel.as_posix().replace("/", "\\"))
    if not (changed or added):
        print("nothing to promote — staging matches the real tree.")


def promote():
    changed, added, gone = changes()
    if not (changed or added):
        show(changed, added, gone)
        return 0
    print("about to promote %d changed + %d new file(s)" % (len(changed), len(added)))
    _plan("promote: checking whether staging is already green")
    if not (already_green(STAGING) or run_qc(STAGING)):
        print("\nREFUSED: QC is not green in staging. Nothing was copied.")
        return 1
    for rel in changed + added:
        dst = MAIN / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STAGING / rel, dst)
    print("\npromoted %d file(s) to %s" % (len(changed) + len(added), MAIN))
    show(changed, added, gone)
    if any(rel.as_posix().endswith("main_python/main.py") for rel in changed + added):
        print("\nNOTE: main_python/main.py changed — rebuild MiceHub.exe:")
        print("  python -m PyInstaller --onefile --icon main_python/nong.ico "
              "--name MiceHub main_python/main.py")
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true", help="create/refresh the staging copy")
    ap.add_argument("--check", action="store_true", help="run full QC in staging, promote nothing")
    ap.add_argument("--diff", action="store_true", help="show what would move")
    ap.add_argument("--staging", metavar="DIR", default=".staging",
                    help="which working copy to use (default .staging) — a second one lets another change be verified at the same time")
    a = ap.parse_args(argv)

    # Rebind the module-level path once, so every helper below keeps
    # working unchanged whichever tree was asked for.
    global STAGING
    STAGING = _pick_staging(a.staging)

    if a.init:
        init()
        return 0
    if not STAGING.exists():
        print("no staging copy yet — run: python promote.py --init")
        return 1
    if a.diff:
        show(*changes())
        return 0
    if a.check:
        return 0 if run_qc(STAGING) else 1
    return promote()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
