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

    _mixed_line(t, _brain)
    _scenarios(t, _brain)

    page = (F.CODE / "apps" / "voice" / "index.html").read_text(
        encoding="utf-8", errors="replace")
    t.ok('id="oneVoice"' in page and "fillOneVoice" in page
         and "/api/voice/voices" in page,
         "the page offers the choice, and gets the names from the helper",
         "the one-voice picker or its source is missing")
    t.ok("Multilingual" not in page.split("fillOneVoice")[0],
         "no voice name is written into the page itself",
         "a voice name is hardcoded in the page")
    t.ok('id="scenPick"' in page and 'id="scenVoice"' in page
         and 'id="scenRate"' in page and "collectScenario" in page,
         "a scenario can be written, and given its own voice, on the page",
         "the Scenario card is missing a field")


def _mixed_line(t, make):
    """A line in two languages must be READ in two languages.

    User 2026-09-18: *make TTS can read all lang in the same time why it
    can't*. A voice from the per-language map is tied to its own language and
    reads the other half as nothing, so a mixed line borrows a voice that
    reads everything - named in tts.mixedVoice, or the first one the speech
    service itself reports.
    """
    cfg = {"tts": {"enabled": True, "language": "th",
                   "voices": {"th": "th-TH-PremwadeeNeural", "en": "en-US-JennyNeural"},
                   "mixedVoice": "en-US-AvaMultilingualNeural"}}
    b = make(json.loads(json.dumps(cfg)))
    t.eq(b.resolve_voice("", text="Hello พุฒิพงศ์, welcome")[1],
         "en-US-AvaMultilingualNeural",
         "a Thai name inside an English line is read by one voice that knows both")
    t.eq(b.resolve_voice("", text="สวัสดีครับ ยินดีต้อนรับ")[1], "th-TH-PremwadeeNeural",
         "a line in one language still uses that language's own voice")
    t.eq(b.resolve_voice("", text="Hello and welcome")[1], "en-US-JennyNeural",
         "and an English-only line is not moved off its voice either")


def _scenarios(t, make):
    """A scenario carries its own words AND its own sound.

    User 2026-09-18: *in senario i will promt what senario and the voice it
    run sound like that*. The name in `scenario` picks one out of
    `scenarios`; plain text there is still its own prompt, so an older store
    is not broken.
    """
    cfg = {"tts": {"enabled": True, "language": "th", "oneVoice": "en-US-EmmaMultilingualNeural",
                   "voices": {"th": "th-TH-PremwadeeNeural"}},
           "scenario": "Poem",
           "scenarios": [{"name": "Shop", "prompt": "A mall greeter.", "voice": "", "rate": ""},
                         {"name": "Poem", "prompt": "Answer in Thai verse.",
                          "voice": "en-US-AvaMultilingualNeural", "rate": "-15%",
                          "pitch": "+2Hz"}]}
    b = make(json.loads(json.dumps(cfg)))
    act = b.active_scenario()
    t.eq(act["prompt"], "Answer in Thai verse.", "the named scenario's words are the ones used")
    t.eq(act["rate"], "-15%", "a scenario can be read slower than the rest")
    t.eq(b.resolve_voice("th")[1], "en-US-AvaMultilingualNeural",
         "the scenario's voice wins over the one-voice setting")

    cfg2 = json.loads(json.dumps(cfg))
    cfg2["scenario"] = "Shop"
    b = make(cfg2)
    t.eq(b.resolve_voice("th")[1], "en-US-EmmaMultilingualNeural",
         "a scenario with no voice of its own falls back to the chosen one voice")

    # The model must be told the scenario's WORDS. Sending the name would
    # make the rig act out the word "Poem".
    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    body = src[src.find("    def generate(self, history"):][:1200]
    t.contains(body, 'self.active_scenario().get("prompt")',
               "the answering brain is given the scenario's words, not its name")

    old = {"tts": {"enabled": True, "language": "th",
                   "voices": {"th": "th-TH-PremwadeeNeural"}},
           "scenario": "พนักงานต้อนรับในศูนย์การค้า"}
    b = make(old)
    t.eq(b.active_scenario()["prompt"], "พนักงานต้อนรับในศูนย์การค้า",
         "a store written before scenarios existed still works")
