"""Every camera board entry is wired sanely for its chip, and the override exists.

The user asked (2026-11-21) for the camera firmware to work on every board,
ESP32-S3 included, chosen automatically or by hand. A pin map that reuses a GPIO
(the TTGO T-Journal row listed GPIO 36 twice until today), or uses a flash/PSRAM
line of its chip, is a camera that initialises and returns noise or a board that
resets. This check holds the data to the rules in gen_tables.CAM_CHIP_RULES,
proves the generator refuses each kind of mistake with a message that names it,
that each chip only compiles its own rows, and that CAM BOARD is wired in.

Tested against the generator and the source text only. No board was tried: the
S3 and WROVER pin maps come from vendor tables (lab list: camera boards).
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "camera boards: pins valid per chip, the right rows per build, CAM BOARD override"


def _gen(box, d):
    tmp = box / "cam_boards.json"
    tmp.write_text(json.dumps(d), encoding="utf-8")
    r = subprocess.run(
        [sys.executable, "-c",
         "import sys;sys.path.insert(0,%r);import gen_tables as g;"
         "from pathlib import Path;g.CAM_BOARDS_JSON=Path(%r);"
         "g.gen_cam_boards(Path(%r), ('cam',))"
         % (str(F.FIRMWARE / "tools"), str(tmp), str(box))],
        capture_output=True, text=True, timeout=90)
    return r.returncode, (r.stdout or "") + (r.stderr or "")


def run(t):
    sys.path.insert(0, str(F.FIRMWARE / "tools"))
    import re
    raw = (F.FIRMWARE / "config" / "cam_boards.json").read_text(encoding="utf-8")
    data = json.loads(re.sub(r"^\s*//.*$", "", raw, flags=re.M))
    boards = data["boards"]

    chips = {b.get("chip", "esp32") for b in boards.values()}
    t.ok(chips == {"esp32", "esp32s3"}, "both chip families have boards",
         "found %s" % sorted(chips))
    t.ok(sum(1 for b in boards.values() if b.get("chip") == "esp32s3") >= 4,
         "at least four ESP32-S3 camera boards", "")

    # Every shipped entry passes the generator's own rules (duplicates, reserved).
    with tempfile.TemporaryDirectory(prefix="qc_camdata_") as d:
        box = Path(d)
        rc, out = _gen(box, data)
        t.ok(rc == 0, "the generator accepts every board in the file", out[-300:])

        first_s3 = next(k for k, b in boards.items() if b.get("chip") == "esp32s3")
        first_c = next(k for k, b in boards.items() if b.get("chip", "esp32") == "esp32")
        cases = (
            ("a GPIO used twice", first_c,
             lambda b: b["pins"].update({"y8": b["pins"]["y9"]}), "both"),
            ("a flash line used by an S3 board", first_s3,
             lambda b: b["pins"].update({"xclk": 30}), "flash"),
            ("an input-only pin as XCLK on a classic chip", first_c,
             lambda b: b["pins"].update({"xclk": 34}), "input-only"),
            ("an unknown chip", first_c,
             lambda b: b.update({"chip": "esp8266"}), "chip"),
        )
        for what, key, breakit, says in cases:
            d2 = json.loads(json.dumps(data))
            breakit(d2["boards"][key])
            rc, out = _gen(box, d2)
            t.ok(rc != 0 and says in out and "Traceback" not in out,
                 "the generator refuses %s and says why" % what, out[-250:])

        # Each chip compiles only its own rows.
        rc, out = _gen(box, data)
        hdr = (box / "modules" / "cam" / "CamBoards.h").read_text(encoding="utf-8")
        s3part, classic = hdr.split("#else")
        t.ok(all(k in s3part for k, b in boards.items() if b.get("chip") == "esp32s3")
             and not any('"%s"' % k in s3part for k, b in boards.items()
                         if b.get("chip", "esp32") == "esp32"),
             "the S3 build holds only S3 rows", "")
        t.ok(all('"%s"' % k in classic for k, b in boards.items()
                 if b.get("chip", "esp32") == "esp32")
             and not any('"%s"' % k in classic for k, b in boards.items()
                         if b.get("chip") == "esp32s3"),
             "the classic build holds only classic rows", "")

    # Selectable by hand as well as automatic.
    src = (F.FIRMWARE / "src" / "modules" / "cam" / "CamModule.cpp").read_text(encoding="utf-8")
    t.contains(src, 'sub == "BOARD"', "CAM BOARD is a command")
    t.contains(src, 'p.putString("board"', "and the choice is kept in NVS")
    t.contains(src, "camTryOrder(", "and boot tries the chosen board first")
    cmds = (F.FIRMWARE / "config" / "commands.json").read_text(encoding="utf-8")
    t.contains(cmds, "BOARD", "the command table documents it")
    ini = (F.FIRMWARE / "platformio.ini").read_text(encoding="utf-8")
    t.contains(ini, "[env:mice_cam_s3]", "there is a build for ESP32-S3 cameras")
