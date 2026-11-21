"""One Edge voice that returns no sound falls back to the next voice of the language.

PC 2026-11-21: th-TH-PremwadeeNeural answered "NoAudioReceived" for every line
while th-TH-NiwatNeural worked with the same text and edge-tts 7.3.1, so the
robot was silent. tts.fallbackVoices (data) lists who may stand in. Proven with
a stand-in edge_tts module: the broken voice fails, the listed one speaks; a
voice that works is used alone; with no fallback listed the failure is reported.
"""
import sys
import types
from types import SimpleNamespace

import qc as F

AREA = "voice"
TITLE = "a silent Edge voice falls back to the language's listed spare"

SOUND = b"x" * 400


def run(t):
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import service                                            # noqa: E402
    used = []

    class NoAudioReceived(Exception):
        pass

    class Communicate:
        def __init__(self, text, voice, **kw):
            self.voice = voice
            used.append(voice)

        async def stream(self):
            if self.voice.endswith("BrokenNeural"):
                raise NoAudioReceived("No audio was received")
            yield {"type": "audio", "data": SOUND}

    fake = types.ModuleType("edge_tts")
    fake.Communicate = Communicate
    old = sys.modules.get("edge_tts")
    sys.modules["edge_tts"] = fake
    try:
        def brain(fallback):
            me = SimpleNamespace(
                cfg={"tts": {"fallbackVoices": fallback}},
                service=lambda pid: {"jobs": {"speak": {"hedgeSeconds": 0.2, "timeoutSeconds": 5}}})
            me._edge_speak = lambda *a, **k: service.Brain._edge_speak(me, *a, **k)
            return me
        speak = service.Brain._edge_speak
        got, why = speak(brain({"th": ["th-TH-SpareNeural"]}), "th-TH-BrokenNeural", "สวัสดี", "", "")
        t.ok(got == SOUND and "th-TH-SpareNeural" in used,
             "the broken voice is replaced by the listed spare", "%r %r %r" % (got, why, used))
        used.clear()
        got, why = speak(brain({"th": ["th-TH-SpareNeural"]}), "th-TH-GoodNeural", "สวัสดี", "", "")
        t.ok(got == SOUND and set(used) == {"th-TH-GoodNeural"},
             "a working voice is used alone", "%r %s" % (got, used))
        got, why = speak(brain({}), "th-TH-BrokenNeural", "สวัสดี", "", "")
        t.ok(not got and "NoAudioReceived" in (why or ""),
             "with no spare listed the failure is reported, not hidden", "%r %r" % (got, why))
        got, why = speak(brain({"th": ["th-TH-BrokenNeural"]}), "th-TH-BrokenNeural", "สวัสดี", "", "")
        t.ok(not got, "a spare that is the same broken voice is not retried forever", "%r %r" % (got, why))
    finally:
        if old is None:
            sys.modules.pop("edge_tts", None)
        else:
            sys.modules["edge_tts"] = old
