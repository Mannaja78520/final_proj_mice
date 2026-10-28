"""The decision loop: limit notice -> resume later, or hand the work to another AI.

    short limit, AI resumes itself (Claude)  -> note only
    short limit, AI does not (Codex, Gemini) -> resume job at reset + resume_delay_seconds
    weekly / reset further than handoff_if_reset_over_hours
                                             -> handoff job to the first free AI in
                                                handoff_order; it gets more rounds
                                                until its task files say done

State (offsets, jobs, which AI is limited until when) is one JSON file under
_out/ai_watch, so the watcher can stop and start without losing a scheduled job.
"""
import datetime as dt
import json
import os
import re
import uuid
from pathlib import Path

from . import brief
from .jobs import Launcher, session_running
from .reset_time import ResetClock
from .sources import KINDS

UTC = dt.timezone.utc


def _iso(t):
    return t.astimezone(UTC).isoformat() if t else None


def _t(s):
    return dt.datetime.fromisoformat(s) if s else None


class Matcher:
    def __init__(self, providers):
        self.limit = {n: [re.compile(p) for p in p_cfg.get("limit_patterns", [])]
                      for n, p_cfg in providers.items()}
        self.long = {n: [re.compile(p) for p in p_cfg.get("long_patterns", [])]
                     for n, p_cfg in providers.items()}

    def is_limit(self, provider, text):
        return any(p.search(text) for p in self.limit.get(provider, []))

    def is_long(self, provider, text):
        return any(p.search(text) for p in self.long.get(provider, []))


class Watcher:
    def __init__(self, cfg, out_dir, repo_root, now=None, home=None):
        self.cfg = cfg
        self.out = Path(out_dir)
        self.repo_root = str(repo_root)
        self.now = now or (lambda: dt.datetime.now(UTC))
        self.home = home or os.path.expanduser("~")
        self.providers = {k: v for k, v in cfg["providers"].items() if not k.startswith("_")}
        self.matcher = Matcher(self.providers)
        self.clock = ResetClock(cfg)
        self.launcher = Launcher(self.out / "logs")
        self.state_path = self.out / "state.json"
        self.state = self._load()
        self.sources = [KINDS[s["kind"]](name, s, self.matcher, self._expand)
                        for name, p in self.providers.items() for s in p.get("sources", [])]

    # ---- state ---------------------------------------------------------------
    def _load(self):
        try:
            st = json.loads(self.state_path.read_text(encoding="utf-8"))
        except (OSError, ValueError):
            st = {}
        for k, v in (("offsets", {}), ("meta", {}), ("seen", {}), ("jobs", []), ("limited", {}),
                     ("goals", {}), ("events", [])):
            st.setdefault(k, v)
        return st

    def save(self):
        self.out.mkdir(parents=True, exist_ok=True)
        tmp = self.state_path.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8", newline="") as f:
            json.dump(self.state, f, indent=1)
        os.replace(tmp, self.state_path)

    def event(self, text):
        line = "%s %s" % (self.now().astimezone().strftime("%Y-%m-%d %H:%M:%S"), text)
        self.state["events"] = (self.state["events"] + [line])[-200:]
        with open(self.out / "events.log", "a", encoding="utf-8", newline="") as f:
            f.write(line + "\n")

    def _expand(self, s):
        s = s.replace("{out}", str(self.out)).replace("{repo}", self.repo_root)
        if s.startswith("~"):
            s = self.home + s[1:]
        return s

    # ---- one pass --------------------------------------------------------------
    def tick(self):
        self.out.mkdir(parents=True, exist_ok=True)
        now = self.now()
        oldest = now - dt.timedelta(hours=self.cfg["ignore_hits_older_than_hours"])
        for src in self.sources:
            for hit in src.scan(self.state["offsets"], self.state["meta"], oldest):
                if hit.key in self.state["seen"] or hit.written_at < oldest:
                    continue
                self.state["seen"][hit.key] = _iso(now)
                self.on_hit(hit, now)
        self._fire_due(now)
        self._check_running(now)
        self.save()

    # ---- decide ---------------------------------------------------------------
    def on_hit(self, hit, now):
        p = self.providers[hit.provider]
        reset = self.clock.parse(hit.text, hit.written_at)
        far = dt.timedelta(hours=self.cfg["handoff_if_reset_over_hours"])
        long = self.matcher.is_long(hit.provider, hit.text) or bool(reset and reset - hit.written_at > far)
        self.state["limited"][hit.provider] = _iso(reset or now + dt.timedelta(
            minutes=self.cfg["unknown_reset_retry_minutes"]))
        goal = self._goal_of(hit)
        self.event("LIMIT %s %s reset=%s long=%s session=%s :: %s" % (
            hit.provider, "(handed-off work)" if goal else "", _iso(reset), long, hit.session,
            hit.text[:160]))
        if reset and reset <= now and long:
            self.event("  limit already over, nothing to do")
            return
        if long:
            if self._handoff(hit, reset, goal, now):
                return
            self.event("  no free AI to hand off to; waiting for the reset instead")
        if p.get("auto_resume"):
            self.event("  %s resumes by itself" % hit.provider)
            return
        due = (reset + dt.timedelta(seconds=self.cfg["resume_delay_seconds"])) if reset else \
            now + dt.timedelta(minutes=self.cfg["unknown_reset_retry_minutes"])
        prompt = self.cfg["prompts"]["resume"]
        job = self._job("resume", hit.provider, p["resume"], hit.cwd or (goal or {}).get("repo", ""),
                        hit.session, prompt, due)
        job["guard"] = {"path": hit.source, "size": hit.size_after}
        job["goal"] = goal and goal["id"]
        self.state["jobs"].append(job)
        self.event("  RESUME %s scheduled %s" % (job["id"], job["due_local"]))

    def _goal_of(self, hit):
        """The handed-off work a limited worker was doing, so it carries over."""
        for j in reversed(self.state["jobs"]):
            if j["provider"] == hit.provider and j.get("goal") and \
                    hit.session in (j.get("session"), j.get("log")):
                return self.state["goals"][j["goal"]]
        return None

    def _free(self, name, now):
        until = _t(self.state["limited"].get(name))
        return name in self.providers and (until is None or until <= now)

    def _handoff(self, hit, reset, goal, now):
        if goal is None:
            repo = brief.repo_of(hit.cwd, self.repo_root)
            for g in self.state["goals"].values():  # one goal per repo while it is open
                if g["repo"] == repo and not g.get("finished"):
                    self.event("  repo already handed off (goal %s)" % g["id"])
                    return True
            tasks = brief.find_tasks(repo, self.cfg["handoff_task_glob"], hit.source,
                                     hit.provider, self.cfg["task_scope_hours"])
            goal = {"id": uuid.uuid4().hex[:6], "repo": repo, "tasks": tasks, "from": hit.provider,
                    "rounds": 0, "last_text": brief.last_words(hit.source), "reset": _iso(reset)}
            self.state["goals"][goal["id"]] = goal
        tried = {hit.provider, goal["from"]}
        worker = next((w for w in self.cfg["handoff_order"]
                       if w not in tried and self._free(w, now)), None)
        if worker is None:
            return False
        names = ", ".join(os.path.relpath(t, goal["repo"]) for t in goal["tasks"]) or \
            "(none named: pick the open ones in handoff/tasks/ that %s owns)" % goal["from"]
        prompt = self.cfg["prompts"]["handoff"].format(
            from_provider=hit.provider, reason="weekly" if self.matcher.is_long(hit.provider, hit.text)
            else "long wait", reset=self._local(reset), repo=goal["repo"], tasks=names,
            agent=self.cfg["handoff_agent_id"].format(provider=worker), last_text=goal["last_text"])
        goal["worker"] = worker
        job = self._job("handoff", worker, self.providers[worker]["start"], goal["repo"], "", prompt, now)
        job["goal"] = goal["id"]
        self.state["jobs"].append(job)
        self.event("  HANDOFF %s -> %s job %s tasks: %s" % (hit.provider, worker, job["id"], names))
        return True

    def _local(self, t):
        return t.astimezone().strftime("%Y-%m-%d %H:%M") if t else "unknown"

    def _job(self, kind, provider, cmd, cwd, session, prompt, due):
        fill = {"cwd": cwd or self.repo_root, "session": session, "prompt": prompt}
        fmt = lambda s: re.sub(r"\{(cwd|session|prompt)\}", lambda m: fill[m.group(1)], s)
        return {"id": "%s-%s" % (self.now().astimezone().strftime("%m%d%H%M"), uuid.uuid4().hex[:4]),
                "kind": kind, "provider": provider, "status": "pending",
                "due": _iso(due), "due_local": self._local(due), "session": session,
                "cwd": fmt(cmd.get("cwd", "{cwd}")), "argv": [fmt(a) for a in cmd["argv"]],
                "stdin": fmt(cmd["stdin"]) if cmd.get("stdin") else None}

    # ---- act ----------------------------------------------------------------
    def _fire_due(self, now):
        for job in self.state["jobs"]:
            if job["status"] != "pending" or _t(job["due"]) > now:
                continue
            g = job.get("guard")
            if g and os.path.exists(g["path"]) and os.path.getsize(g["path"]) > g["size"] + 64 \
                    and not g["path"].startswith(str(self.out)):
                job["status"] = "skipped"
                self.event("SKIP %s: %s already continued (its log grew)" % (job["id"], job["session"]))
                continue
            if job["kind"] == "resume" and session_running(job["session"]):
                job["status"] = "skipped"
                self.event("SKIP %s: session %s is already running" % (job["id"], job["session"]))
                continue
            try:
                self.launcher.start(job)
            except Exception as e:  # missing CLI etc.: say it, do not loop on it
                job["status"] = "failed"
                job["error"] = str(e)
                self.event("FAIL %s: %s" % (job["id"], e))
                continue
            job["status"] = "running"
            job["started"] = _iso(now)
            if job.get("goal"):
                g = self.state["goals"][job["goal"]]
                g["snap"] = brief.snapshot(g["repo"], g["tasks"])
            self.event("START %s %s %s pid=%s log=%s" % (job["kind"], job["id"], job["provider"],
                                                        job["pid"], job["log"]))

    def _check_running(self, now):
        for job in list(self.state["jobs"]):
            if job["status"] != "running":
                continue
            pat = self.providers[job["provider"]].get("session_from_log")
            if pat and not job.get("session") and os.path.exists(job.get("log", "")):
                m = re.search(pat, open(job["log"], encoding="utf-8", errors="replace").read(20000))
                if m:
                    job["session"] = m.group(1)
            alive, rc = self.launcher.running(job)
            if alive:
                continue
            job["status"] = "done"
            job["rc"] = rc
            job["ended"] = _iso(now)
            self.event("END %s rc=%s" % (job["id"], rc))
            if job.get("goal"):
                self._next_round(job, now)

    def _next_round(self, job, now):
        g = self.state["goals"][job["goal"]]
        if g.get("finished"):
            return
        limited = _t(self.state["limited"].get(job["provider"]))
        if limited and limited > now and any(
                j["status"] in ("pending", "running") and j.get("goal") == g["id"]
                for j in self.state["jobs"]):
            return  # its limit already scheduled a resume / next handoff
        if limited and limited > _t(job["started"]):
            return
        left = brief.open_tasks(g["tasks"]) if g["tasks"] else ["?"]
        if not left:
            g["finished"] = "done"
            self.event("GOAL DONE %s: every task file says done" % g["repo"])
            return
        if brief.snapshot(g["repo"], g["tasks"]) == g.get("snap"):
            g["finished"] = "stalled"
            self.event("GOAL STALLED %s: the last round changed nothing; stopping" % g["repo"])
            return
        if g["rounds"] >= self.cfg["handoff_max_rounds"]:
            g["finished"] = "max rounds"
            self.event("GOAL STOP %s: %d rounds" % (g["repo"], g["rounds"]))
            return
        g["rounds"] += 1
        names = ", ".join(os.path.relpath(t, g["repo"]) for t in g["tasks"]) or "the same tasks"
        prompt = self.cfg["prompts"]["handoff_round"].format(tasks=names)
        p = self.providers[job["provider"]]
        cmd = p["resume"] if job.get("session") or "{session}" not in " ".join(p["resume"]["argv"]) \
            else p["start"]
        nxt = self._job("round", job["provider"], cmd, g["repo"], job.get("session", ""), prompt, now)
        nxt["goal"] = g["id"]
        self.state["jobs"].append(nxt)
        self.event("ROUND %d for %s -> job %s" % (g["rounds"], g["repo"], nxt["id"]))
