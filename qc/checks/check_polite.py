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
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "QC and tools run at below-normal priority, children inherit it, the switch keeps Normal"

BELOW, NORMAL = 0x4000, 0x20

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


def run(t):
    if os.name != "nt":
        t.ok(True, "priority classes are Windows-only here; the cloud run uses nice")
        return
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

    # never applied to the real services
    for name in ("main_python/main.py", "apps/voice/service.py", "apps/faces/service.py"):
        p = F.CODE / name
        if p.is_file():
            src = p.read_text(encoding="utf-8", errors="replace")
            t.ok("import polite" not in src and "polite.apply" not in src,
                 "%s is never made polite" % name)
