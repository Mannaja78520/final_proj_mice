"""Each voice job picks its own service, falls back, and never leaks a key.

A45-1, user 2026-10-19: *use Google AI Studio / Gemini by voice, and other
services too, keep a local backup*, then *make it fit the situation - any
service or local, not fixed to one*. config/voice.json `use` is an ordered
list per job (hear, think, speak); config/voice_providers.json says who can
do what. Bugs this holds, each one found in the code that came before:

  1. The Google answer path never sent the saved answers: a question one
     word off a saved one got a made-up reply. Every service now gets the
     same prompt as the local model - the nearest saved answer rides along.
  2. The Google key lived in config/voice.json, which GET /api/voice/config
     hands to anyone on the WiFi, in a public repo. Keys now live in a
     git-ignored file, an old key is moved there, and no read returns one.
  3. A cloud failure must not cost every next visitor the same timeout: a
     429 or a dead line rests that service and the backup answers at once.

Runs the real Brain against a fake service on 127.0.0.1 (both wire shapes:
Gemini's interactions and the OpenAI shape); no internet, no key.
"""
import base64
import importlib.util
import json
import os
import sys
import tempfile
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import qc as F

AREA = "tools"
TITLE = "each voice job picks its service, falls back at once, and keeps keys off the wire"

SAID = []                                    # every request the fake received
MODE = {"gemini": "ok"}


class Fake(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def do_POST(self):                       # noqa: N802
        body = self.rfile.read(int(self.headers.get("Content-Length") or 0))
        SAID.append({"path": self.path, "body": body,
                     "headers": {k.lower(): v for k, v in self.headers.items()}})
        if self.path.startswith("/gemini/interactions"):
            if MODE["gemini"] == "busy":
                return self._send(429, {"error": {"message": "quota"}})
            req = json.loads(body)
            if req.get("response_format", {}).get("type") == "audio":
                pcm = b"\x01\x00" * 2400                       # 0.1 s of headerless l16
                return self._send(200, {"steps": [{"type": "model_output", "content": [
                    {"type": "audio", "mime_type": "audio/l16", "sample_rate": 24000,
                     "data": base64.b64encode(pcm).decode()}]}]})
            if any(c.get("type") == "audio" for c in req["input"]):
                return self._send(200, {"steps": [{"type": "model_output",
                                                   "content": [{"type": "text", "text": "ห้องน้ำอยู่ไหน"}]}]})
            return self._send(200, {"steps": [
                {"type": "thought", "content": []},
                {"type": "model_output", "content": [{"type": "text", "text": "ห้องน้ำอยู่ชั้นสองครับ"}]}]})
        if self.path.endswith("/chat/completions"):
            return self._send(200, {"choices": [{"message": {"content": "ที่จอดรถอยู่ด้านหลังครับ"}}]})
        if self.path.endswith("/audio/transcriptions"):
            return self._send(200, {"text": "ที่จอดรถ ที่จอดรถ ที่จอดรถ อยู่ไหน"})
        return self._send(404, {})

    def _send(self, code, obj):
        b = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(b)))
        self.end_headers()
        self.wfile.write(b)


def _brain(tmp, cfg):
    os.environ["MICE_VOICE_KEYS"] = str(tmp / "voice_keys.json")
    path = F.CODE / "apps" / "voice" / "service.py"
    spec = importlib.util.spec_from_file_location("voice_services_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_services_check"] = mod
    spec.loader.exec_module(mod)
    mod.CODE = tmp                                       # sound cache lands in tmp
    (tmp / "apps" / "voice").mkdir(parents=True, exist_ok=True)
    (tmp / "voice.json").write_text(json.dumps(cfg, ensure_ascii=False), encoding="utf-8")
    (tmp / "qa.json").write_text(json.dumps({"faqs": [
        {"questions": ["ห้องน้ำอยู่ที่ไหน"], "answer": "ห้องน้ำอยู่ชั้นสองครับ"}]},
        ensure_ascii=False), encoding="utf-8")
    return mod, mod.Brain(tmp / "voice.json", tmp / "qa.json")


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_services_qc_"))
    srv = ThreadingHTTPServer(("127.0.0.1", 0), Fake)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    cfg = {"googleApiKey": "OLD-GOOGLE-KEY",
           "llm": {"enabled": False, "provider": "google_studio"},
           "stt": {"enabled": True, "language": "th"},
           "tts": {"enabled": True, "language": "th", "voices": {"th": "th-TH-PremwadeeNeural"}},
           "providers": {"gemini": {"base": base + "/gemini"},
                         "groq": {"base": base + "/groq"},
                         "typhoon": {"base": base + "/typhoon"}}}
    try:
        mod, b = _brain(tmp, cfg)
        prov = mod.providers

        # 2: an old key moves out of the store anyone can read
        t.eq(b.chain("think"), ["gemini", "local"],
             "the old Google switch still means Gemini first, this PC second")
        b.move_old_key()
        on_disk = (tmp / "voice.json").read_text(encoding="utf-8")
        t.ok("OLD-GOOGLE-KEY" not in on_disk and prov.read_keys().get("gemini") == "OLD-GOOGLE-KEY",
             "an old Google key moves from voice.json to the key file", on_disk[:200])
        view = json.dumps(b.services_view())
        t.ok("OLD-GOOGLE-KEY" not in view and b.services_view()["providers"]["gemini"]["hasKey"],
             "the page is told a key is saved, never the key", view[:300])
        t.ok(prov.keys_path().name == "voice_keys.json"
             and "main_python/voice_keys.json" in (F.CODE / ".gitignore").read_text(encoding="utf-8"),
             "the key file is one git never sees")

        # 1: Gemini answers with the saved answer in its prompt
        SAID.clear()
        got, why = b.generate([{"role": "user", "content": "ห้องน้ำอยู่ไหนครับ"}], lang="th")
        t.ok(got == "ห้องน้ำอยู่ชั้นสองครับ", "Gemini answers when it is first in line", repr((got, why)))
        sent = json.loads(SAID[-1]["body"]) if SAID else {}
        t.ok("ห้องน้ำอยู่ชั้นสองครับ" in str(sent.get("system_instruction")),
             "the nearest saved answer reaches the online service too",
             str(sent.get("system_instruction"))[:200])
        t.ok(SAID and SAID[-1]["headers"].get("x-goog-api-key") == "OLD-GOOGLE-KEY"
             and "key=" not in SAID[-1]["path"],
             "the key goes in a header, never in the address (addresses get logged)",
             SAID[-1]["path"] if SAID else "no call")
        t.eq(b.services_view()["last"]["think"]["by"], "gemini",
             "the page can say who answered")

        # 3: a busy service rests and the backup answers at once
        b.cfg["use"] = {"think": ["gemini", "groq", "local"], "hear": ["typhoon", "groq"],
                        "speak": ["gemini", "local"]}
        b.save_keys({"groq": "GROQ-KEY"})
        MODE["gemini"] = "busy"
        got, why = b.generate([{"role": "user", "content": "ที่จอดรถอยู่ไหน"}], lang="th")
        t.ok(got == "ที่จอดรถอยู่ด้านหลังครับ", "Gemini out of free use: Groq answers", repr((got, why)))
        n = len(SAID)
        got, _ = b.generate([{"role": "user", "content": "ที่จอดรถอยู่ไหน"}], lang="th")
        t.ok(got and not any(s["path"].startswith("/gemini") for s in SAID[n:]),
             "...and the next question does not wait on Gemini again",
             repr([s["path"] for s in SAID[n:]]))
        MODE["gemini"] = "ok"

        # hear: no key = passed over without a call; the OpenAI shape uploads the sound
        n = len(SAID)
        heard, why = b.listen(b"\x1aE\xdf\xa3" + b"\0" * 400, "th")
        t.ok(not any(s["path"].startswith("/typhoon") for s in SAID[n:]),
             "a service with no key is passed over without a call", repr(SAID[n:]))
        up = [s for s in SAID[n:] if s["path"].endswith("/audio/transcriptions")]
        t.ok(up and b'name="model"' in up[0]["body"] and b"whisper-large-v3-turbo" in up[0]["body"]
             and b'filename="speech.webm"' in up[0]["body"],
             "the sound goes up as a form with the model and the file", repr(up[:1])[:300])
        t.ok(heard and heard["text"] == "ที่จอดรถ อยู่ไหน" and heard["language"] == "th",
             "a phrase said over and over is the listener stuck, not the visitor", repr((heard, why)))

        # speak: Gemini's bare sound gets a header, and is kept under its own name
        b._rest.clear()
        got, why = b.say("ห้องน้ำอยู่ชั้นสองครับ", "th")
        t.ok(got and got[:4] == b"RIFF" and got[8:12] == b"WAVE",
             "Gemini's headerless sound is wrapped so the browser plays it", repr((got or b"")[:12]))
        n = len(SAID)
        again, _ = b.say("ห้องน้ำอยู่ชั้นสองครับ", "th")
        t.ok(again == got and len(SAID) == n, "the second time it is played from the cache")
        t.ok(b.voice_heard().get("natural") is True, "an online voice counts as natural")

        # a scenario leans on its own language (user 2026-10-19: a global event)
        b.cfg["tts"]["voices"]["en"] = "en-US-JennyNeural"
        b.cfg["scenarios"] = [{"name": "Global expo", "prompt": "x", "language": "en"}]
        b.cfg["scenario"] = "Global expo"
        t.ok(b.main_language() == "en" and b.resolve_voice("")[1] == "en-US-JennyNeural",
             "an event's own main language wins over the Voice tab's", repr(b.main_language()))
        b.cfg["scenario"] = ""
        t.eq(b.main_language(), "th", "...and without one, the Voice tab's main language")

        # the hub gates the key save like every save
        sys.path.insert(0, str(F.CODE / "main_python"))
        import hub_auth
        t.ok(hub_auth.gated("/api/voice/keys", "POST") and hub_auth.gated("/api/voice/unload", "POST"),
             "saving a key, and dropping the loaded models, need a login")
    finally:
        srv.shutdown()
        os.environ.pop("MICE_VOICE_KEYS", None)
