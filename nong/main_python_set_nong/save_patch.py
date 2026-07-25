#!/usr/bin/env python3
"""Save the current web app as a numbered PATCH — a preserved snapshot.

Each patch is one change (whatever was asked for that one time). Patches never
overwrite each other: the old versions stay, so you can always look back at or
restore any earlier version of the web app.

    python save_patch.py "what this change did"      # save the current web/ as the next patch
    python save_patch.py --list                       # list every saved patch
    python save_patch.py --restore 3                  # copy patch 0003 back into web/ (backs up current first)

A patch stores the source files that actually change (app.js, index.html,
style.css) — not the vendored three.js libraries, which don't change. Snapshots
live in  patches/NNNN_<slug>/  and are indexed in  PATCHES.md.
"""
import sys
import shutil
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
WEB = ROOT / "web"
PATCHES = ROOT / "patches"
INDEX = ROOT / "PATCHES.md"
# the hand-written source of the web app (vendor/ is third-party, never changes)
SRC_FILES = ["app.js", "index.html", "style.css"]


def existing():
    """Sorted list of (number, path) for every saved patch."""
    if not PATCHES.is_dir():
        return []
    out = []
    for p in PATCHES.iterdir():
        if p.is_dir() and p.name[:4].isdigit():
            out.append((int(p.name[:4]), p))
    return sorted(out)


def slugify(text):
    keep = "".join(c if c.isalnum() or c in " -_" else " " for c in text.lower())
    return "-".join(keep.split())[:48] or "patch"


def save(desc):
    PATCHES.mkdir(exist_ok=True)
    patches = existing()
    n = (patches[-1][0] + 1) if patches else 1
    folder = PATCHES / ("%04d_%s" % (n, slugify(desc)))
    folder.mkdir()
    saved = []
    for name in SRC_FILES:
        src = WEB / name
        if src.exists():
            shutil.copy2(src, folder / name)
            saved.append(name)
    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    (folder / "patch.md").write_text(
        "# Patch %04d\n\n- **when:** %s\n- **change:** %s\n- **files:** %s\n\n"
        "Restore this exact version with:  `python save_patch.py --restore %d`\n"
        % (n, when, desc, ", ".join(saved), n), encoding="utf-8")
    # append to the index (append-only — earlier lines are never touched)
    if not INDEX.exists():
        INDEX.write_text(
            "# Web app patches\n\nEvery change to the Nong Studio web app is saved "
            "here as a numbered patch. Old patches are never removed — each row is "
            "a snapshot you can restore with `python save_patch.py --restore <n>`.\n\n"
            "| # | when | change |\n|---|---|---|\n", encoding="utf-8")
    with INDEX.open("a", encoding="utf-8") as f:
        f.write("| %04d | %s | %s |\n" % (n, when, desc.replace("|", "/")))
    print("saved patch %04d -> %s (%s)" % (n, folder.name, ", ".join(saved)))


def show_list():
    patches = existing()
    if not patches:
        print("no patches yet")
        return
    for n, p in patches:
        md = p / "patch.md"
        desc = ""
        if md.exists():
            for line in md.read_text(encoding="utf-8").splitlines():
                if line.startswith("- **change:**"):
                    desc = line.split(":**", 1)[1].strip()
        print("%04d  %s" % (n, desc))


def restore(n):
    match = [p for num, p in existing() if num == int(n)]
    if not match:
        print("no patch %s" % n)
        return
    folder = match[0]
    # back up whatever is in web/ now, so restoring never loses the current work
    save("auto-backup before restoring patch %s" % n)
    for name in SRC_FILES:
        src = folder / name
        if src.exists():
            shutil.copy2(src, WEB / name)
    print("restored patch %04d into web/ (current version was auto-saved first)" % int(n))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
    elif sys.argv[1] == "--list":
        show_list()
    elif sys.argv[1] == "--restore":
        restore(sys.argv[2])
    else:
        save(" ".join(sys.argv[1:]))
