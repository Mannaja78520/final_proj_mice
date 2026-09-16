"""Two overlapping scans must both get their PONGs answered.

Broadcast replies waited in ONE slot (`pendingReply_`): a second #* PING
arriving before the first answer fired OVERWROTE it, so the first scan
silently lost boards — exactly the symptom the staggered slots were built to
prevent, reintroduced one level up. Now they queue: first free slot, and when
the queue is full the entry that has waited longest gives way.

This pins the queue shape so it cannot quietly collapse back to one slot.
"""
import qc as F

AREA = "connection"
TITLE = "broadcast replies queue instead of overwriting one slot"


def run(t):
    h = (F.FIRMWARE / "src" / "core" / "RS485Bus.h").read_text(encoding="utf-8")
    t.ok("pendingReply_" not in h,
         "no single pendingReply_ slot left in the header")
    m = __import__("re").search(r"PENDING_N = (\d+)", h)
    if t.ok(m, "the pending queue has a declared size"):
        t.ok(int(m.group(1)) >= 2, "and it holds more than one (%s)" % m.group(1),
             "a size of 1 is the old bug with an array costume on")

    src = (F.FIRMWARE / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    t.ok("pendingReply_" not in src,
         "no single pendingReply_ slot left in the code either")

    loop = src[src.find("void RS485Bus::loop("):]
    loop = loop[:loop.find("\n}") + 2]
    t.contains(loop, "for (uint8_t i = 0; i < PENDING_N; i++)",
               "loop() checks EVERY queued reply, not just the newest")

    line = src[src.find("void RS485Bus::handleLine("):]
    t.contains(line, "if (!pending_[i].length()) { slot = i; break; }",
               "a new answer takes the first FREE slot")
    # full queue: the NEWEST gives way (nothing already waiting is lost, and
    # nothing about to fire is destroyed). Signed delta: millis() rolls over.
    t.contains(line, "(int32_t)(pendingAt_[i] - pendingAt_[slot]) > 0",
               "displacement picks the newest entry, by signed delta")
    t.ok("UINT32_MAX" not in line and "< oldest" not in line,
         "no unsigned oldest-wins comparison left",
         "smallest pendingAt_ is the SOONEST-DUE reply - displacing it "
         "destroys an answer that was about to be sent (panel, 2026-08-26)")
