"""Open work for any AI: one file per task in handoff/tasks/ (see HANDOFF.md).

    python tools/handoff.py list                 open tasks, owner, last update
    python tools/handoff.py new <name> "<title>" make handoff/tasks/<name>.md from the template
    python tools/handoff.py take <name> <agent>  write your agent id as Owner, stamp Updated
    python tools/handoff.py done <name>          delete the file (do it in the merging PR)

WHY one file per task (user 2026-10-21): one shared handoff got conflicting
edits when several agents worked at once, and a new AI spent its first turns
working out which of five places was current. Plain Markdown, no task names or
AI names in here: the fields come from handoff/TEMPLATE.md, so adding a field
there needs no change to this script.
"""
import datetime
import os
import pathlib
import re
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
TASKS = ROOT / "handoff" / "tasks"
TEMPLATE = ROOT / "handoff" / "TEMPLATE.md"
FIELD = re.compile(r"^([A-Z][A-Za-z ]*):[ \t]*(.*)$", re.M)


def fields(text):
    """Every 'Name: value' line before the first section heading."""
    return dict(FIELD.findall(text.split("\n## ", 1)[0]))


def now():
    return datetime.datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")


def set_field(text, name, value):
    # Edits only the header line, so the rest of the file stays as its owner wrote it.
    line = ("%s: %s" % (name, value)).rstrip()
    return re.sub(r"^%s:.*$" % re.escape(name), lambda m: line, text, count=1, flags=re.M)


def write(path, text):
    path.write_bytes(text.encode("utf-8"))   # LF on Windows too (CLAUDE.md)


def task_path(name):
    return TASKS / (name if name.endswith(".md") else name + ".md")


def cmd_list():
    files = sorted(TASKS.glob("*.md"))
    for f in files:
        text = f.read_text(encoding="utf-8")
        meta = fields(text)
        title = text.splitlines()[0].lstrip("# ").strip() if text else f.stem
        owner = meta.get("Owner", "").strip() or "free"
        print("%-24s %-22s %-24s %s" % (f.stem, owner, meta.get("Updated", "").strip(), title))
    if not files:
        print("no open task files in handoff/tasks/")
    # Branches carry their own task files until they merge; show them so nobody doubles up.
    out = subprocess.run(["git", "branch", "-r", "--no-merged", "origin/main"], cwd=ROOT,
                         capture_output=True, text=True)
    branches = [b.strip() for b in out.stdout.splitlines() if "->" not in b]
    if branches:
        print("\nunmerged branches (open PRs may own work too):")
        for b in branches:
            print("  " + b)


def cmd_new(name, title):
    path = task_path(name)
    if path.exists():
        sys.exit("%s already exists - take it or pick another name" % os.path.relpath(path, ROOT))
    text = TEMPLATE.read_text(encoding="utf-8")
    text = re.sub(r"^# .*$", "# " + title, text, count=1, flags=re.M)
    text = set_field(text, "Owner", "")
    text = set_field(text, "Updated", now())
    TASKS.mkdir(parents=True, exist_ok=True)
    write(path, text)
    print("made", os.path.relpath(path, ROOT))


def cmd_take(name, agent):
    path = task_path(name)
    text = path.read_text(encoding="utf-8")
    text = set_field(set_field(text, "Owner", agent), "Updated", now())
    write(path, text)
    print("%s owned by %s" % (os.path.relpath(path, ROOT), agent))


def cmd_done(name):
    path = task_path(name)
    path.unlink()
    print("removed", os.path.relpath(path, ROOT), "- commit it with the work that finished it")


def main(argv):
    usage = __doc__.split("\n\n", 2)[1]
    if not argv:
        sys.exit(usage)
    act, rest = argv[0], argv[1:]
    if act == "list" and not rest:
        cmd_list()
    elif act == "new" and len(rest) == 2:
        cmd_new(*rest)
    elif act == "take" and len(rest) == 2:
        cmd_take(*rest)
    elif act == "done" and len(rest) == 1:
        cmd_done(*rest)
    else:
        sys.exit(usage)


if __name__ == "__main__":
    main(sys.argv[1:])
