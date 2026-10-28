"""Execute the actual Lift class/header/motion/config methods with fake clock and IO."""
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import sys

import qc as F
sys.path.insert(0, str(F.QC / "checks"))
from check_gacha_motion import _block

AREA = "firmware"
TITLE = "Lift motion always has a deadline and a fault cannot resume a sequence"


def run(t):
    cpp = (F.FIRMWARE / "src/modules/lift/LiftModule.cpp").read_text(encoding="utf-8")
    header = (F.FIRMWARE / "src/modules/lift/LiftModule.h").read_text(encoding="utf-8")
    header = re.sub(r"^#(?:include|pragma).*\n", "", header, flags=re.M)
    methods = "\n\n".join(_block(cpp, marker, whole=True) for marker in (
        "void LiftModule::applySettings(", "float LiftModule::cpm(", "float LiftModule::maxMms(",
        "float LiftModule::estMms(", "int LiftModule::travelPwm(", "float LiftModule::posMm(",
        "void LiftModule::deriveGeometry(", "long LiftModule::counts(", "int LiftModule::currentStage(",
        "const char* LiftModule::stateName(", "bool LiftModule::busy(", "void LiftModule::stopMotor(",
        "void LiftModule::startGoto(", "bool LiftModule::limitsValid(", "void LiftModule::startMotion(",
        "void LiftModule::latchFault(", "bool LiftModule::motionReady(",
        "bool LiftModule::handleMotionCommand(", "bool LiftModule::handleCommand(",
        "void LiftModule::updateMotion("))
    config = (F.FIRMWARE / "src/core/ConfigStore.cpp").read_text(encoding="utf-8")
    mapping = config[config.index("struct KeyMap"):config.index("String ConfigStore::keys")]
    config_header = (F.FIRMWARE / "src/core/ConfigStore.h").read_text(encoding="utf-8")
    config_header = re.sub(r"^#(?:include|pragma).*\n", "", config_header, flags=re.M)
    config_methods = _block(config, "bool ConfigStore::set(const String& key, float value, String* why)", whole=True)
    code = (F.QC / "data/lift_motion.cpp").read_text(encoding="utf-8").replace(
        "/*__HEADER__*/", header + "\n" + config_header).replace("/*__METHODS__*/", methods + "\n" + mapping + config_methods)
    cxx = shutil.which("g++") or shutil.which("clang++")
    if not t.ok(bool(cxx), "host C++ compiler exists; Lift motion proof cannot be skipped"):
        return
    with tempfile.TemporaryDirectory(prefix="mice_lift_motion_") as folder:
        src, exe = Path(folder) / "lift.cpp", Path(folder) / "lift.exe"
        src.write_bytes(code.encode("utf-8"))
        built = subprocess.run([cxx, "-std=c++17", "-Wall", "-Wextra", "-Werror",
                                "-I", str(F.FIRMWARE / "config"), str(src), "-o", str(exe)],
                               capture_output=True, text=True, timeout=90)
        if not t.eq(built.returncode, 0, "actual Lift header/methods compile against fake IO"):
            t.ok(False, "native compiler diagnostic", built.stderr[-3000:])
            return
        ran = subprocess.run([str(exe)], capture_output=True, text=True, timeout=15)
    for line in ran.stdout.splitlines():
        if line.startswith(("CPP_PASS ", "CPP_FAIL ")):
            t.ok(line.startswith("CPP_PASS "), line[9:])
    t.eq(ran.returncode, 0, "executed actual Lift methods finish without failure")
    t.ok(ran.stdout.count("CPP_PASS ") >= 35, "all native motion scenarios ran", ran.stdout[-1000:])
    # Contract prevents a waiting sequence from interpreting fault as arrival.
    commands = (F.FIRMWARE / "config/commands.json").read_text(encoding="utf-8")
    t.ok(re.search(r'"name": "FAULT",[^\n]*"scope": "lift"[^\n]*"motion": true', commands),
         "FAULT CLEAR preempts the waiting sequence through the shared command registry")
    t.contains(cpp, 'o["fault"]', "status exposes the latched fault")
    t.contains(cpp, 'o["motion_timeout_ms"]', "status exposes the snapshotted active phase timeout")
