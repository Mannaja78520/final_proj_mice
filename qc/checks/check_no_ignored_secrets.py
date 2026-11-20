"""No file the .gitignore hides may be tracked by git (the public-repo leak).

2026-11-04: `main_python/faces_login.json` was listed in .gitignore AND tracked,
so a Reconize admin password sat in the public repo. .gitignore does nothing to
a file git already tracks; the only honest test is asking git itself:
`git ls-files -ci --exclude-standard` (tracked + ignored).

Frozen copies under `*/patches/` are the patch snapshots (PATCHES.md) and are
tracked on purpose, and one `.bak` rig backup is a known leftover without a
secret in it. Anything else tracked-but-ignored is a leak or a trap.
"""
import subprocess

import qc as F

ALLOWED_PARTS = ("/patches/",)
ALLOWED_FILES = {"nong/main_python_set_nong/rig_default.json.bak"}


def run(t):
    if not (F.CODE / ".git").exists():
        t.ok(True, "not a git checkout: nothing to ask git (skipped)", "")
        return
    out = subprocess.run(["git", "ls-files", "-ci", "--exclude-standard"],
                         cwd=F.CODE, capture_output=True, text=True).stdout.splitlines()
    bad = [f for f in out
           if f not in ALLOWED_FILES and not any(p in "/" + f for p in ALLOWED_PARTS)]
    t.ok(not bad, "nothing the .gitignore hides is tracked by git "
         "(git rm --cached it; the password is then still in history)", bad[:10])
