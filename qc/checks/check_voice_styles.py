"""A speaking manner (จริต) reaches the speaking service it can, honestly (A45-25).

User 2026-10-21: closer to a person, polite / friendly / playful / อ้อน, real
emotion, ทำนองเสนาะ. What each service can really change is DATA - the speak
job's `styles` in voice_providers.json, checked against each service's docs:
Gemini TTS is TOLD the manner in words; Edge and Azure only move speed and
pitch; this PC's Windows voice changes nothing. So this check asserts on what
REACHED the speaking call, not on a label:

  * request beats scenario beats tts.style; unknown or empty = as before;
  * Edge gets the manner's speed/pitch steps added to the chosen ones, kept
    inside the limits; Gemini gets the manner's words; Windows gets neither;
  * each manner has its OWN cached sound (a playful line never replays the
    neutral one) while a line with no manner keeps its old cache name;
  * /say says how it was applied (X-Voice-Style), /styles lists per service.

Real Edge samples of every manner are private evidence in
scratch/voice-a45-24-2026-10-21/styles (prosody only, not emotion). Gemini's
manner is NOT heard on this PC: no key yet (user deferred sign-in).
"""
import importlib.util
import json
import shutil
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "a speaking manner reaches each speaking service as far as it can, honestly"


def _service():
    spec = importlib.util.spec_from_file_location(
        "mice_voice_service_styles", F.CODE / "apps" / "voice" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    svc = _service()
    tmp = Path(tempfile.mkdtemp(prefix="qc_styles_"))
    try:
        cfg = tmp / "voice.json"
        cfg.write_text(json.dumps({
            "presence": {"on": False}, "face": {"on": False}, "stt": {"enabled": False},
            "llm": {"enabled": False},
            "tts": {"enabled": True, "rate": "+0%", "pitch": "+0Hz",
                    "voices": {"th": "th-TH-PremwadeeNeural"}},
            "use": {"speak": ["edge", "local"]},
            "scenarios": [{"name": "fair", "style": "friendly"}],
        }), encoding="utf-8")
        faq = tmp / "qa.json"
        faq.write_text(json.dumps({"faqs": []}), encoding="utf-8")
        brain = svc.Brain(str(cfg), str(faq))
        cache = tmp / "cache"
        cache.mkdir()
        brain._cache_path_real = brain._cache_path
        brain._cache_path = lambda ident, text, rate=None, pitch=None: cache / (
            brain._cache_path_real(ident, text, rate, pitch).name)
        _choice(t, brain)
        _edge(t, brain, cache)
        _others(t, brain, svc)
        _http(t, brain, svc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _choice(t, brain):
    styles = brain.styles().get("styles") or {}
    for key in ("polite", "friendly", "playful", "coaxing", "recite"):
        s = styles.get(key) or {}
        t.ok(s.get("says") and s.get("instruct") and "prosody" in s,
             "manner %s has a name, words for a service that takes them, and speed/pitch" % key)
    t.eq(brain.style_choice()[0], "", "no manner chosen = speaks as before (the user has not picked one)")
    brain.cfg["tts"]["style"] = "polite"
    t.eq(brain.style_choice()[0], "polite", "tts.style picks the manner")
    brain.cfg["scenario"] = "fair"
    t.eq(brain.style_choice()[0], "friendly", "an event's own manner beats tts.style")
    t.eq(brain.style_choice("playful")[0], "playful", "a request's manner beats both")
    t.eq(brain.style_choice("")[0], "", "a request for no manner is no manner")
    t.eq(brain.style_choice("shouty")[0], "", "an unknown manner is none, never a silent voice")
    brain.cfg.pop("scenario", None)
    brain.cfg["tts"].pop("style", None)
    t.eq(brain.style_steps("+0%", "+0Hz", styles["friendly"]), ("+3%", "+3Hz"),
         "speed and pitch steps are ADDED to the chosen ones")
    t.eq(brain.style_steps("+45%", "-28Hz", styles["playful"]), ("+50%", "-22Hz"),
         "and kept inside the limits")


def _edge(t, brain, cache):
    got = []

    def fake_edge(voice, text, rate, pitch):
        got.append((voice, rate, pitch))
        return b"ID3" + bytes([len(got)]) * 400, None
    brain._edge_speak = fake_edge
    plain, why = brain.say("สวัสดีครับ", "th")
    t.ok(plain and got[-1] == ("th-TH-PremwadeeNeural", "+0%", "+0Hz"),
         "no manner: Edge is asked exactly as before", (why, got[-1:]))
    old_name = brain._cache_path_real("th-TH-PremwadeeNeural", "สวัสดีครับ", "+0%", "+0Hz").name
    t.ok((cache / old_name).exists(), "and its sound keeps its old cache name, so old caches still work")
    sound, why = brain.say("สวัสดีครับ", "th", style="playful")
    t.ok(sound and sound != plain and got[-1] == ("th-TH-PremwadeeNeural", "+8%", "+6Hz"),
         "playful reaches Edge as its speed and pitch, and is a NEW sound, not the cached plain one",
         (why, got[-1:]))
    t.eq(brain._style_done, {"style": "playful", "how": "prosody", "by": "edge"},
         "and it is recorded as speed and pitch only")
    n = len(got)
    again, _ = brain.say("สวัสดีครับ", "th", style="playful")
    t.ok(again == sound and len(got) == n, "the same manner again comes from its own cache")
    coax, _ = brain.say("สวัสดีครับ", "th", style="coaxing")
    t.ok(coax not in (sound, plain), "another manner is another sound")
    brain.cfg["tts"]["rate"] = "+44%"
    brain.say("สวัสดีครับ", "th", style="playful")
    t.eq(got[-1][1], "+50%", "a chosen speed plus the manner never passes Edge's limit")
    brain.cfg["tts"]["rate"] = "+0%"


def _others(t, brain, svc):
    seen = {}

    def fake_wire(prov, key, job, text, lang, voice, timeout, style=""):
        seen["style"] = style
        return b"RIFF" + b"\x01" * 400, None
    svc.providers.WIRES["gemini"]["speak"] = fake_wire
    brain.key_for = lambda pid: "test-key"
    brain.cfg["use"] = {"speak": ["gemini"]}
    snd, why = brain.say("สวัสดีครับ", "th", style="coaxing")
    want = (brain.styles()["styles"]["coaxing"]["instruct"])
    t.ok(snd and seen.get("style") == want,
         "Gemini is TOLD the manner in words (the documented speech_metadata style)", (why, seen))
    t.eq(brain._style_done.get("how"), "instruct", "and it is recorded as told in words")
    seen.clear()
    brain.say("สวัสดีครับ", "th")
    t.eq(seen.get("style"), "", "no manner: Gemini gets no style line")

    spoke = []
    brain._windows_speak = lambda text, lang, voice: (spoke.append(text) or b"RIFF" + b"\x02" * 400, None)
    brain.cfg["use"] = {"speak": ["local"]}
    snd, why = brain.say("สวัสดีครับ", "th", style="playful")
    t.ok(snd and spoke == ["สวัสดีครับ"], "this PC's voice still speaks the same words", (why, spoke))
    t.eq(brain._style_done.get("how"), "none", "and says plainly that the manner was not applied")
    brain.cfg["use"] = {"speak": ["edge", "local"]}
    view = brain.styles_view()
    t.ok(view["styles"]["recite"]["by"].get("edge") == "prosody"
         and "not a real" in view["styles"]["recite"]["prosodyNote"],
         "the page is told recital on Edge is a slow reading, not a real ทำนองเสนาะ", view["styles"]["recite"])


def _http(t, brain, svc):
    brain._edge_speak = lambda voice, text, rate, pitch: (b"ID3" + b"\x03" * 400, None)
    svc.VoiceHandler.brain = brain
    httpd = ThreadingHTTPServer(("127.0.0.1", 0), svc.VoiceHandler)
    port = httpd.server_address[1]
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    try:
        req = urllib.request.Request("http://127.0.0.1:%d/say" % port,
                                     data=json.dumps({"text": "ทดสอบ", "lang": "th", "style": "polite"},
                                                     ensure_ascii=False).encode(),
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=10) as r:
            head = r.headers.get("X-Voice-Style", "")
        t.eq(head, "polite; prosody; edge", "/say tells how the manner was applied")
        with urllib.request.urlopen("http://127.0.0.1:%d/styles" % port, timeout=10) as r:
            got = json.loads(r.read())
        t.ok(got.get("ok") and set(got.get("styles", {})) >= {"polite", "friendly", "playful", "coaxing", "recite"},
             "/styles lists every manner for the Voice page", list(got.get("styles", {})))
    finally:
        httpd.shutdown()
        httpd.server_close()
