"""Playback must not cost more work than it needs, and scrubbing moves the arm.

Reported from the bench: Studio lags and freezes while playing, and freezes
again on returning to the page.

The cause was work, not logic. `renderSliders()` runs on every tick of
playback, and it wrote six DOM properties per joint every time — sixty writes
a frame, of which the min/max were the same numbers as the frame before.
Setting min/max on a range input makes the browser re-validate and clamp the
value, so those were the expensive ones. And `playTick` is called from BOTH
the animation frame and the keep-awake interval, so the picture was being
redrawn about 76 times a second on a 60 Hz screen. Roughly 4500 DOM writes a
second, for a slider row that mostly had not changed.

Also here: dragging the scrubber takes the real arm with it. Checking a single
move without playing the whole show is the reason the scrubber exists, and a
preview that moves while the robot stays still is the one thing you cannot
check against.
"""
import re

import qc as F

AREA = "studio"
TITLE = "playback does not burn work it does not need, and scrubbing moves the arm"
SLOW = False


def _js(src):
    """Code without comments — a comment saying "cached" is not caching."""
    nl = chr(10)
    src = re.sub(r"/\*(?:.|" + nl + r")*?\*/", " ", src)
    return re.sub(r"//[^" + nl + r"]*", " ", src)


def run(t):
    app = (F.STUDIO / "web/app.js").read_text(encoding="utf-8", errors="replace")
    code = _js(app)

    # ---- the slider row only writes what changed ------------------------
    i = code.find("function renderSliders()")
    if t.ok(i >= 0, "renderSliders exists"):
        body = code[i:i + 2600]
        # the COMPARISON, not just the name: `if (true) { _lastVal[i] = v; ... }`
        # still mentions _lastVal while writing on every single frame
        t.contains(body, "_lastVal[i] !== v",
                   "a joint value is only written when it actually changed")
        t.ok("_lastMin" in body and "_lastMax" in body,
             "and the travel limits are not rewritten every frame",
             "setting min/max makes the browser re-validate the value each time")
        # the naive form: an unconditional write of every property
        t.ok(not re.search(r'\$\("js" \+ i\)\.min = \$\("jn" \+ i\)\.min = RIG\.min\[i\];',
                           body),
             "the unconditional per-frame writes are gone")

    # ---- drawing happens once per frame, not per tick -------------------
    i = code.find("function playTick()")
    if t.ok(i >= 0, "playTick exists"):
        body = code[i:i + 2200]
        t.contains(body, "_drawing",
                   "painting is limited to the animation frame")
        j = body.find("_drawing")
        k = body.find("applyPose()")
        t.ok(0 <= j < k,
             "so the keep-awake interval advances time without repainting",
             "both callers painted, which is ~76 paints a second on a 60Hz screen")

    t.contains(code, "_drawing = true",
               "the animation frame is the one that may paint")
    t.contains(code, "_drawing = false",
               "and it is cleared again, so the interval never paints")

    # ---- scrubbing takes the arm with it --------------------------------
    i = code.find("function scrubTo(")
    if t.ok(i >= 0, "the scrubber exists"):
        body = code[i:i + 900]
        t.contains(body, "sendPoseLive",
                   "dragging the scrubber moves the real arm too")
        t.contains(body, "liveLinked",
                   "but only when something is actually connected")

    # ---- and the poll that broke playback stays gone ---------------------
    # Correcting the play head from GET /api/play while the hub is running the
    # show disturbed it: a four-move timeline went out as 90,60,120,60,120,90
    # and the hold between moves collapsed from 2200 ms to 1565 ms.
    t.ok("hubFollow" not in code,
         "the page does not poll the hub for the play head",
         "reading the player once a second while it runs breaks its timing")
