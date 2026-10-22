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
                    "voices": {"th": "th-TH-PremwadeeNeural", "en": "en-US-JennyNeural"}},
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
        # Hermetic: a real feeling server may run on this PC (it does once
        # deployed). It is "off" here unless a case turns it on.
        brain.feeling_ready = lambda pid, prov: False
        _choice(t, brain)
        _edge(t, brain, cache)
        _others(t, brain, svc)
        _feeling(t, brain, svc, tmp)
        _sassy(t, brain)
        _http(t, brain, svc)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _choice(t, brain):
    styles = brain.styles().get("styles") or {}
    for key in ("polite", "friendly", "playful", "coaxing", "recite"):
        s = styles.get(key) or {}
        t.ok(s.get("says") and s.get("instruct") and "prosody" in s,
             "manner %s has a name, words for a service that takes them, and speed/pitch" % key)
    t.eq(brain.style_choice()[0], "", "no manner set = speaks as before (the pick is only recommended)")
    t.eq(brain.styles().get("recommended"), "friendly", "the Voice page recommends friendly (user: pick one)")
    brain.cfg["tts"]["style"] = "polite"
    t.eq(brain.style_choice()[0], "polite", "tts.style picks the manner")
    brain.cfg["scenario"] = "fair"
    t.eq(brain.style_choice()[0], "friendly", "an event's own manner beats tts.style")
    t.eq(brain.style_choice("playful")[0], "playful", "a request's manner beats both")
    t.eq(brain.style_choice("")[0], "", "a request for no manner is no manner")
    t.eq(brain.style_choice("shouty")[0], "", "an unknown manner is none, never a silent voice")
    brain.cfg.pop("scenario", None)
    brain.cfg["tts"].pop("style", None)
    # Expected values come from the data (manner speeds were retuned 2026-10-22).
    fr, pl = styles["friendly"]["prosody"], styles["playful"]["prosody"]
    t.eq(brain.style_steps("+5%", "+0Hz", styles["friendly"]),
         ("%+d%%" % (5 + fr["rate"]), "%+dHz" % fr["pitch"]),
         "speed and pitch steps are ADDED to the chosen ones")
    t.eq(brain.style_steps("+49%", "-28Hz", styles["playful"]),
         ("%+d%%" % min(50, 49 + pl["rate"]), "%+dHz" % (-28 + pl["pitch"])),
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
    pl = brain.styles()["styles"]["playful"]["prosody"]
    t.ok(sound and sound != plain
         and got[-1] == ("th-TH-PremwadeeNeural", "%+d%%" % pl["rate"], "%+dHz" % pl["pitch"]),
         "playful reaches Edge as its speed and pitch, and is a NEW sound, not the cached plain one",
         (why, got[-1:]))
    t.eq(brain._style_done, {"style": "playful", "how": "prosody", "by": "edge"},
         "and it is recorded as speed and pitch only")
    import threading
    other = threading.Thread(target=lambda: brain.say("อีกบรรทัดหนึ่ง", "th", style="coaxing"))
    other.start()
    other.join()
    t.eq(brain._style_done.get("style"), "playful",
         "another thread's line (the saved-answer sweep) never rewrites this line's record")
    n = len(got)
    again, _ = brain.say("สวัสดีครับ", "th", style="playful")
    t.ok(again == sound and len(got) == n, "the same manner again comes from its own cache")
    coax, _ = brain.say("สวัสดีครับ", "th", style="coaxing")
    t.ok(coax not in (sound, plain), "another manner is another sound")
    brain.cfg["tts"]["rate"] = "+49%"
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


def _feeling(t, brain, svc, tmp):
    """The Thai voice with feeling: first while a manner is on, Thai only,
    told the manner's feeling; asleep or missing = the backup speaks."""
    styles = brain.styles()["styles"]
    brain.cfg["use"] = {"speak": ["edge", "local"]}
    # A45-26 (user 2026-10-22: clear first): the shipped data prefers nothing,
    # so a manner keeps the chosen, clearer order.
    t.eq(brain.speak_order("playful"), ["edge", "local"],
         "clarity first: a manner keeps the chosen order unless the data prefers a service")
    real = brain.styles()
    mtime = brain._styles[0]
    data = json.loads(json.dumps(real))
    data["prefer"] = ["feeling"]
    data["styles"]["polite"]["prefer"] = []
    brain._styles = (mtime, data)              # same mtime: kept until the file changes
    t.eq(brain.speak_order("playful")[:2], ["feeling", "edge"],
         "a preferred service goes first, the chosen order stays as backup")
    t.eq(brain.speak_order("polite"), ["edge", "local"],
         "a manner's own prefer wins over the shared one")
    data["styles"]["polite"].pop("prefer")
    t.eq(brain.speak_order(""), ["edge", "local"], "no manner: the chosen order exactly")
    told = []

    def fake_feel(prov, key, job, text, lang, voice, timeout, style="", emotion=""):
        told.append((text, emotion))
        return b"RIFF" + bytes([len(told)]) * 400, None
    real_feel = svc.providers.feeling_speak
    svc.providers.feeling_speak = fake_feel
    brain.feeling_ready = lambda pid, prov: True
    try:
        for key in ("friendly", "coaxing", "polite"):
            snd, why = brain.say("ยินดีต้อนรับครับ", "th", style=key)
            t.ok(snd and told and told[-1] == ("ยินดีต้อนรับครับ", styles[key]["emotion"]),
                 "%s reaches the feeling voice as the feeling %r" % (key, styles[key]["emotion"]), (why, told[-1:]))
        t.eq(brain._style_done, {"style": "polite", "how": "emotion", "by": "feeling"},
             "and it is recorded as a real feeling")
        n = len(told)
        snd, _ = brain.say("Welcome to the show", "en", style="friendly")
        t.ok(snd and len(told) == n and brain._style_done.get("by") == "edge",
             "an English line skips the Thai-only feeling voice; Edge says it", brain._style_done)
        brain.feeling_ready = lambda pid, prov: False
        snd, why = brain.say("สวัสดีตอนบ่าย", "th", style="friendly")
        t.ok(snd and brain._style_done.get("by") == "edge",
             "feeling voice asleep or not installed: the line is still said, by Edge", (why, brain._style_done))
    finally:
        svc.providers.feeling_speak = real_feel
        brain.feeling_ready = lambda pid, prov: False

    # Its install is NOT under apps/: the hub serves every file there to the
    # WiFi with no login (check_faces_secret caught the first layout).
    st = brain.service("feeling")["jobs"]["speak"]["start"]
    places = list(st["python"]) + list((st.get("env") or {}).values())
    t.ok(places and not any(str(x).replace("\\", "/").startswith("apps/") for x in places),
         "the feeling voice's venv and models live outside the served apps folder", places)
    # the start command is DATA: built from the registry, nothing hard-coded
    started = []

    class FakeProc:
        def poll(self):
            return None
    real_popen = svc.subprocess.Popen
    svc.subprocess.Popen = lambda cmd, **kw: started.append((cmd, kw)) or FakeProc()
    try:
        prov = dict(brain.service("feeling"))
        job = dict(prov["jobs"]["speak"])
        job["start"] = dict(job["start"], python=[sys.executable], script=str(Path(__file__)))
        prov["jobs"] = {"speak": job}
        prov["base"] = "http://127.0.0.1:9"            # nothing listens: asleep
        ready = svc.Brain.feeling_ready(brain, "feeling", prov)
        t.ok(not ready and started and "--port" in started[0][0] and "8779" in started[0][0]
             and started[0][1]["env"].get("HF_HOME", "").endswith("hf"),
             "an asleep feeling voice is started from the registry's start command", started[:1])
        again = svc.Brain.feeling_ready(brain, "feeling", prov)
        t.ok(not again and len(started) == 1, "and not started twice while it loads")
        job["start"] = dict(job["start"], python=[str(tmp / "no-such-python.exe")])
        brain._feeling_proc = {}
        svc.Brain.feeling_ready(brain, "feeling", prov)
        t.ok("not installed" in brain._feeling_why.get("feeling", ""),
             "not installed says how to install it", brain._feeling_why)
    finally:
        svc.subprocess.Popen = real_popen


def _sassy(t, brain):
    """User 2026-10-21: *ขอจริตแบบฟาดๆด้วยหน่อยแบบเจ๊*. The manner's `answer`
    reaches the MODEL's prompt and the guards that fix its Thai, and (opt-in
    `saved`) the ending of saved answers - nothing else changes."""
    s = brain.styles()["styles"].get("sassy") or {}
    t.ok(s.get("emotion") and s.get("answer", {}).get("pronoun") == "เจ๊",
         "the sassy เจ๊ manner is data: a feeling, an ending and a self-word")
    brain.cfg["tts"]["style"] = "sassy"
    try:
        system, _limit, _v = brain._think_prompt([{"role": "user", "content": "ทดสอบ"}], "th", "", "")
        t.ok("'ค่ะ'" in system and "'เจ๊'" in system and s["answer"]["wording"]["th"] in system,
             "the model is told to end ค่ะ, call itself เจ๊ and speak sassy", system[:200])
        t.ok("ห้ามใช้คำลงท้ายอื่น เช่น ค่ะ" not in system and "ห้ามใช้ ผม หรือ ฉัน หรือ ดิฉัน" in system,
             "and is not told the opposite in the next breath", system[:260])
        en, _l, _v = brain._think_prompt([{"role": "user", "content": "hi"}], "en", "", "")
        t.ok(s["answer"]["wording"]["en"] in en, "English answers get the manner's English line")
        t.eq(brain.tidy_answer("ผมว่าอากาศดีครับ", "th"), "เจ๊ว่าอากาศดีค่ะ",
             "a model answer that slipped back to ผม/ครับ is put in the manner's words")
        t.eq(brain.manner_saved("เดินตรงไปจะเห็นป้ายห้องน้ำทางซ้ายครับ", "th"),
             "เดินตรงไปจะเห็นป้ายห้องน้ำทางซ้ายค่ะ", "a saved answer's ending follows (answer.saved)")
        t.eq(brain.manner_saved("Walk straight ahead.", "en"), "Walk straight ahead.",
             "an English saved answer is left alone")
        real = brain.styles
        plain = json.loads(json.dumps(real()))
        plain["styles"]["sassy"]["answer"].pop("saved", None)
        brain.styles = lambda: plain
        t.eq(brain.manner_saved("ทางซ้ายครับ", "th"), "ทางซ้ายครับ",
             "without answer.saved a saved answer keeps its own ending")
        brain.styles = real
    finally:
        brain.cfg["tts"]["style"] = ""
    t.eq(brain.tidy_answer("ผมว่าอากาศดีครับ", "th"), "ผมว่าอากาศดีครับ",
         "no manner: the store's ผม/ครับ, exactly as before")
    t.eq(brain.manner_saved("ทางซ้ายครับ", "th"), "ทางซ้ายครับ", "and saved answers untouched")


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
