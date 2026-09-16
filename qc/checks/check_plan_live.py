"""The plan is written in ONE place, and the page updates itself while open.

Both were asked for directly on 2026-08-19, and both are the kind of thing that
works today and quietly stops working later, so they are held here.

ONE PLACE. `docs/PLAN.html` in the real tree is the only record of progress.
A copy inside `.staging` is worse than no copy: it is a day old, it says work
is still to do that has already landed, and nothing writes to it. `plan.py`
therefore climbs out of `.staging` on its own rather than relying on anyone
remembering which shell they are in - and this asserts that, because the tool
is run from both trees all day.

UPDATES WHILE OPEN. The page is opened as `file:///E:/...`, and that decides
the mechanism: a file:// page may NOT fetch or XHR a file next to it - the
browser gives it a null origin and refuses - but it MAY load a script. So
plan.py publishes `docs/plan_state.js` and the page pulls it in on a timer.
The obvious "tidy-up" later is to replace that with fetch(), which works
perfectly over http:// while silently doing nothing for the person actually
reading the file. That is what the last assertion here is for.
"""
import json
import subprocess
import sys
from pathlib import Path

import qc as F

AREA = "docs"
TITLE = "the plan lives in one place, and updates while it is open"


def _plan_module():
    sys.path.insert(0, str(F.CODE / "tools"))
    import plan  # noqa: PLC0415 - the module under test
    return plan


def run(t):
    plan = _plan_module()
    path = plan.plan_path()

    # ---- one place -------------------------------------------------
    t.ok(".staging" not in str(path),
         "plan.py writes to the real tree, not to .staging",
         "it resolved to %s - a plan inside .staging is a day old the moment "
         "it is written, and nothing ever reads it back" % path)
    t.ok(path.is_file(), "and that file is there", str(path))
    t.contains(str(path).replace("\\", "/"), "docs/PLAN.html",
               "at the path everything else names")

    # Run the tool the way it is really run, from THIS tree, and prove where
    # the change landed. Asserting on the function alone would not catch a
    # wrapper, a shell alias, or a second copy of the tool.
    # Driven against a COPY, not the real plan. A check that wrote to the real
    # one would stamp its own name over whatever the session is running, in the
    # page someone is watching to see whether work is happening.
    import os as _os
    import shutil as _sh
    import tempfile as _tf
    work = Path(_tf.mkdtemp(prefix="qc_plan_")) / "PLAN.html"
    _sh.copy(path, work)
    # A different mark every run: writing the SAME text twice changes nothing,
    # and "nothing changed" would then look like a broken tool.
    mark = "QC checked the plan tool (%d)" % _os.getpid()
    env = dict(_os.environ, MICE_PLAN=str(work))
    before = work.read_text(encoding="utf-8")
    r = subprocess.run([sys.executable, str(F.CODE / "tools" / "plan.py"),
                        "running", mark],
                       capture_output=True, text=True, env=env)
    t.eq(r.returncode, 0, "the tool runs from a staging tree without complaint")
    after = work.read_text(encoding="utf-8")
    t.ok(after != before, "and the real plan is what changed",
         "ran from %s" % F.CODE)
    t.contains(after, mark,
               "with the text that was asked for")

    # ---- a task id may carry a suffix letter ------------------------
    # A9-3b is the half of A9-3 that needs no hardware. Both the tool and the
    # page used to stop at the digit, so that task could be set to `doing`
    # without complaint and then be missing from every count and from the
    # page itself - work in progress that the page said did not exist.
    # Driven on a STATE block written here, so it does not depend on which
    # tasks happen to exist today.
    tiny = work.parent / "tiny.html"
    tiny.write_bytes(('<pre id="state"><code>STATE\n'
                      '# RUNNING: nothing right now\n'
                      'A9-3b: doing    2026-08-21 21:52  — the PC-only half\n'
                      'A9-3: blocked  2026-08-20 23:56  — the hardware half\n'
                      '</code></pre>').encode("utf-8"))
    counts, _run, live = plan.Plan(tiny).summary()
    t.eq(counts["doing"], 1, "a task id with a suffix letter is counted")
    t.eq(live, ["A9-3b"], "and named as one of the things in flight")

    # ---- published beside it, for the page to read -----------------
    state = work.parent / "plan_state.js"
    t.ok(state.is_file(), "the state is published beside the page",
         "the page cannot update itself without it")
    js = state.read_text(encoding="utf-8")
    t.contains(js, "window.PLAN_STATE=", "as a script the page can load")
    data = json.loads(js.split("=", 1)[1].rsplit(";", 1)[0].strip())
    t.ok(data.get("stamp"), "stamped, so the page can tell it moved")
    t.contains(data.get("raw", ""), mark,
               "and carrying the change that was just made")
    t.contains(data.get("raw", ""), "STATE",
               "it is the whole STATE block, not a summary of it")

    # The published copy and the page must agree, or the page would flip
    # between two versions of the truth every four seconds.
    pre = after[after.index("<pre id=\"state\">"):]
    pre = pre[pre.index(">", pre.index("<code")) + 1:pre.index("</code>")]
    for ent, ch in (("&amp;", "&"), ("&lt;", "<"), ("&gt;", ">"),
                    ("&quot;", '"'), ("&#39;", "'")):
        pre = pre.replace(ent, ch)
    t.eq(data.get("raw", "").strip(), pre.strip(),
         "the published state and the page say the same thing")

    # ---- and the REAL page reads it the only way it can -------------
    page = path.read_text(encoding="utf-8")
    t.contains(page, "plan_state.js",
               "the page loads the published state")
    t.contains(page, r"[A-Z]\d+-\d+[a-z]?",
               "and its renderer reads suffixed ids, like the tool does")
    loader = page[page.find("LIVE, without a refresh"):]
    loader = loader[:4000]
    t.contains(loader, "createElement('script')",
               "with a script tag, which is what a file:// page is allowed")
    # Comments strippped first: the loader EXPLAINS why it cannot use fetch,
    # and the first version of this assertion failed on its own explanation.
    import re as _re
    code = _re.sub("//[^" + chr(10) + "]*", "", loader)
    t.ok("fetch(" not in code and "XMLHttpRequest" not in code,
         "and NOT with fetch, which a file:// page is refused",
         "fetch works perfectly over http:// and does nothing at all for the "
         "person reading this from a file, which is how it is read")
    t.ok("location.reload" not in page,
         "the page no longer reloads itself",
         "a reload loses the scroll position and any text being read")
    t.contains(loader, "renderPlan()",
               "it redraws in place when the state moves")

    # ---- written whole, even while something else is reading it -----
    # Since 2026-08-20 the QC runner reports progress into this file WHILE it
    # runs, so a reader can arrive mid-write. It really happened: check_plan_live
    # crashed in a gate on a page that was half there, which reads as a broken
    # check rather than a torn read. Driven rather than asserted from the source,
    # because "it calls os.replace" is not the property - "nobody ever sees half
    # a file" is.
    import threading  # noqa: PLC0415
    stop, torn = [False], []

    def reader():
        while not stop[0]:
            try:
                txt = work.read_text(encoding="utf-8")
            except OSError:
                continue                     # mid-rename on Windows: not torn
            if txt and "</html>" not in txt:
                torn.append(len(txt))

    th = threading.Thread(target=reader, daemon=True)
    th.start()
    try:
        for n in range(6):
            subprocess.run([sys.executable, str(F.CODE / "tools" / "plan.py"),
                            "running", "torn-read self-test %d" % n],
                           capture_output=True, env=env, timeout=60)
    finally:
        stop[0] = True
        th.join(timeout=3)
    t.eq(torn, [],
         "the plan is never seen half-written while something reports progress")

    # The drive above is worth keeping but it does NOT discriminate: a 200 KB
    # write finishes faster than the reader can catch it, so it passed with the
    # atomic write removed. Proved with tools/sabotage.py rather than assumed.
    # What actually holds the property is that both writes go through a rename.
    tool_src = (F.CODE / "tools" / "plan.py").read_text(encoding="utf-8")
    t.contains(tool_src, "os.replace",
               "the page is moved into place, not written in place")
    save = tool_src[tool_src.find("    def save(self):"):][:600]
    t.ok("_atomic(self.path" in save and "self.path.write_text" not in save,
         "saving the plan goes through the atomic write",
         "writing in place lets a reader catch half a file, which looks like a "
         "broken plan and not like the race it is")
    pub = tool_src[tool_src.find("    def publish(self):"):][:1400]
    t.ok("_atomic(" in pub,
         "and so does publishing the state the open page reads",
         "the page polls that file every four seconds; a torn read there is "
         "a syntax error in a script tag, which fails silently")

    # ---- a NEW task is added through the tool, so it gets published --
    # Asked on 2026-08-20: *the plan.html did it auto change?* It had not, and
    # the page was innocent. New tasks were being written into PLAN.html by
    # hand, and plan_state.js - the file an open page pulls every four seconds
    # - is only rewritten when this tool runs. So the page showed the last
    # PUBLISHED state until some later status change happened to republish it.
    # The fix is that adding a task is a command, not an edit.
    tool = F.CODE / "tools" / "plan.py"
    src = tool.read_text(encoding="utf-8")
    t.contains(src, "def add(", "a task can be ADDED through the tool")

    tid = "Z9-%d" % (_os.getpid() % 1000)
    r = subprocess.run([sys.executable, str(tool), "add", tid, "qc self-test"],
                       capture_output=True, text=True, timeout=60,
                       env=env)
    t.eq(r.returncode, 0, "adding a task succeeds")
    t.contains(work.read_text(encoding="utf-8"), tid,
               "the task really lands in the page")
    fresh = json.loads((work.parent / "plan_state.js")
                       .read_text(encoding="utf-8")
                       .split("=", 1)[1].rstrip().rstrip(";"))
    t.contains(fresh.get("raw", ""), tid,
               "and the PUBLISHED state carries it, without a second command")

    # Adding the same id twice is refused rather than silently duplicated: two
    # lines with one id makes the progress card count it twice.
    again = subprocess.run([sys.executable, str(tool), "add", tid, "again"],
                           capture_output=True, text=True, timeout=60,
                           env=env)
    t.ok(again.returncode != 0, "adding the same id twice is refused",
         "it returned %d; a duplicated id is counted twice by the progress card"
         % again.returncode)

    # A STATUS WORD AS THE FIRST WORD OF A NOTE IS A MISTYPED --status.
    # `add <id> doing "..."` filed "doing" as note text and left the task
    # `todo` while it was actively being worked, so the page said nothing was
    # in flight - the one thing it exists to show. The user caught it on
    # 2026-08-28, after it had already happened silently to an earlier task.
    # Refusing costs nothing; guessing the status would be worse.
    for word in ("doing", "done", "blocked"):
        bad = subprocess.run(
            [sys.executable, str(tool), "add", "Z8-%s" % word[:2], word,
             "the note", "after", "it"],
            capture_output=True, text=True, timeout=60, env=env)
        t.ok(bad.returncode != 0,
             "a note beginning with %r is refused, not filed as todo" % word,
             bad.stdout + bad.stderr)
        t.contains((bad.stdout + bad.stderr), "--status",
                   "and the refusal names the flag that was meant")

    # ...while a QUOTED note is ordinary text, even when it opens with one of
    # those words. "qc self-test" is a real note this very check writes.
    for note in ("qc self-test of the note guard",
                 "the arm is doing the wrong thing when a show is done"):
        ok = subprocess.run(
            [sys.executable, str(tool), "add", "Z7-%d" % len(note), note],
            capture_output=True, text=True, timeout=60, env=env)
        t.eq(ok.returncode, 0, "a quoted note starting %r is still fine"
             % note.split(" ", 1)[0])

    # ---- two plans, and a stamp must not land on the wrong one --------
    # There are two pages now: docs/PLAN.html for the rig, and
    # docs/system_integral.html for joining Mice to outside programs. The
    # second was numbered from A1 at the user's request, so 37 of its 41 ids
    # ALSO exist on the robot plan. Stamping the wrong page is invisible - the
    # page being watched simply never changes and the work looks stalled.
    #
    # Driven in a throwaway tree with its own docs/, never against the real
    # plans: a check that could mark a real task done when the guard breaks is
    # a check that damages the thing it is guarding.
    two = Path(_tf.mkdtemp(prefix="qc_pages_"))
    (two / "tools").mkdir()
    (two / "docs").mkdir()
    _sh.copy(F.CODE / "tools" / "plan.py", two / "tools" / "plan.py")
    both = "<pre id='state'><code>STATE\n# RUNNING: nothing\n%s\n</code></pre>"
    (two / "docs" / "PLAN.html").write_text(
        both % "A1-1: todo   - on both plans\nA25-5: todo   - robot only",
        encoding="utf-8", newline="")
    (two / "docs" / "system_integral.html").write_text(
        both % "A1-1: todo   - on both plans\nA5-4: todo   - system only",
        encoding="utf-8", newline="")
    twotool = two / "tools" / "plan.py"
    clean = {k: v for k, v in _os.environ.items() if k != "MICE_PLAN"}

    before_robot = (two / "docs" / "PLAN.html").read_text(encoding="utf-8")
    before_sys = (two / "docs" / "system_integral.html").read_text(encoding="utf-8")
    clash = subprocess.run([sys.executable, str(twotool), "done", "A1-1"],
                           capture_output=True, text=True, timeout=60, env=clean)
    said = clash.stdout + clash.stderr
    t.ok(clash.returncode != 0,
         "an id BOTH plans carry is refused, not guessed",
         "guessing writes to a page nobody is watching: " + said)
    t.contains(said, "--page", "and the refusal names the flag that settles it")
    t.eq((two / "docs" / "PLAN.html").read_text(encoding="utf-8"), before_robot,
         "a refused stamp leaves the robot plan untouched")
    t.eq((two / "docs" / "system_integral.html").read_text(encoding="utf-8"),
         before_sys, "and leaves the integration plan untouched")

    # An id only ONE page has needs no flag - there is nothing to confuse.
    for tid, page, other in (("A5-4", "system_integral.html", "PLAN.html"),
                             ("A25-5", "PLAN.html", "system_integral.html")):
        untouched = (two / "docs" / other).read_text(encoding="utf-8")
        r2 = subprocess.run([sys.executable, str(twotool), "doing", tid],
                            capture_output=True, text=True, timeout=60, env=clean)
        t.eq(r2.returncode, 0, "%s needs no --page, only one plan has it" % tid)
        t.contains((two / "docs" / page).read_text(encoding="utf-8"),
                   "%s: doing" % tid, "and it landed on the right page")
        t.eq((two / "docs" / other).read_text(encoding="utf-8"), untouched,
             "while the other plan was not written at all")

    # And naming the page always wins, even when both carry the id.
    named = subprocess.run(
        [sys.executable, str(twotool), "--page", "system", "done", "A1-1"],
        capture_output=True, text=True, timeout=60, env=clean)
    t.ok(named.returncode == 0, "--page settles it",
         named.stdout + named.stderr)
    t.contains((two / "docs" / "system_integral.html").read_text(encoding="utf-8"),
               "A1-1: done", "on the page that was named")
    t.contains((two / "docs" / "PLAN.html").read_text(encoding="utf-8"),
               "A1-1: todo", "and the other plan still says todo")
    _sh.rmtree(two, ignore_errors=True)
