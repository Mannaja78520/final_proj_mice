"""Speech-in reaches the helper honestly, and the recogniser is told right.

A20-7: local STT, never Thai-only - the language comes from the request hint,
else the store's stt.language, else it is DETECTED; bias words ride along per
language; adding a language is one entry in config/voice.json and no code.

This PC has no faster_whisper, so the heavy half is faked IN PROCESS while
everything around it runs for real:

  1. the route is GATED like every command that may move a rig;
  2. helper off / stt switched off -> plain words naming the switch;
  3. audio bytes travel the hub->helper hop untouched (JSON decoding them
     would destroy them - that was the trap);
  4. the recogniser call itself: hint beats store, store beats detect,
     detect passes NO prompt (it cannot know the language yet),
     condition_on_previous_text=False always, bias from the store,
     and the temp audio file does not leak.
"""
import io
import json
import os
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
import importlib.util
from pathlib import Path
from types import SimpleNamespace

import qc as F

AREA = "tools"
TITLE = "speech-in is gated, honest about being off, and tells the recogniser right"

PORT = F._free_port()


def boot_helper(cfg, tmp):
    log = open(tmp / "svc.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--port", str(PORT)],
        stdout=log, stderr=subprocess.STDOUT,
        env=dict(os.environ, PYTHONUNBUFFERED="1"))
    deadline = time.time() + 15
    while time.time() < deadline:
        try:
            with urllib.request.urlopen(
                    "http://127.0.0.1:%d/health" % PORT, timeout=2) as r:
                if json.loads(r.read()).get("ok"):
                    return proc
        except Exception:                           # noqa: BLE001
            time.sleep(0.3)
    proc.terminate()
    return None


def post_bytes(base, path, data, cookie=None):
    req = urllib.request.Request(base + path, data=data, method="POST")
    if cookie:
        req.add_header("Cookie", cookie)
    req.add_header("Content-Type", "audio/webm")
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def load_service_module():
    spec = importlib.util.spec_from_file_location(
        "mice_voice_service", F.CODE / "apps" / "voice" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


class FakeSeg:
    def __init__(self, text):
        self.text = text


class FakeInfo:
    language = "xx"


class FakeSTT:
    def __init__(self, texts=("hello ", "there")):
        self.texts = texts
        self.paths, self.kwargs = [], []

    def transcribe(self, path, **kw):
        self.paths.append(path)
        self.kwargs.append(kw)
        return iter([FakeSeg(t) for t in self.texts]), FakeInfo()


def run(t):
    # ---- the store under test: two languages as DATA -------------------
    tmp = Path(tempfile.mkdtemp(prefix="mice_stt_qc_"))
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % PORT,
        "faqThreshold": 0.75,
        "stt": {"enabled": False, "model": "small", "language": "",
                "languages": {
                    "th": {"bias": "ห้องน้ำ หุ่นยนต์"},
                    "en": {"bias": "toilet robot"}}},
        "llm": {"enabled": False}, "tts": {"enabled": False},
    }, ensure_ascii=False), encoding="utf-8")
    os.environ["MICE_VOICE_CONFIG"] = str(cfg)

    base, _main = F.start_hub()
    cookie = F.login(base)

    # ---- 1: the gate ---------------------------------------------------
    st, got = post_bytes(base, "/api/voice/transcribe", b"riff")
    t.eq(st, 401, "listening without logging in is refused")
    t.ok(got.get("need_login"), "...with the login request", json.dumps(got)[:100])

    # ---- 2+3: through the hub, the switch-off is what comes back -------
    proc = boot_helper(cfg, tmp)
    try:
        if not t.ok(proc is not None, "the real helper came up"):
            return
        st, got = post_bytes(base, "/api/voice/transcribe",
                             b"RIFFnot really audio", cookie)
        t.ok(not got.get("ok") and "off in config/voice.json" in got.get("error", ""),
             "stt switched off says so in plain words",
             json.dumps(got, ensure_ascii=False)[:150])
        st, got = post_bytes(base, "/api/voice/transcribe", b"", cookie)
        t.eq(st, 400, "an empty recording is refused before any model runs")

        st, body = F.get(base + "/api/voice/health")
        parts = (json.loads(body) or {}).get("parts", {})
        t.ok("stt" in parts, "health reports the speech half too",
             body[:150])
    finally:
        os.environ.pop("MICE_VOICE_CONFIG", None)
        if proc:
            proc.terminate()

    # ---- 4: what the recogniser is actually told (in process) ----------
    # The fake below STANDS IN for a loaded model, so this store copy says
    # enabled - A20-12 made the switch outrank whatever is cached, and an
    # off store must refuse before any model, real or fake, is asked.
    cfg_on = tmp / "voice_on.json"
    on = json.loads(cfg.read_text(encoding="utf-8"))
    on["stt"]["enabled"] = True
    cfg_on.write_text(json.dumps(on, ensure_ascii=False), encoding="utf-8")
    svc = load_service_module()
    brain = svc.Brain(cfg_on, tmp / "qa.json")
    fake = FakeSTT()
    brain._stt = fake

    got, err = brain.listen(b"RIFFdata", hint="th")
    t.ok(err is None and got["text"] == "hello there",
         "segments join into one transcript", repr((got, err)))
    k = fake.kwargs[-1]
    t.ok(k.get("condition_on_previous_text") is False,
         "each utterance stands alone (condition_on_previous_text=False)")
    t.eq(k.get("language"), "th", "the request hint wins")
    t.eq(k.get("initial_prompt"), "ห้องน้ำ หุ่นยนต์",
         "...and gets that language's bias words from the store")

    brain.listen(b"x")                       # no hint, store language empty
    t.ok(fake.kwargs[-1].get("language") is None,
         "store language empty means DETECT, not a hardcoded default")
    t.ok(fake.kwargs[-1].get("initial_prompt") is None,
         "detecting passes no bias prompt - it cannot know the language yet")
    t.ok(all(not os.path.exists(p) for p in fake.paths),
         "the temp audio files are cleaned up")

    fake2 = FakeSTT(texts=("", ""))
    brain._stt = fake2
    got, _err = brain.listen(b"x", hint="en")
    t.ok(got is not None and got["text"] == "",
         "an empty transcript comes back as data, not an exception")

    # ---- 5: the handler turns that into visitor words ------------------
    def handler_call(body, result):
        h = SimpleNamespace(brain=brain, path="/transcribe",
                            headers={"Content-Length": str(len(body))},
                            rfile=io.BytesIO(body))
        h._json = lambda obj, code=200: result.append((obj, code))
        svc.VoiceHandler.do_transcribe(h)
        return result[-1]

    out = []
    obj, code = handler_call(b"", out)
    t.ok("no sound arrived" in obj.get("error", ""),
         "empty body names what to do, before touching the model")
    obj, _code = handler_call(b"riff", out)
    t.ok(not obj.get("ok") and "say it again" in obj.get("error", ""),
         "a wordless recording asks the visitor to try again",
         json.dumps(obj, ensure_ascii=False)[:120])
