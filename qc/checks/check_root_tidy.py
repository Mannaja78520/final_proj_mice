"""The repo root holds only what config/layout.json lists (A51-1).

User 2026-10-27: "why does it keep adding things here, it will be hard to
read in the future". Twenty working copies (.staging-*) and seventeen one-off
scripts (check_tabs.py, do_fix.py, a 5-byte web.js) had piled up at the root,
each made by an AI that needed a scratch file once. Nothing stopped the next
one. Now a new root entry must be put in its folder, or added to the map with
a line saying what it is, and docs/LAYOUT.md (the map every AI reads instead
of listing folders) must match the map.

Git-ignored leftovers on one PC (build/, scratch/, old .staging-xxx) are
reported, never failed: they are not in git and the PC steps move them.
"""
import shutil
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "nothing new goes loose at the repo root, and the layout map is current"


def run(t):
    L = F.LAYOUT
    bad, local = L.root_report(F.CODE)
    t.ok(not bad, "every root entry is in config/layout.json",
         "move it into its folder (tools/, docs/, _out/...) or add one line to "
         "config/layout.json saying what it is: %s" % ", ".join(bad))
    if local:
        print("   local only (git-ignored, move with the PC steps): %s"
              % ", ".join(local[:12]))
    for name in sorted(L.allowed()):
        if name.startswith("."):
            continue
        t.ok(name in (L.data["root"]["files"]) or (F.CODE / name).exists()
             or name in (L.data["staging"]["home"], L.data["out"]["home"]),
             "the map names %s, and it is there" % name,
             "a map entry for a folder that is gone sends the next AI looking")
    t.ok(L.map_is_current(), "docs/LAYOUT.md matches config/layout.json",
         "run: python tools/layout.py build")
    handoff = (F.CODE / "HANDOFF.md").read_text(encoding="utf-8")
    t.ok("docs/LAYOUT.md" in handoff, "HANDOFF.md points every AI at the map", "")

    # Driven, not read: a stray file in a copy of a root is caught, a mapped
    # one and a working copy are not. Breaks if root_report stops looking.
    box = Path(tempfile.mkdtemp(prefix="qc_root_tidy_"))
    try:
        (box / "README.md").write_bytes(b"x")
        (box / ".staging-old").mkdir()
        (box / "do_fix.py").write_bytes(b"print(1)\n")
        bad, local = L.root_report(box)
        t.ok(bad == ["do_fix.py"], "a new loose script at the root is caught",
             "got %r" % bad)
        t.ok(".staging-old" in local, "an old working copy is only reported",
             "got %r" % local)
    finally:
        shutil.rmtree(box, ignore_errors=True)

    # Working copies live INSIDE .staging, and the real root is found from
    # one, however deep (the rule fifteen tools used to repeat).
    t.eq(L.real_root(L.real / ".staging" / "main" / "tools"), L.real,
         "the real root is found from .staging/<task>")
    t.eq(L.real_root(L.real / ".staging-ui" / "qc"), L.real,
         "and from an old .staging-xxx copy")
    fresh = L.rooted(Path(tempfile.gettempdir()) / "qc_no_such_root")
    t.eq(fresh.tree("ui"), fresh.staging_home / "ui",
         "a new working copy goes in .staging/<task>, not beside the root")
