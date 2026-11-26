"""Any AI turns the PC assistant's keep-running check on by itself, once, and never against the user's stop.

User 2026-11-27: whichever AI starts a task runs `python tools/pc_assistant_ensure.py` (no double-click); after a
restart the user's first message means "continue" and the AI runs it again; nothing starts by itself at logon;
"Stop PC Assistant" must hold. Everything here uses a throwaway task name, a throwaway root and a harmless script.
"""
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "tooling"
TITLE = "the ensure step turns the check on once, respects Stop, never adds a logon trigger; AIs are told to run it"


def run(t):
    if os.name != "nt":
        t.ok(True, "the keep-running check is a Windows Scheduled Task")
        return
    box = Path(tempfile.mkdtemp(prefix="qc_ensure_"))
    root = box / "root"
    (root / ".local").mkdir(parents=True)
    dummy = box / "dummy.ps1"
    dummy.write_text("Set-Content -Path '%s' -Value ok" % str(box / "ran.txt").replace("'", "''"), encoding="utf-8")
    name = "MiceEnsureQC%d" % os.getpid()
    py = [sys.executable, str(F.CODE / "tools" / "pc_assistant_ensure.py"), "--root", str(root),
          "--task-name", name, "--script", str(dummy)]

    def ensure(*extra):
        r = subprocess.run(py + list(extra), capture_output=True, text=True, timeout=120)
        return r.returncode, r.stdout.strip()

    def triggers():
        r = subprocess.run(["powershell", "-NoProfile", "-Command",
                            "(Get-ScheduledTask -TaskName '%s' -ErrorAction SilentlyContinue).Triggers | "
                            "ForEach-Object { $_.CimClass.CimClassName }" % name],
                           capture_output=True, text=True, timeout=60)
        return r.stdout.split()

    uninst = F.CODE / "tools" / "rc_watchdog_uninstall.ps1"
    try:
        rc, out = ensure("--status")
        t.ok("off" in out, "before: the check is off", out)
        rc, out = ensure()
        t.ok(rc == 0 and "Turned on" in out, "the first run turns it on", out)
        kinds = triggers()
        t.ok(kinds and not any("Logon" in k for k in kinds),
             "and registers NO logon trigger (nothing starts by itself at logon)", repr(kinds))
        rc, out = ensure()
        t.ok(rc == 0 and "already on" in out, "the second run changes nothing: idempotent", out)
        rc, out = ensure("--status")
        t.ok("on" in out and "off" not in out, "status says on", out)

        # the user pressed Stop: no AI may turn it on again
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(uninst),
                        "-TaskName", name], capture_output=True, text=True, timeout=60)
        rc, out = ensure("--off")
        t.ok(rc == 0 and (root / ".local" / "pc_assistant_off.json").exists(), "Stop writes the off flag", out)
        rc, out = ensure()
        t.ok("turned off by the user" in out and not triggers(),
             "while the flag is there an AI's ensure step does NOT install it", out)
        rc, out = ensure("--on")
        rc, out = ensure()
        t.ok("Turned on" in out, "Start clears the flag and the next ensure installs it", out)
    finally:
        subprocess.run(["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(uninst),
                        "-TaskName", name], capture_output=True, text=True, timeout=60)
    t.ok(not triggers(), "the throwaway task is gone again")

    # the AIs are told, and the launchers say it in plain words
    hint = subprocess.run([sys.executable, str(F.CODE / "tools" / "resume_hint.py")], capture_output=True,
                          text=True, timeout=60, encoding="utf-8", errors="replace").stdout
    t.ok("pc_assistant_ensure.py" in hint and "FIRST message" in hint,
         "a new session is told to run the ensure step and that the first message after a restart means continue", hint[:120])
    handoff = (F.CODE / "HANDOFF.md").read_text(encoding="utf-8")
    t.ok("pc_assistant_ensure.py" in handoff, "HANDOFF.md carries the rule for every AI")
    mem = list((F.CODE / "handoff" / "memory").glob("pc-assistant-ensure*.md"))
    t.ok(mem, "and it is in the shared memory")
    import json
    import re
    text = (F.CODE / "config" / "ai_watch.json").read_text(encoding="utf-8")
    prompts = json.loads(text)["prompts"]
    t.ok(all("pc_assistant_ensure" in prompts[k] for k in ("handoff", "resume", "handoff_round")),
         "Codex and Gemini are told in their task-start text")
    ldir = F.CODE / "main_python" / "launchers"
    start = (ldir / "Start PC Assistant.bat").read_text(encoding="utf-8")
    stop = (ldir / "Stop PC Assistant.bat").read_text(encoding="utf-8")
    t.ok("just send any message" in start and "--on" in start,
         "Start says in plain words: after a restart just send any message; and clears the off flag")
    t.ok("--off" in stop and "no AI will turn it on again" in stop,
         "Stop writes the off flag and says so in plain words")
