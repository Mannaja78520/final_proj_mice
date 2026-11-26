"""The AI fallback chain: Claude, then GPT Codex, then Gemini 4 Argon, then regular Gemini for small steps only.

User 2026-11-27: when Claude hits its limit the work goes to GPT Codex; when Codex is limited too, to Gemini 4
Argon (a FULL fallback: hard and long work allowed); when Argon is also exhausted, the regular Gemini models do ONLY
small safe steps; when all are limited it waits and the watcher keeps checking the reset times; only ONE AI edits
at a time (.local/ai_active.lock); when Claude is free again no new round starts for the fallback (hand-back through
the task files). tools/limitwatch (config/ai_watch.json) already detected limits, read reset times and handed work
on; this holds the order, the scope text, the single-editor lock and the hand-back, on fakes (no CLI is run).
"""
import datetime as dt
import json
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "AI fallback chain: Claude, Codex, Gemini 4 Argon (full), regular Gemini (small only), one editor at a time"

sys.path.insert(0, str(F.CODE / "tools"))

UTC = dt.timezone.utc
NOW = dt.datetime(2026, 11, 27, 3, 0, tzinfo=UTC)
WEEKLY = "You've hit your weekly limit \u00b7 resets Dec 3, 9am (Asia/Bangkok)"


class FakeLauncher:
    def __init__(self):
        self.alive = {}
        self.n = 0

    def start(self, job):
        self.n += 1
        job["pid"] = 1000 + self.n
        job["log"] = ""
        self.alive[job["id"]] = True
        return job["pid"]

    def running(self, job):
        return self.alive.get(job["id"], False), (None if self.alive.get(job["id"]) else 0)


def _setup(tmp, limited):
    from limitwatch.watcher import Watcher
    from limitwatch.sources import LimitHit
    cfg = json.loads((F.CODE / "config" / "ai_watch.json").read_text(encoding="utf-8"))
    cfg["default_timezone"] = "+07:00"
    for p in cfg["providers"].values():
        if isinstance(p, dict):
            p["sources"] = []                      # never read the real ~/.codex, ~/.claude or logs
    repo = tmp / "repo"
    (repo / "handoff" / "tasks").mkdir(parents=True)
    (repo / "handoff" / "tasks" / "job.md").write_text("Owner: claude\nUpdated: today\n\n## Doing now\nstep\n",
                                                       encoding="utf-8")
    src = tmp / "claude.jsonl"
    src.write_text("", encoding="utf-8")
    (tmp / "out").mkdir()
    w = Watcher(cfg, tmp / "out", repo, now=lambda: NOW)
    w.launcher = FakeLauncher()
    for name in limited:
        w.state["limited"][name] = (NOW + dt.timedelta(hours=40)).isoformat()
    hit = LimitHit(provider="claude", source=str(src), session="s1", cwd="", text=WEEKLY, written_at=NOW, size_after=0)
    return w, hit, repo


def run(t):
    with tempfile.TemporaryDirectory(ignore_cleanup_errors=True) as d:
        tmp = Path(d)

        def case(name, limited):
            sub = tmp / name
            sub.mkdir()
            w, hit, repo = _setup(sub, limited)
            w.on_hit(hit, NOW)
            jobs = [j for j in w.state["jobs"] if j["kind"] == "handoff"]
            return w, hit, repo, (jobs[-1] if jobs else None)

        cfg = json.loads((F.CODE / "config" / "ai_watch.json").read_text(encoding="utf-8"))
        t.ok(cfg["handoff_order"] == ["codex", "gemini_argon", "gemini"],
             "the order after Claude is data: Codex, Gemini 4 Argon, regular Gemini", repr(cfg["handoff_order"]))
        argon = cfg["providers"]["gemini_argon"]
        t.ok(argon["scope"] == "full" and "gemini-4-argon" in " ".join(argon["start"]["argv"])
             and cfg["providers"]["gemini"]["scope"] == "small",
             "Argon is the full fallback model, the regular Gemini is marked small-only")

        w, hit, repo, job = case("a", [])
        t.ok(job and job["provider"] == "codex", "Claude limited: the work goes to GPT Codex", repr(job and job["provider"]))
        t.ok("SCOPE LIMIT" not in (job or {}).get("stdin", ""), "Codex gets the normal brief, no scope limit")

        w, hit, repo, job = case("b", ["codex"])
        t.ok(job and job["provider"] == "gemini_argon", "Claude and Codex limited: Gemini 4 Argon takes it", repr(job and job["provider"]))
        t.ok("SCOPE LIMIT" not in (job or {}).get("stdin", ""), "Argon may do hard and long work: no scope limit in its brief")

        w, hit, repo, job = case("c", ["codex", "gemini_argon"])
        t.ok(job and job["provider"] == "gemini", "Argon exhausted too: the regular Gemini gets it", repr(job and job["provider"]))
        t.ok("SCOPE LIMIT" in (job or {}).get("stdin", "") and "Do NOT start long edits" in (job or {}).get("stdin", ""),
             "its brief says: small safe steps only, no long edits, no hard fixes")

        w, hit, repo, job = case("d", ["codex", "gemini_argon", "gemini"])
        t.ok(job is None and any("no free AI" in e for e in w.state["events"]),
             "all limited: nothing is started, it waits for the first reset", "\n".join(w.state["events"][-3:]))
        first = min(w.state["limited"].values())
        t.ok(w.state["limited"].get("claude") and first, "each tool's limit and reset time is kept in the state")

        # one editor at a time, and the lock file
        w, hit, repo, job = case("e", [])
        lock = repo / ".local" / "ai_active.lock"
        other = w._job("handoff", "gemini_argon", w.providers["gemini_argon"]["start"], str(repo), "", "x", NOW)
        w.state["jobs"].append(other)
        w._fire_due(NOW)
        t.ok(job["status"] == "running" and lock.exists() and json.loads(lock.read_text())["tool"] == "codex",
             "the Codex job runs and .local/ai_active.lock names it", lock.exists() and lock.read_text() or "no lock")
        t.ok(other["status"] == "pending" and other.get("waiting_for") == "codex",
             "a job of another AI does not start while Codex is editing", repr(other["status"]))
        w.launcher.alive[job["id"]] = False
        w.state["limited"].pop("claude", None)       # Claude is free again
        w._check_running(NOW + dt.timedelta(hours=50))
        t.ok(job["status"] == "done" and not (lock.exists() and json.loads(lock.read_text())["tool"] == "codex"),
             "when it ends the lock is released (or passes to the next AI)", lock.exists() and lock.read_text() or "gone")
        goal = w.state["goals"][job["goal"]]
        t.ok(goal.get("finished") == "handed back",
             "Claude is free again: no new fallback round, the task files carry the hand-over", repr(goal.get("finished")))
        rounds = [j for j in w.state["jobs"] if j["kind"] == "round"]
        t.ok(not rounds, "and no round job was created", repr(len(rounds)))
