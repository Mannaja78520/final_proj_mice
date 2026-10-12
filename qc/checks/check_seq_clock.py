"""A sequence played BY THE BOARD keeps one clock, so the song and the arm agree.

User 2026-10-12, after a show sent to nong 67 with "Send to robot" played from
its card: *the moves ended late and the music followed them, not the times I
set*. Two causes, measured on the board over WiFi (music start to the end of the
last move, against the file's own T and wait values):

* the show file started the song BEFORE the walk onto the first pose, so the
  song ran 3.3 s ahead of every move. The hub's ShowPlayer starts it on
  arrival. Covered in check_show_to_robot (the file's cue order).
* the board started each move only when busy() cleared - the first 20 ms servo
  frame past the end - and every wait from that late moment. The lateness
  added up: 90.46 s of moves played in 91.59 s. With the deadline clock below
  the same file played in 90.42 s.

There is no host build of the firmware, so this reads SequencePlayer.cpp for
the pieces that make the clock - each one was removed by sabotage and seen to
fail here:

* a move that says its time (`OK pose T=<ms>ms`) moves the deadline by that
  time, and the next step waits for the deadline, not for busy();
* the time is the LAST " T=" of the reply: a JOINT reply starts with the joint,
  and `WAIST=90.0` carries a T= of its own;
* a `wait` is counted on the same clock, not from the moment it is read;
* a real stall re-anchors the clock (CATCH_UP_MS) instead of rushing moves.
"""
import re

import qc as F

AREA = "sequences"
TITLE = "the board plays a sequence on one clock, not move after late move"
SLOW = False

PLAYER = F.FIRMWARE / "src" / "core" / "SequencePlayer.cpp"
HEADER = F.FIRMWARE / "src" / "core" / "SequencePlayer.h"


def _flat(text):
    return re.sub(r"\s+", " ", text)


def run(t):
    src = _flat(PLAYER.read_text(encoding="utf-8", errors="replace"))
    head = _flat(HEADER.read_text(encoding="utf-8", errors="replace"))
    body = src[src.index("void SequencePlayer::execStep"):]

    t.contains(body, 'String reply = router_->handleFromSequence(',
               "a step's reply is read, so the board's own move time is known")
    t.contains(body, 'reply.lastIndexOf(" T=")',
               "the move time is the LAST \" T=\" (WAIST=90.0 has a T= of its own)")
    t.ok(re.search(r"if \(took > 0\) \{ due_ \+= \(uint32_t\)took; waitUntil_ = due_;", body),
         "a timed move ends on the deadline clock", body[:400])
    t.ok(re.search(r"else \{ waitBusy_ = true; \}", body),
         "and only an untimed step still waits for busy()", body[:400])
    t.ok(re.search(r'key == "wait"\) \{.*?due_ \+= \(uint32_t\)w;.*?waitUntil_ = due_;', body),
         "a wait is counted on the same clock", body[:600])
    t.ok("millis() + (uint32_t)w" not in src,
         "and never again from the moment it is read")
    t.contains(body, "if (s->wait) catchUp();",
               "a stall re-anchors the clock before the next move")
    t.ok(re.search(r"millis\(\) - due_\) > \(int32_t\)CATCH_UP_MS\) due_ = millis\(\);", src),
         "past CATCH_UP_MS late, the clock starts again from now", "")
    t.contains(head, "CATCH_UP_MS", "the stall limit is named once")
    # every way a run starts sets the clock, or the first deadline is stale
    t.eq(len(re.findall(r"due_ = waitUntil_;", src)), 2,
         "both ways to start a run (card and memory) start the clock")
