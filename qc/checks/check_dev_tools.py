"""The repeated cycles are commands, and the risky one always cleans up.

Asked on 2026-08-20: *any system or file involving repetitive tasks, convert
them into executable scripts to minimize token usage as much as possible*. Two
cycles were being written out by hand every single time:

  * proving a check bites - copy the file, patch it, run the check, read the
    result, copy it back, run it again. Six commands, done more than a dozen
    times in one day, and each one written out fresh;
  * landing work - quick suite, full gate, find the verdict in three hundred
    lines, move the plan. Four commands plus a grep, and the grep has been
    mistyped, which reads as *the gate said nothing*.

The dangerous half is the first one, and it is the reason this check exists
rather than a note in a README: `sabotage.py` deliberately writes broken code
into the tree. If it ever fails to put the file back - because the check
crashed, or the run was interrupted - the tree is left sabotaged and the next
gate fails for a reason nobody can find. So the property held here is that the
file is restored on EVERY path, including the failing ones.
"""
import subprocess
import sys

import qc as F

AREA = "tools"
TITLE = "the sabotage and landing cycles are scripts, and always clean up"


def run(t):
    sab = F.CODE / "tools" / "sabotage.py"
    land = F.CODE / "tools" / "land.py"
    t.ok(sab.is_file(), "proving a check bites is one command", str(sab))
    t.ok(land.is_file(), "and so is landing work", str(land))

    src = sab.read_text(encoding="utf-8")
    t.contains(src, "finally:",
               "the file is put back even when the check crashes")
    t.ok("f.write_text(was" in src,
         "restoring writes the ORIGINAL text back",
         "restoring from anything but the text read before the patch is a "
         "guess, and a wrong guess silently edits the tree")

    # ---- a sabotage that does not apply is an ERROR ------------------
    # The subtle failure this prevents: if the text to break is not found, the
    # tool patches nothing, the check passes, and that reads as "the check is
    # weak" when the truth is "the sabotage missed".
    t.contains(src, "does not appear in",
               "a sabotage that changes nothing is refused, not counted")

    # ---- and it really restores, driven for real --------------------
    target = F.CODE / "tools" / "ai_panel.py"
    before = target.read_text(encoding="utf-8")
    spec = ('[{"file": "tools/ai_panel.py", '
            '"find": "PANEL = [", "replace": "PANEL = [] or [", '
            '"why": "qc self-test"}]')
    r = subprocess.run([sys.executable, str(sab), "--check", "check_panel",
                        "--spec", "-"],
                       input=spec, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=300,
                       cwd=str(F.CODE))
    out = (r.stdout or "") + (r.stderr or "")
    t.eq(target.read_text(encoding="utf-8"), before,
         "the file is byte-identical after a real sabotage run")
    t.contains(out, "caught",
               "and the sabotage it ran was caught by the check")

    # ---- landing only marks work done when it really landed ---------
    lsrc = land.read_text(encoding="utf-8")
    t.contains(lsrc, "--quick",
               "the quick suite runs before the five-minute gate")
    i = lsrc.find("if ok and landed:")
    t.ok(i > 0 and 'plan("done", tid)' in lsrc[i:i + 300],
         "tasks are marked done only when the gate was green AND it promoted",
         "marking work done because the command finished is how a plan starts "
         "lying about what is in the tree")
    t.contains(lsrc, "promoted",
               "and it checks that the promote really copied")
    # A promote that reused the receipt prints no verdict, because the suite did
    # not run - the tree had not changed since it last went green. Reading that
    # as a red gate marked finished work as still in flight, and the plan then
    # said the opposite of the truth.
    t.contains(lsrc, "ok is None",
               "a promote that reused the green receipt counts as a pass")
