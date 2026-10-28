"""The PC tidy renames the repo and moves only what the user approved (A51-3).

User 2026-10-27/28: rename `code` to `mice_system`, move the friend's
Photobooth and its run data under photobooth/, and list the thesis/hardware
leftovers for an OK. The rules that matter on the real PC, each driven here
against a throwaway parent folder:

  * an entry whose "ok" is empty is listed, never moved;
  * nothing is deleted - every file that was there is still there;
  * a git repo that moved (the friend's Photobooth) is still a git repo;
  * it refuses while a program is working inside a folder it would move
    (Windows would fail half-way: RL/YOLO training, the hub, a session),
    and when run from a shell sitting inside the repo;
  * after the rename, this PC's git-ignored files that named the old path
    name the new one, with the old copy kept as .bak;
  * no live file in git names the PC's absolute repo path, so the rename
    needs no code change (hooks use CLAUDE_PROJECT_DIR, voice finds llm/
    from its own file).
"""
import argparse
import json
import shutil
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "the PC tidy renames the repo and moves only approved folders, deleting nothing"

# live files: code, settings, the rules every AI reads. History (plans,
# panels, bridges, handoff notes, the prompt log) keeps the old path on purpose.
LIVE = ("*.py", "*.js", "*.json", "*.bat", "*.ps1", "*.spec", ".claude/**", ".agents/**",
        "CLAUDE.md", "AGENTS.md", "GEMINI.md", "HANDOFF.md", "docs/COORDINATION.md")
HISTORY = ("docs/PLAN.html", "docs/plan_state.js", "docs/a22_sweep_findings.json")
OLD_ROOT = ("final_proj/mice/code", "final_proj\\mice\\code", "final_proj\\\\mice\\\\code")


def _files(root):
    return sorted(str(p.relative_to(root)) for p in root.rglob("*")
                  if p.is_file() and ".git" not in p.parts)


def run(t):
    sys.path.insert(0, str(F.CODE / "tools"))
    import tidy_pc as T

    box = Path(tempfile.mkdtemp(prefix="qc_tidy_"))
    sleeper = None
    try:
        repo = box / "code"
        (repo / "config").mkdir(parents=True)
        shutil.copy(F.CODE / "config" / "layout.json", repo / "config" / "layout.json")
        (repo / ".gitignore").write_text("local.json\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q"], cwd=repo)
        (repo / "local.json").write_text(json.dumps({"llm": str(repo / "llm")}), encoding="utf-8")
        booth = box / "Photobooth"
        booth.mkdir()
        subprocess.run(["git", "init", "-q"], cwd=booth)
        (booth / "app.py").write_text("x", encoding="utf-8")
        (box / "Photobooth-run" / "Dummy").mkdir(parents=True)
        (box / "Photobooth-run" / "Dummy" / "shot.jpg").write_bytes(b"jpg")
        (box / "electric").mkdir()
        (box / "electric" / "board.sch").write_text("s", encoding="utf-8")
        (box / "ตู้มหัสจรรย์_old.docx").write_bytes(b"doc")
        (box / "Face_Regonize").mkdir()
        before = _files(box)

        tp = T.PcTidy(repo)
        plan = {e["to"]: (pairs, ok) for e, pairs, ok in tp.plan()}
        t.ok(plan["photobooth/Photobooth"][1] and plan["photobooth/run"][1],
             "the photobooth moves are approved (user 2026-10-27)", plan.keys())
        t.ok(not plan["hardware/electric"][1] and not plan["thesis_archive"][1],
             "the thesis and hardware moves wait for an OK", "")
        t.eq([d.name for _, d in plan["thesis_archive"][0]], ["ตู้มหัสจรรย์_old.docx"],
             "a pattern entry gathers matching files into its folder")
        t.eq(tp.target_root(), box / "mice_system", "the repo becomes mice_system")

        # ---- refuses while something works inside ------------------------
        args = argparse.Namespace(yes=True, closed_everything=False)
        sleeper = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"],
                                   cwd=str(box / "Photobooth-run"))
        time.sleep(0.5)
        busy = tp.busy([repo, box / "Photobooth-run"])
        if busy is None:
            t.ok(True, "psutil missing here: busy check skipped", "")
        else:
            t.ok(any(str(sleeper.pid) in b for b in busy),
                 "a program working inside a folder to move is found", busy)
            code = T._apply(tp, args)
            t.ok(code == 2 and booth.is_dir() and repo.is_dir(),
                 "and nothing moves while it runs", code)
        sleeper.kill()
        sleeper.wait()
        sleeper = None

        # ---- the real run -----------------------------------------------------
        args.closed_everything = True
        t.eq(T._apply(tp, args), 0, "apply finishes once nothing runs inside")
        new = box / "mice_system"
        t.ok(new.is_dir() and not repo.exists(), "code was renamed to mice_system", "")
        t.ok((box / "photobooth" / "Photobooth" / ".git").is_dir()
             and (box / "photobooth" / "run" / "Dummy" / "shot.jpg").is_file(),
             "the friend's repo and its run data are under photobooth/, still a git repo", "")
        t.ok((box / "electric" / "board.sch").is_file()
             and (box / "ตู้มหัสจรรย์_old.docx").is_file(),
             "what waits for an OK did not move", "")
        after = _files(box)
        lost = [f for f in before if Path(f).name not in {Path(a).name for a in after}]
        t.ok(not lost, "nothing was deleted", lost)
        local = json.loads((new / "local.json").read_text(encoding="utf-8"))
        t.ok(local["llm"] == str(new / "llm") and (new / "local.json.bak").is_file(),
             "this PC's file that named the old path names the new one (.bak kept)", local)
        t.ok("mice_system" in tp.rc_command(new) and "{root}" not in tp.rc_command(new),
             "the Remote Control start command names the new folder", tp.rc_command(new))
    finally:
        if sleeper:
            sleeper.kill()
        shutil.rmtree(box, ignore_errors=True)

    # ---- a shell inside the repo is refused ----------------------------------------
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "tidy_pc.py"), "apply", "--yes"],
                       cwd=str(F.CODE), capture_output=True, text=True)
    t.ok(r.returncode == 2 and "folder above" in r.stdout,
         "apply refuses from a shell inside the repo (Windows would block the rename)",
         r.stdout[-300:])

    # ---- no live file names the PC's repo path ---------------------------------------
    hits = []
    tracked = subprocess.run(["git", "ls-files", *LIVE], cwd=F.CODE,
                             capture_output=True, text=True).stdout.splitlines()
    for rel in tracked:
        if rel in HISTORY or rel.startswith(("docs/archive/", "handoff/tasks/")):
            continue
        try:
            text = (F.CODE / rel).read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if any(o in text for o in OLD_ROOT) and rel != "qc/checks/check_tidy_pc.py":
            hits.append(rel)
    t.ok(not hits, "no live file names the PC's repo folder by its absolute path",
         "use a path relative to the repo (hooks: $env:CLAUDE_PROJECT_DIR): %s" % hits)
