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

AND THEY MUST SURVIVE A THAI WORD. Measured 2026-08-22: Windows hands python a
cp1252 console on this machine, and cp1252 cannot encode Thai at all - so
`print()` of one Thai word raised UnicodeEncodeError and the tool died AFTER it
had already written the file. The plan would have been changed with the command
reporting a traceback, which reads as *it did not work* and leads to running it
twice. The tools that people type into are the ones most likely to be given
Thai: a note, a report, a reason for a sabotage. Every entry point sets its
output to UTF-8 and never crashes on a character, and their own words are ASCII
so no console can mangle them.
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

    # ---- a SECOND working copy is skipped, not swallowed ---------------
    # promote.py has always taken `--staging DIR`, so two trees for two
    # different jobs is a supported thing to do. But SKIP_DIRS matched the
    # exact name `.staging`, so `.staging-integral` was ordinary source:
    # `--init` copied one whole tree inside the other, and each promote
    # carried the other tree's files. Found by reading, 2026-09-09, before
    # the second tree existed. The prefix match is what stops it.
    import importlib.util
    from pathlib import Path
    spec = importlib.util.spec_from_file_location(
        "_promote_under_test", F.CODE / "promote.py")
    promote = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(promote)

    for tree in (".staging", ".staging-integral", ".staging-ui"):
        t.ok(promote.skip(Path(tree) / "main_python" / "main.py"),
             "%s is a working copy, never source" % tree,
             "an unskipped second tree is copied into the first by --init, "
             "and both promote each other's files")
    t.ok(promote.skip(Path(".claude") / "settings.local.json"),
         "this machine's Claude settings never travel",
         "staging's copy is stale the moment it is made; promoting it put an "
         "old permissions file over the live one")
    t.ok(not promote.skip(Path("main_python") / "main.py"),
         "and ordinary source is still promoted",
         "a skip rule that is too wide silently stops promoting real work")

    ignored = (F.CODE / ".gitignore").read_text(encoding="utf-8")
    t.contains(ignored, ".staging*/",
               "git ignores every working copy, not only the first")

    # And the TOOLS have to know it too. Five of them climbed out of the
    # working copy by the exact name `.staging` - plan.py, handover.py,
    # ai_panel.py, make_app_branch.py, next_batch.py - so inside
    # `.staging-integral` each one looked for the repo root in the wrong place.
    # plan.py then wrote to a docs/PLAN.html that does not exist there, and
    # three checks died on FileNotFoundError. Found 2026-09-10, the same defect
    # as SKIP_DIRS above, fixed there first and left in every sibling.
    for tool in sorted((F.CODE / "tools").glob("*.py")):
        src = tool.read_text(encoding="utf-8", errors="replace")
        if ".staging" not in src:
            continue
        t.ok('name == ".staging"' not in src,
             "tools/%s knows a working copy by prefix, not by one name"
             % tool.name,
             "a second tree for a second job is normal here, and an exact "
             "name match sends this tool at the wrong repo root")

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

    # ---- a Thai word must not kill a tool ----------------------------
    TOOLS = ("tools/plan.py", "tools/land.py", "tools/sabotage.py",
             "promote.py", "qc/run_qc.py")
    for rel in TOOLS:
        src_t = (F.CODE / rel).read_text(encoding="utf-8")
        t.contains(src_t, 'reconfigure(encoding="utf-8", errors="replace")',
                   "%s prints UTF-8, whatever the console codepage is" % rel)

    # Driven for real, on a COPY of the plan: the tool is given a Thai word and
    # must finish, print it back, and leave it in the file. Asserting on the
    # source alone would pass a tool that reconfigured stdout and still threw.
    import os
    import shutil
    import tempfile
    from pathlib import Path
    plan_src = F.CODE.parent / "docs" / "PLAN.html"
    if not plan_src.is_file():
        plan_src = F.CODE / "docs" / "PLAN.html"
    work = Path(tempfile.mkdtemp(prefix="qc_thai_")) / "PLAN.html"
    shutil.copy(plan_src, work)
    thai = "ทดสอบภาษาไทย"
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "plan.py"),
                        "running", thai],
                       capture_output=True, text=True, encoding="utf-8",
                       errors="replace",
                       env=dict(os.environ, MICE_PLAN=str(work)))
    t.eq(r.returncode, 0, "the plan tool survives a Thai word")
    t.contains(work.read_text(encoding="utf-8"), thai,
               "and the Thai reaches the plan intact")
    t.ok("UnicodeEncodeError" not in (r.stdout + r.stderr),
         "with nothing printed about encodings",
         "the tool wrote the file and then died printing it, which reads as a "
         "failed command and gets run twice: %s" % (r.stderr or "")[:120])

    # ---- and the tools' OWN words stay ASCII -------------------------
    # The em dash and middle dot they used to print came back as replacement
    # characters in the user's terminal on 2026-08-22 - unreadable output from
    # the tool that reports what the plan says.
    said = subprocess.run([sys.executable, str(F.CODE / "tools" / "plan.py"), "show"],
                          capture_output=True, text=True, encoding="utf-8",
                          errors="replace",
                          env=dict(os.environ, MICE_PLAN=str(work)))
    # The FIRST line only: it is the tool's own words. The lines under it echo
    # whatever the user typed, which is Thai a moment ago and must stay Thai -
    # asserting ASCII on those would demand the opposite of the fix above.
    counts_line = (said.stdout.splitlines() or [""])[0]
    t.ok(counts_line.isascii(),
         "what the tool says about itself is plain ASCII",
         "a console that cannot draw it shows garbage instead of the plan: %r"
         % counts_line[:80])
    shutil.rmtree(work.parent, ignore_errors=True)

    # ---- landing driven END TO END, in a sandbox ---------------------
    # A22-2: on 2026-08-23 land reported REFUSED while promote had actually
    # promoted - the deciding word sat at the end of hundreds of lines that a
    # truncated read never reached, and nothing about the LAST line said what
    # really happened. So: the last line of land's output always decides, and
    # work already sitting in the real tree is reported as landed rather than
    # refused, so --done can still mark it.
    box = Path(tempfile.mkdtemp(prefix="qc_land_"))
    try:
        (box / "tools").mkdir()
        (box / "qc").mkdir()
        (box / ".staging" / "qc").mkdir(parents=True)
        shutil.copy(F.CODE / "promote.py", box / "promote.py")
        for tool in ("land.py", "plan.py"):
            shutil.copy(F.CODE / "tools" / tool, box / "tools" / tool)
        stub = ('import sys\nif __name__ == "__main__":\n'
                '    print("QC PASS  5 passed, 0 failed in 0.1s")\n'
                '    sys.exit(0)\n')
        for d in ("qc", ".staging/qc"):
            (box / d / "run_qc.py").write_bytes(stub.encode("utf-8"))
        (box / ".staging" / "f.txt").write_bytes(b"staged\n")
        (box / "f.txt").write_bytes(b"old\n")
        state = ('<!doctype html><html><body><pre id="state"><code>STATE\n'
                 'SBX-1: doing\nSBX-2: doing\nEND</code></pre></body></html>')
        (box / "PLAN.html").write_bytes(state.encode("utf-8"))
        env = dict(os.environ, MICE_PLAN=str(box / "PLAN.html"))

        def land(*args):
            r = subprocess.run([sys.executable, str(box / "tools" / "land.py")]
                               + list(args),
                               capture_output=True, text=True, encoding="utf-8",
                               errors="replace", env=env, timeout=300,
                               cwd=str(box))
            out = (r.stdout or "") + (r.stderr or "")
            last = [l for l in out.splitlines() if l.strip()][-1:]
            return r.returncode, out, (last[0] if last else "")

        code, out, last = land("--skip-quick", "--done", "SBX-1")
        t.eq(code, 0, "a green gate through land exits 0")
        t.eq((box / "f.txt").read_text(encoding="utf-8"), "staged\n",
             "and the staged file really reached the real tree")
        t.ok(last.startswith("LAND RESULT:") and "LANDED" in last,
             "the LAST line names the outcome, whatever else scrolled past",
             "a truncated read saw no verdict and called a landed promote "
             "REFUSED - the decision must survive reading only the tail: %r"
             % last[:120])
        t.contains((box / "PLAN.html").read_text(encoding="utf-8"),
                   "SBX-1: done",
                   "and --done marked the task once the copy was proven")
        t.ok("not re-run" not in out,
             "a gate that RAN is not described as a reused receipt",
             "promote ran the stub suite here; calling that a receipt reuse "
             "hides whether the suite really ran")

        # Already synced: staging matches the real tree and the receipt is
        # gone, so there is nothing to copy. That is landed work, not a
        # refusal - refusing left A20-1 stuck at doing forever.
        code, out, last = land("--skip-quick", "--done", "SBX-2")
        t.eq(code, 0, "relanding a tree already in main succeeds")
        t.ok(last.startswith("LAND RESULT:") and "LANDED" in last,
             "and says so on the last line, not REFUSED")
        t.contains((box / "PLAN.html").read_text(encoding="utf-8"),
                   "SBX-2: done",
                   "so --done still marks it - the task IS in the tree")
    finally:
        shutil.rmtree(box, ignore_errors=True)

    # ---- the handover: a checkpoint somebody else can resume from -------
    # Asked for 2026-09-08 when the interface work went to another agent:
    # *make it have backup when it hit limit you can access and do it follow
    # the codex as fallback*. An agent that stops mid-task leaves two questions
    # - what did it already change, and where do I pick up - and neither is
    # answerable from the code alone.
    ho = (F.CODE / "tools" / "handover.py")
    t.ok(ho.is_file(), "there is one command that checkpoints every area")
    src = ho.read_text(encoding="utf-8", errors="replace")
    for area in ("save_code_patch.py", "save_patch.py", "save_fw_patch.py"):
        t.contains(src, area, "it snapshots through the existing patcher %s" % area)
    t.contains(src, "staging_diff",
               "the note says what is unpromoted, so nothing is lost in staging")
    t.contains(src, "plan_open",
               "and what the plan still has open, so the next agent knows where to start")

    # A source assertion previously required rebasing the whole checkpoint to
    # main. That saved old UI bytes while claiming the staging work was safe.
    # Drive both entry points, a stale history, and the unchanged Studio saver.
    box = Path(tempfile.mkdtemp(prefix="qc_handover_"))
    try:
        scripts = ("tools/handover.py", "tools/snapshot.py",
                   "tools/save_code_patch.py",
                   "nong/main_python_set_nong/save_patch.py",
                   "firmware/save_fw_patch.py")
        for rel in scripts:
            dest = box / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(F.CODE / rel, dest)
        sources = {"main_python/web/hub.html": "old hub",
                   "shared/web/mice.css": "old style",
                   "nong/main_python_set_nong/web/index.html": "old studio",
                   "firmware/src/web/WebUI.h": "old module"}
        for rel, text in sources.items():
            dest = box / rel
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_text(text, encoding="utf-8")
        (box / "docs").mkdir()
        (box / "docs/plan_state.js").write_text(
            'window.STATE={"raw":"A25-1: doing interface"};\n', encoding="utf-8")
        secret = "CHECKPOINT-SECRET-7Q"
        (box / "main_python/hub_password.txt").write_text(secret, encoding="utf-8")

        def invoke(tree, script, *args):
            return subprocess.run([sys.executable, str(tree / script), *args],
                                  cwd=str(tree), capture_output=True, text=True,
                                  encoding="utf-8", errors="replace", timeout=120)

        r = invoke(box, "tools/handover.py", "save", "main first")
        t.ok(r.returncode == 0, "main checkpoint succeeds in a bare tree", r.stderr[-300:])
        stage = box / ".staging"
        # Copy siblings, never recurse into the destination being created.
        stage.mkdir()
        for child in list(box.iterdir()):
            if child == stage:
                continue
            if child.is_dir():
                shutil.copytree(child, stage / child.name)
            else:
                shutil.copy2(child, stage / child.name)

        histories = ("patches_code", "nong/main_python_set_nong/patches", "firmware/patches")
        for script in (scripts[2], scripts[3], scripts[4]):
            r = invoke(box, script, "main newer")
            t.eq(r.returncode, 0, "a direct patcher can advance main history")
        for rel in sources:
            (stage / rel).write_text("draft " + rel, encoding="utf-8")
        r = invoke(stage, "tools/handover.py", "sync")
        t.ok(r.returncode == 0, "sync reconciles newer main history", r.stderr[-300:])
        r = invoke(stage, scripts[3], "standalone Studio draft")
        t.eq(r.returncode, 0, "Studio save_patch.py remains usable after sync")
        r = invoke(stage, "tools/handover.py", "save", "draft " + thai)
        t.ok(r.returncode == 0, "staging checkpoint saves the actual draft", r.stderr[-300:])

        locations = ((histories[0], "main_python/web/hub.html"),
                     (histories[1], "index.html"),
                     (histories[2], "src/web/WebUI.h"))
        draft_files = ("main_python/web/hub.html",
                       "nong/main_python_set_nong/web/index.html",
                       "firmware/src/web/WebUI.h")
        for (history, saved), source in zip(locations, draft_files):
            folders = sorted((box / history).iterdir())
            t.eq((folders[-1] / saved).read_text(encoding="utf-8"), "draft " + source,
                 "%s latest snapshot contains STAGING bytes" % history)
            shared = "shared/web/mice.css" if history == "patches_code" else "shared/mice.css"
            t.eq((folders[-1] / shared).read_text(encoding="utf-8"), "draft shared/web/mice.css",
                 "%s also preserves the draft shared stylesheet" % history)
            index = (box / history).parent / "PATCHES.md"
            staged_index = stage / index.relative_to(box)
            t.eq(index.read_bytes(), staged_index.read_bytes(),
                 "%s index is safe to promote after checkpoint" % history)
            t.contains(index.read_text(encoding="utf-8"), "main newer",
                       "%s keeps rows written after staging was made" % history)
            numbers = [int(f.name.split("_")[0]) for f in folders]
            t.eq(len(numbers), len(set(numbers)), "%s allocates no duplicate numbers" % history)
            t.ok(all(secret not in p.read_text(encoding="utf-8", errors="replace")
                     for f in folders for p in f.rglob("*") if p.is_file()),
                 "%s still excludes secrets" % history)
        studio_index = box / "nong/main_python_set_nong/PATCHES.md"
        t.contains(studio_index.read_text(encoding="utf-8"), "standalone Studio draft",
                   "the independent staging Studio snapshot is preserved")
        for rel, text in sources.items():
            t.eq((box / rel).read_text(encoding="utf-8"), text,
                 "checkpoint never promotes source: %s" % rel)
            t.eq((stage / rel).read_text(encoding="utf-8"), "draft " + rel,
                 "sync never refreshes working source: %s" % rel)
        note = (box / "docs/HANDOVER.md").read_text(encoding="utf-8")
        t.contains(note, str(stage), "the live note names the saved source tree")
        t.contains(note, str(box / "patches_code"), "the note names real snapshot locations")
        t.contains(note, "A25-1", "the staging checkpoint still reads the live plan")
        t.eq((box / "docs/HANDOVER.md").read_bytes(), (stage / "docs/HANDOVER.md").read_bytes(),
             "promotion cannot replace the new handover note with a stale copy")

        r = invoke(box, "tools/handover.py", "save", "main after")
        t.ok(r.returncode == 0, "main entry point still saves main", r.stderr[-300:])
        last = sorted((box / "patches_code").iterdir())[-1]
        t.eq((last / "main_python/web/hub.html").read_text(encoding="utf-8"), "old hub",
             "main checkpoint contains main source, even while staging differs")

        # Refuse an edited old snapshot before overwriting any history bytes.
        first = sorted((box / "patches_code").iterdir())[0]
        original = (first / "main_python/web/hub.html").read_bytes()
        (stage / first.relative_to(box) / "main_python/web/hub.html").write_bytes(b"collision")
        r = invoke(stage, "tools/handover.py", "sync")
        t.ok(r.returncode != 0, "sync refuses conflicting old snapshot bytes")
        t.eq((first / "main_python/web/hub.html").read_bytes(), original,
             "a history conflict leaves the authoritative snapshot unchanged")
        (stage / first.relative_to(box) / "main_python/web/hub.html").write_bytes(original)
        duplicate = stage / "patches_code" / (first.name.split("_")[0] + "_independent")
        shutil.copytree(first, duplicate)
        r = invoke(stage, "tools/handover.py", "sync")
        t.ok(r.returncode != 0, "sync refuses an independently reused snapshot number")
        t.ok(not (box / "patches_code" / duplicate.name).exists(),
             "a reused number never enters authoritative history")
    finally:
        shutil.rmtree(box, ignore_errors=True)
