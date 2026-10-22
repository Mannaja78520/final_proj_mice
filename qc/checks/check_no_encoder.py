"""The gachapon and the lift are built without an encoder.

A47-12, user 2026-10-22 20:15Z: "no encoder, the lift has no encoder either".
A47-11 had added an optional encoder to mice_gacha from a CAD reading (the
Namiki motor's catalogue part has one) - it was taken out again, so the hall
and its magnets alone decide where the gachapon stops. The lift keeps its
encoder code for a lift that gets one later ("CFG encoder 1"), but starts
with it OFF, so it trusts only its limit switches.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "the gachapon and the lift start without an encoder"


def run(t):
    cfg = F.FIRMWARE / "config"
    lift = (cfg / "esp32_hardware_lift_module.h").read_text(encoding="utf-8")
    m = re.search(r"#define\s+LIFT_HAS_ENCODER\s+(\d+)", lift)
    t.ok(m and m.group(1) == "0", "the lift starts with no encoder",
         m.group(0) if m else "LIFT_HAS_ENCODER not found")
    gacha = [cfg / "esp32_hardware_gacha_module.h"]
    gacha += sorted((F.FIRMWARE / "src" / "modules" / "gacha").glob("*"))
    hits = [p.name for p in gacha if re.search(r"(?i)encoder|\benc_?[ab]\b|ENC_A",
                                               p.read_text(encoding="utf-8"))]
    t.ok(not hits, "the gachapon firmware has no encoder code", hits)
