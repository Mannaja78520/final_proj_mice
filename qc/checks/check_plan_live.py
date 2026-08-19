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
