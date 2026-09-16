"""A promote asks before it overwrites another agent's newer work.

Asked 2026-09-16: *if other AI do in the same time and need to promote in the
same time, check each other and ask need promote or not, then promote with no
conflict*. The same evening showed why: a shared .staging promoted older
copies of promote.py, README.md and COORDINATION.md over newer ones in main,
and was one promote away from replacing the user's Nong Studio save with a
copy from August.

Holds:
  * a file main changed AFTER staging's copy is refused, by name;
  * the refusal is written to BRIDGE as a REQUEST, so the other agent sees it;
  * a file staging really changed later still promotes (no false refusal);
  * Nong Studio projects/ never travel with a promote - they are user data.
Driven in throwaway trees; the real tree and BRIDGE are never touched.
"""
import importlib.util
import os
import tempfile
import time
from pathlib import Path

import qc as F


AREA = "tools"
TITLE = "promote refuses to overwrite newer work and asks in BRIDGE"


def run(t):
    spec = importlib.util.spec_from_file_location("promote_under_test",
                                                  str(F.CODE / "promote.py"))
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)

    root = Path(tempfile.mkdtemp(prefix="qc_promote_ask_"))
    main, stage = root, root / ".staging"
    (main / "docs").mkdir(parents=True)
    (main / "docs" / "BRIDGE.md").write_text("# bridge\n", encoding="utf-8")
    stage.mkdir()
    P.MAIN, P.STAGING = main, stage

    old = time.time() - 3600
    # theirs.txt: staging holds an OLD copy, main was changed after it
    (stage / "theirs.txt").write_text("stale staging copy", encoding="utf-8")
    os.utime(stage / "theirs.txt", (old, old))
    (main / "theirs.txt").write_text("someone's newer work", encoding="utf-8")
    # mine.txt: staging changed it after main's copy
    (main / "mine.txt").write_text("main before", encoding="utf-8")
    os.utime(main / "mine.txt", (old, old))
    (stage / "mine.txt").write_text("my newer edit", encoding="utf-8")

    newer = [r.as_posix() for r in P.main_is_newer([Path("theirs.txt"), Path("mine.txt")])]
    t.ok(newer == ["theirs.txt"],
         "a file main changed after staging's copy is caught, and only that one",
         newer)

    P.bridge("REQUEST (promote refused: main is newer)", ["Files: theirs.txt"])
    said = (main / "docs" / "BRIDGE.md").read_text(encoding="utf-8")
    t.ok("REQUEST" in said and "theirs.txt" in said,
         "the refusal is asked in BRIDGE, where every agent reads", said[-300:])
    t.ok(not (main / ".staging-coordination.lock").exists(),
         "and the shared BRIDGE lock is released afterwards")

    # ---- every land is a commit of exactly what it copied ----------------
    import subprocess
    repo = Path(tempfile.mkdtemp(prefix="qc_promote_git_"))
    g = ["git", "-C", str(repo), "-c", "user.name=qc", "-c", "user.email=qc@x"]
    subprocess.run(["git", "init", "-q", str(repo)], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "qc"], check=True)
    subprocess.run(["git", "-C", str(repo), "config", "user.email", "qc@x"], check=True)
    # Both tracked, both then changed - main's real state: other sessions'
    # uncommitted edits sit beside the files a promote just copied.
    for name in ("landed.txt", "someone_else.txt"):
        (repo / name).write_text("baseline", encoding="utf-8")
    subprocess.run(g + ["add", "."], check=True, capture_output=True)
    subprocess.run(g + ["commit", "-q", "-m", "base"], check=True, capture_output=True)
    (repo / "landed.txt").write_text("promoted", encoding="utf-8")
    (repo / "someone_else.txt").write_text("another session's work", encoding="utf-8")
    (repo / ".gitignore").write_text("patches/\n", encoding="utf-8")
    (repo / "patches").mkdir()
    (repo / "patches" / "0001.txt").write_text("snapshot", encoding="utf-8")
    P.MAIN = repo
    # an ignored snapshot copied alongside must not sink the whole commit
    sha = P.commit_copied([Path("landed.txt"), Path("patches/0001.txt")])
    t.ok(bool(sha), "a promote leaves a commit to roll back to", sha)
    shown = subprocess.run(g + ["show", "--name-only", "--format=", "HEAD"],
                           capture_output=True, text=True).stdout.split()
    t.ok(shown == ["landed.txt"],
         "and it holds only the files it copied, never another session's work", shown)
    P.MAIN = main
    # ...and the real promote uses it on what it copied. Read from the live
    # function: driving a whole promote needs a full gate, which this is not.
    import inspect
    src = inspect.getsource(P.promote)
    t.ok("commit_copied(changed + added)" in src
         and src.index("shutil.copy2(STAGING / rel, dst)") < src.index("commit_copied("),
         "promote commits right after it copies", "")

    t.ok(P.skip(Path("nong/main_python_set_nong/projects/all_move.json")),
         "Nong Studio saves never travel with a promote")
    t.ok(P.skip(Path("nong/main_python_set_nong/sequences/my_move.yaml")),
         "nor do the sequences Studio saves")
    t.ok(not P.skip(Path("nong/main_python_set_nong/web/app.js")),
         "while the Studio's own code still does")
