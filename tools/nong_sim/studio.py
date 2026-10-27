"""What the simulator takes from Nong Studio and the firmware, read from THEIR files.

The sim must move exactly like Studio and time moves exactly like the board,
so it never keeps its own copy of a joint sense, a body size or a speed floor:
each number below is read from the file that owns it. A rename there fails
here loudly instead of the sim quietly drifting from the robot.
"""
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
STUDIO = ROOT / "nong" / "main_python_set_nong"
PARTS = STUDIO / "web" / "app_parts"
FW_CONFIG = ROOT / "firmware" / "config" / "esp32_hardware_nong_module.h"


def _read(path):
    return path.read_text(encoding="utf-8")


def js_value(file, name):
    """`const NAME = <number or [list]>` (or `let`) from one Studio part."""
    text = _read(PARTS / file)
    m = re.search(r"\b(?:const|let)\s+(?:[A-Z_]+\s*=\s*[^,;]+,\s*)*" + name + r"\s*=\s*(\[[^\]]*\]|[-\d.]+)", text)
    if not m:
        raise KeyError(f"{name} not found in {file}")
    return json.loads(re.sub(r"(?<![\w.])\+(?=\d)", "", m.group(1)))   # JS allows +1


def fw_define(name):
    m = re.search(r"#define\s+" + name + r"\s+([-\d.]+)f?", _read(FW_CONFIG))
    if not m:
        raise KeyError(f"{name} not found in {FW_CONFIG.name}")
    return float(m.group(1))


class StudioFacts:
    """The constants Studio's kinematics, collision check and timing use."""

    def __init__(self):
        self.joint_names = js_value("rig_data.js", "JOINT_NAMES")
        self.base_dir = js_value("rig_data.js", "BASE_DIR")
        self.clear_mm = js_value("collisions.js", "CLEAR")
        self.wrist_r = js_value("collisions.js", "R_WRIST")
        self.head_r = js_value("collisions.js", "R_HEAD")
        self.min_move_ms = fw_define("NONG_MIN_MOVE_MS")
        self.safe_dps = fw_define("NONG_SAFE_DPS")
        self.max_dps = fw_define("NONG_MAX_SPEED_DPS")


# What Studio's mergeRig() fills when a rig file leaves it out (rig_data.js):
# all of them change nothing, so a rig saved before A48-6 moves as it did.
RIG_FILL = {
    "after": [[0, 0, 0]] * 10,
    "mount": {"L": [0, 0, 0], "R": [0, 0, 0]},
    "order": [[0, 1, 2, 3], [4, 5, 6, 7]],
    "tilt": [[0, 0, 0]] * 10,
    "shrugCurve": [],
    "extraClearanceMm": 0,
}


def load_rig(path=None):
    """A rig as Studio holds it. Takes the shipped rig_default.json, a rig the
    Studio saved, or a whole Studio settings backup ({"rig": {...}}); a part
    missing from the file comes from rig_default.json, then RIG_FILL."""
    base = json.loads(_read(STUDIO / "rig_default.json"))
    rig = dict(base)
    if path:
        given = json.loads(Path(path).read_text(encoding="utf-8"))
        rig.update(given.get("rig", given))
    for key, value in RIG_FILL.items():
        rig.setdefault(key, json.loads(json.dumps(value)))
    rig["dims"] = {**base["dims"], **rig.get("dims", {})}
    return rig
