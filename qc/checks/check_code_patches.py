"""Every part of the project can be rolled back by number, not only Nong Studio.

Asked 2026-08-24: *save other thing too not only nong studio*. Studio has had
numbered patches since week one; the hub pages and the firmware got their own
patchers later; but main.py, mice.css, the QC suite and promote.py itself had
no history at all. tools/save_code_patch.py closes that gap on ONE engine
(tools/snapshot.py) shared with the other three patchers.

What would make this worthless, and what each assertion is for:

  * a patch that captures a SECRET. The whitelist globs are the whole defence:
    only source globs are ever walked, so hub_password.txt or a cookie file
    cannot get in by appearing somewhere new. The test plants both beside real
    source in a sandbox and fails if the VALUE survives anywhere under the
    patches directory - by value, never by filename;
  * a patcher that exists but does not round-trip. Naming files is not
    restoring them: the sandbox saves, mutates a file, restores, and demands
    the old bytes back while files added after the save stay untouched -
    restore never deletes (that is what makes it safe to run carelessly);
  * a description that breaks the table. One newline in a change description
    split the markdown row in two when this was written; the row must survive
    one piece in BOTH patch.md and PATCHES.md;
  * land.py forgetting to snapshot. The whole point of A24-1 was that every
    LANDED change gets a number without anyone remembering to ask, so the
    landed paths must call it - not just the manual command.
"""
import os
import re
import shutil
import subprocess
import sys
import tempfile

import qc as F

AREA = "tools"
TITLE = "every area of the project keeps numbered patches, restorable by number"


def run(t):
    code = F.CODE / ".staging"
    if not code.is_dir():
        code = F.CODE                      # checking the promoted tree works too
    saver = code / "tools" / "save_code_patch.py"
    t.ok(saver.is_file(), "there is one patcher for the project's code")
    src = saver.read_text(encoding="utf-8", errors="replace")

    # ---- it covers what the other three patchers do not -----------------
    for want in ("main_python/*.py", "shared/web/*", "qc/*.py",
                 "tools/*.py", "promote.py"):
        t.contains(src, want, "it snapshots %s" % want)
    engine = (code / "tools" / "snapshot.py").read_text(encoding="utf-8",
                                                        errors="replace")
    # "%04d" grows past four digits at patch 10000; name[:4] aliased that onto
    # patch 1000. Leading digits before the underscore keep numbering honest.
    t.ok('p.name.split("_")[0]' in engine and 'head.isdigit()' in engine,
         "patch numbers are read as leading digits, not a fixed slice")

    # ---- land.py takes the number automatically, BEFORE promote ---------
    # Before, not after: promote carries the whole tree including the fresh
    # patch into the real tree. Taken after, the newest patch stayed stranded
    # in staging (patch 0003, A21-7) - the one landing someone might need to
    # undo was the one main had no rollback point for.
    land = (code / "tools" / "land.py").read_text(encoding="utf-8",
                                                  errors="replace")
    calls = [m.start() for m in re.finditer(r"^\s+snap\(", land, re.M)]
    gate_at = land.find('plan("running", "full gate')
    t.ok(len(calls) == 1 and gate_at > 0 and calls[0] < gate_at,
         "the snapshot is taken once, before anything is copied",
         "A24-1: every LANDED change gets a number without anyone remembering "
         "to ask - and it must ride INTO the real tree with the promote "
         "(found %d call(s), first at %d, gate at %d)"
         % (len(calls), calls[0] if calls else -1, gate_at))

    # ---- end-to-end in a sandbox, secrets planted -----------------------
    box = tempfile.mkdtemp(prefix="mice_code_patch_")
    try:
        for d in ("main_python", "shared/web", "qc/checks", "tools", "docs"):
            os.makedirs(os.path.join(box, d), exist_ok=True)
        def put(rel, text):
            with open(os.path.join(box, rel), "w", encoding="utf-8",
                      newline="") as f:
                f.write(text)
        put("main_python/main.py", "HUB = 1\n")
        put("shared/web/mice.css", ":root { --x: 1; }\n")
        put("qc/checks/check_x.py", "ok = True\n")
        put("tools/save_code_patch.py", src)      # the real patcher
        shutil.copy2(code / "tools" / "snapshot.py",
                     os.path.join(box, "tools", "snapshot.py"))
        put("promote.py", "print('gate')\n")
        # the traps: a secret, a cookie, a runtime file. None may ever be saved.
        put("main_python/hub_password.txt", "S3CRET-VALUE-9Q\n")
        put("cookies.txt", "session=S3CRET-VALUE-9Q\n")
        put("docs/PLAN.html", "<html>PLAN</html>\n")

        def cli(*args):
            return subprocess.run(
                [sys.executable, os.path.join(box, "tools", "save_code_patch.py")]
                + list(args), capture_output=True, text=True, encoding="utf-8",
                errors="replace", cwd=box, timeout=120)

        r = cli("first snapshot")
        t.ok(r.returncode == 0, "the patcher saves from a bare tree",
             (r.stderr or r.stdout)[-200:])
        n = re.search(r"saved patch (\d+)", r.stdout)
        if t.ok(n, "and says its own number"):
            num = n.group(1)

            leaks = []
            for root, _dirs, files in os.walk(os.path.join(box, "patches_code")):
                for fn in files:
                    try:
                        with open(os.path.join(root, fn), encoding="utf-8",
                                  errors="replace") as f:
                            if "S3CRET-VALUE-9Q" in f.read():
                                leaks.append(fn)
                    except OSError:
                        pass
            t.ok(not leaks,
                 "NO secret value survives anywhere under patches/",
                 "found the planted password inside: %r" % leaks[:3])
            idx = open(os.path.join(box, "PATCHES.md"), encoding="utf-8").read()
            t.ok("PLAN.html" not in idx and "cookie" not in idx,
                 "runtime files and cookies are not in the record either")

            # round-trip: mutate, restore, demand the old bytes back
            put("shared/web/mice.css", ":root { --x: 999; }\n")
            put("main_python/added_later.py", "NEW = 1\n")   # post-save file
            r = cli("--restore", num)
            t.ok(r.returncode == 0, "restore runs", (r.stderr or "")[-200:])
            back = open(os.path.join(box, "shared", "web", "mice.css"),
                        encoding="utf-8").read()
            t.ok("--x: 1" in back,
                 "restore puts the SAVED bytes back after an edit")
            t.ok(os.path.isfile(os.path.join(box, "main_python",
                                             "added_later.py")),
                 "and never deletes anything - restore is safe to run casually")

            # one description, one markdown row, in both files
            r = cli("two\nlines | test")
            last = sorted(os.listdir(
                os.path.join(box, "patches_code")))[-1]
            md = open(os.path.join(box, "patches_code", last, "patch.md"),
                      encoding="utf-8").read()
            # counting change-lines misses the damage: an unsanitised newline
            # leaves ONE change-line plus an ORPHAN line after it. The next
            # field must follow immediately.
            ci = md.find("- **change:**")
            nxt = md[md.find("\n", ci) + 1:]
            t.ok(ci > 0 and nxt.startswith("- **files:**"),
                 "a newline in a description stays ONE row",
                 "an orphan line followed the change field: %r" % nxt[:40])
            idx = open(os.path.join(box, "PATCHES.md"), encoding="utf-8").read()
            li = idx.find("| " + "".join(ch for ch in last if ch.isdigit())[:4])
            inxt = idx[idx.find("\n", li) + 1:]
            t.ok(li > 0 and (inxt.startswith("| 0") or not inxt.strip()),
                 "and the PATCHES.md table row stays whole",
                 "an orphan line followed the table row: %r" % inxt[:40])
    finally:
        shutil.rmtree(box, ignore_errors=True)
