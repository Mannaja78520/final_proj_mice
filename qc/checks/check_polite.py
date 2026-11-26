"""QC and our tools run at low priority, and say so when they do not.

User 2026-11-26: a full QC run made the PC laggy and hard to use. Polite mode lowers the
runner to BELOW_NORMAL CPU, LOW I/O and memory priority, and its job object lowers every
process in it - including an Edge launched through PowerShell, which is not a child of the
check. This proves it with REAL processes: a process that applies politeness like a tool
does and the grandchild it starts are BelowNormal; a process launched through PowerShell
inside the polite job is BelowNormal; with MICE_POLITE=0 / --exact-timing the priority stays
Normal and the tool says so; the real hub, Voice and Faces are never made polite.
"""
import os
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "QC and tools run at below-normal priority, children inherit it, the switch keeps Normal"

BELOW, NORMAL = 0x4000, 0x20

SLEEPER_SRC = "import time" + chr(10) + "while True:" + chr(10) + "    time.sleep(0.05)"
JOB_SRC = """
import sys
sys.path.insert(0, LIB)
import jobguard
ok = jobguard.install(cpu_cap_percent=70, below_normal=True, job_memory_gb=12)
print(ok, jobguard.set_cpu_cap(50), jobguard.job_peak_memory_gb() is not None,
      len(jobguard.job_pids()) >= 1)
"""

TOOL = '''
import os, subprocess, sys
sys.path.insert(0, TOOLS)
import polite
sys.argv = ["tool"] + EXTRA
before = polite.priority_class()
how = polite.apply("probe")
kid = subprocess.run([sys.executable, KID], capture_output=True, text=True)
print("RESULT", before, polite.priority_class(), kid.stdout.strip(), how.replace(" ", "_").replace(",", ""))
'''

KID = '''
import sys
sys.path.insert(0, TOOLS)
import polite
print(polite.priority_class())
'''

PS_RUNNER = '''
import subprocess, sys, time
sys.path.insert(0, LIB)
import jobguard
assert jobguard.install(cpu_cap_percent=80, below_normal=True)
subprocess.run(["powershell", "-NoProfile", "-Command",
                "Start-Process -FilePath '%s' -ArgumentList '%s'" % (sys.executable, KID_PY)])
time.sleep(5)
'''

WRITE_KID = '''
import sys
sys.path.insert(0, TOOLS)
import polite
open(OUT, "w").write(str(polite.priority_class()))
'''


def _governor_checks(t):
    """The headroom governor, on synthetic load (inputs injected) and with real processes."""
    import polite
    import check_pool
    base = {"targetCpuPct": 75.0, "reserveRamGb": 6.0, "gpuReservePct": 30.0, "yieldTo": [],
            "idleSeconds": 20.0, "yieldToInput": False, "yieldMode": "none",
            "reserveCpus": 4, "cpuCapPercent": None}
    T0 = time.time() + 1000.0            # fake clock: ticks are spaced by hand
    load = {"cpu": 20.0, "ram_free_gb": 20.0, "gpu": 10.0}
    caps = []
    g = polite.Governor(dict(base), load=lambda: dict(load), set_cap=caps.append, base_cap=80.0,
                        every=0)
    g.tick(now=T0 + 1)
    t.ok(not g.hold, "with room on the machine no start is held")
    load["cpu"] = 95.0
    g.tick(now=T0 + 2)
    t.ok(g.hold and "CPU" in g.reasons[0], "total CPU above the target holds new starts", repr(g.reasons))
    load.update(cpu=20.0, ram_free_gb=3.0)
    g.tick(now=T0 + 3)
    t.ok(g.hold and "RAM" in g.reasons[0], "free RAM below the reserve holds new starts", repr(g.reasons))
    load.update(ram_free_gb=20.0, gpu=90.0)
    g.tick(now=T0 + 4)
    t.ok(g.hold and "GPU" in g.reasons[0], "a busy GPU holds new starts", repr(g.reasons))
    load.update(gpu=10.0)
    g.tick(now=T0 + 5)
    t.ok(not g.hold, "and the hold is released when the load drops")
    load["cpu"] = 99.0
    for n in range(6, 14):
        g.tick(now=T0 + n)
    t.ok(caps and min(caps) == 40.0, "the CPU cap tightens under load, down to a floor", repr(caps))
    load["cpu"] = 10.0
    for n in range(14, 30):
        g.tick(now=T0 + n)
    t.ok(caps[-1] == 80.0, "and relaxes back to the base when there is room", repr(caps[-3:]))
    g2 = polite.Governor(dict(base), load=lambda: {"cpu": 5.0, "ram_free_gb": 30.0, "gpu": 0.0},
                         probe=lambda: "SLDWORKS.exe is running", every=0)
    g2.tick(now=T0 + 1)
    t.ok(not g2.hold, "by default a foreground app does NOT pause us (always-on headroom, no waiting)")
    g3 = polite.Governor(dict(base, yieldMode="pause"), load=lambda: {"cpu": 5.0, "ram_free_gb": 30.0,
                         "gpu": 0.0}, probe=lambda: "SLDWORKS.exe is running", every=0)
    g3.tick(now=T0 + 1)
    t.ok(g3.hold, "yieldMode pause (opt-in) holds starts while a foreground app runs")

    # a real pool: under load only ONE check per pool runs; when the load drops the rest start
    state = {"busy": True}
    pool = check_pool.CheckPool(check_pool.selftest_work, 4, hold=lambda: state["busy"])
    for i in range(4):
        pool.submit("j%d" % i, ("sleep", 2), 60)
    pool.poll()
    t.ok(len(pool.running) == 1, "under load a pool keeps one check going and starts no more",
         str(len(pool.running)))
    state["busy"] = False
    pool.poll()
    t.ok(len(pool.running) == 4, "when the load drops it starts the rest", str(len(pool.running)))
    end = time.time() + 30
    while pool.busy() and time.time() < end:
        pool.poll()
        time.sleep(0.1)

    # frozen time never counts against a hard limit (optional freeze mode: real suspend/resume)
    clock = polite.PauseClock()
    p2 = check_pool.CheckPool(check_pool.selftest_work, 1, clock=clock)
    p2.submit("slow", ("sleep", 5), 4)
    got, t0, cycled = [], time.time(), False
    while not got and time.time() - t0 < 30:
        got = p2.poll()
        el = time.time() - t0
        if not cycled and el > 1.0:
            clock.begin()
        if not cycled and el > 4.0:
            clock.end()
            cycled = True
        time.sleep(0.1)
    t.ok(got and got[0][1] == "done",
         "a check is not timed out for the seconds the run spent frozen", repr(got))

    sleeper = subprocess.Popen([sys.executable, "-c", SLEEPER_SRC])
    try:
        time.sleep(0.5)
        t.ok(polite.freeze([sleeper.pid]) == 1, "freeze reaches the process (nothing is killed)")
        time.sleep(0.5)
        t.ok(sleeper.poll() is None, "a frozen process is still alive")
        t.ok(polite.thaw([sleeper.pid]) == 1 and sleeper.poll() is None,
             "and thaw resumes it")
    finally:
        sleeper.kill()


def run(t):
    if os.name != "nt":
        t.ok(True, "priority classes are Windows-only here; the cloud run uses nice")
        return
    _governor_checks(t)
    box = Path(tempfile.mkdtemp(prefix="qc_polite_"))
    tools = str(F.CODE / "tools")
    pre = "TOOLS = %r\n" % tools

    kid = box / "kid.py"
    kid.write_text(pre + KID, encoding="utf-8")
    tool = box / "tool.py"

    def probe(extra=(), env_extra=None):
        tool.write_text(pre + "KID = %r\nEXTRA = %r\n" % (str(kid), list(extra)) + TOOL,
                        encoding="utf-8")
        env = dict(os.environ)
        env.pop("MICE_POLITE", None)
        env.update(env_extra or {})
        # NORMAL on purpose: this check itself runs polite (inherited), and a tool started
        # with polite OFF must be shown to keep the class it was given, not the parent's
        r = subprocess.run([sys.executable, str(tool)], capture_output=True, text=True,
                           timeout=60, env=env, creationflags=0x20)
        line = [l for l in r.stdout.splitlines() if l.startswith("RESULT")]
        parts = line[0].split() if line else []
        got = [int(x) for x in parts[1:4]] if len(parts) >= 5 else []
        return r, got + [parts[4]] if got else []

    # NOTE the whole QC run is itself inside the polite job, which forces BELOW_NORMAL on every
    # process in it; so "keeps Normal" is shown by what the tool DID (it left its class alone
    # and said so), and the polite case by the class the tool and its grandchild end up with.
    r, got = probe()
    t.ok(len(got) == 4 and got[1] == BELOW and got[2] == BELOW and "cpu" in got[3],
         "a polite tool and the grandchild it starts are BelowNormal",
         repr((r.stdout[-200:], r.stderr[-300:])))
    for label, kw in (("MICE_POLITE=0", {"env_extra": {"MICE_POLITE": "0"}}),
                      ("--exact-timing", {"extra": ["--exact-timing"]})):
        r, got = probe(**kw)
        t.ok(len(got) == 4 and got[0] == got[1] and got[3] == "normal"
             and "NORMAL priority" in r.stdout,
             "%s leaves the priority alone and the tool says it runs at normal priority" % label,
             repr((r.stdout[-200:], r.stderr[-200:])))

    # the polite job: a process launched through PowerShell (detached from its parent, the way
    # QC starts Edge) is lowered too
    out = box / "cls.txt"
    wk = box / "write_kid.py"
    wk.write_text(pre + "OUT = %r\n" % str(out) + WRITE_KID, encoding="utf-8")
    runner = box / "runner.py"
    runner.write_text("LIB = %r\nKID_PY = %r\n" % (str(F.QC / "lib"), str(wk)) + PS_RUNNER,
                      encoding="utf-8")
    pr = subprocess.run([sys.executable, str(runner)], capture_output=True, text=True, timeout=90)
    got = out.read_text(encoding="utf-8").strip() if out.exists() else ""
    t.ok(got == str(BELOW), "a process launched through PowerShell inside the polite job is BelowNormal",
         repr((got, pr.stderr[-300:])))

    # the job carries a CPU cap and a memory limit, and the cap can be changed while it runs
    job_py = box / "job.py"
    job_py.write_text(("LIB = %r" % str(F.QC / "lib")) + chr(10) + JOB_SRC, encoding="utf-8")
    jr = subprocess.run([sys.executable, str(job_py)], capture_output=True, text=True, timeout=60)
    t.ok(jr.stdout.split() == ["True", "True", "True", "True"],
         "the job object takes a CPU cap and a memory limit, the cap can be changed live, "
         "and it lists its processes", repr((jr.stdout, jr.stderr[-200:])))

    # never applied to the real services
    for name in ("main_python/main.py", "apps/voice/service.py", "apps/faces/service.py"):
        p = F.CODE / name
        if p.is_file():
            src = p.read_text(encoding="utf-8", errors="replace")
            t.ok("import polite" not in src and "polite.apply" not in src,
                 "%s is never made polite" % name)
