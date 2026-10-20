"""The good voice is the one that speaks, and a bad minute is not kept.

A42-1, user 2026-10-15: *the voice settings and the voice that comes out
are not that good*. Three causes, none of them the voice itself:

  1. **A slower speed killed the good voice.** The helper ran
     `edge_tts --rate -10%`; argparse reads a lone "-10%" as an unknown
     option ("argument --rate: expected one argument", reproduced
     2026-10-15), so every slower speed or lower pitch failed and the PC's
     flat backup voice spoke instead. Then `--rate=-10%`; since A45-1 the
     voice runs inside the helper (a new Python per line was slow) and the
     speed goes as an argument, which is what this checks now.
  2. **One outage was kept for ever.** When the online voice did not answer,
     the backup voice's wav was cached under the GOOD voice's name, and every
     later visitor heard that saved answer flat. Now the stand-in plays once
     and is not kept, and such a file left by an older helper is rebuilt.
  3. **The page chose the voice.** Every answer sent the language's own
     voice, which skipped the scenario's voice and the one voice for every
     language (check_voice_source holds the page side).

Runs the real Brain.say with the speech service and PowerShell faked: no
network, no PowerShell, a throwaway cache folder.
"""
import importlib.util
import sys
import tempfile
import threading
from pathlib import Path
from types import SimpleNamespace

import qc as F

AREA = "tools"
TITLE = "the chosen voice speaks at any speed, and a stand-in voice is never cached"

MP3 = b"\xff\xf3" + b"good-voice" * 20         # what the online voice answers
WAV = b"RIFF" + b"\0" * 40 + b"backup" * 10     # what the PC's backup voice answers


def _brain(tmp, cfg):
    path = F.CODE / "apps" / "voice" / "service.py"
    spec = importlib.util.spec_from_file_location("voice_sound_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_sound_check"] = mod
    spec.loader.exec_module(mod)
    mod.CODE = tmp                                   # the cache lands in tmp
    (tmp / "apps" / "voice").mkdir(parents=True, exist_ok=True)
    b = mod.Brain.__new__(mod.Brain)                 # no files, no threads
    b.cfg = cfg
    b._tts_lock = threading.Lock()
    return mod, b


def run(t):
    was = sys.modules.get("edge_tts")
    try:
        _run(t)
        _edge_race(t)
    finally:
        if was is None:
            sys.modules.pop("edge_tts", None)
        else:
            sys.modules["edge_tts"] = was


def _run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_sound_qc_"))
    cfg = {"tts": {"enabled": True, "language": "th", "rate": "-10%", "pitch": "-5Hz",
                   "voices": {"th": "th-TH-PremwadeeNeural"}}}
    mod, b = _brain(tmp, cfg)
    calls = []
    online = {"up": True}

    class Communicate:
        """edge_tts.Communicate, as far as Brain._edge_speak uses it."""
        def __init__(self, text, voice, **kw):
            calls.append(["edge_tts", voice, text] + ["--%s=%s" % kv for kv in sorted(kw.items())])

        async def stream(self):
            if not online["up"]:
                raise OSError("offline")
            yield {"type": "audio", "data": MP3}

    sys.modules["edge_tts"] = SimpleNamespace(Communicate=Communicate)

    def fake_run(cmd, **kw):
        calls.append(cmd)
        return SimpleNamespace(returncode=0, stdout=WAV, stderr=b"")
    mod.subprocess = SimpleNamespace(run=fake_run, TimeoutExpired=TimeoutError)
    b._edge_installed = lambda: True        # this machine's own install is not the test

    # 0: nothing spoken yet - the page has nothing to warn about
    t.ok(b.voice_heard().get("natural") in (None, False),
         "before any line, the helper does not claim a voice spoke", repr(b.voice_heard()))

    # 1: slower and lower still reach the good voice
    got, why = b.say("ช้าลงหน่อย", "th")
    t.ok(got == MP3, "a slower speed and a lower pitch are spoken by the chosen voice",
         "the backup voice spoke (%s): %r" % (why, calls[-1]))
    edge = [c for c in calls if "edge_tts" in c][0]
    t.ok("--rate=-10%" in edge and "--pitch=-5Hz" in edge,
         "the speed and pitch reach the speech service joined with '='", repr(edge))

    # 2: a stand-in voice plays, but is not kept under the good voice's name
    online["up"] = False
    got, _ = b.say("วันนี้ฝนตก", "th")
    t.ok(got == WAV, "offline, the PC's own voice still answers", repr(got[:8]))
    rate, pitch = b.steps()
    kept = b._cache_path("th-TH-PremwadeeNeural", "วันนี้ฝนตก", rate=rate, pitch=pitch)
    t.ok(not kept.exists(), "...and nothing is kept under the good voice's name",
         "the backup's wav was cached at %s" % kept.name)
    # A42-2: the stand-in is NAMED, with what the speech service said, so
    # "the voice is not natural" is not a mystery (user 2026-10-15).
    heard = b.voice_heard()
    t.ok(heard.get("natural") is False and "offline" in heard.get("tech", ""),
         "the helper says the backup voice spoke, and why", repr(heard))
    online["up"] = True
    got, _ = b.say("วันนี้ฝนตก", "th")
    t.ok(got == MP3, "and once the good voice is back, that line is spoken by it",
         "the backup's sound was kept and replayed")
    t.ok(b.voice_heard().get("natural") is True,
         "...and the warning goes with it", repr(b.voice_heard()))

    # 3: a stand-in left in the cache by an older helper is rebuilt
    rate, pitch = b.steps()
    old = b._cache_path("th-TH-PremwadeeNeural", "เก่า", rate=rate, pitch=pitch)
    old.parent.mkdir(parents=True, exist_ok=True)
    old.write_bytes(WAV)
    got, _ = b.say("เก่า", "th")
    t.ok(got == MP3, "a flat file kept by an older helper is built again",
         "the old backup wav was played")
    got2, _ = b.say("เก่า", "th")
    t.ok(got2 == MP3 and old.read_bytes() == MP3, "and the good one is what is kept now")

    # 5: the natural voice missing from this PC is said before anything is spoken
    b._edge_installed = lambda: False
    heard = b.voice_heard()
    t.ok(heard.get("natural") is False and "not installed" in heard.get("why", "")
         and "pip install edge-tts" in heard.get("tech", ""),
         "a PC without the natural voice is told so, with the fix behind the switch", repr(heard))

    # 4: Try it - a speed heard before saving; a shape it cannot read is dropped
    n = len(calls)
    b.say("ลองเสียง", "th", voice="th-TH-NiwatNeural", rate="+20%", pitch="+0Hz")
    t.ok(any("--rate=+20%" in c for c in calls[n:] if "edge_tts" in c),
         "Try sends the speed on screen, not the saved one", repr(calls[n:]))
    n = len(calls)
    got, _ = b.say("ลองเสียงสอง", "th", rate="fast", pitch="loud")
    edge = [c for c in calls[n:] if "edge_tts" in c]
    t.ok(got == MP3 and edge and not any(a.startswith(("--rate", "--pitch")) for a in edge[0]),
         "a speed it cannot read is dropped and the voice kept", repr(edge))


def _edge_race(t):
    """A stalled first request cannot hold up the spare or the next provider."""
    import asyncio
    import time
    tmp = Path(tempfile.mkdtemp(prefix="mice_edge_qc_"))
    mod, b = _brain(tmp, {"providers": {"edge": {"speak": {
        "hedgeSeconds": 0.03, "timeoutSeconds": 0.18}}}})
    calls, closed = [], []
    mode = ["stall"]

    class Communicate:
        def __init__(self, *a, **k):
            self.index = len(calls)
            calls.append(self.index)

        async def stream(self):
            try:
                if mode[0] == "dead" or (mode[0] == "stall" and self.index == 0):
                    await asyncio.sleep(1)
                if mode[0] == "fail" and self.index == 0:
                    raise OSError("NoAudioReceived")
                if mode[0] == "partial" and self.index == 0:
                    yield {"type": "audio", "data": MP3[:10]}
                    raise OSError("broken stream")
                yield {"type": "audio", "data": MP3}
            finally:
                closed.append(self.index)

    sys.modules["edge_tts"] = SimpleNamespace(Communicate=Communicate)
    for case in ("fast", "stall", "fail", "partial", "dead"):
        mode[0] = case
        calls.clear()
        closed.clear()
        start = time.monotonic()
        got, why = b._edge_speak("th-TH-PremwadeeNeural", "hello", "", "")
        elapsed = time.monotonic() - start
        t.eq(len(calls), 1 if case == "fast" else 2, case + ": at most one spare")
        t.ok(sorted(closed) == calls, case + ": every stream is closed", repr(closed))
        if case == "dead":
            t.ok(got is None and "timed out" in str(why) and elapsed < 0.7,
                 "two stalled streams stop at the shared deadline", repr((elapsed, why)))
        else:
            t.ok(got == MP3 and why is None and elapsed < 0.4,
                 case + ": the first complete sound wins without waiting for the stalled request",
                 repr((elapsed, why)))
