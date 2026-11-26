"""Run QC checks in their own processes, with a hard time limit and a heartbeat.

Why this exists (2026-11-25): three scheduled full runs stalled at ~340 of 415
checks and nothing said which check, or why. The standard process pool cannot answer:
it does not say which job a worker is running, it cannot stop one job (killing a
worker breaks the WHOLE pool and every pending future fails or hangs), and a
dead worker can leave the main loop waiting forever. So each check gets its own
process (the old pool also used a fresh process per check)
and this module owns three things the pool could not:

  * a HARD LIMIT per check: past its budget the check's process tree and its
    browsers are killed and the check is reported as a failure, "timed out after
    N s" - the other checks never notice;
  * a process that dies without answering is a failed check ("died, exit code N"),
    not a hang;
  * a HEARTBEAT (qc/last_progress.json, every ~10 s): what finished last and what
    is running now with pid and age. When nothing finishes for STALL_SECS the
    running set is printed to the real stderr, so a stall names its check.

No assertion is touched. The budget is generous by construction: never below
`floor`, and never below 3x the slowest healthy time seen for that check.
"""
import json
import multiprocessing as mp
import os
import subprocess
import sys
import time
from pathlib import Path

STALL_SECS = 300          # nothing finished for this long: say what is running
BEAT_SECS = 10


def budget_for(stem, durations, floor):
    """Seconds a check may run: the floor, or 3x its slowest healthy time."""
    try:
        seen = float(durations.get(stem, 0.0) or 0.0)
    except (TypeError, ValueError):
        seen = 0.0
    return max(float(floor), 3.0 * seen)


def kill_tree(pid):
    """Kill a process and everything it started. Never raises."""
    try:
        if os.name == "nt":
            subprocess.run(["taskkill", "/F", "/T", "/PID", str(pid)],
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
        else:
            os.kill(pid, 9)
    except (OSError, subprocess.SubprocessError):
        pass


def _entry(worker, arg, conn):
    try:
        conn.send(worker(arg))
    except BaseException as e:                       # noqa: BLE001 - reported, not hidden
        try:
            conn.send(("__error__", "%s: %s" % (type(e).__name__, e)))
        except Exception:                            # noqa: BLE001
            pass
    finally:
        conn.close()


class _Job:
    def __init__(self, key, arg, budget):
        self.key, self.arg, self.budget = key, arg, budget
        self.proc = self.conn = None
        self.t0 = 0.0
        self.p0 = 0.0


class CheckPool:
    """`width` checks at once, each in its own process. Use submit() then poll()."""

    def __init__(self, worker, width, on_kill=None, ctx=None, hold=None, clock=None):
        self.worker, self.width = worker, max(1, int(width))
        # hold(): True while NO new check may start (the person is using the PC, tools/polite.py);
        # clock.paused: seconds this run spent frozen, never counted against a hard limit
        self.hold, self.clock = hold, clock
        self.on_kill = on_kill            # called with the pid of a check that was killed
        self.ctx = ctx or mp.get_context("spawn")
        self.waiting, self.running = [], []

    def submit(self, key, arg, budget):
        self.waiting.append(_Job(key, arg, budget))

    def busy(self):
        return bool(self.waiting or self.running)

    def _start(self, job):
        job.p0 = self.clock.paused if self.clock else 0.0
        parent, child = self.ctx.Pipe(duplex=False)
        job.conn = parent
        job.proc = self.ctx.Process(target=_entry, args=(self.worker, job.arg, child))
        job.proc.start()
        child.close()
        job.t0 = time.time()
        self.running.append(job)

    def poll(self):
        """Start what fits, return [(key, kind, value, secs)] finished since the
        last call. kind: "done" (value = the worker's result), "timeout", "died"."""
        out = []
        # `hold` (the headroom governor) only stops EXTRA starts: one check per pool always runs,
        # so a busy PC slows QC down instead of stopping it
        while self.waiting and len(self.running) < self.width and not (
                self.running and self.hold and self.hold()):
            self._start(self.waiting.pop(0))
        for job in list(self.running):
            secs = time.time() - job.t0 - ((self.clock.paused - job.p0) if self.clock else 0.0)
            kind = value = None
            try:
                if job.conn.poll():
                    value = job.conn.recv()
                    kind = "done"
            except (EOFError, OSError):
                job.proc.join(timeout=2)
                kind = "died"
                value = ("process ended with exit code %s without an answer"
                         % job.proc.exitcode)
            if kind is None and not job.proc.is_alive():
                if job.conn.poll():                   # answered just before exiting
                    continue
                kind = "died"
                value = "process ended with exit code %s without an answer" % job.proc.exitcode
            if kind is None and secs > job.budget:
                kind = "timeout"
                value = "timed out after %.0f s (hard limit %.0f s)" % (secs, job.budget)
                if self.on_kill:
                    self.on_kill(job.proc.pid)
                kill_tree(job.proc.pid)
            if kind is None:
                continue
            self.running.remove(job)
            try:
                job.conn.close()
                job.proc.join(timeout=5)
            except (OSError, ValueError):
                pass
            out.append((job.key, kind, value, secs))
        return out

    def snapshot(self):
        now = time.time()
        return [{"check": j.key, "pid": j.proc.pid,
                 "age": round(now - j.t0 - ((self.clock.paused - j.p0) if self.clock else 0.0), 1),
                 "budget": round(j.budget)} for j in self.running]


class Heartbeat:
    """Writes qc/last_progress.json and speaks when nothing has finished for a while."""

    def __init__(self, path, total, pools, held=None):
        self.path, self.total, self.pools = Path(path), total, pools
        self.held = held                     # callable: True while the run yields to the person
        self.done, self.last, self.t_last_done = 0, "", time.time()
        self.t_beat = 0.0
        self.t_stall_said = 0.0

    def finished(self, name):
        self.done += 1
        self.last = name
        self.t_last_done = time.time()

    def tick(self, now=None):
        now = now or time.time()
        if now - self.t_beat < BEAT_SECS:
            return
        self.t_beat = now
        running = [r for p in self.pools for r in p.snapshot()]
        try:
            self.path.write_text(json.dumps(
                {"time": time.strftime("%H:%M:%S"), "done": self.done, "total": self.total,
                 "last_finished": self.last, "running": running}, indent=1), encoding="utf-8")
        except OSError:
            pass
        if self.held and self.held():
            self.t_last_done = now           # yielding on purpose is not a stall
        if now - self.t_last_done > STALL_SECS and now - self.t_stall_said > STALL_SECS:
            self.t_stall_said = now
            names = ", ".join("%s (pid %s, %ss)" % (r["check"], r["pid"], int(r["age"]))
                              for r in running) or "nothing running"
            print("QC STALL: nothing finished for %d s (%d/%d done, last: %s). Running: %s"
                  % (now - self.t_last_done, self.done, self.total, self.last or "-", names),
                  file=sys.__stderr__, flush=True)
            print("QC STALL: nothing finished for %d s; running: %s"
                  % (now - self.t_last_done, names), flush=True)


# ---- tiny workers for check_hard_timeout (spawn needs them importable) ----
def selftest_work(arg):
    kind, secs = arg
    if kind == "sleep":
        time.sleep(secs)
    elif kind == "die":
        os._exit(3)
    return ("ok", kind)
