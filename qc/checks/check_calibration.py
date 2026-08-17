"""Calibration must survive a power cycle on a board with NO SD card.

This is a source-level check: the failure is about where bytes are written, and
proving it end-to-end would need a real board (or an NVS emulator). What it
guards is the specific shape of the bug that was hit — `saveCal()` returning
early when there is no card, so every unplug threw the tuning away.
"""
import re

import qc as F

AREA = "calibration"
TITLE = "tuning survives a power cycle without an SD card"
SLOW = False

NONG_C = F.FIRMWARE / "src/modules/nong/NongModule.cpp"
NONG_H = F.FIRMWARE / "src/modules/nong/NongModule.h"


def handler_body(src, at):
    """The whole `if (cmd == "X" ...) { ... }` block containing position `at`.

    Brace-matched, because these handlers answer a query form first and return
    early — stopping at the first `return true;` would read only that branch,
    and `cmd == "LIMIT" || cmd == "LIMIT?"` puts two names on one line.
    """
    open_brace = src.find("{", at)
    if open_brace < 0:
        return ""
    depth, i = 0, open_brace
    while i < len(src):
        if src[i] == "{":
            depth += 1
        elif src[i] == "}":
            depth -= 1
            if depth == 0:
                return src[at:i + 1]
        i += 1
    return src[at:]


def run(t):
    src = NONG_C.read_text(encoding="utf-8", errors="replace")
    hdr = NONG_H.read_text(encoding="utf-8", errors="replace")

    # ---- there is a copy that does not depend on the card --------------
    t.contains(hdr, "CalBlob", "calibration has an on-chip format")
    t.contains(src, "saveCalNvs", "there is a save path that needs no card")
    t.contains(src, "loadCalNvs", "and a load path for it")
    t.contains(src, 'Preferences', "it uses the chip's own NVS")

    # ---- THE bug: the chip save must happen BEFORE the no-card return ---
    m = re.search(r"void NongModule::saveCal\(\)\s*\{(.*?)\n\}", src, re.S)
    if t.ok(m, "saveCal() found"):
        body = m.group(1)
        nvs = body.find("saveCalNvs")
        bail = body.find("available()) return")
        t.ok(nvs >= 0 and (bail < 0 or nvs < bail),
             "the chip copy is written before the no-card early return",
             "saveCal() still gives up before saving when there is no SD card")

    # ---- boot applies it, and after the card so it wins -----------------
    m = re.search(r"void NongModule::begin\(\)\s*\{(.*?)writeServos", src, re.S)
    if t.ok(m, "begin() found"):
        b = m.group(1)
        t.ok("loadCalNvs" in b, "boot loads the chip copy")
        t.ok(b.find("loadCal();") < b.find("loadCalNvs"),
             "the chip copy is applied after the card file, so it wins",
             "the card file would override the newer chip copy")

    # ---- every calibration command must persist -------------------------
    # A command that changes calibration but never asks for a save is a
    # setting that silently disappears on the next power cycle.
    for cmd in ("LIMIT", "GEAR", "PULSE", "RANGE", "RATE", "SERVO", "SETZERO"):
        m = re.search(r'cmd == "%s"' % cmd, src)
        if not t.ok(m, "%s exists" % cmd):
            continue
        seg = handler_body(src, m.start())
        t.ok("saveCal" in seg, "%s persists the change" % cmd,
             "changes calibration but never saves it")

    # ---- a bad calibration must be recoverable without a card -----------
    t.contains(src, 'cmd == "CAL"', "CAL reports where the calibration lives")
    t.contains(src, "clearCal", "CAL CLEAR can forget it")
    m = re.search(r"void NongModule::clearCal\(\)\s*\{(.*?)\n\}", src, re.S)
    if t.ok(m, "clearCal() found"):
        t.contains(m.group(1), "p.clear()", "clearing wipes the chip copy")
        t.contains(m.group(1), "nong_cal.yaml", "and the card copy when there is one")

    # ---- a blob from another firmware must not be half-applied ----------
    m = re.search(r"bool NongModule::loadCalNvs\(\)\s*\{(.*?)\n\}", src, re.S)
    if t.ok(m, "loadCalNvs() found"):
        b = m.group(1)
        t.contains(b, "CAL_MAGIC", "a foreign blob is rejected by magic")
        t.contains(b, "CAL_VERSION", "and by version")
        t.ok("return false" in b, "rejection falls back to the defaults")
        t.contains(b, "reclamp", "and the loaded values are re-clamped")

    # ---- documented ------------------------------------------------------
    cmds = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(cmds, "CAL CLEAR", "COMMANDS.md documents CAL CLEAR")
    t.contains(cmds, "no SD card", "COMMANDS.md says it works without a card")
