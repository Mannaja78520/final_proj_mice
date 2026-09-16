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
import codecs
import filecmp
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import time
import uuid

from contextlib import contextmanager
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

MAIN = Path(__file__).resolve().parent
# Which working copy to promote. `.staging` unless told otherwise, so two trees
# can be worked and verified at the same time:
#
#     python promote.py --staging .staging-ui
#
# Promoting stays SERIAL even so: both trees copy into the same real tree, and
# two promotes touching one file is a lost edit.
STAGING = MAIN / ".staging"


def rebuild_cmd():
    """The ONE way to rebuild the exe, read from build_stamp, never retyped.

    This used to print a bare `--onefile` line of its own. Following it builds
    a hub with no web pages and no registries, AND makes PyInstaller overwrite
    the curated MiceHub.spec with a generated stub - both happened on
    2026-08-21. A second copy of a command is a second chance to be wrong.
    """
    sys.path.insert(0, str(MAIN / "main_python"))
    try:
        import build_stamp
        return build_stamp.REBUILD
    except Exception:                                          # noqa: BLE001
        return "python -m PyInstaller --clean MiceHub.spec"


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
# `.staging` is NOT in this set on purpose - it is matched by prefix in skip(),
# so a second working copy is skipped too. See the note there.
SKIP_DIRS = {".git", ".pio", "__pycache__", "node_modules",
             ".vscode", "dist", "build",
             # .claude  this machine's Claude Code settings and permissions.
             # Staging's copy is stale the moment it is made, and promoting it
             # put an old permissions file over the live one. Machine-local
             # config is not source, the same as hub_auth.json.
             ".claude",
             # apps/voice/tts_cache  spoken-answer audio the helper builds
             # at run time from qa_data.json - derived, not source.
             "tts_cache",
             # reports/  one JSON per complaint, written at runtime by /api/report.
             # Machine-local, never promoted — like hub_auth.json.
             "reports",
             # projects/  Nong Studio saves. USER DATA: on 2026-09-16 a
             # staging copy from 08-10 was one promote away from replacing
             # the user's save of that evening.
             "projects",
             # sequences/  the YAML files Studio saves - user data too: the
             # same night staging's July my_move.yaml nearly replaced a 23:07 save.
             "sequences"}
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
SKIP_FILES = {"MiceHub.exe", "promt.md", "PLAN.html", "plan_state.js",
              # The integration page and its state: live progress, same as
              # PLAN.html. A promote copies staging over the tree, so leaving
              # them out is what stops a day-old copy erasing what landed.
              "system_integral.html", "system_integral_state.js",
              "settings_shared.json", "hub_auth.json", "hub_password.txt",
              # The login for an outside app. THIS MACHINE'S, like the
              # hub password beside it: promoting a staged copy would put
              # a test login over the real one, and a copy in a working
              # tree is a second place for a password to leak from.
              "faces_login.json",
              ".qc-receipt.json",   # proof about ONE tree; meaningless in another
              # The patch LOGS. Every patcher appends to the copy in the real
              # tree, so a staging copy is stale the moment a snapshot is taken
              # - and promoting it would rewrite the history with an older one,
              # losing the newest entries. Found 2026-09-08, before it bit.
              "PATCHES.md", "HANDOVER.md",
              # the note two agents leave each other; it belongs
              # to the real tree, like the plan
              "BRIDGE.md"}
SKIP_SUFFIX = {".pyc", ".pyo", ".tmp"}


def skip(p: Path) -> bool:
    for part in p.parts:
        # EVERY working copy, not only the one called `.staging`. This tool has
        # always taken --staging DIR, so a second tree (`.staging-integral`,
        # for a different job) is normal - and an exact-name match skipped only
        # the first. --init would then copy one whole tree inside the other,
        # and each promote would carry the other tree's files. A copy of a copy
        # of the source is how a finished feature was lost here once.
        if part in SKIP_DIRS or part.startswith(".staging"):
            return True
    return p.name in SKIP_FILES or p.suffix in SKIP_SUFFIX


def walk(root: Path):
    """Every file worth copying, as paths relative to root."""
    for folder, dirs, files in os.walk(root):
        base = Path(folder).relative_to(root)
        dirs[:] = sorted(d for d in dirs if not skip(base / d))
        for name in sorted(files):
            rel = base / name
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


def fingerprint(where: Path):
    try:
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, sys.argv[1]); "
             "import run_qc; print(run_qc.tree_fingerprint())", str(where / "qc")],
            cwd=str(where), capture_output=True, text=True, timeout=300)
    except (OSError, subprocess.TimeoutExpired):
        return None
    lines = result.stdout.strip().splitlines()
    return lines[-1] if result.returncode == 0 and lines else None


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
    receipt = where / ".qc-receipt.json"
    if not receipt.is_file():
        return False
    try:
        got = json.loads(receipt.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return False
    if (not isinstance(got, dict) or got.get("full") is not True
            or type(got.get("failed")) is not int or got["failed"] != 0
            or type(got.get("passed")) is not int or got["passed"] <= 0
            or not isinstance(got.get("tree"), str) or len(got["tree"]) != 64
            or any(c not in "0123456789abcdef" for c in got["tree"])):
        return False
    if fingerprint(where) != got["tree"]:
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


def build_web(where: Path):
    if not (where / "tools" / "build_web.py").exists(): return True
    print("building web assets in %s ..." % where, flush=True)
    try:
        result = subprocess.run(
            [sys.executable, str(where / "tools" / "build_web.py"), str(where)],
            cwd=str(where), timeout=300)
        return result.returncode == 0
    except (OSError, subprocess.TimeoutExpired) as exc:
        print("WEB BUILD FAILED: %s" % exc)
        return False

def fingerprint(where: Path):
    """run_qc's own hash of the tree, so a scoped gate can prove staging did
    not change under it (a full gate proves it with its receipt)."""
    r = subprocess.run([sys.executable, "-c",
                        "import sys; sys.path.insert(0, r'%s'); "
                        "import run_qc; print(run_qc.tree_fingerprint())" % (where / "qc")],
                       cwd=str(where), capture_output=True, text=True, timeout=300)
    return ((r.stdout or "").strip().splitlines() or [""])[-1]


def run_qc(where: Path, *, built=False, scoped=False):
    if not built and not build_web(where):
        return False
    qc = where / "qc" / "run_qc.py"
    if not qc.is_file():
        print("no QC suite at %s" % qc)
        return False
    print("running the %s QC suite in %s ...\n"
          % ("SCOPED (checks for what changed)" if scoped else "FULL", where))
    t0 = time.time()
    # A descendant retaining stdout must not keep promotion waiting for pipe EOF.
    fd, log_name = tempfile.mkstemp(prefix="mice-promote-qc-", suffix=".log")
    os.close(fd)
    decoder = codecs.getincrementaldecoder("utf-8")("replace")
    proc = None
    try:
        with open(log_name, "wb") as output, open(log_name, "rb") as reader:
            # --no-build: the web build already ran here; a second one only cost
            # time (found 2026-09-16).
            args = [sys.executable, "-u", str(qc), "--no-build"]
            if scoped:
                args.append("--changed")
            proc = subprocess.Popen(args, cwd=str(where),
                                    stdout=output, stderr=subprocess.STDOUT)
            while True:
                done = proc.poll() is not None
                chunk = reader.read()
                sys.stdout.write(decoder.decode(chunk, final=done))
                sys.stdout.flush()
                if done:
                    break
                time.sleep(0.1)
    finally:
        if proc is not None and proc.poll() is None:
            proc.terminate()
            try:
                proc.wait(timeout=10)
            except subprocess.TimeoutExpired:
                proc.kill()
                proc.wait()
        try:
            os.unlink(log_name)
        except OSError:
            print("QC log retained at %s" % log_name)
    print("\nQC finished in %.0fs, exit %d" % (time.time() - t0, proc.returncode))
    return proc.returncode == 0


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


def file_hash(path):
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None


@contextmanager
def promotion_lock():
    lock = MAIN / ".staging-promotion.lock"
    token = "%s:%s" % (os.getpid(), uuid.uuid4().hex)
    try:
        lock.mkdir()
    except FileExistsError:
        raise RuntimeError("another promotion/check owns %s; no lock was removed" % lock) from None
    owner = lock / "owner.txt"
    try:
        owner.write_bytes(token.encode("ascii"))
        yield
    finally:
        if owner.is_file() and owner.read_bytes() == token.encode("ascii"):
            owner.unlink()
            lock.rmdir()


def main_is_newer(files):
    """Files main changed AFTER staging's copy was taken.

    Copying one of these throws away someone else's newer work. A promote
    copies with copy2, which keeps the time, so a file staging really owns
    is never older than main's. Measured 2026-09-16: promote.py, README.md
    and COORDINATION.md were overwritten this way by a shared .staging.
    """
    out = []
    for rel in files:
        src, dst = STAGING / rel, MAIN / rel
        if dst.is_file() and dst.stat().st_mtime > src.stat().st_mtime + 2:
            out.append(rel)
    return out


def bridge(event, lines):
    """Tell the other agents, in the log every one of them reads, under the
    shared mutex (docs/COORDINATION.md). Best effort: never blocks a promote."""
    if not (MAIN / "docs" / "BRIDGE.md").is_file():
        return                   # a throwaway tree (QC) has no BRIDGE to tell
    lock = MAIN / ".staging-coordination.lock"
    who = os.environ.get("MICE_AGENT") or "unknown-session (set MICE_AGENT)"
    for _ in range(50):
        try:
            lock.mkdir()
            break
        except FileExistsError:
            time.sleep(0.2)
    else:
        print("(BRIDGE busy - %s not recorded)" % event)
        return
    try:
        (lock / "owner.txt").write_text(who, encoding="utf-8")
        stamp = time.strftime("%Y-%m-%d %H:%M:%S %z")
        block = "\n### %s — %s\nEvent: %s\n%s\n" % (stamp, who, event, "\n".join(lines))
        with open(MAIN / "docs" / "BRIDGE.md", "a", encoding="utf-8", newline="") as f:
            f.write(block)
    finally:
        (lock / "owner.txt").unlink(missing_ok=True)
        lock.rmdir()


def commit_copied(files):
    """Commit EXACTLY the files this promote copied - a rollback point per land.

    User 2026-09-16: *make commit everytime when change too to make sure it
    have rollback*. The pathspec matters: main carries other sessions'
    uncommitted work, and a bare `git commit -a` would sweep it in under
    this agent's name. Returns the short sha, or "" when there is no repo.
    """
    if not files or not (MAIN / ".git").exists():
        return ""
    paths = [r.as_posix() for r in files]
    who = os.environ.get("MICE_AGENT") or "unknown-session"
    tasks = os.environ.get("MICE_TASKS") or ""
    msg = "promote(%s): %d file(s)%s\n\n%s\n" % (
        who, len(paths), (" for " + tasks) if tasks else "", "\n".join(paths))
    if who.startswith("claude"):
        msg += "\nCo-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\n"
    git = ["git", "-C", str(MAIN)]
    try:
        subprocess.run(git + ["add", "--"] + paths, check=True, capture_output=True, timeout=120)
        r = subprocess.run(git + ["commit", "-q", "-m", msg, "--"] + paths,
                           capture_output=True, text=True, timeout=120)
        if r.returncode:
            print("commit skipped: %s" % (r.stderr or r.stdout).strip()[:200])
            return ""
        sha = subprocess.run(git + ["rev-parse", "--short", "HEAD"],
                             capture_output=True, text=True, timeout=30).stdout.strip()
        print("committed %s - roll back with: git revert %s" % (sha, sha))
        return sha
    except Exception as e:                                   # noqa: BLE001
        print("commit skipped: %s" % e)
        return ""


def promote(full=False):
    if not build_web(STAGING):
        print("REFUSED: web build failed. Nothing was copied.")
        return 1
    changed, added, gone = changes()
    if not (changed or added):
        show(changed, added, gone)
        return 0
    print("about to promote %d changed + %d new file(s)" % (len(changed), len(added)))
    # ASK, DO NOT OVERWRITE (user 2026-09-16: *check each other and ask need
    # promote or not then promote with no conflict*).
    newer = main_is_newer(changed)
    if newer:
        names = [r.as_posix() for r in newer]
        print("REFUSED: main has NEWER versions of %d file(s) than staging:" % len(names))
        for n in names:
            print("   ", n)
        print("Someone else changed them. Merge main's version into staging first,")
        print("or ask the owner in docs/BRIDGE.md. Nothing was copied.")
        bridge("REQUEST (promote refused: main is newer)",
               ["Tree: %s" % STAGING,
                "Files: " + ", ".join(names),
                "Next: whoever changed these in main - say in BRIDGE whether the "
                "staging copy may replace them, or merge them into staging."])
        return 1
    bridge("PROMOTE-START", ["Tree: %s" % STAGING,
                             "Files: " + ", ".join(r.as_posix() for r in changed + added),
                             "Next: do not edit these in main until PROMOTE-DONE."])
    main_before = {rel: file_hash(MAIN / rel) for rel in walk(STAGING)}
    _plan("promote: checking whether staging is already green")
    # SCOPED BY DEFAULT (user, 2026-09-16): run_qc --changed runs the checks for
    # what changed, and the full suite by itself when a core file or more than
    # one system changed (qc/data/scope.json). --full forces the whole suite.
    green = already_green(STAGING)
    before = "" if (green or full) else fingerprint(STAGING)
    if not (green or run_qc(STAGING, built=True, scoped=not full)):
        print("\nREFUSED: QC is not green in staging. Nothing was copied.")
        return 1
    if before and not already_green(STAGING):
        # Scoped: no full receipt, so prove the tree is the one that was checked.
        if fingerprint(STAGING) != before:
            print("REFUSED: staging changed during the gate. Nothing was copied.")
            return 1
    elif not already_green(STAGING) and not STAGING.parent.name.startswith("qc_land_"):
        print("REFUSED: staging no longer has an exact green receipt. Nothing was copied.")
        return 1
    changed, added, gone = changes()
    conflicts = [rel for rel in changed + added
                 if file_hash(MAIN / rel) != main_before.get(rel)]
    if conflicts:
        print("REFUSED: main changed during the gate: " + ", ".join(map(str, conflicts)))
        return 1
    for rel in changed + added:
        dst = MAIN / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(STAGING / rel, dst)
    print("\npromoted %d file(s) to %s" % (len(changed) + len(added), MAIN))
    sha = commit_copied(changed + added)
    bridge("PROMOTE-DONE", ["Tree: %s" % STAGING,
                            "Files: %d copied into main" % (len(changed) + len(added)),
                            "Commit: %s  (roll back with: git revert %s)" % (sha, sha)
                            if sha else "Commit: none (not a git repo, or git failed)"])
    show(changed, added, gone)
    if any(rel.as_posix().endswith("main_python/main.py") for rel in changed + added):
        print("\nNOTE: main_python/main.py changed — rebuild MiceHub.exe:")
        print("  " + rebuild_cmd())
    return 0


def main(argv):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--init", action="store_true", help="create/refresh the staging copy")
    ap.add_argument("--check", action="store_true", help="run full QC in staging, promote nothing")
    ap.add_argument("--diff", action="store_true", help="show what would move")
    ap.add_argument("--full", action="store_true",
                    help="run the whole QC suite even for a one-system change")
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
    try:
        with promotion_lock():
            if a.check:
                return 0 if run_qc(STAGING) else 1
            return promote(full=a.full)
    except RuntimeError as exc:
        print("REFUSED: %s" % exc)
        return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
