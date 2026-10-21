"""What a question asks for beyond its words reaches the right answer (A45-24).

The 2026-10-21 acceptance run on the real helper (31 typed, 19 spoken
questions) found five things wrong. Each one is replayed here with the
audit's own words, against the real /ask route, in process:

  1. "สวัสดี Please answer in English: where is the restroom?" got Thai -
     the script of the words beat the request;
  2. "Read this aloud: ..." went to the model, which put the visitor's name
     in - the read path only knew Thai;
  3. "แต่งกลอน ... ใหม่" got a greeting, or the SAVED poem on the word กลอน;
  4. the spoken English word "parking" inside Thai came out "ปาร์กกิ้ง", so
     no saved answer fit and the model said "it is here";
  5. a Thai greeting then an English question was written as Thai words
     (restroom -> bedroom) and answered wrong.

The model and the listener are FAKED (a scripted _complete, _transcribe and
_language_share), because what is tested is the routing, the checks on the
model's verse and the rule that picks a second hearing - not whisper. The
real-audio replay of all 50 audit cases is private evidence in
scratch/voice-a45-24-2026-10-21 (not in git: recordings).
"""
import importlib.util
import json
import re
import shutil
import sys
import tempfile
import threading
import urllib.request
from http.server import ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "reply language, read-aloud, new verse, loanwords and mixed Thai-English hearing"

RESTROOM_TH = "เดินตรงไปจะเห็นป้ายห้องน้ำทางซ้ายครับ"
RESTROOM_EN = "Walk straight ahead, you will see the restroom sign on your left."
PARKING_TH = "ที่จอดรถอยู่ด้านหลังอาคารครับ"
WIFI_TH = "รหัสไวไฟคือ mice1234 ครับ"
OLD_POEM = "แล้วสอนว่าอย่าไว้ใจมนุษย์\nมันแสนสุดลึกล้ำเหลือกำหนด\nถึงเถาวัลย์พันเกี่ยวที่เลี้ยวลด\nก็ไม่คดเหมือนหนึ่งในน้ำใจคน"
GOOD_VERSE = ("หุ่นยนต์น้อยคอยยิ้มรับทุกท่าน\nทักทายกันด้วยใจอันสดใส\n"
              "ชวนเดินชมงานนี้ไม่ไกล\nขอให้ได้รอยยิ้มกลับบ้านไป")
FAQS = [
    {"questions": ["ห้องน้ำไปทางไหน", "where is the restroom", "where is the toilet"],
     "answer": RESTROOM_TH, "answer_en": RESTROOM_EN},
    {"questions": ["ที่จอดรถอยู่ที่ไหน", "parking อยู่ตรงไหน", "where is the parking"],
     "answer": PARKING_TH, "answer_en": "The car park is behind the building."},
    {"questions": ["รหัสไวไฟคืออะไร"], "answer": WIFI_TH, "answer_en": "The wifi password is mice1234."},
    {"questions": ["ท่องกลอนให้ฟังหน่อย", "บทกลอน", "recite a poem"], "answer": OLD_POEM,
     "answer_en": "A poem."},
    {"questions": ["hello", "hi", "สวัสดี"], "answer": "สวัสดีครับ", "answer_en": "Hello!",
     "wholeQuestion": True},
]


def _service():
    spec = importlib.util.spec_from_file_location(
        "mice_voice_service_intents", F.CODE / "apps" / "voice" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class Model:
    """A scripted local model: each call takes the next reply."""
    def __init__(self):
        self.replies, self.calls = [], []

    def complete(self, messages, max_tokens=None, details=False):
        self.calls.append(messages)
        reply = self.replies.pop(0) if self.replies else "สวัสดีครับ"
        return (reply, False) if details else reply


def _ask(port, text, **extra):
    body = json.dumps(dict({"text": text, "person": "ทดสอบ", "autoDetect": True}, **extra),
                      ensure_ascii=False).encode()
    req = urllib.request.Request("http://127.0.0.1:%d/ask" % port, data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=20) as r:
        return json.loads(r.read())


def _data_checks(t, intents):
    raw = (F.CODE / "config" / "voice_intents.json").read_text(encoding="utf-8")
    data = intents.table()
    pats = [p for ps in (data.get("replyLanguage") or {}).values() for p in ps]
    pats += list(data.get("readAloud") or []) + list((data.get("compose") or {}).get("patterns") or [])
    bad = [p for p in pats if intents._rx(p) is None]
    t.ok(pats and not bad, "every intent pattern in voice_intents.json compiles", bad[:2])
    # The comment remover drops a comma before } - "{3,}" became "{3}" once
    # and the English read-aloud matched nothing. Loaded must equal written.
    mangled = [p for p in pats if json.dumps(p, ensure_ascii=False)[1:-1] not in raw]
    t.ok(not mangled, "every pattern loads exactly as written in the file", mangled[:2])
    t.ok(all("(?P<text>" in p for p in data.get("readAloud") or []),
         "every read-aloud pattern names the part to read")
    for need in ("en", "th", "ja", "zh"):
        t.ok(need in (data.get("replyLanguage") or {}) and intents.compose_text("failed", need),
             "language %s can be asked for and has an honest verse sorry" % need)


def run(t):
    sys.path.insert(0, str(F.CODE / "apps" / "voice"))
    import intents
    _data_checks(t, intents)

    svc = _service()
    tmp = Path(tempfile.mkdtemp(prefix="qc_intents_"))
    try:
        cfg = tmp / "voice.json"
        cfg.write_text(json.dumps({
            "faqThreshold": 0.75, "faqAskAgain": 0, "presence": {"on": False},
            "face": {"on": False}, "stt": {"enabled": False}, "tts": {"enabled": False},
            "llm": {"enabled": True, "provider": "local", "model": "fake"},
        }, ensure_ascii=False), encoding="utf-8")
        faq = tmp / "qa.json"
        faq.write_text(json.dumps({"faqs": FAQS}, ensure_ascii=False), encoding="utf-8")
        brain = svc.Brain(str(cfg), str(faq))
        model = Model()
        brain._ensure_llm = lambda: (True, "")
        brain._complete = model.complete
        svc.VoiceHandler.brain = brain
        httpd = ThreadingHTTPServer(("127.0.0.1", 0), svc.VoiceHandler)
        port = httpd.server_address[1]
        threading.Thread(target=httpd.serve_forever, daemon=True).start()
        try:
            _routes(t, port, model)
            _verse(t, port, model, intents)
            _hearing(t, brain, svc)
            _jobs(t, brain)
        finally:
            httpd.shutdown()
            httpd.server_close()
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def _routes(t, port, model):
    got = _ask(port, "สวัสดี Please answer in English: where is the restroom?")
    t.ok(got.get("lang") == "en" and RESTROOM_EN in got.get("answer", ""),
         "1. Thai greeting + 'Please answer in English' answers in English", got)
    got = _ask(port, "Hello ช่วยตอบเป็นภาษาไทย where is the restroom?", lang="en")
    t.ok(got.get("lang") == "th" and RESTROOM_TH in got.get("answer", ""),
         "   and 'ตอบเป็นภาษาไทย' wins over English words and the hearing's language", got)
    got = _ask(port, "where is the restroom?")
    t.ok(got.get("lang") == "en" and RESTROOM_EN in got.get("answer", ""),
         "   a question with no request keeps its own language", got)

    before = len(model.calls)
    got = _ask(port, "Read this aloud: Hello, welcome to the robot demonstration.")
    t.ok(got.get("source") == "read" and got.get("answer") == "Hello, welcome to the robot demonstration."
         and got.get("lang") == "en",
         "2. 'Read this aloud:' reads the words exactly, in English, no name added", got)
    for said, want in (("ช่วยอ่าน: Hello ห้องน้ำทางไหนหรอจ๊ะ", "Hello ห้องน้ำทางไหนหรอจ๊ะ"),
                       ("อ่านกลอนนี้: " + OLD_POEM, OLD_POEM),
                       ("これを読んでください：こんにちは", "こんにちは"),
                       ("请朗读：欢迎光临", "欢迎光临")):
        got = _ask(port, said)
        t.ok(got.get("source") == "read" and got.get("answer") == want,
             "   read exactly: %s" % said[:20], got)
    t.eq(len(model.calls), before, "   and reading never asks the model")

    for said, want in (("ฮัลโหล ปาร์กกิ้ง อยู่ตรงไหนครับ", PARKING_TH),
                       ("ฮัลโหล พาร์คิง อยู่ตรงไหนครับ", PARKING_TH),
                       ("รหัสไวไฟคืออะไร", WIFI_TH)):
        got = _ask(port, said)
        t.ok(got.get("source") == "faq" and want in got.get("answer", ""),
             "4. Thai-letter loanword finds its saved answer: %s" % said, got)


def _verse(t, port, model, intents):
    model.replies = ["สวัสดีครับ คุณทดสอบ คุณรู้สึกว่าฝนตกหน่อยไหมครับ", GOOD_VERSE]
    got = _ask(port, "แต่งกลอนหุ่นยนต์สี่วรรค ไม่ใช้บทกลอนเดิม")
    t.ok(got.get("source") == "verse" and got.get("answer") == GOOD_VERSE,
         "3. 'แต่งกลอน...ไม่ใช้บทกลอนเดิม' is a NEW verse, not the saved poem; a greeting is retried", got)
    t.ok("ทดสอบ" not in got.get("answer", ""), "   and no name is pushed into the first line")
    t.ok(model.calls and "กลอน" in model.calls[-1][0]["content"],
         "   the model was told to write a verse", model.calls[-1][0]["content"][:60] if model.calls else "")
    cases = (("bullet list", "- เดินเข้าไปในห้อง\n- แสดงความยินดีต้อนรับ\n- ให้กำลังใจกันและกัน\n- แนะนำวิธีการใช้งาน"),
             ("saved poem", OLD_POEM),
             ("Chinese in Thai", "หุ่นยนต์น้อยคอยยิ้มรับทุกท่าน\nแสดงความ欢迎ด้วยใจอันสดใส\nชวนเดินชมงานนี้ไม่ไกล\nขอให้ได้รอยยิ้มกลับบ้านไป"),
             ("short lines", "ฝนตกหนาแน่น\nลมกระแทกสูง\nแสงสว่างผม\nความร้อนแรง"),
             ("three lines", "หุ่นยนต์น้อยคอยยิ้มรับทุกท่าน\nทักทายกันด้วยใจอันสดใส\nชวนเดินชมงานนี้ไม่ไกล"))
    sorry = intents.compose_text("failed", "th")
    for name, bad in cases:
        model.replies = [bad, bad]
        got = _ask(port, "ช่วยแต่งกลอนใหม่สี่วรรคเกี่ยวกับหุ่นยนต์ต้อนรับผู้คน")
        t.ok(got.get("answer") == sorry and got.get("source") == "verse",
             "   a %s is never spoken as a new verse: the honest sorry is" % name, got.get("answer"))
    model.replies = ["Rain taps softly on the glass\nGrey clouds wander slowly past\n"
                     "Puddles shine where children run\nWaiting for the morning sun"]
    got = _ask(port, "write a new poem about rain")
    t.ok(got.get("source") == "verse" and got.get("lang") == "en" and len(got["answer"].splitlines()) == 4,
         "   an English 'write a new poem' gets the English verse", got)
    got = _ask(port, "ท่องกลอนให้ฟังหน่อย")
    t.ok(got.get("source") == "faq" and OLD_POEM in got.get("answer", ""),
         "   'ท่องกลอน' still recites the SAVED poem", got.get("source"))


class Seg:
    def __init__(self, text):
        self.text, self.no_speech_prob = text, 0.0


def _hearing(t, brain, svc):
    """5. the second hearing: when, and which hearing wins."""
    calls = []

    def fake_transcribe(model, path, lang, scfg, prompt=None):
        calls.append((lang, prompt))
        return [Seg(heard[lang])], None
    brain._transcribe = fake_transcribe
    brain._own_model = lambda lang: None
    brain._stt = object()
    share = {"en": 0.98}
    brain._language_share = lambda path, lang, cs: share.get(lang, 0.0)

    heard = {"en": "where is the restroom."}
    text, lang = brain._code_switch("x.wav", "สวัสดี ไหนเป็นห้องหลังจากที่นั่งรอบนี้", "th", None, {})
    t.ok((text, lang) == ("where is the restroom.", "en"),
         "5. Thai greeting + English question: the English hearing wins", (text, lang))
    t.ok(calls and calls[-1][1] and "where is the restroom" in calls[-1][1],
         "   and it was given the saved English questions as its word hint", calls[-1:])
    heard = {"en": "so what do you where is the restroom."}
    t.eq(brain._code_switch("x.wav", "สวัสดี ไหนเป็นห้องหลังจากที่นั่งรอบนี้", "th", None, {})[1], "en",
         "   a partly wrong English hearing still wins when it is clearly closer")

    calls.clear()
    share["en"] = 0.01
    heard = {"en": "hello. where is the restroom."}
    t.eq(brain._code_switch("x.wav", "ฮัลโหลห้องน้ำทางไหนหรอจ๊ะ", "th", None, {}),
         ("ฮัลโหลห้องน้ำทางไหนหรอจ๊ะ", "th"),
         "   a clip that does not sound English keeps its Thai hearing (no translated reply)")
    t.eq(calls, [], "   and is not heard a second time")

    share["en"] = 0.98
    heard = {"en": "Hello"}
    t.eq(brain._code_switch("x.wav", "ฮัลโหล ไหนเป็นห้องนอน", "th", None, {})[1], "th",
         "   an English hearing that is only a greeting never wins")
    calls.clear()
    t.eq(brain._code_switch("x.wav", "ห้องน้ำไปทางไหน", "th", None, {})[0], "ห้องน้ำไปทางไหน",
         "   a Thai hearing that already fits a saved answer is kept")
    t.eq(brain._code_switch("x.wav", "ไหนเป็นห้องนอน", "th", "th", {})[0], "ไหนเป็นห้องนอน",
         "   a language picked on the page is respected")
    t.eq(calls, [], "   and neither is heard a second time")


def _jobs(t, brain):
    view = brain.services_view()
    t.ok("compose" in view["jobs"] and "compose" in view["providers"]["local"]["jobs"],
         "the Voice page lists Writing verse, and every service that thinks can do it")
    t.eq(brain.chain("compose"), brain.chain("think"),
         "unchosen, verse is written by whoever answers questions")
    brain.cfg["use"] = {"think": ["local"], "compose": ["groq", "local"]}
    t.eq(brain.chain("compose"), ["groq", "local"],
         "a stronger writer can be picked for verse alone (per situation)")
    brain.cfg.pop("use", None)
