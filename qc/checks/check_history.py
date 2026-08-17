"""Every web app keeps a history, and the diary is generated from it.

Nong Studio has been snapshotted since the first week; the hub was not. That
gap only showed when an old screenshot was wanted: Studio could be restored to
any past day and photographed, and the hub could not, because no earlier
version of `hub.html` existed anywhere. A history you did not keep cannot be
recovered later.

The diary is built from those snapshots rather than written by hand, so it
cannot quietly disagree with what actually landed.
"""
import re
import subprocess
import sys

import qc as F

AREA = "docs"
TITLE = "every web app is snapshotted, and the diary is built from those records"
SLOW = False

PATCHERS = [
    ("studio", "nong/main_python_set_nong/save_patch.py",
     "nong/main_python_set_nong/PATCHES.md"),
    ("hub", "main_python/save_hub_patch.py", "main_python/PATCHES.md"),
    ("firmware", "firmware/save_fw_patch.py", "firmware/PATCHES.md"),
]


def run(t):
    for name, script, index in PATCHERS:
        t.ok((F.CODE / script).is_file(),
             "%s has a way to snapshot its pages" % name,
             "changes there leave no 'old' version to compare against")
        t.ok((F.CODE / index).is_file(),
             "%s records what each snapshot changed" % name)

    # the hub patcher must actually cover the pages, not just exist
    src = (F.CODE / "main_python/save_hub_patch.py").read_text(
        encoding="utf-8", errors="replace")
    t.contains(src, "*.html", "the hub snapshot takes its pages")
    t.ok("main.py" not in src.split('"""')[-1],
         "and not the program itself — patchers snapshot pages, not code")

    # ---- the diary is generated, and matches the records ----------------
    gen = F.CODE / "tools/make_diary.py"
    t.ok(gen.is_file(), "there is a diary generator")

    r = subprocess.run([sys.executable, str(gen), "--print"], cwd=str(F.CODE),
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace")
    out = r.stdout
    t.ok(r.returncode == 0, "it runs", r.stderr[:200])
    t.contains(out, "# Mice", "and produces a diary")

    days = re.findall(r"^## (\d{4}-\d{2}-\d{2})$", out, re.M)
    t.ok(len(days) >= 2, "with a heading per day (%d)" % len(days))
    t.eq(days, sorted(days, reverse=True),
         "newest first, the way a diary reads")

    # every day that has a patch must appear — the point is that nothing
    # landed can be left out of the record
    recorded = set()
    for _, _, index in PATCHERS:
        p = F.CODE / index
        if p.is_file():
            recorded |= set(re.findall(r"\|\s*\d{3,4}\s*\|\s*(\d{4}-\d{2}-\d{2})",
                                       p.read_text(encoding="utf-8", errors="replace")))
    missing = sorted(recorded - set(days))
    t.ok(not missing,
         "and every day something landed is in it",
         "days with changes but no diary entry: %s" % missing)

    entries = re.findall(r"^- \*\*(\w+) (\d{3,4})\*\*", out, re.M)
    t.ok(len(entries) >= len(recorded),
         "each change is listed, not just the day (%d entries)" % len(entries))
    t.ok(any(w == "hub" for w, _ in entries),
         "including the hub, now that it has a history too")
