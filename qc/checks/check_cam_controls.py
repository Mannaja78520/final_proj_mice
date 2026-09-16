"""Every camera setting is one entry in a registry, and none of them can panic.

Asked for 2026-08-21: *make the esp32 cam can setting all everything we can
setup ... or can check to be auto like default*. The sensor has two dozen
controls; the firmware exposed four. They live in config/cam_controls.json now
and gen_tables.py writes both the table a person sees and the switch that
applies it, so a control cannot appear on a page the firmware has no way to
apply.

THE ONE THAT WOULD HAVE CRASHED BOARDS
--------------------------------------
`sensor_t` is a struct of function pointers filled in per sensor, and a part
that does not implement a control leaves its pointer NULL. Calling it does not
return an error - it panics the board with LoadProhibited. Four setters were
already being called unchecked; exposing twenty-four from data would have made
that a certainty. Measured on the real OV2640 the same day: `sharpness` is
exactly such a control, and it now answers *this sensor has no sharpness*.

THE ONE THE USER ACTUALLY REPORTED
----------------------------------
*it fix only 1 size*. The size was changing all along - what came back was the
picture from BEFORE the change. With one frame buffer and GRAB_LATEST the next
capture hands back the frame already in flight, so a SNAP straight after
switching to qqvga returned 15,007 bytes (a real qqvga frame is about 1,700)
and vga returned 2,127. Two frames are dropped after a size change now, and
the captures scale the way they should: 1.7k / 4.1k / 10.5k / 15k.
"""
import importlib.util
import json
import re
import tempfile
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "every camera setting is one registry entry, and an unsupported one cannot crash the board"
SLOW = False

GEN = F.FIRMWARE / "tools" / "gen_tables.py"
HEADER = F.FIRMWARE / "generated" / "modules" / "cam" / "CamControls.h"
SRC = F.FIRMWARE / "src" / "modules" / "cam" / "CamModule.cpp"
JSON_SRC = F.FIRMWARE / "config" / "cam_controls.json"


def _controls(text):
    """name -> (kind, lo, hi, def) as the generated header declares it."""
    out = {}
    for m in re.finditer(
            r'\{\s*"(\w+)",\s*"[^"]*",\s*"(\w+)",\s*(-?\d+),\s*(-?\d+),\s*(-?\d+),',
            text):
        out[m.group(1)] = (m.group(2), int(m.group(3)), int(m.group(4)),
                           int(m.group(5)))
    return out


def run(t):
    head = HEADER.read_text(encoding="utf-8", errors="replace")
    src = SRC.read_text(encoding="utf-8", errors="replace")
    table = _controls(head)

    t.ok(len(table) >= 20,
         "the sensor's settings are all declared (%d)" % len(table),
         "four were exposed before; the rest may as well not have existed")
    for want in ("brightness", "contrast", "saturation", "wb_mode", "aec",
                 "agc", "special_effect", "vflip", "hmirror", "quality"):
        t.ok(want in table, "'%s' is one of them" % want)

    # ---- NO SETTER IS CALLED BLIND -----------------------------------
    # The generated switch must guard every pointer. This is the assertion
    # that stands between a data-driven control list and a board that panics
    # on a sensor which does not implement one.
    calls = re.findall(r"return s->set_(\w+)\(s,", head)
    guards = re.findall(r"if \(!s->set_(\w+)\) return false;", head)
    t.eq(sorted(set(calls)), sorted(set(guards)),
         "every generated setter call is guarded by a null check")
    t.ok(len(guards) == len(table),
         "one guard per control (%d guards, %d controls)"
         % (len(guards), len(table)))

    # ...and the four that were already in the boot path go through it too.
    t.ok("s->set_bpc(s," not in src and "s->set_wpc(s," not in src,
         "the boot-time corrections no longer call the sensor directly",
         "these four were the unchecked calls the panel found")
    t.contains(src, 'applyCamControl(s, "bpc"',
               "they apply through the guarded table instead")

    # ---- a size change must not hand back the old picture -------------
    # THE NUMBER, not the loop. `drop < 0` matched a \d+ pattern happily and
    # dropped nothing — caught by sabotage 2026-08-21.
    m = re.search(r"for \(int drop = 0; drop < (\d+); drop\+\+\)", src)
    t.ok(m, "there is a drop loop after a size change")
    t.ok(m and int(m.group(1)) >= 1,
         "and it really drops frames (%s)" % (m.group(1) if m else "none"),
         "without this the next capture is the picture from BEFORE the "
         "change, which is what made changing size look like it did nothing")

    # ---- a setter that needs a cast gets one --------------------------
    # set_gainceiling takes an enum; a bare int there does not misbehave at
    # runtime, it fails to compile — so the whole camera build stops. The
    # cast is declared in the registry, and this is what proves it arrives.
    decl = json.loads(re.sub(r"^\s*//.*$", "", JSON_SRC.read_text(encoding="utf-8"),
                             flags=re.M))["controls"]
    for name, c in sorted(decl.items()):
        if not c.get("cast"):
            continue
        t.contains(head, "s->set_%s(s, (%s)v)" % (c["setter"], c["cast"]),
                   "%s is cast to %s in the generated call" % (name, c["cast"]))

    # ...and the one the API really requires. Checking only the controls that
    # DECLARE a cast proves nothing when the declaration is what went missing:
    # dropping it made this check pass and the firmware stop compiling.
    # esp_camera's set_gainceiling takes gainceiling_t, not int.
    t.eq((decl.get("gainceiling") or {}).get("cast"), "gainceiling_t",
         "gainceiling still declares the enum cast its setter needs")

    # ---- the command surface -----------------------------------------
    for verb in ("LIST", "SET", "AUTO"):
        t.contains(src, '"%s"' % verb, "CAM %s exists" % verb)
    t.contains((F.FIRMWARE / "COMMANDS.md").read_text(
        encoding="utf-8", errors="replace"), "CAM LIST",
        "COMMANDS.md documents the new camera controls")

    # ---- the registry refuses nonsense --------------------------------
    # A default outside its own range would be written into every board by
    # CAM AUTO, and a choice list that does not match its range would put a
    # name against the wrong value on the page.
    for name, (kind, lo, hi, dflt) in sorted(table.items()):
        t.ok(lo <= dflt <= hi,
             "%s has a default inside its range" % name,
             "%d is outside %d..%d" % (dflt, lo, hi))

    # ---- ADDING ONE COSTS ONE FILE ------------------------------------
    # AGAINST A COPY, NEVER THE REAL REGISTRY. Editing the shipped json and
    # putting it back is fine alone and wrong in the suite: the run is
    # parallel, and while this check held a deliberately broken registry the
    # other checks called gen_tables and crashed on it — `camera control
    # 'brightness': default 9 is outside -2..2`, reported against
    # check_design_system, which had touched nothing. Found 2026-08-21.
    original = JSON_SRC.read_text(encoding="utf-8")

    def generate(text):
        """Run the real generator over `text`. -> (controls, error or None)."""
        box = Path(tempfile.mkdtemp(prefix="qc_camctl_"))
        cfg = box / "cam_controls.json"
        cfg.write_bytes(text.encode("utf-8"))     # write_bytes: never CRLF
        spec = importlib.util.spec_from_file_location("qc_gen_tables", GEN)
        mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(mod)
        mod.CAM_CONTROLS_JSON = cfg               # the copy, not the shipped one
        out = box / "out"
        try:
            mod.gen_camcontrols(out, ("cam",))
        except SystemExit as e:
            return {}, str(e)
        made = out / "modules" / "cam" / "CamControls.h"
        return (_controls(made.read_text(encoding="utf-8")) if made.is_file()
                else {}), None

    added = original.replace(
        '"colorbar":', '"qcnewcontrol": {"setter": "colorbar", "kind": "toggle",'
        ' "lo": 0, "hi": 1, "def": 0, "label": "QC"},\n    "colorbar":', 1)
    if t.ok(added != original, "the registry could be extended for this test",
            "the anchor moved; this check would prove nothing"):
        grown, err = generate(added)
        t.ok("qcnewcontrol" in grown,
             "a control added to the registry appears with NO C++ change",
             "generator said: %s" % err)

    # ---- and refuses a default it cannot honour -----------------------
    bad = original.replace(
        '"kind": "range",  "lo": -2, "hi": 2, "def": 0,\n                    "label": "Brightness"',
        '"kind": "range",  "lo": -2, "hi": 2, "def": 9,\n                    "label": "Brightness"', 1)
    if t.ok(bad != original,
            "the registry could be given a bad default for this test"):
        _, err = generate(bad)
        t.ok(err is not None,
             "a default outside its own range is refused by the generator",
             "CAM AUTO would otherwise write it into every board")
        t.ok(err is None or "brightness" in err,
             "and the refusal names the control", err or "")
