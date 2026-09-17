"""One voice can speak every language, when one is chosen.

A26-64 (user 2026-09-18): *when i use multi lang it have this problem it name
is thai and this model lang in en ot can't read thai so can we use only 1
voice but can adjust and can read all lang*. With Multi-lang on, an answer can
hold a Thai name inside an English sentence - and an English voice reads the
Thai letters as nothing. Measured the same day: the same mixed sentence
produced 28512 bytes of audio from en-US-AvaMultilingualNeural and 16128 from
en-US-JennyNeural, which is the Thai half going missing.

So `tts.oneVoice` in config/voice.json wins over the per-language map for
EVERY language, and the list of voices that can do it comes from the speech
service itself, never from a list typed into a page. Empty keeps the old
behaviour, so nothing changes for a rig that never sets it.
"""
import json
import sys

import qc as F

AREA = "tools"
TITLE = "one voice for every language, chosen not hardcoded"


def _brain(cfg):
    """The real Brain class, with a config in memory - no helper process."""
    import importlib.util
    path = F.CODE / "apps" / "voice" / "service.py"
    spec = importlib.util.spec_from_file_location("voice_service_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_service_check"] = mod
    spec.loader.exec_module(mod)
    b = mod.Brain.__new__(mod.Brain)                    # no files, no threads
    b.cfg = cfg
    return b


def run(t):
    per_lang = {"tts": {"enabled": True, "language": "th", "voices": {
        "th": "th-TH-PremwadeeNeural", "en": "en-US-JennyNeural"}}}
    b = _brain(json.loads(json.dumps(per_lang)))
    t.eq(b.resolve_voice("en")[1], "en-US-JennyNeural",
         "with no one-voice chosen, each language keeps its own")

    one = json.loads(json.dumps(per_lang))
    one["tts"]["oneVoice"] = "en-US-AvaMultilingualNeural"
    b = _brain(one)
    for lang in ("th", "en", "ja", "zh", ""):
        got = b.resolve_voice(lang)[1]
        t.eq(got, "en-US-AvaMultilingualNeural",
             "the chosen voice speaks %s too" % (lang or "an unnamed language"))
    # A language that is in NO map still speaks: the whole point is that the
    # voice is not tied to a language.
    t.eq(b.resolve_voice("de")[1], "en-US-AvaMultilingualNeural",
         "and a language nobody mapped is spoken as well")
    t.contains(b.tts_status(), "every language",
               "the status says one voice is doing all of it")

    page = (F.CODE / "apps" / "voice" / "index.html").read_text(
        encoding="utf-8", errors="replace")
    t.ok('id="oneVoice"' in page and "fillOneVoice" in page
         and "/api/voice/voices" in page,
         "the page offers the choice, and gets the names from the helper",
         "the one-voice picker or its source is missing")
    t.ok("Multilingual" not in page.split("fillOneVoice")[0],
         "no voice name is written into the page itself",
         "a voice name is hardcoded in the page")
