"""Compile actual gacha motion methods against fake IO: deadlines, STOP and defaults."""
import json
from pathlib import Path
import re
import shutil
import subprocess
import tempfile

import qc as F

AREA = "gacha"
TITLE = "gacha motion is bounded, nonblocking and reports missing Hall as a fault"


def _block(source, marker, whole=False):
    """Keep the exact production body; ignore braces inside comments/strings."""
    start = source.index(marker)
    stripped = re.sub(r'"(?:\\.|[^"\\])*"|//[^\n]*|/\*.*?\*/',
                      lambda m: " " * len(m.group()), source, flags=re.S)
    first = stripped.index("{", start)
    depth = 1
    end = first + 1
    while depth:
        depth += (stripped[end] == "{") - (stripped[end] == "}")
        end += 1
    return source[start:end] if whole else source[first + 1:end - 1]


def run(t):
    root = F.CODE
    cpp = (root / "firmware/src/modules/gacha/GachaModule.cpp").read_text(encoding="utf-8")
    methods = "\n\n".join(_block(cpp, "void GachaModule::" + name + "(", whole=True)
                            for name in ("startTurn", "startNudge", "startCenter", "startCalibrate", "startSpan",
                                         "finish", "invalidateReference", "resetDefaults", "loop"))
    for name, marker, args in (
            ("nudge", 'if (cmd == "GNUDGE")', "String argv[], int argc, String& reply"),
            ("calibrate", 'if (cmd == "GCALIB")', "String& reply"),
            ("test", 'if (cmd == "GTEST")', "String argv[], int argc, String& reply"),
            ("spin", 'if (cmd == "GSPIN")', "String argv[], int argc, String& reply"),
            ("home", 'if (cmd == "GHOME")', "String& reply"),
            ("drain", 'if (cmd == "GDRAIN")', "String argv[], int argc, String& reply"),
            ("stop", 'if (cmd == "STOP")', "String& reply"),
            ("config", 'if (cmd == "GCFG")', "String argv[], int argc, String& reply")):
        methods += "\nbool GachaModule::%s(%s) {\n%s\n}\n" % (name, args, _block(cpp, marker))
    template = (root / "qc/data/gacha_motion.cpp").read_text(encoding="utf-8")
    code = template.replace("/*__PRODUCTION_METHODS__*/", methods).replace(
        "/*__CONFIG_REFERENCE_CHECKS__*/", (root / "qc/data/gacha_config.cpp").read_text(encoding="utf-8"))
    cxx = shutil.which("g++") or shutil.which("clang++")
    if not t.ok(bool(cxx), "host C++ compiler is available", "the motion regression must run, not silently skip"):
        return
    with tempfile.TemporaryDirectory(prefix="mice_gacha_motion_") as folder:
        src, exe = Path(folder) / "motion.cpp", Path(folder) / "motion.exe"
        src.write_bytes(code.encode("utf-8"))
        built = subprocess.run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                "-I", str(root / "firmware/config"), "-I", str(root / "firmware/src"),
                                str(src), "-o", str(exe)], capture_output=True, text=True, timeout=90)
        if not t.ok(built.returncode == 0, "actual gacha motion methods compile with fake IO",
                    (built.stderr or built.stdout)[-1600:]):
            return
        ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
    for line in ran.stdout.splitlines():
        if line.startswith(("CPP_PASS ", "CPP_FAIL ")):
            t.ok(line.startswith("CPP_PASS "), line[9:], "actual production C++ failed this invariant")
    t.ok(ran.returncode == 0, "actual gacha motion regression exits cleanly", ran.stderr[-600:])
    t.ok(ran.stdout.count("CPP_PASS ") >= 45, "the full motion harness ran", ran.stdout[-1200:])
    raw = (root / "firmware/config/commands.json").read_text(encoding="utf-8")
    raw = re.sub(r'("(?:\\.|[^"\\])*")|//[^\n]*', lambda m: m.group(1) or "", raw)
    entries = json.loads(raw)["commands"]
    nudge = next((entry for entry in entries if entry["name"] == "GNUDGE"), {})
    t.ok(nudge.get("motion") is True and nudge.get("scope") == "gacha",
         "GNUDGE is a gacha motion in the shared registry", nudge)
    t.contains((root / "firmware/COMMANDS.md").read_text(encoding="utf-8"),
               "GNUDGE", "the command contract documents manual movement")
