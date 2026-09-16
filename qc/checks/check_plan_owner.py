"""Every task in the plan says which agent AND which session owns it.

Asked 2026-09-16, three times in one evening:
  * *make sure every agent save task to plan so we can track each agent too*;
  * *maybe i ask the same agent provider but in different session*;
  * *make sure all agent can hand off ... for the hit limit one*.

So tools/plan.py:
  * refuses add / doing / qc with no owner, and refuses a provider alone
    (`claude`) - two Claude sessions must never look like one owner;
  * writes `agent=provider:session` on the task line, and `show` lists it;
  * refuses `doing` on a task another session holds, unless `--take`;
  * `handoff` puts the task back to todo, owner `open`, with the next step
    written on it, so ANY agent or session can pick it up;
  * `session <provider>` hands out a fresh name.
Driven against a throwaway plan (MICE_PLAN), never the real one.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F


AREA = "tools"
TITLE = "every plan task names its agent and session, and can be handed off"


def run(t):
    tool = F.CODE / "tools" / "plan.py"
    work = Path(tempfile.mkdtemp(prefix="qc_owner_")) / "PLAN.html"
    work.write_text("<pre id=\"state\"><code>STATE\n# RUNNING: nothing\n"
                    "A1-1: todo   — first task\n</code></pre>\n",
                    encoding="utf-8", newline="")
    base = {k: v for k, v in os.environ.items() if k != "MICE_AGENT"}
    base["MICE_PLAN"] = str(work)

    def plan(*args, agent=None):
        env = dict(base)
        if agent:
            env["MICE_AGENT"] = agent
        r = subprocess.run([sys.executable, str(tool)] + list(args),
                           capture_output=True, text=True, timeout=60, env=env)
        return r.returncode, r.stdout + r.stderr

    def text():
        return work.read_text(encoding="utf-8")

    code, out = plan("add", "A1-2", "no owner given")
    t.ok(code != 0 and "A1-2" not in text(), "a task with no owner is refused", out)
    code, out = plan("add", "A1-2", "provider only", agent="claude")
    t.ok(code != 0 and "A1-2" not in text(),
         "a provider with no session is refused", out)

    code, out = plan("session", "codex")
    name = out.strip()
    t.ok(code == 0 and name.startswith("codex:") and len(name) > 7,
         "session hands out a provider:session name", out)

    code, out = plan("add", "A1-2", "real work", agent="claude:aaaa")
    t.ok(code == 0 and "agent=claude:aaaa" in text(),
         "the owner is written on the task line", out + text())

    code, out = plan("doing", "A1-1", agent="claude:aaaa")
    t.ok(code == 0 and "agent=claude:aaaa" in text().split("A1-1:")[1].split("\n")[0],
         "doing stamps the owner too", text())
    code, out = plan("show")
    t.contains(out, "A1-1(claude:aaaa)", "show lists who holds each task")

    code, out = plan("doing", "A1-1", agent="claude:bbbb")
    t.ok(code != 0 and "claude:aaaa" in out,
         "ANOTHER session of the same provider cannot take it silently", out)
    t.ok("agent=claude:aaaa" in text(), "and the owner did not change", text())

    code, out = plan("handoff", "A1-1", "run check_x next", agent="claude:aaaa")
    line = text().split("A1-1:")[1].split("\n")[0]
    t.ok(code == 0 and line.lstrip().startswith("todo") and "agent=open" in line
         and "run check_x next" in line,
         "handoff: back to todo, open to anyone, next step written", out + line)

    code, out = plan("doing", "A1-1", agent="gemini:cccc")
    t.ok(code == 0 and "agent=gemini:cccc" in text(),
         "any other agent picks a handed-off task up", out)

    # A session cut off by its limit cannot hand off: it just goes quiet. With
    # the silence limit at 0 minutes every owner counts as quiet, which is how
    # a PC-speed check sees what a 45-minute silence looks like.
    base["MICE_SILENT_MIN"] = "0"
    code, out = plan("show")
    t.ok("SILENT" in out and "gemini:cccc" in out,
         "an owner that went quiet is shown as probably stopped", out)
    code, out = plan("doing", "A1-1", agent="codex:dddd")
    t.ok(code != 0 and "SILENT" in out and "--take" in out,
         "and taking it says it is silent and how to take it", out)
    code, out = plan("doing", "A1-1", "--take", agent="codex:dddd")
    t.ok(code == 0 and "agent=codex:dddd" in text(),
         "--take lets a session continue one that hit its limit", out)
