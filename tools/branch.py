#!/usr/bin/env python3
"""One task, one branch, one working copy - and main is changed only by a merge.

    set MICE_AGENT=claude:09171042-a7db
    python tools/branch.py start A0-24      main must be clean; makes .staging-A0-24-<session>
    python tools/branch.py save  A0-24      commit the copy to task/A0-24-<session>
    python tools/branch.py check A0-24      would it merge into main? names the conflicts
    python tools/branch.py land  A0-24      gate, then fast-forward main to a merge commit
    python tools/branch.py list             every task branch
    python tools/branch.py live             commit the plan, logs and Studio saves

User decision 2026-09-17 (A0-24): *main stays clean* - no agent writes main
directly; each task has its own branch, so a file conflict is visible before
anything lands, and every land is one merge commit to roll back.

Why copy trees and not `git worktree`: QC needs files git does not track
(firmware/generated, patch logs, hub_auth.json). A copy has them; a worktree
does not. So the branch commit is built from the copy with a private index,
and `land` proves the copy QC checked IS the merge result before it merges.

Git runs with core.autocrlf=false here: this repo is LF, and the machine-wide
autocrlf=true would write every merged file back CRLF (see CLAUDE.md, mice.css).
"""
import importlib.util
import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

HERE = Path(__file__).resolve().parent.parent
REAL = HERE.parent if HERE.name.startswith(".staging") else HERE
META = ".staging-branch.json"        # in the copy: task, session, base, branch


def load_promote(main=None):
    spec = importlib.util.spec_from_file_location("branch_promote", str(HERE / "promote.py"))
    P = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(P)
    P.MAIN = main or REAL
    return P


def git(main, *args, index=None, work=None, check=True, stdin=None):
    env = dict(os.environ)
    if index:
        env["GIT_INDEX_FILE"] = str(index)
    cmd = ["git", "-c", "core.autocrlf=false", "-c", "core.safecrlf=false",
           "--git-dir", str(main / ".git"), "--work-tree", str(work or main)] + list(args)
    r = subprocess.run(cmd, cwd=str(work or main), env=env, capture_output=True,
                       text=True, encoding="utf-8", errors="replace", input=stdin, timeout=600)
    if check and r.returncode:
        raise SystemExit("git %s failed: %s" % (args[0], (r.stderr or r.stdout).strip()[:400]))
    return r


def who():
    agent = os.environ.get("MICE_AGENT", "")
    if ":" not in agent:
        raise SystemExit("set MICE_AGENT=provider:session first (python tools/plan.py session <provider>)")
    return agent


def names(task, agent):
    session = agent.split(":", 1)[1]
    return ".staging-%s-%s" % (task, session), "task/%s-%s" % (task, session)


def dirty(main):
    """Source changed in main: tracked changes and untracked, not-ignored files.

    Paths promote never copies do not count - the plan, BRIDGE, prompt logs,
    Studio saves. They are written live in main by design; `live` commits them."""
    P = load_promote(main)
    out = git(main, "status", "--porcelain", "--untracked-files=all").stdout
    paths = [line[3:].strip().strip('"') for line in out.splitlines() if line.strip()]
    paths = [p.split(" -> ")[-1] for p in paths]
    return [p for p in paths if not P.skip(Path(p))]


def live(main):
    """Commit the live files (plan, logs, user saves) - a rollback point for them too."""
    P = load_promote(main)
    out = git(main, "status", "--porcelain", "--untracked-files=all").stdout
    paths = [line[3:].strip().strip('"').split(" -> ")[-1] for line in out.splitlines() if line.strip()]
    paths = [p for p in paths if P.skip(Path(p))]
    if not paths:
        print("no live files changed")
        return 0
    git(main, "add", "-A", "--", *paths)
    git(main, "commit", "-q", "-m", "live: plan, logs and saves (%d path(s))" % len(paths), "--", *paths)
    print("committed %d live path(s)" % len(paths))
    return 0


def meta(tree):
    try:
        return json.loads((tree / META).read_text(encoding="utf-8"))
    except (OSError, ValueError):
        raise SystemExit("%s is not a task copy (no %s) - run start first" % (tree, META))


def start(main, task, agent):
    P = load_promote(main)
    folder, branch = names(task, agent)
    tree = main / folder
    if tree.exists():
        raise SystemExit("REFUSED: %s already exists - one copy per task and session" % folder)
    left = dirty(main)
    if left:
        raise SystemExit("REFUSED: main is not clean (%d path(s), first: %s). Main stays clean: "
                         "commit or move that work first." % (len(left), left[0]))
    with P.promotion_lock():
        base = git(main, "rev-parse", "HEAD").stdout.strip()
        P.STAGING = tree
        P.init()
        if dirty(main) or git(main, "rev-parse", "HEAD").stdout.strip() != base:
            raise SystemExit("REFUSED: main moved while copying; delete %s and start again" % folder)
    git(main, "update-ref", "refs/heads/" + branch, base, "0" * 40)
    (tree / META).write_text(json.dumps({"task": task, "agent": agent, "base": base,
                                         "branch": branch}, indent=1), encoding="utf-8")
    P.bridge("CLAIM", ["Task: %s" % task, "Tree: %s" % tree,
                       "Branch: %s from %s" % (branch, base[:10])])
    print("started %s at %s - work in %s" % (branch, base[:10], tree))
    return tree


def source_paths(P, tree, tracked):
    """(what git should hold from the copy, everything the copy holds).
    An ignored path counts only when the parent already tracks it."""
    paths = [r.as_posix() for r in P.walk(tree)]
    if not paths:
        return [], set()
    ignored = git(P.MAIN, "check-ignore", "--no-index", "--stdin", work=tree, check=False,
                  stdin="\n".join(paths) + "\n").stdout.split("\n")
    skip = {x.strip() for x in ignored if x.strip()} - tracked
    return [p for p in paths if p not in skip], set(paths)


def tree_of(P, tree, parent_commit):
    """A git tree of the copy, built in a private index over the parent commit.

    Paths promote never copies (PLAN.html, BRIDGE.md, user data) keep the
    parent's version: the copy's own are stale by design, never newer."""
    main = P.MAIN
    fd, index = tempfile.mkstemp(prefix="mice-branch-", suffix=".index")
    os.close(fd)
    os.unlink(index)
    try:
        git(main, "read-tree", parent_commit, index=index)
        listed = git(main, "ls-tree", "-r", "--name-only", parent_commit).stdout.splitlines()
        present, known = source_paths(P, tree, set(listed))
        gone = [p for p in listed if p not in known and not P.skip(Path(p))]
        for chunk in range(0, len(present), 500):
            git(main, "add", "-f", "--", *present[chunk:chunk + 500], index=index, work=tree)
        for chunk in range(0, len(gone), 500):
            git(main, "rm", "-q", "--cached", "--ignore-unmatch", "--", *gone[chunk:chunk + 500],
                index=index, work=tree)
        return git(main, "write-tree", index=index).stdout.strip()
    finally:
        if os.path.exists(index):
            os.unlink(index)


def save(main, task, agent, message=""):
    P = load_promote(main)
    folder, branch = names(task, agent)
    tree = main / folder
    info = meta(tree)
    tip = git(main, "rev-parse", "refs/heads/" + branch).stdout.strip()
    new_tree = tree_of(P, tree, tip)
    if new_tree == git(main, "rev-parse", tip + "^{tree}").stdout.strip():
        print("%s: nothing new since %s" % (branch, tip[:10]))
        return tip
    msg = "%s(%s): %s\n\n%s" % (task, agent, message or "save", "Co-Authored-By: Claude Opus 5 (1M context) "
                                "<noreply@anthropic.com>\n" if agent.startswith("claude") else "")
    commit = git(main, "commit-tree", new_tree, "-p", tip, stdin=msg).stdout.strip()
    # expected old value: a concurrent save of the same branch fails instead of winning
    git(main, "update-ref", "refs/heads/" + branch, commit, tip)
    print("saved %s -> %s (base %s)" % (branch, commit[:10], info["base"][:10]))
    return commit


def merge_result(main, head, tip):
    """(tree, conflict text). A non-zero exit is a conflict even when a tree is printed."""
    r = git(main, "merge-tree", "--write-tree", "--name-only", head, tip, check=False)
    lines = r.stdout.splitlines()
    if r.returncode == 0 and lines:
        return lines[0].strip(), ""
    return None, (r.stdout + r.stderr).strip() or "merge-tree exit %d" % r.returncode


def copy_matches(P, tree, result_tree):
    """Paths where the copy differs from the merge result - QC must see exactly it."""
    main = P.MAIN
    fd, index = tempfile.mkstemp(prefix="mice-branch-check-", suffix=".index")
    os.close(fd)
    os.unlink(index)
    try:
        git(main, "read-tree", result_tree, index=index)
        git(main, "update-index", "-q", "--refresh", index=index, work=tree, check=False)
        diff = git(main, "diff-files", "--name-only", index=index, work=tree).stdout.split("\n")
        extra = git(main, "ls-files", "--others", "--exclude-standard", index=index,
                    work=tree).stdout.split("\n")
        return sorted({p for p in diff + extra if p.strip() and not P.skip(Path(p))})
    finally:
        if os.path.exists(index):
            os.unlink(index)


def check(main, task, agent):
    folder, branch = names(task, agent)
    head = git(main, "rev-parse", "HEAD").stdout.strip()
    tip = git(main, "rev-parse", "refs/heads/" + branch).stdout.strip()
    result, conflict = merge_result(main, head, tip)
    if result is None:
        print("CONFLICT merging %s into main:\n%s" % (branch, conflict))
        return 1
    changed = git(main, "diff", "--name-only", head, result).stdout.split()
    print("%s merges cleanly into main: %d file(s) change" % (branch, len(changed)))
    return 0


def land(main, task, agent, full=False):
    P = load_promote(main)
    folder, branch = names(task, agent)
    tree = main / folder
    meta(tree)
    P.STAGING = tree
    if not P.build_web(tree):                  # build BEFORE the save: commit what QC reads
        raise SystemExit("REFUSED: web build failed")
    with P.promotion_lock():
        left = dirty(main)
        if left:
            raise SystemExit("REFUSED: main is not clean (%s ...). Main stays clean." % left[0])
        head = git(main, "rev-parse", "HEAD").stdout.strip()
        tip = save(main, task, agent, "land")
        result, conflict = merge_result(main, head, tip)
        if result is None:
            print("REFUSED: %s does not merge into main:\n%s" % (branch, conflict))
            return 1
        differ = copy_matches(P, tree, result)
        if differ:
            print("REFUSED: the copy is not the merge result (%d path(s), first: %s).\n"
                  "Main moved: run promote.py --staging %s --init, merge, then land again."
                  % (len(differ), differ[0], folder))
            return 1
        before = P.fingerprint(tree)
        if not (P.already_green(tree) or P.run_qc(tree, built=True, scoped=not full)):
            print("REFUSED: QC is not green. main untouched.")
            return 1
        if P.fingerprint(tree) != before:
            print("REFUSED: the copy changed during the gate. main untouched.")
            return 1
        if (git(main, "rev-parse", "HEAD").stdout.strip() != head or dirty(main)
                or git(main, "rev-parse", "refs/heads/" + branch).stdout.strip() != tip):
            print("REFUSED: main or the branch moved during the gate. main untouched.")
            return 1
        files = [f for f in git(main, "diff", "--name-only", head, result).stdout.split("\n") if f]
        with open(main / P.LANDED_LOG, "a", encoding="utf-8", newline="") as f:
            f.write(json.dumps({"tree": str(tree), "who": agent, "files": {
                x: P.file_hash(tree / x) for x in files}}) + "\n")
        msg = "land(%s): %s from %s\n\n%s\n" % (agent, task, branch, "\n".join(files))
        if agent.startswith("claude"):
            msg += "\nCo-Authored-By: Claude Opus 5 (1M context) <noreply@anthropic.com>\n"
        merged = git(main, "commit-tree", result, "-p", head, "-p", tip, stdin=msg).stdout.strip()
        git(main, "merge", "--ff-only", "--no-overwrite-ignore", merged)
        base = P.load_base()
        for x in files:
            base[x] = P.file_hash(main / x)
        P.save_base(base)
        info = meta(tree)
        info["base"] = merged
        (tree / META).write_text(json.dumps(info, indent=1), encoding="utf-8")
    P.bridge("PROMOTE-DONE", ["Task: %s" % task, "Tree: %s" % tree,
                              "Files: %d merged into main" % len(files),
                              "Commit: %s  (roll back with: git revert -m 1 %s)" % (merged[:10], merged[:10])])
    print("landed %s: main is now %s (%d file(s))" % (branch, merged[:10], len(files)))
    return 0


def list_tasks(main):
    out = git(main, "for-each-ref", "--format=%(refname:short) %(objectname:short)",
              "refs/heads/task/").stdout.strip()
    print(out or "no task branches")
    return 0


def main(argv):
    if len(argv) < 1 or argv[0] in ("-h", "--help"):
        print(__doc__)
        return 0
    action = argv[0]
    if action == "list":
        return list_tasks(REAL)
    if action == "live":
        return live(REAL)
    if len(argv) < 2:
        raise SystemExit("%s: need a task id" % action)
    agent, task = who(), argv[1]
    if action == "start":
        start(REAL, task, agent)
        return 0
    if action == "save":
        save(REAL, task, agent, " ".join(argv[2:]))
        return 0
    if action == "check":
        return check(REAL, task, agent)
    if action == "land":
        return land(REAL, task, agent, full="--full" in argv)
    raise SystemExit("unknown action %r" % action)


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
