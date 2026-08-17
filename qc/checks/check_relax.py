"""RELAX must actually relax — every joint, including the awkward ones.

Reported from the bench: nine servos went limp and SHRUG stayed stiff.

The loop was never wrong; it always covered all ten. The problem is that
`detach()` only hands the pin back to plain GPIO — it says nothing about what
level the line ends up at. On a pin with an internal pull-up the line then sits
HIGH, and a servo watching a permanently high signal holds its position rather
than going limp. SHRUG is on **GPIO 15**, a strapping pin (MTDO) that the ESP32
pulls up at reset; the other nine happened to settle low and so appeared to
work.

That is why "does the code loop over all ten?" was the wrong question, and why
every check that asked it passed while the arm was visibly still powered.

QC before this covered RELAX only as *a command that interrupts a sequence*
(check_one_player). Nothing checked that it reaches every joint or that a
relaxed line is actually idle. This does both, and treats every per-joint
command the same way — one joint left out of a loop is invisible until someone
notices that one servo behaves differently from the rest.
"""
import re

import qc as F

AREA = "nong"
TITLE = "RELAX really relaxes every joint, and per-joint loops cover all of them"
SLOW = False

SRC = "src/modules/nong/NongModule.cpp"


def _code(s):
    """No comments — a comment describing a loop is not a loop."""
    nl = chr(10)
    s = re.sub(r"/\*(?:.|" + nl + r")*?\*/", " ", s)
    return re.sub(r"//[^" + nl + r"]*", " ", s)


def block(code, marker):
    i = code.find(marker)
    if i < 0:
        return ""
    depth, j = 0, code.find("{", i)
    if j < 0:
        return ""
    for k in range(j, min(len(code), j + 4000)):
        if code[k] == "{":
            depth += 1
        elif code[k] == "}":
            depth -= 1
            if depth == 0:
                return code[i:k + 1]
    return code[i:i + 4000]


def run(t):
    raw = (F.FIRMWARE / SRC).read_text(encoding="utf-8", errors="replace")
    code = _code(raw)

    # ---- a relaxed line must be IDLE, not merely un-driven --------------
    relax = block(code, 'cmd == "RELAX"')
    if t.ok(relax, "RELAX is handled"):
        t.contains(relax, "detach()", "it detaches the servos")
        t.contains(relax, "digitalWrite", "and then drives the line itself")
        t.contains(relax, "LOW",
                   "LOW — a pin left to a pull-up sits HIGH and the servo holds")
        t.ok("pinMode" in relax,
             "taking the pin as an output first, or the write does nothing")
        t.ok("i < N" in relax,
             "and it covers every joint, not just the arm")

    # ---- ATTACH is the mirror image ------------------------------------
    att = block(code, 'cmd == "ATTACH"')
    if t.ok(att, "ATTACH is handled"):
        t.ok("i < N" in att, "it re-attaches every joint")
        t.contains(att, "setPeriodHertz",
                   "restoring each joint's own frame rate, not a shared default")

    # ---- no per-joint loop may stop at the arm -------------------------
    # ARMJ is 8 (the arm chain, for IK) and N is 10. A loop over ARMJ where N
    # was meant leaves WAIST and SHRUG out, and that is invisible until one
    # servo behaves differently from the others — which is how this was found.
    for name in ("RELAX", "ATTACH"):
        b = block(code, 'cmd == "%s"' % name)
        t.ok("ARMJ" not in b,
             "%s does not loop over the arm joints only" % name,
             "WAIST and SHRUG would be silently skipped")

    # writeServos and the interpolator drive the real hardware: same rule
    for fn in ("void NongModule::writeServos", "void NongModule::reattach"):
        b = block(code, fn)
        if b:
            t.ok("ARMJ" not in b,
                 "%s covers all ten joints" % fn.split("::")[-1],
                 "a hardware loop that stops at 8 leaves two servos behind")

    # ---- the pin map still puts SHRUG on the pin this is about ----------
    hw = (F.FIRMWARE / "config/esp32_hardware_nong_module.h").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r"NONG_SERVO_PINS\s*\{([^}]*)\}", hw)
    if t.ok(m, "the servo pin map is readable"):
        pins = [p.strip() for p in m.group(1).split(",")]
        t.eq(len(pins), 10, "ten servo pins, one per joint")
        # Strapping pins carry a pull-up or pull-down at reset. Using one is
        # allowed — this is a note for whoever moves a servo, not a ban.
        strap = {"0", "2", "5", "12", "15"}
        used = [p for p in pins if p in strap]
        t.ok(True, "servo pins on strapping GPIOs: %s"
             % (", ".join(used) if used else "none"))
