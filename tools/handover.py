#!/usr/bin/env python3
"""One checkpoint across every area, and the note that lets someone else finish.

Asked for 2026-09-08, when the owner handed the interface work to Codex:
*make it have backup when it hit limit you can access and do it follow the
codex as fallback*. An agent that runs out of budget mid-task leaves two
questions behind - what did it already change, and where do I pick it up - and
neither is answerable from the code alone.

    python tools/handover.py save "what I just finished"    checkpoint + note
    python tools/handover.py sync                           reconcile histories
    python tools/handover.py show                           read the note
    python tools/handover.py undo                           how to go back

WHAT `save` DOES
    * snapshots EVERY area with the patchers that already exist - the hub and
      shared code (tools/save_code_patch.py), Nong Studio's web app and the
      firmware (their own save_patch/save_fw_patch). Nothing new is invented:
      each area keeps its own numbered, append-only history, and any of them
      can be restored on its own;
    * writes docs/HANDOVER.md: when, what was said, which snapshot numbers were
      made, what is different between .staging and the real tree, what the plan
      says is unfinished, and the exact commands to carry on with.

WHY A FILE AND NOT A COMMIT. The real tree here carries uncommitted work by
design, and `git checkout` has destroyed promoted work in this project before.
The patchers copy; they never revert anything by themselves.
"""
import argparse
import filecmp
import re
import runpy
import shutil
import sys
import time
from pathlib import Path

WORK = Path(__file__).resolve().parent.parent
# Save the working source, while the live note and authoritative histories
# belong to main. Merely rebasing everything to main lost unpromoted edits.
ROOT = WORK.parent if WORK.name.startswith(".staging") else WORK
NOTE = ROOT / "docs" / "HANDOVER.md"

for _out in (sys.stdout, sys.stderr):
    try:
        _out.reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):
        pass

# Read each existing patcher's whitelist, including its shared stylesheet.
AREAS = [
    ("hub, shared web, QC and tools", "tools/save_code_patch.py"),
    ("Nong Studio web app", "nong/main_python_set_nong/save_patch.py"),
    ("firmware and the module page", "firmware/save_fw_patch.py"),
]


def patcher(source, script):
    return runpy.run_path(str(source / script))["SNAP"]


def _files(folder):
    return {p.relative_to(folder): p for p in folder.rglob("*") if p.is_file()}


def _same_snapshot(a, b):
    left, right = _files(a), _files(b)
    return left.keys() == right.keys() and all(
        filecmp.cmp(p, right[rel], shallow=False) for rel, p in left.items())


def _index_text(main, staged, folders):
    """Keep every existing index row, and recover omitted rows from patch.md."""
    lines = main.read_text(encoding="utf-8").splitlines() if main.is_file() else []
    if staged.is_file():
        extra = staged.read_text(encoding="utf-8").splitlines()
        if not lines:
            lines = extra
        else:
            lines += [line for line in extra if re.match(r"\| \d+ \|", line)
                      and line not in lines]
    if not lines:
        lines = ["# Patches", "", "| # | when | change |", "|---|---|---|"]
    for folder in folders:
        note = folder / "patch.md"
        if not note.is_file():
            continue
        fields = dict(re.findall(r"^- \*\*(when|change):\*\* (.*)$",
                                 note.read_text(encoding="utf-8"), re.M))
        if "when" in fields and "change" in fields:
            row = "| %04d | %s | %s |" % (int(folder.name.split("_")[0]),
                                         fields["when"], fields["change"])
            if row not in lines:
                lines.append(row)
    return "\n".join(lines) + "\n"


def sync_histories():
    """Merge only append-only histories; never copy working source either way.

    Preflight every area before copying. An independently reused number or
    edited old snapshot needs attention, and must never overwrite its peer.
    Mirroring complete histories also keeps the unchanged save_patch.py safe:
    its next number comes from directories, not from PATCHES.md.
    """
    staging = ROOT / ".staging"
    if not staging.is_dir():
        return
    jobs = []
    for _name, script in AREAS:
        snap = patcher(ROOT, script)
        main_dir = snap.patches
        stage_dir = staging / main_dir.relative_to(ROOT)
        main = {p.name: p for _n, p in snap.existing()}
        staged = {p.name: p for p in stage_dir.iterdir()
                  if p.is_dir() and p.name.split("_")[0].isdigit()} if stage_dir.is_dir() else {}
        for name in main.keys() & staged.keys():
            if not _same_snapshot(main[name], staged[name]):
                raise ValueError("snapshot differs between main and staging: " + str(main[name]))
        for name in staged.keys() - main.keys():
            number = int(name.split("_")[0])
            if any(int(old.split("_")[0]) == number for old in main):
                raise ValueError("snapshot number reused in staging: " + str(staged[name]))
        folders = {**main, **staged}
        stage_index = staging / snap.index.relative_to(ROOT)
        text = _index_text(snap.index, stage_index,
                           [folders[n] for n in sorted(folders)])
        jobs.append((snap.index, stage_index, main_dir, stage_dir, main, staged, text))
    for index, stage_index, main_dir, stage_dir, main, staged, text in jobs:
        for name in sorted(staged.keys() - main.keys()):
            shutil.copytree(staged[name], main_dir / name)
        for name in sorted(main.keys() - staged.keys()):
            shutil.copytree(main[name], stage_dir / name)
        for path in (index, stage_index):
            path.parent.mkdir(parents=True, exist_ok=True)
            temp = path.with_name(path.name + ".tmp")
            temp.write_text(text, encoding="utf-8", newline="")
            temp.replace(path)
    # promote does not skip this live note. Keep its staged copy current too.
    if NOTE.is_file():
        target = staging / NOTE.relative_to(ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(NOTE, target)


def staging_diff():
    """Source files that differ between .staging and the real tree.

    Runtime files (the plan, the prompt log, passwords, build output) are not
    source and are skipped - promote.py skips them for the same reason.
    """
    import filecmp
    import os
    staging = ROOT / ".staging"
    if not staging.is_dir():
        return ["(no .staging - nothing in progress)"]
    skip_dir = {".git", ".staging", "__pycache__", ".pio", "node_modules",
                "build", "dist", "reports", "patches", "patches_code"}
    skip_name = ("qc-receipt", "promt.md", "hub_auth", "hub_password",
                 "settings_shared", "PLAN.html", "settings.local")
    out = []
    for dirpath, dirs, files in os.walk(staging):
        dirs[:] = [d for d in dirs if d not in skip_dir]
        for f in files:
            p = Path(dirpath) / f
            rel = p.relative_to(staging)
            if any(s in rel.as_posix() for s in skip_name):
                continue
            m = ROOT / rel
            if not m.exists():
                out.append("new in staging: %s" % rel.as_posix())
            else:
                try:
                    if not filecmp.cmp(p, m, shallow=False):
                        out.append("changed in staging: %s" % rel.as_posix())
                except OSError:
                    pass
    return out or ["(staging matches the real tree - nothing unpromoted)"]


def plan_open():
    """The tasks the plan does not call done yet."""
    import json
    import re
    js = (ROOT / "docs" / "plan_state.js")
    if not js.is_file():
        return ["(no plan state)"]
    raw = json.loads(js.read_text(encoding="utf-8").split("=", 1)[1].rstrip(";\n"))["raw"]
    open_ = []
    for m in re.finditer(r"^([A-Z]\d+-\d+):\s+(todo|doing|qc)\s+(.*)$", raw, re.M):
        open_.append("%s [%s] %s" % (m.group(1), m.group(2), m.group(3)[:110]))
    return open_ or ["(nothing open)"]


def save(what):
    sync_histories()
    when = time.strftime("%Y-%m-%d %H:%M")
    lines = ["# Handover", "",
             "Written by `tools/handover.py`. Read this first if you are "
             "picking up work somebody else started.", "",
             "**When:** %s  " % when,
             "**Last step:** %s" % (what or "(not said)"), "",
             "**Source saved:** `%s`" % WORK, "",
             "## Snapshots taken", ""]
    for name, script in AREAS:
        snap = patcher(WORK, script)
        snap.patches = ROOT / snap.patches.relative_to(WORK)
        snap.index = ROOT / snap.index.relative_to(WORK)
        number = snap.save(what or ("handover %s" % when), quiet=True)
        folder = next(p for n, p in snap.existing() if n == number)
        lines.append("* **%s** - patch %04d: `%s`" % (name, number, folder))
    lines += ["",
              "Each area keeps its own numbered history and can be put back on "
              "its own: `--list` to see them, `--restore <n>` to go back. "
              "Nothing here reverts anything by itself.", "",
              "## What is in .staging but not promoted", ""]
    lines += ["* %s" % d for d in staging_diff()]
    lines += ["", "## What the plan still has open", ""]
    lines += ["* %s" % t for t in plan_open()]
    lines += ["", "## How to carry on", "",
              "```",
              "python qc/run_qc.py --quick                    ~90 s, is it green now",
              "python firmware/tools/gen_tables.py            after editing WebUI.h or mice.css",
              "python qc/run_qc.py                            full, real browser",
              "python E:/final_proj/mice/code/promote.py      gate + promote, absolute path",
              "python tools/plan.py show                      what the plan says",
              "python tools/handover.py save \"<next step>\"     checkpoint again",
              "```", "",
              "Work in `code/.staging`, never the real tree. Read `CLAUDE.md` "
              "first - it is the standing agreement, and every rule in it was "
              "paid for.", ""]
    NOTE.parent.mkdir(parents=True, exist_ok=True)
    NOTE.write_bytes("\n".join(lines).encode("utf-8"))
    sync_histories()
    print("handover saved -> %s" % NOTE)
    print("  %d file(s) differ in staging, %d task(s) open"
          % (len(staging_diff()), len(plan_open())))


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("action", choices=["save", "sync", "show", "undo"])
    ap.add_argument("what", nargs="*", help="what you just finished")
    a = ap.parse_args(argv)
    if a.action == "save":
        save(" ".join(a.what))
    elif a.action == "sync":
        sync_histories()
        print("snapshot histories reconciled; working source was not copied")
    elif a.action == "show":
        print(NOTE.read_text(encoding="utf-8") if NOTE.is_file()
              else "no handover note yet - run: python tools/handover.py save \"...\"")
    else:
        print("Every area has its own history. To see and to go back:\n")
        for name, script in AREAS:
            print("  %-32s python %s --list | --restore <n>"
                  % (name, ROOT / script))
        print("\nRestoring saves the current version first, so going back is "
              "itself reversible. `git checkout` is NOT the way: the real tree "
              "carries uncommitted work by design.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
