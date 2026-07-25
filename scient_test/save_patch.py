#!/usr/bin/env python3
"""Save the current test plan as a numbered PATCH — a preserved snapshot.

Same idea as code/nong/main_python_set_nong/save_patch.py, applied to the test
files instead of the web app: every change to a test is one snapshot, and old
snapshots are never overwritten. So when a measurement stops matching an older
result sheet, you can see exactly which version of the test produced it.

    python save_patch.py "what this change did"   # save tests/ + tools/ as the next patch
    python save_patch.py --list                    # list every saved patch
    python save_patch.py --restore 3               # roll the test files back to patch 0003
    python save_patch.py --show 3                  # print what patch 0003 changed

A patch stores the test DEFINITIONS (tests/*.md, tools/*.py, the results CSV
headers) — never the recorded data in results/, which is measurement, not
source. Snapshots live in patches/NNNN_<slug>/ and are indexed in PATCHES.md.
"""
import sys
import shutil
import datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PATCHES = ROOT / "patches"
INDEX = ROOT / "PATCHES.md"

# folders whose contents are the test definition (copied whole, by extension)
SRC_DIRS = {
    "tests": (".md",),
    "tools": (".py",),
}
# single files at the root that are part of the definition
SRC_FILES = ("README.md", "CLAUDE.md")


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


def collect():
    """[(relative path, absolute path)] of every file that belongs in a patch."""
    found = []
    for name in SRC_FILES:
        f = ROOT / name
        if f.is_file():
            found.append((Path(name), f))
    for folder, exts in SRC_DIRS.items():
        d = ROOT / folder
        if not d.is_dir():
            continue
        for f in sorted(d.iterdir()):
            if f.is_file() and f.suffix in exts:
                found.append((Path(folder) / f.name, f))
    return found


def save(desc):
    PATCHES.mkdir(exist_ok=True)
    patches = existing()
    n = (patches[-1][0] + 1) if patches else 1
    folder = PATCHES / ("%04d_%s" % (n, slugify(desc)))
    folder.mkdir()
    saved = []
    for rel, src in collect():
        dst = folder / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        saved.append(str(rel).replace("\\", "/"))
    when = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
    (folder / "patch.md").write_text(
        "# Patch %04d\n\n- **when:** %s\n- **change:** %s\n- **files:** %d\n\n"
        % (n, when, desc, len(saved))
        + "\n".join("  - `%s`" % s for s in saved)
        + "\n\nRestore this exact version with:  `python save_patch.py --restore %d`\n" % n,
        encoding="utf-8")
    if not INDEX.exists():
        INDEX.write_text(
            "# Test plan patches\n\nEvery change to the test files is saved here as a "
            "numbered patch, so a result sheet can always be matched back to the exact "
            "version of the test that produced it. Old patches are never removed — "
            "restore any of them with `python save_patch.py --restore <n>`.\n\n"
            "Recorded data in `results/` is never patched: that is measurement, not "
            "source.\n\n| # | when | change | files |\n|---|---|---|---|\n",
            encoding="utf-8")
    with INDEX.open("a", encoding="utf-8") as f:
        f.write("| %04d | %s | %s | %d |\n" % (n, when, desc.replace("|", "/"), len(saved)))
    print("saved patch %04d -> %s (%d files)" % (n, folder.name, len(saved)))


def show_list():
    patches = existing()
    if not patches:
        print("no patches yet — run:  python save_patch.py \"first version\"")
        return
    for n, p in patches:
        desc = ""
        md = p / "patch.md"
        if md.exists():
            for line in md.read_text(encoding="utf-8").splitlines():
                if line.startswith("- **change:**"):
                    desc = line.split(":**", 1)[1].strip()
        print("%04d  %s" % (n, desc))


def show(n):
    match = [p for num, p in existing() if num == int(n)]
    if not match:
        print("no patch %s" % n)
        return
    md = match[0] / "patch.md"
    print(md.read_text(encoding="utf-8") if md.exists() else "(no patch.md)")


def restore(n):
    match = [p for num, p in existing() if num == int(n)]
    if not match:
        print("no patch %s" % n)
        return
    folder = match[0]
    # back up whatever is here now, so restoring never loses the current work
    save("auto-backup before restoring patch %s" % n)
    count = 0
    for src in folder.rglob("*"):
        if not src.is_file() or src.name == "patch.md":
            continue
        rel = src.relative_to(folder)
        dst = ROOT / rel
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, dst)
        count += 1
    print("restored patch %04d (%d files; the current version was auto-saved first)"
          % (int(n), count))


if __name__ == "__main__":
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print(__doc__)
    elif sys.argv[1] == "--list":
        show_list()
    elif sys.argv[1] == "--show":
        show(sys.argv[2])
    elif sys.argv[1] == "--restore":
        restore(sys.argv[2])
    else:
        save(" ".join(sys.argv[1:]))
