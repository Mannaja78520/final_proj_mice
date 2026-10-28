"""The AI usage-limit watcher resumes, waits and hands off exactly as asked.

User 2026-10-29: when Codex, Gemini or Claude hits a usage limit, read the
reset time from its own message and send the continue command 1 minute after
the reset (Claude resumes by itself); a weekly limit, or a reset more than 7
hours away, hands the unfinished work to Codex or Gemini through HANDOFF.md and
handoff/tasks, round after round until the task files say done.

Held here on fakes in a temp home (the same file formats as the real PC,
samples copied 2026-10-29 from ~/.codex/sessions and ~/.claude/projects):
- the reset time of every real wording (Codex "try again at 3:26 AM", Claude
  "resets 11:50am (Asia/Bangkok)" and "resets Nov 3, 9am", Gemini "retry in
  1h2m3.5s") is read right, without tzdata (the PC has none);
- a Codex limit becomes ONE resume of that session, not before reset + 60 s;
- a limit someone already resumed by hand (its log grew) is skipped;
- a short Claude limit does nothing; a quoted limit inside a tool result is no limit;
- a Claude weekly limit starts Codex on the task files the session named, the
  prompt points at HANDOFF.md, and a second round runs until "Status: done";
- with Codex itself limited, the handoff goes to Gemini instead;
- a limit older than the history window is ignored.
"""
import datetime as dt
import json
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "AI usage-limit watcher: reset times, resume at reset + 1 min, weekly -> handoff"

sys.path.insert(0, str(F.CODE / "tools"))

BKK = dt.timezone(dt.timedelta(hours=7))
WORKER = r'''
import pathlib, re, sys
mode, cwd, session, marks = sys.argv[1:5]
text = sys.stdin.read()
open(pathlib.Path(marks, "%s-%s.txt" % (mode, session or "new")), "a", encoding="utf-8").write(text)
for name in set(re.findall(r"handoff[/\\]+tasks[/\\]+([\w.-]+\.md)", text)):
    f = pathlib.Path(cwd, "handoff", "tasks", name)
    if f.exists():
        body = f.read_text(encoding="utf-8")
        f.write_text(body + ("\nStatus: done\n" if "progress" in body else "\nprogress\n"), encoding="utf-8")
'''


def _cfg(tmp):
    cfg = json.loads((F.CODE / "config" / "ai_watch.json").read_text(encoding="utf-8"))
    cfg["default_timezone"] = "+07:00"  # the samples were written on the PC (+07)
    (tmp / "worker.py").write_text(WORKER, encoding="utf-8")
    for name, p in cfg["providers"].items():
        if name.startswith("_"):
            continue
        for mode in ("resume", "start"):
            if mode in p:
                p[mode] = {"argv": [sys.executable, str(tmp / "worker.py"), name + "-" + mode, "{cwd}",
                                    "{session}", str(tmp / "marks")], "stdin": "{prompt}"}
    return cfg


def _line(f, row):
    with open(f, "a", encoding="utf-8", newline="") as fh:
        fh.write(json.dumps(row) + "\n")


def _settle(w, clock, t, pred, label):
    for _ in range(100):
        w.tick()
        if pred():
            return True
        time.sleep(0.1)
    t.ok(False, label, "\n".join(w.state["events"][-8:]))
    return False


def run(t):
    from limitwatch.watcher import Watcher
    from limitwatch.reset_time import ResetClock

    real = json.loads((F.CODE / "config" / "ai_watch.json").read_text(encoding="utf-8"))
    clk = ResetClock(dict(real, default_timezone="+07:00"))
    at = dt.datetime(2026, 10, 29, 3, 22, 51, tzinfo=BKK)
    for text, want in [
            ("You’ve hit your usage limit. ... or try again at 3:26 AM.", dt.datetime(2026, 10, 29, 3, 26, tzinfo=BKK)),
            ("You've hit your session limit · resets 11:50am (Asia/Bangkok)", dt.datetime(2026, 10, 29, 11, 50, tzinfo=BKK)),
            ("You've hit your session limit · resets 1am (Asia/Bangkok)", dt.datetime(2026, 10, 30, 1, 0, tzinfo=BKK)),
            ("You've hit your weekly limit · resets Nov 3, 9am (Asia/Bangkok)", dt.datetime(2026, 11, 3, 9, 0, tzinfo=BKK)),
            ("RESOURCE_EXHAUSTED: Quota exceeded. Please retry in 1h2m3.5s.", at + dt.timedelta(seconds=3723.5))]:
        got = clk.parse(text, at)
        t.ok(got == want, "reset read from %r" % text[:48], "got %s want %s" % (got, want))
    codex = real["providers"]["codex"]["resume"]["argv"]
    t.ok("resume" in codex and "{session}" in codex and "{cwd}" in codex,
         "the real Codex resume command resumes the same session in its folder", " ".join(codex))

    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        tmp = Path(d)
        home, marks, repo = tmp / "home", tmp / "marks", tmp / "repo"
        marks.mkdir()
        (repo / "handoff" / "tasks").mkdir(parents=True)
        (repo / "HANDOFF.md").write_text("rules\n", encoding="utf-8")
        task = repo / "handoff" / "tasks" / "cad-wall.md"
        task.write_text("# cad wall\nOwner: claude:x\n", encoding="utf-8")
        subprocess.run(["git", "init", "-q", str(repo)], check=True)
        clock = [dt.datetime(2026, 10, 29, 3, 23, tzinfo=BKK)]
        w = Watcher(_cfg(tmp), tmp / "out", repo, now=lambda: clock[0], home=str(home))

        # --- Codex: resume once, at reset + 60 s -----------------------------------
        sess = "01a1842a-0000-7000-8000-000000000001"  # not a real session: the real one may be running
        roll = home / ".codex" / "sessions" / "2026" / "10" / "29" / ("rollout-2026-10-29T03-18-50-%s.jsonl" % sess)
        roll.parent.mkdir(parents=True)
        _line(roll, {"timestamp": "2026-10-28T20:18:51Z", "type": "session_meta",
                     "payload": {"session_id": sess, "cwd": str(tmp)}})
        _line(roll, {"timestamp": "2026-10-28T20:22:51.109Z", "type": "event_msg", "payload": {
            "type": "task_complete", "error": {"message": "You’ve hit your usage limit. Upgrade to Pro "
                                               "or try again at 3:26 AM.",
                                               "codex_error_info": "usage_limit_exceeded"}}})
        w.tick()
        jobs = [j for j in w.state["jobs"] if j["provider"] == "codex"]
        t.ok(len(jobs) == 1 and jobs[0]["kind"] == "resume", "a Codex limit schedules one resume", str(jobs))
        t.ok(jobs and jobs[0]["due"].startswith("2026-10-28T20:27:00"), "due at reset + 60 s (03:27 local)",
             jobs and jobs[0]["due"])
        w.tick()
        t.eq(len([j for j in w.state["jobs"] if j["provider"] == "codex"]), 1, "the same notice is not counted twice")
        clock[0] = dt.datetime(2026, 10, 29, 3, 26, 30, tzinfo=BKK)
        w.tick()
        t.eq(jobs[0]["status"] if jobs else None, "pending", "nothing is sent before reset + 60 s")
        clock[0] = dt.datetime(2026, 10, 29, 3, 27, 5, tzinfo=BKK)
        _settle(w, clock, t, lambda: w.state["jobs"][0]["status"] == "done", "the resume job runs and ends")
        sent = marks / ("codex-resume-%s.txt" % sess)
        t.ok(sent.exists() and "usage limit" in sent.read_text(encoding="utf-8"),
             "the continue prompt reached Codex for that session", str(list(marks.iterdir())))

        # --- resumed by hand already: skipped ----------------------------------------
        sess2 = "01a1842a-0000-7000-8000-000000000002"
        roll2 = roll.with_name("rollout-2026-10-29T03-30-00-%s.jsonl" % sess2)
        _line(roll2, {"timestamp": "2026-10-28T20:30:00Z", "type": "session_meta", "payload": {"session_id": sess2, "cwd": str(tmp)}})
        _line(roll2, {"timestamp": "2026-10-28T20:31:00Z", "type": "event_msg", "payload": {
            "type": "task_complete", "error": {"message": "hit your usage limit. try again at 3:40 AM.",
                                               "codex_error_info": "usage_limit_exceeded"}}})
        w.tick()
        _line(roll2, {"timestamp": "2026-10-28T20:41:00Z", "type": "event_msg", "payload": {"type": "task_started", "pad": "x" * 200}})
        clock[0] = dt.datetime(2026, 10, 29, 3, 41, 30, tzinfo=BKK)
        w.tick()
        j2 = [j for j in w.state["jobs"] if j["session"] == sess2]
        t.ok(j2 and j2[0]["status"] == "skipped", "a session already resumed by hand is not resumed again",
             j2 and j2[0]["status"])

        # --- Claude: short limit = nothing; quoted text = nothing --------------------
        proj = home / ".claude" / "projects" / "E--x"
        proj.mkdir(parents=True)
        tr = proj / "s1.jsonl"
        _line(tr, {"type": "user", "timestamp": "2026-10-28T20:40:00Z", "cwd": str(repo), "sessionId": "s1",
                   "message": {"role": "user", "content": [{"type": "tool_result",
                               "content": "You've hit your weekly limit · resets Nov 3, 9am <synthetic>"}]}})
        _line(tr, {"type": "assistant", "timestamp": "2026-10-28T20:40:30Z", "cwd": str(repo), "sessionId": "s1",
                   "message": {"model": "claude-opus-5-5", "content": [{"type": "text",
                               "text": "Codex wrote: You've hit your weekly limit · resets Nov 3, 9am (model <synthetic>)"}]}})
        _line(tr, {"type": "assistant", "timestamp": "2026-10-28T20:41:00Z", "cwd": str(repo), "sessionId": "s1",
                   "message": {"model": "claude-opus-5-5", "content": [{"type": "text",
                               "text": "Working on handoff/tasks/cad-wall.md step 3."}]}})
        _line(tr, {"type": "assistant", "timestamp": "2026-10-28T20:42:00Z", "cwd": str(repo), "sessionId": "s1",
                   "message": {"model": "<synthetic>", "content": [{"type": "text",
                               "text": "You've hit your session limit · resets 5am (Asia/Bangkok)"}]}})
        n = len(w.state["jobs"])
        w.tick()
        t.eq(len(w.state["jobs"]), n, "a short Claude limit or a quoted limit starts nothing")

        # --- Claude weekly: hand off to Codex, rounds until done ----------------------
        _line(tr, {"type": "assistant", "timestamp": "2026-10-28T20:43:00Z", "cwd": str(repo), "sessionId": "s1",
                   "message": {"model": "<synthetic>", "content": [{"type": "text",
                               "text": "You've hit your weekly limit · resets Nov 3, 9am (Asia/Bangkok)"}]}})
        _settle(w, clock, t, lambda: any(g.get("finished") for g in w.state["goals"].values()),
                "the handed-off work runs to an end")
        goals = list(w.state["goals"].values())
        g = goals[0] if goals else {}
        t.ok(g.get("worker") == "codex" and g.get("finished") == "done" and g.get("rounds") == 1,
             "weekly -> Codex, a second round, then done", str(g))
        hand = marks / "codex-start-new.txt"
        body = hand.read_text(encoding="utf-8") if hand.exists() else ""
        t.ok("HANDOFF.md" in body and "cad-wall.md" in body and "step 3" in body,
             "the handoff prompt names HANDOFF.md, the session's task file and its last words", body[:300])
        t.ok("Status: done" in task.read_text(encoding="utf-8"), "the worker really edited the task file")

        # --- Codex limited -> Gemini --------------------------------------------------
        w.state["limited"]["codex"] = (clock[0] + dt.timedelta(hours=3)).isoformat()
        task2 = repo / "handoff" / "tasks" / "next.md"
        task2.write_text("# next\n", encoding="utf-8")
        tr2 = proj / "s2.jsonl"
        _line(tr2, {"type": "assistant", "timestamp": "2026-10-28T20:44:00Z", "cwd": str(repo), "sessionId": "s2",
                    "message": {"model": "claude-opus-5-5", "content": [{"type": "text", "text": "on handoff/tasks/next.md"}]}})
        _line(tr2, {"type": "assistant", "timestamp": "2026-10-28T20:45:00Z", "cwd": str(repo), "sessionId": "s2",
                    "message": {"model": "<synthetic>", "content": [{"type": "text",
                                "text": "You've hit your weekly limit · resets Nov 3, 9am (Asia/Bangkok)"}]}})
        w.tick()
        g2 = [g for g in w.state["goals"].values() if any("next.md" in x for x in g["tasks"])]
        t.ok(g2 and g2[0].get("worker") == "gemini", "Codex limited: the handoff goes to Gemini", str(g2))

        # --- old notice ignored ---------------------------------------------------------
        tr3 = proj / "s3.jsonl"
        _line(tr3, {"type": "assistant", "timestamp": "2026-10-26T20:45:00Z", "cwd": str(repo), "sessionId": "s3",
                    "message": {"model": "<synthetic>", "content": [{"type": "text",
                                "text": "You've hit your weekly limit · resets Nov 3, 9am (Asia/Bangkok)"}]}})
        n = len(w.state["goals"])
        w.tick()
        t.eq(len(w.state["goals"]), n, "a limit older than the history window is ignored")
        for _ in range(100):  # let the fake workers end before the folder goes
            w.tick()
            if not any(j["status"] == "running" for j in w.state["jobs"]):
                break
            time.sleep(0.1)
