"""One task, one branch: main changes only by a merge that QC saw first.

User decision 2026-09-17 (A0-24): *main stays clean* - no agent writes main
directly, every task has its own branch, a conflict shows before landing.
Codex review of the design (same day) named the traps this holds:

  * start refuses a dirty main, and an existing copy;
  * save commits the copy on task/<TASK>-<session> - never the copy's stale
    PLAN.html, never deleting a tracked-but-ignored file it did not copy;
  * check names a conflict with main before anything lands;
  * land refuses when main moved so the copy is not the merge result
    (QC would have checked a tree that never reaches main);
  * land merges only after a green gate, as one merge commit, byte-exact LF
    even with the machine's core.autocrlf=true;
  * a red gate leaves main exactly as it was.
Driven in a throwaway git repo with a stub QC; the real repo is never touched.
"""
import importlib.util
import os
import subprocess
import tempfile
from pathlib import Path

import qc as F


AREA = "tools"
TITLE = "branch.py: one branch per task, main moves only by a checked merge"

STUB_QC = '''import hashlib, json, os, sys
from pathlib import Path
ROOT = Path(__file__).resolve().parent.parent
def tree_fingerprint():
    h = hashlib.sha256()
    for p in sorted(ROOT.rglob('*')):
        if p.is_file() and not p.name.startswith('.staging') and p.name != '.qc-receipt.json' \\
                and '.git' not in p.parts and '__pycache__' not in p.parts:
            h.update(str(p.relative_to(ROOT)).encode()); h.update(p.read_bytes())
    return h.hexdigest()
if __name__ == '__main__':
    if (ROOT / 'RED').exists():
        print('QC FAIL 0 passed, 1 failed'); sys.exit(1)
    print('QC PASS 1 passed, 0 failed')
'''


def _git(repo, *args):
    return subprocess.run(["git", "-c", "core.autocrlf=false", "-C", str(repo)] + list(args), capture_output=True,
                          text=True, check=True).stdout.strip()


def run(t):
    spec = importlib.util.spec_from_file_location("branch_under_test", str(F.CODE / "tools" / "branch.py"))
    B = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(B)
    pspec = importlib.util.spec_from_file_location("branch_promote_test", str(F.CODE / "promote.py"))
    P = importlib.util.module_from_spec(pspec)
    pspec.loader.exec_module(P)
    B.load_promote = lambda main=None: (setattr(P, "MAIN", main), P)[1]

    repo = Path(tempfile.mkdtemp(prefix="qc_branch_"))
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    for k, v in (("user.name", "qc"), ("user.email", "qc@x"), ("core.autocrlf", "true")):
        _git(repo, "config", k, v)
    files = {"app.js": b"one\ntwo\n", "other.js": b"x\n", "docs/PLAN.html": b"plan v1\n",
             "gen/keep.txt": b"tracked but ignored\n", "projects/save.json": b"user data\n",
             "qc/run_qc.py": STUB_QC.encode(),
             "tools/build_web.py": b"", ".gitignore": b"gen/\n.staging*/\n.staging*\n"}
    for name, data in files.items():
        (repo / name).parent.mkdir(parents=True, exist_ok=True)
        (repo / name).write_bytes(data)
    _git(repo, "add", "-f", ".")
    _git(repo, "commit", "-q", "-m", "base")
    os.environ.setdefault("MICE_AGENT", "qc:branch")
    agent = "qc:b1"

    (repo / "stray.txt").write_bytes(b"dirty\n")
    try:
        B.start(repo, "T-1", agent)
        t.ok(False, "start refuses a dirty main", "it started")
    except SystemExit as e:
        t.ok("not clean" in str(e), "start refuses a dirty main", str(e))
    (repo / "stray.txt").unlink()
    (repo / "docs" / "PLAN.html").write_bytes(b"plan v2, written live\n")
    t.ok(B.dirty(repo) == [], "the live plan does not make main dirty", B.dirty(repo))
    B.live(repo)
    t.ok(_git(repo, "status", "--porcelain") == "", "live commits it", "")

    tree = B.start(repo, "T-1", agent)
    t.ok(_git(repo, "rev-parse", "task/T-1-b1") == _git(repo, "rev-parse", "HEAD"),
         "start makes task/<TASK>-<session> at main", "")
    try:
        B.start(repo, "T-1", agent)
        t.ok(False, "a second start of the same task is refused", "")
    except SystemExit as e:
        t.ok("already exists" in str(e), "a second start of the same task is refused", str(e))

    (tree / "app.js").write_bytes(b"one\nTWO\n")
    (tree / "new.js").write_bytes(b"new\n")
    (tree / "docs").mkdir(exist_ok=True)       # --init never copies the plan
    (tree / "docs" / "PLAN.html").write_bytes(b"stale copy\n")
    t.ok(not (tree / "projects").exists(), "--init never copies user data", "")
    (tree / "gen" / "keep.txt").write_bytes(b"tracked but ignored, edited\n")
    B.save(repo, "T-1", agent)
    shown = _git(repo, "diff", "--name-status", "main", "task/T-1-b1").split("\n")
    t.ok(sorted(shown) == ["A\tnew.js", "M\tapp.js", "M\tgen/keep.txt"],
         "save commits the edits and the new file - not the stale PLAN.html, "
         "not deleting user data the copy never had", shown)

    # someone lands a change to app.js on main: a conflict, named before landing
    (repo / "app.js").write_bytes(b"ONE\ntwo-main\n")
    _git(repo, "commit", "-q", "-am", "main moves")
    t.ok(B.check(repo, "T-1", agent) == 1, "check names a conflict with main", "")
    t.ok(B.land(repo, "T-1", agent) == 1 and _git(repo, "log", "-1", "--format=%s") == "main moves",
         "land refuses a conflicting branch and main stays put", "")
    _git(repo, "reset", "-q", "--hard", "HEAD~1")

    # main moves on ANOTHER file: merges cleanly, but the copy never saw it
    (repo / "other.js").write_bytes(b"y\n")
    _git(repo, "commit", "-q", "-am", "other moves")
    t.ok(B.check(repo, "T-1", agent) == 0, "a change to another file merges cleanly", "")
    t.ok(B.land(repo, "T-1", agent) == 1,
         "land refuses when the copy is not the merge result QC would need to see", "")
    (tree / "other.js").write_bytes(b"y\n")       # what --init refresh brings in

    (tree / "RED").write_bytes(b"")
    before = _git(repo, "rev-parse", "HEAD")
    t.ok(B.land(repo, "T-1", agent) == 1 and _git(repo, "rev-parse", "HEAD") == before,
         "a red gate leaves main exactly as it was", "")
    (tree / "RED").unlink()

    code = B.land(repo, "T-1", agent)
    parents = _git(repo, "log", "-1", "--format=%p").split()
    t.ok(code == 0 and len(parents) == 2, "a green gate lands as one merge commit", (code, parents))
    t.ok((repo / "app.js").read_bytes() == b"one\nTWO\n" and (repo / "new.js").is_file(),
         "main's files are the branch's, byte-exact LF despite autocrlf=true",
         (repo / "app.js").read_bytes())
    t.ok((repo / "docs" / "PLAN.html").read_bytes() == b"plan v2, written live\n"
         and (repo / "projects" / "save.json").read_bytes() == b"user data\n",
         "main's own PLAN.html and its user data survive the merge", "")
    t.ok(B.dirty(repo) == [], "and main is clean afterwards", B.dirty(repo))
