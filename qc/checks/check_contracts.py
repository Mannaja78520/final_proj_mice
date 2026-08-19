"""Firmware and Nong Studio must agree. These are source checks — no board,
no browser, milliseconds — and they catch the mistakes that are invisible
until the robot moves wrongly.

Every rule here exists because the two sides drifted apart once.
"""
import re

import qc as F

AREA = "contracts"
TITLE = "firmware <-> studio agreement"
SLOW = False

JOINT_ORDER = ["L_SH_P", "L_SH_R", "L_EL_P", "L_EL_R",
               "R_SH_P", "R_SH_R", "R_EL_P", "R_EL_R", "WAIST", "SHRUG"]


def run(t):
    nong_h = (F.FIRMWARE / "src/modules/nong/NongModule.h").read_text(
        encoding="utf-8", errors="replace")
    nong_c = (F.FIRMWARE / "src/modules/nong/NongModule.cpp").read_text(
        encoding="utf-8", errors="replace")
    app = (F.STUDIO_WEB / "app.js").read_text(encoding="utf-8", errors="replace")
    cmds = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")

    # ---- joint count, one number on both sides ----------------------
    m = re.search(r"static\s+const\s+int\s+N\s*=\s*(\d+)", nong_h)
    t.ok(m, "firmware declares NongModule::N", nong_h[:200])
    if m:
        t.eq(int(m.group(1)), 10, "firmware N = 10 joints")
    # declared together as `const ARMJ = 8, NJ = 10;` — match each on its own
    m = re.search(r"\bNJ\s*=\s*(\d+)", app)
    t.ok(m, "studio declares NJ")
    if m:
        t.eq(int(m.group(1)), 10, "studio NJ = 10 joints")
    m = re.search(r"\bARMJ\s*=\s*(\d+)", app)
    if m:
        t.eq(int(m.group(1)), 8, "studio ARMJ = 8 arm joints (IK/arm-FK)")

    # ---- joint ORDER is the wire format: a swap silently moves the
    # wrong limb, and no test of either side alone would see it -------
    # declared `static const char* JOINT_NAMES[NongModule::N] = {`
    names = re.search(r"JOINT_NAMES\[[^\]]*\]\s*=\s*\{(.*?)\}", nong_c, re.S) or \
        re.search(r"JOINT_NAMES\[[^\]]*\]\s*=\s*\{(.*?)\}", nong_h, re.S)
    if t.ok(names, "firmware has JOINT_NAMES"):
        got = re.findall(r'"([A-Z_]+)"', names.group(1))
        t.eq(got, JOINT_ORDER, "firmware joint order")
    for i, n in enumerate(JOINT_ORDER):
        if not t.contains(app, n, "studio knows joint %s" % n):
            break

    # ---- the move-time floor: the SAME formula must live on both
    # sides or the editor promises moves the servos cannot do --------
    t.contains(nong_c, "minDuration", "firmware has the per-joint time floor")
    t.contains(app, "function minTime", "studio has the per-joint time floor")
    fw_min = re.search(r"MIN_MOVE_MS\s*[=:]?\s*(\d+)", nong_h + nong_c)
    js_min = re.search(r"MIN_MOVE_MS\s*=\s*(\d+)", app)
    if fw_min and js_min:
        t.eq(js_min.group(1), fw_min.group(1), "same minimum move time both sides")

    # ---- every command Studio sends must exist in the firmware ------
    # Studio calling something the firmware does not implement fails
    # silently at runtime (the reply is just an error string).
    # EVERY sender, not three of them. `cableCmd` is what Studio actually uses
    # over a cable (10 call sites) and it was missing from this pattern, so
    # this loop found exactly 3 commands — LIMIT?, MOVE, SETZERO — out of about
    # thirty, and ran three times while looking like full coverage.
    SENDERS = r'(?:rawCmd|robotCmd|serialCmd|cableCmd|httpCmd|hubUsbCmd|liveSend)'
    sends = set()
    for m in re.finditer(SENDERS + r'\(\s*[`"\']([A-Z][A-Z0-9?]*)', app):
        sends.add(m.group(1))
    for m in re.finditer(SENDERS + r'\(\s*[`"\']\$?\{?\s*([A-Z][A-Z0-9?]*)', app):
        sends.add(m.group(1))
    # `cableCmd("FBEGIN " + name)` and friends: the command is the head of a
    # concatenation, so the literal does not run to the closing quote.
    for m in re.finditer(SENDERS + r'\(\s*[`"\']([A-Z][A-Z0-9?]*)\s', app):
        sends.add(m.group(1))

    # The guard that stops this going quiet again. If a rename ever makes the
    # patterns match nothing, THIS fails loudly instead of the loop below
    # simply not running.
    # 12 today, 3 while the pattern was broken. Ten is comfortably above the
    # vacuous state and below the real count, so it catches "the scan stopped
    # matching" without failing every time a command is added or removed.
    t.ok(len(sends) >= 10,
         "the scan really found Studio's commands (%d)" % len(sends),
         "if this drops, the pattern stopped matching and the loop below is "
         "checking nothing at all")
    known = set(re.findall(r'cmd\s*==\s*"([A-Z][A-Z0-9?]*)"', nong_c))
    # commands handled by the shared router, not the nong module
    router = {"INFO", "PING", "FILES", "PIN", "AUTH", "USER", "SET", "REBOOT",
              "FBEGIN", "FDATA", "FEND", "FREAD", "FDEL", "MOVE", "PLAY"}
    for c in sorted(sends):
        t.ok(c in known or c in router,
             "firmware implements %s (studio sends it)" % c,
             "not found in NongModule.cpp or the shared router")

    # ---- STOP: Studio's Pause depends on it -------------------------
    t.contains(nong_c, 'cmd == "STOP"', "firmware has STOP (Pause needs it)")
    t.contains(app, '"STOP"', "studio sends STOP on pause")

    # ---- every YAML key Studio WRITES must be understood -------------
    # SequencePlayer ignores unknown keys on purpose (so future modules can
    # extend the format), which means a typo in the exporter is silent: the
    # file uploads, runs, and simply leaves that step out.
    player = (F.FIRMWARE / "src/core/SequencePlayer.cpp").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"function buildYaml\(\)\s*\{(.*?)\n\}", app, re.S)
    if t.ok(m, "studio's buildYaml found"):
        body = m.group(1)
        step_keys = set(re.findall(r'`?\s*-\s*(\w+):', body))
        step_keys |= set(re.findall(r'"\s*-\s*(\w+):', body))
        handled = set(re.findall(r'key == "(\w+)"', player))
        for k in sorted(step_keys):
            t.ok(k in handled, "the player understands the '%s:' step studio writes" % k,
                 "unknown keys are ignored silently, so this step would do nothing")
        # top-level keys the player reads directly
        top = set(re.findall(r'^\s*(?:lines|)\s*"?(\w+):', body, re.M))
        for k in ("name", "loop", "next"):
            if k in body:
                t.ok(('"%s"' % k) in player or k == "name",
                     "the player reads the top-level '%s:' studio writes" % k,
                     "written by the editor but never read by the firmware")

    # ---- COMMANDS.md is the reference and must not go stale ---------
    for c in ("POSE", "STOP", "GEAR", "RANGE", "LIMIT", "PULSE", "RATE"):
        t.contains(cmds, c, "COMMANDS.md documents %s" % c)

    # ---- BUG CLASS that hit twice: every per-joint RIG array read by
    # applyPose/buildRobot MUST be in mergeRig's fixLen list, or an old
    # saved rig stays length 8, applyPose gets undefined -> NaN, and the
    # whole robot renders invisible. A fresh browser never sees it.
    fix = re.search(r"\[([^\]]*?)\]\.forEach\(fixLen\)", app, re.S)
    if t.ok(fix, "mergeRig has a fixLen list"):
        listed = set(re.findall(r'"(\w+)"', fix.group(1)))
        rig = re.search(r"DEFAULT_RIG\s*=\s*\{(.*?)\n\}", app, re.S)
        if t.ok(rig, "DEFAULT_RIG found"):
            per_joint = set()
            for m in re.finditer(r"^\s*(\w+):\s*\[([^\]]*)\]", rig.group(1), re.M):
                vals = [v for v in m.group(2).split(",") if v.strip()]
                if len(vals) == 10:          # a per-joint array
                    per_joint.add(m.group(1))
            missing = sorted(per_joint - listed)
            t.eq(missing, [],
                 "every per-joint rig array is length-fixed on load "
                 "(missing one = invisible robot on an old saved rig)")
