"""Three tones to click, a fast speed, and saved women's and men's voices (A45-29).

User 2026-10-22: *โทนแบบเลือกได้ คลิกเป็น default ได้ซัก 3 โทน และขอมีแบบเร็ว
... เลือกเสียงได้ทั้งชายและหญิง* and *default clear ยังดูเป็น AI*, then *เร็วขึ้น
ได้แต่ไม่รวบคำ*. The Thai feeling voice copied its speaker from an Edge clip
(so it sounded like Edge). Prompted without one, the model invents its own
speaker: 32 global tokens. The clearest invented voices, judged by the Thai
whisper in scratch/voice-human-2026-10-22 (PC only), are DATA in
config/voice_people.json. This check holds:

  * every saved voice has a gender, 32 speaker tokens and a same-gender
    Edge backup; the helper lists it as "person:<id>" with its gender;
  * a line for a saved voice goes to the feeling voice FIRST with that
    speaker and the chosen speed as a tempo, its own cache name per voice
    and speed; feeling voice down = the backup Edge voice says it;
  * the server takes a speaker per request (and refuses a wrong one), and
    a tempo really changes the length, not the words;
  * `featured` names three known tones and `speeds` has a fast one, sent
    to the page; the page draws tiles that SAVE on click.

Whether a voice sounds human is a human judgement; tested against fakes.
"""
import importlib.util
import io
import json
import re
import shutil
import tempfile
import wave
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "three tones to click, a fast speed, and saved women's and men's voices"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def run(t):
    svc = _load("mice_voice_service_people", "apps/voice/service.py")
    tmp = Path(tempfile.mkdtemp(prefix="qc_people_"))
    try:
        cfg = tmp / "voice.json"
        cfg.write_text(json.dumps({
            "presence": {"on": False}, "face": {"on": False}, "stt": {"enabled": False},
            "llm": {"enabled": False},
            "tts": {"enabled": True, "rate": "+20%", "pitch": "+0Hz",
                    "voices": {"th": "th-TH-PremwadeeNeural", "en": "en-US-JennyNeural"}},
            "use": {"speak": ["edge", "local"]}}), encoding="utf-8")
        faq = tmp / "qa.json"
        faq.write_text(json.dumps({"faqs": []}), encoding="utf-8")
        brain = svc.Brain(str(cfg), str(faq))
        cache = tmp / "cache"
        cache.mkdir()
        real_path = brain._cache_path
        brain._cache_path = lambda ident, text, rate=None, pitch=None: cache / (
            real_path(ident, text, rate, pitch).name)
        brain.feeling_ready = lambda pid, prov: False
        _data(t, brain)
        _say(t, brain, svc)
        _agree(t, brain)
        _quick(t, brain)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)
    _server(t)
    _page(t)


def _data(t, brain):
    people = brain.people().get("people") or {}
    t.ok({p.get("gender") for p in people.values()} >= {"female", "male"},
         "there are saved voices for women AND men", sorted(people))
    bad = [k for k, p in people.items()
           if p.get("gender") not in ("female", "male") or len(p.get("speaker") or []) != 32
           or not all(isinstance(v, int) for v in p.get("speaker") or [])
           or "Neural" not in str(p.get("backup") or "") or not p.get("languages")]
    t.ok(not bad, "every saved voice has a gender, 32 speaker tokens, a backup voice and its languages", bad)
    rows = brain.voices_by_lang().get("th") or []
    own = [r for r in rows if r.get("own")]
    t.ok(len(own) == len([p for p in people.values() if "th" in p["languages"]])
         and all(r["name"].startswith("person:") and r["gender"] in ("Female", "Male") for r in own),
         "the Thai voice list offers every saved voice, with its gender", own[:2])
    t.ok(abs(brain.tempo_of("+20%") - 1.2) < 1e-9 and abs(brain.tempo_of("-10%") - 0.9) < 1e-9
         and brain.tempo_of("") == 1.0, "a speed of +20% is a tempo of 1.2")


def _say(t, brain, svc):
    people = brain.people()["people"]
    pid = next(k for k, p in people.items() if p["gender"] == "male")
    brain.cfg["tts"]["voices"]["th"] = "person:" + pid
    t.eq(brain.speak_order("", brain.person("person:" + pid))[:1], ["feeling"],
         "a saved voice puts the feeling voice first")
    told, edged = [], []

    def fake_feel(prov, key, job, text, lang, voice, timeout, style="", emotion="", person=None, tempo=1.0):
        told.append((person and person.get("speaker"), person and person.get("gender"), tempo))
        return b"RIFF" + bytes([len(told)]) * 400, None
    real = svc.providers.feeling_speak
    svc.providers.feeling_speak = fake_feel
    brain._edge_speak = lambda voice, text, rate, pitch: edged.append(voice) or (b"ID3" + b"\x05" * 400, None)
    try:
        brain.feeling_ready = lambda pid_, prov: True
        a, why = brain.say("สวัสดีครับ", "th")
        t.ok(a and told and told[-1][0] == people[pid]["speaker"] and told[-1][1] == "male"
             and abs(told[-1][2] - 1.2) < 1e-9,
             "the line reaches the feeling voice with that speaker, its gender and the speed as tempo",
             (why, told[-1:]))
        other = next(k for k in people if k != pid)
        brain.cfg["tts"]["voices"]["th"] = "person:" + other
        b, _ = brain.say("สวัสดีครับ", "th")
        t.ok(b and b != a, "another saved voice is another sound, never the first one's cache")
        brain.cfg["tts"]["rate"] = "+0%"
        c, _ = brain.say("สวัสดีครับ", "th")
        t.ok(c and c != b, "another speed is another sound too")
        brain.feeling_ready = lambda pid_, prov: False
        brain.cfg["tts"]["voices"]["th"] = "person:" + pid
        d, why = brain.say("ขอบคุณครับ", "th")
        t.ok(d and edged and edged[-1] == people[pid]["backup"],
             "feeling voice off: its same-gender backup voice says the line", (why, edged[-1:]))
    finally:
        svc.providers.feeling_speak = real
        brain.feeling_ready = lambda pid_, prov: False
        brain.cfg["tts"]["voices"]["th"] = "th-TH-PremwadeeNeural"
    prov = _load("mice_voice_providers_people", "apps/voice/providers.py")
    sent = {}
    prov._call = lambda url, body=None, **k: sent.update(body) or b"RIFF" + b"\0" * 200
    prov.feeling_speak({"base": "http://x"}, "", {"tune": {"tailMs": 450}}, "x", "th", "", 5,
                       person={"speaker": [1] * 32, "gender": "male"}, tempo=1.2)
    t.ok(sent.get("speaker") == [1] * 32 and sent.get("gender") == "male"
         and sent.get("tune") == {"tailMs": 450, "tempo": 1.2},
         "the speaker, gender and tempo go to the server with the line", sent)


def _agree(t, brain):
    """User 2026-10-22: *เสียงไทยชายหญิงมันมีลงท้ายต่างกัน ครับ/ค่ะ ทำให้ตรงกับภาษา*."""
    people = brain.people()["people"]
    man = next(k for k, p in people.items() if p["gender"] == "male")
    woman = next(k for k, p in people.items() if p["gender"] == "female")
    words = brain.people()["agree"]["th"]
    brain.cfg["tts"]["voices"]["th"] = "person:" + woman
    t.ok(brain.manner_answer("th")[:2] == (words["female"]["particle"], words["female"]["pronoun"]),
         "a woman's voice: model answers end with ค่ะ and say ดิฉัน", brain.manner_answer("th")[:2])
    said = brain.manner_saved("ผมช่วยได้ครับ เชิญทางนี้ครับ", "th")
    t.ok(said == "ดิฉันช่วยได้ค่ะ เชิญทางนี้ค่ะ", "and a saved answer is said with her ending too", said)
    brain.cfg["tts"]["voices"]["th"] = "person:" + man
    t.ok(brain.manner_answer("th")[:2] == ("ครับ", "ผม"), "a man's voice: ครับ and ผม",
         brain.manner_answer("th")[:2])
    t.ok(brain.manner_saved("ดิฉันช่วยได้ค่ะ", "th") == "ผมช่วยได้ครับ", "and his saved answers end with ครับ")
    t.ok(brain.agree_text("ยินดีต้อนรับครับ", "th", "person:" + woman) == "ยินดีต้อนรับค่ะ"
         and brain.agree_text("Hello", "en", "person:" + woman) == "Hello",
         "Try plays a sample in THAT voice's ending; other languages untouched")
    brain.cfg["tts"]["style"] = "sassy"
    own = (brain.styles()["styles"]["sassy"].get("answer") or {}).get("particle")
    t.ok(own and brain.manner_answer("th")[0] == own,
         "a manner with its own ending (the เจ๊ manner) still wins over the voice's", brain.manner_answer("th"))
    brain.cfg["tts"].pop("style", None)
    brain.cfg["tts"]["voices"]["th"] = "th-TH-PremwadeeNeural"


def _quick(t, brain):
    v = brain.styles_view()
    styles = brain.styles()["styles"]
    t.ok(len(v.get("featured") or []) == 3 and all(k in styles for k in v["featured"]),
         "three known tones are offered as the quick choice", v.get("featured"))
    sp = v.get("speeds") or {}
    rates = [int(re.sub(r"[^0-9+-]", "", s.get("rate") or "0") or 0) for s in sp.values()]
    t.ok(len(sp) >= 2 and max(rates) > 0 and 0 in rates,
         "the speeds include normal and a faster one", sp)


def _server(t):
    import numpy as np
    srv = _load("mice_tts_spark_people", "apps/voice/tts_spark/server.py")
    x = np.sin(np.linspace(0, 800, 16000)).astype("float32") * 0.5
    t.ok(srv.stretch(x, 16000, 1.0) is x, "tempo 1 leaves the sound as it is")
    if shutil.which("ffmpeg"):
        y = srv.stretch(x, 16000, 1.25)
        t.ok(abs(len(y) - len(x) / 1.25) < 400, "tempo 1.25 makes it 1.25 times shorter",
             "%d -> %d samples" % (len(x), len(y)))
        fast = srv.to_wav({"rate": 16000}, [x], {"leadMs": 0, "tailMs": 0, "fadeMs": 0, "pauseMs": 0,
                                                "tempo": 1.25})
        with wave.open(io.BytesIO(fast)) as w:
            t.ok(abs(w.getnframes() - len(x) / 1.25) < 400, "a tempo in the tune reaches the sound",
                 "%d frames" % w.getnframes())
    code = (F.CODE / "apps" / "voice" / "tts_spark" / "server.py").read_text(encoding="utf-8")
    t.ok('"that voice is not one this server can use"' in code and "ref)" in code,
         "the server takes a speaker per request and refuses a wrong one")
    wav = srv.to_wav({"rate": 16000}, [x], {"leadMs": 0, "tailMs": 0, "fadeMs": 0, "pauseMs": 0, "tempo": 1.0})
    with wave.open(io.BytesIO(wav)) as w:
        t.ok(w.getnframes() == len(x), "no tempo in the tune = the same length")


def _page(t):
    page = (F.CODE / "apps" / "voice" / "index.html").read_text(encoding="utf-8")
    t.ok(all('id="%s"' % i in page for i in ("toneTiles", "speedTiles", "voiceTiles")),
         "the Voice tab has the tone, speed and voice tiles")
    t.ok("fillQuick" in page and re.search(r"quickSave\(said\)\{\s*const ok = await this\.postConfig", page)
         and page.count("this.quickSave(") >= 3,
         "a click on a tone, a speed or a voice saves it")
    t.ok('"Female", "Women"' in page and '"Male", "Men"' in page,
         "the voices are shown as women and men")
