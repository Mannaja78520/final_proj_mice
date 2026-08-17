"""The firmware must COMPILE, and its logic must be right — not just look right.

Every other firmware check in this suite reads source text. That catches a
missing call or an undocumented command, but a change that compiles into the
wrong behaviour still passes them all. This one builds the real binary and runs
the real logic.

Slow (a clean build is ~70 s), so it is skipped by --quick. Run it before
flashing anything.
"""
import os
import re
import subprocess
import time
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "firmware builds, and its logic is correct"
SLOW = True

# pio is not on PATH — it lives in PlatformIO's own venv
PIO = Path(os.environ.get("USERPROFILE", "")) / ".platformio/penv/Scripts/pio.exe"
# The build a real board runs. Since the per-type split there is one env per
# module type; this is the one on the bench. check_build_split.py builds the
# others and proves each carries only its own type.
ENV = "mice_nong"
FLASH_CEILING = 90.0     # % — a change must not quietly fill the chip


def _run(args, cwd, timeout=900):
    r = subprocess.run(args, cwd=str(cwd), capture_output=True, text=True,
                       timeout=timeout)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run(t):
    if not PIO.is_file():
        t.give_up("PlatformIO not found at %s — install it or skip this check" % PIO)

    # ---- 1. the real firmware compiles ------------------------------
    t0 = time.time()
    code, out = _run([str(PIO), "run", "-e", ENV], F.FIRMWARE)
    took = time.time() - t0
    if not t.ok(code == 0, "the firmware compiles (%s)" % ENV,
                _first_error(out)):
        return                      # nothing below is meaningful if it won't build
    print("      (build took %.0fs)" % took)

    # ---- 2. it still fits, with room to grow ------------------------
    m = re.search(r"Flash:\s*\[[^\]]*\]\s*([\d.]+)%", out)
    if t.ok(m, "the build reports flash usage"):
        used = float(m.group(1))
        t.under(used, FLASH_CEILING, "flash usage leaves room to grow", "%")
        print("      (flash %.1f%%)" % used)

    # ---- 3. one env per module type ---------------------------------
    ini = (F.FIRMWARE / "platformio.ini").read_text(encoding="utf-8", errors="replace")
    for env in ("mice_nong", "mice_lift", "mice_blank"):
        t.contains(ini, "[env:%s]" % env, "platformio.ini defines %s" % env)
    t.ok("[env:lift_module]" not in ini,
         "the first env name (lift_module) is gone")
    # The generated tables and page no longer live in src/: they are written
    # per env, because two envs would otherwise overwrite each other's.
    for stale in ("src/core/CommandHelp.h", "src/modules/nong/ServoPresets.h"):
        t.ok(not (F.FIRMWARE / stale).exists(),
             "%s is not left behind in src/" % stale,
             "a stale copy in src/ shadows the per-type header on the include "
             "path, so the build would silently carry every type again")
    t.ok(F.generated("core/CommandHelp.h").is_file(),
         "the generator still writes an all-types tree for the tools to read")

    # ---- 4. the LOGIC runs, on this PC, with no board ---------------
    # The part source-reading cannot do: the gear/travel maths and the
    # move-time floor are EXECUTED and asserted.
    t.ok((F.FIRMWARE / "test" / "test_logic" / "test_main.cpp").is_file(),
         "the native logic tests are present in the repo")

    if not _host_compiler():
        # Do not pretend. PlatformIO ships only the xtensa cross-compiler, which
        # builds for the ESP32 and cannot run here, so these tests are written
        # and committed but cannot execute on this machine.
        print("      \033[33mNOTE: no host C++ compiler (g++/clang) on PATH, so the\033[0m")
        print("      \033[33mnative logic tests could not RUN here. They are in the repo\033[0m")
        print("      \033[33mand run anywhere that has one. Install MSYS2/MinGW-w64 or\033[0m")
        print("      \033[33mVS Build Tools to enable them, then re-run this check.\033[0m")
        return

    code, out = _run([str(PIO), "test", "-e", "native", "--without-uploading"],
                     F.FIRMWARE)
    # PlatformIO prints one "…test_name\t[PASSED]" line per test
    passed = len(re.findall(r"\[PASSED\]", out)) - len(
        re.findall(r"^-+ native:.*\[PASSED\]", out, re.M))   # minus the suite line
    if t.ok(code == 0, "the native logic tests pass", _first_error(out)):
        t.ok(passed >= 8, "and there are enough of them (%d ran)" % passed,
             "expected at least 8 native tests to run")
        print("      (%d native tests ran on this PC)" % passed)


def _host_compiler():
    """A compiler that produces binaries THIS machine can run."""
    import shutil
    return any(shutil.which(c) for c in ("g++", "gcc", "clang++", "clang", "cl"))


def _first_error(out):
    """The first line that actually says what went wrong — build logs are long."""
    for line in out.splitlines():
        low = line.lower()
        if "error:" in low or "fatal" in low or line.startswith("*** "):
            return line.strip()[:300]
    tail = [l for l in out.strip().splitlines() if l.strip()][-3:]
    return " / ".join(x.strip()[:120] for x in tail)
