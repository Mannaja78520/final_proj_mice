"""Adding a per-joint field reaches every place that reports it.

Ten numbers describe a joint, and three places used to write them out as text:
the YAML calibration file, the LIMIT? reply, and the status JSON. Each spelled
out every field by hand, so adding one meant editing all three - and forgetting
one was SILENT. The field would save, load and drive the servo perfectly while
being absent from one API, so Nong Studio or the hub would show a stale value
with nothing on screen to explain it.

The fields are now one table in NongModule.h, built once at boot, and the YAML
export and the status JSON are generated from it. Writing that table proved the
point immediately: the first version listed ten fields and missed `frame_hz`,
in an array sized exactly ten, so there was no room left to notice.

Two things deliberately left alone, because a table would cost more than it
saves:

  * the binary calibration blob. It is a fixed struct whose layout is guarded by
    CAL_VERSION and checked by the compiler, field by field;
  * the LIMIT? reply, which is an older contract with its own key names (`min`,
    `max`) and its own subset. Forcing it through the table would either rename
    keys that Studio and the hub already read, or need a mapping as long as the
    code it replaced.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "one table of per-joint fields, and the serialisers follow it"

NONG_H = "src/modules/nong/NongModule.h"
NONG_C = "src/modules/nong/NongModule.cpp"


def run(t):
    hdr = (F.FIRMWARE / NONG_H).read_text(encoding="utf-8")
    src = (F.FIRMWARE / NONG_C).read_text(encoding="utf-8")

    # ---- the table exists and covers what the robot has -------------
    t.contains(hdr, "struct JointField",
               "there is one description of a per-joint field")
    rows = re.findall(r'fields_\[n\+\+\] = \{ "(\w+)"', src)
    t.ok(len(rows) >= 11,
         "every per-joint field is in the table (%d)" % len(rows),
         "found %s" % rows)
    for want in ("joint_min", "joint_max", "trim", "neutral", "gear_pinion",
                 "gear_gear", "pulse_min", "pulse_max", "max_dps",
                 "servo_range", "frame_hz"):
        t.ok(want in rows, "%s is in the table" % want,
             "a field missing here is missing from every API built from it")

    # The array must have room to grow. The first version was sized exactly to
    # the fields it listed and frame_hz was missed - the very mistake the table
    # exists to prevent, hidden by an array with no spare room.
    m = re.search(r"JointField fields_\[(\d+)\]", hdr)
    if t.ok(m, "the table has a size"):
        t.ok(int(m.group(1)) > len(rows),
             "with room for the next field (%s slots, %d used)"
             % (m.group(1), len(rows)),
             "sized exactly to today's list, the next field overruns it")

    # ---- the serialisers are generated, not written out -------------
    ycode = src[src.find("String y = "):src.find("saveText(")]
    t.contains(ycode, "fieldCount_",
               "the YAML export walks the table")
    t.ok("gear_pinion" not in ycode,
         "and does not name the fields again",
         "eleven hand-written blocks is exactly what this replaced: %s"
         % re.findall(r'"(\w+): \["', ycode))

    jcode = src[src.find("Per-joint servo + gear, from the ONE table"):]
    jcode = jcode[:jcode.find('o["moving"]')]
    t.contains(jcode, "fieldCount_",
               "the status JSON walks the table too")
    t.ok("gearPinion_[i]" not in jcode,
         "and does not read the arrays field by field",
         "seven hand-declared JsonArrays is what this replaced")

    # ---- one place decides how a number is written ------------------
    # The three serialisers each chose their own decimals, so the same trim
    # read 1.5 in the YAML and 2 in the JSON.
    t.contains(src, "String NongModule::fieldText",
               "one function turns a field into text")
    ft = src[src.find("String NongModule::fieldText"):]
    ft = ft[:ft.find("\n}") + 2]
    t.contains(ft, "d.decimals",
               "using the decimals the table declares")

    # ---- and what was left alone is still whole ---------------------
    # The binary blob is a fixed struct: every field must still be copied both
    # ways, or calibration is silently lost on the next boot.
    save = src[src.find("void NongModule::saveCal"):]
    save = save[:save.find("void NongModule::loadCal")]
    load = src[src.find("bool NongModule::loadCalNvs"):]
    load = load[:load.find("\n}\n") + 3] if "loadCalNvs" in src else ""
    for field in ("gearPinion", "pulseMin", "frameHz", "servoRange"):
        t.ok(field in save or field in src,
             "%s is still written to the calibration blob" % field)
