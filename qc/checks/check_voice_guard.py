"""The voice helper answers programs only, and hands a robot sound it can play (A4-4).

THE HOLE (2026-09-29 review). The voice helper has no password and listens on
127.0.0.1:8767. A website open in this PC's browser can POST there without
asking - a text/plain body is a "simple" request - and POST /config picks
the language model the helper loads next, which may run its own code. /stop
and /unload were open the same way. Every browser request carries Origin or
Sec-Fetch-*, and a DNS-rebinding page names its own host in Host; the hub's
proxy, the hub's speaking queue and the face watcher send none of those. So
the helper now refuses them, and this holds it - asserting on the store that
was (not) written and on a helper still (not) running.

THE SOUND. The neural voices answer MP3, which a browser plays and a robot's
speaker cannot: it takes 16-bit PCM. The hub's queue asks /say for
`format: wav` and the helper decodes with PyAV (faster-whisper already brings
it). The browser path keeps MP3, and the cache keeps its key. Where PyAV is
missing the helper says so in plain words; this check says when it skipped
the decode half for that reason rather than passing it.
"""
import importlib.util
import io
import json
import math
import sys
import threading
import urllib.error
import urllib.request
import wave
from http.server import ThreadingHTTPServer

import qc as F

AREA = "tools"
TITLE = "the voice helper answers programs only, and hands a robot plain sound"


def _load():
    spec = importlib.util.spec_from_file_location(
        "voice_service_guard", F.CODE / "apps" / "voice" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _tone_wav(seconds=1.0, rate=24000, width=2):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(width)
        w.setframerate(rate)
        n = int(seconds * rate)
        if width == 2:
            w.writeframes(b"".join(int(8000 * math.sin(2 * math.pi * 440 * i / rate))
                                   .to_bytes(2, "little", signed=True) for i in range(n)))
        else:                                   # 8-bit is unsigned
            w.writeframes(bytes(128 + int(60 * math.sin(2 * math.pi * 440 * i / rate))
                                for i in range(n)))
    return buf.getvalue()


def _mp3(seconds=1.0, rate=24000):
    """A 440 Hz tone as MP3, or None when PyAV cannot encode one here."""
    try:
        import array
        import av
        buf = io.BytesIO()
        with av.open(buf, "w", format="mp3") as out:
            st = out.add_stream("libmp3lame", rate=rate)
            st.layout = "mono"
            n = int(seconds * rate)
            a = array.array("h", [int(8000 * math.sin(2 * math.pi * 440 * i / rate))
                                  for i in range(n)])
            for i in range(0, n, 1152):
                part = a[i:i + 1152]
                fr = av.AudioFrame(format="s16", layout="mono", samples=len(part))
                fr.planes[0].update(part.tobytes())
                fr.rate, fr.pts = rate, i
                for p in st.encode(fr):
                    out.mux(p)
            for p in st.encode(None):
                out.mux(p)
        return buf.getvalue()
    except Exception:                               # noqa: BLE001
        return None


def _ask(url, body=None, headers=None, method=None):
    req = urllib.request.Request(url, data=body, method=method or ("POST" if body is not None else "GET"))
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.headers.get("Content-Type", ""), r.read()
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get("Content-Type", ""), e.read()


def run(t):
    svc = _load()
    sound = {"bytes": _tone_wav()}
    stores = []

    class Brain:
        cfg = {"service": "http://127.0.0.1:8767", "llm": {"model": "the-real-one"}}
        cfg_path = "voice.json"
        faq_path = "qa.json"

        def maybe_reload(self):
            pass

        def health(self):
            return {"ok": True}

        def say(self, text, lang="", voice=""):
            return sound["bytes"], None

        def write_store(self, path, data):
            stores.append(data)

    svc.VoiceHandler.brain = Brain()
    srv = ThreadingHTTPServer(("127.0.0.1", 0), svc.VoiceHandler)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    base = "http://127.0.0.1:%d" % srv.server_address[1]
    evil = json.dumps({"config": {"llm": {"model": "someone/runs-code"}}}).encode()
    try:
        # ---- programs only ---------------------------------------------------
        code, _, _ = _ask(base + "/health")
        t.eq(code, 200, "a program on this PC is answered")
        for why, hdr in (("another website open on this PC", {"Origin": "https://evil.example"}),
                         ("the hub's own page, which must go through the hub",
                          {"Origin": "http://127.0.0.1:8765"}),
                         ("a browser request without Origin", {"Sec-Fetch-Site": "cross-site"}),
                         ("a DNS-rebinding page, by its own name",
                          {"Host": "evil.example:%d" % srv.server_address[1]})):
            code, _, body = _ask(base + "/config", evil,
                                 dict({"Content-Type": "text/plain"}, **hdr))
            t.ok(code == 403 and b"voice helper" in body,
                 "a settings change is refused from %s" % why, (code, body[:120]))
        t.eq(stores, [], "and nothing was written to the settings store")
        code, _, body = _ask(base + "/stop", b"{}", {"Origin": "https://evil.example"})
        code2, _, _ = _ask(base + "/health")
        t.ok(code == 403 and code2 == 200, "a website cannot switch the helper off",
             (code, code2))
        code, _, body = _ask(base + "/config", json.dumps({"config": {"scenario": "qc"}}).encode(),
                             {"Content-Type": "application/json"})
        t.ok(code == 200 and stores and stores[-1].get("scenario") == "qc",
             "the hub's proxy - a program - still saves settings", (code, body[:120]))
        code, _, body = _ask(base + "/health", headers={"Host": "[::1]:8767"})
        t.eq(code, 200, "an IP literal Host is fine (IPv6 too)")

        # ---- plain sound for a robot ------------------------------------------
        say = lambda fmt: _ask(base + "/say", json.dumps(dict({"text": "hello", "rate": 22050},
                                                             **({"format": fmt} if fmt else {})
                                                             )).encode(),
                               {"Content-Type": "application/json"})
        code, ctype, body = say("wav")
        t.ok(code == 200 and body == sound["bytes"],
             "a 16-bit WAV passes through untouched", (code, ctype, body[:12]))

        sound["bytes"] = _tone_wav(width=1)
        eight = sound["bytes"]
        mp3 = _mp3()
        if mp3 is None:
            print("SKIPPED the decode half: PyAV cannot encode MP3 on this PC, so there "
                  "is no neural-voice sound to decode. `pip install av` (faster-whisper "
                  "brings it) runs it.")
        else:
            code, ctype, body = say("wav")
            with wave.open(io.BytesIO(body)) as w:
                t.ok(w.getsampwidth() == 2, "an 8-bit WAV comes back as 16-bit, which the board plays")
            sound["bytes"] = mp3
            code, ctype, body = say(None)
            t.ok(code == 200 and body == mp3 and "mpeg" in ctype,
                 "the browser still gets the neural voice's MP3 as it was", (code, ctype))
            code, ctype, body = say("wav")
            ok = code == 200 and body[:4] == b"RIFF"
            if t.ok(ok, "asked for wav, the MP3 comes back as WAV", (code, ctype, body[:60])):
                with wave.open(io.BytesIO(body)) as w:
                    n, rate = w.getnframes(), w.getframerate()
                    shape = (w.getnchannels(), w.getsampwidth(), rate)
                    import array
                    a = array.array("h")
                    a.frombytes(w.readframes(n))
                t.eq(shape, (1, 2, 22050), "mono, 16-bit, at the rate the robot plays")
                t.ok(0.9 <= n / 22050.0 <= 1.2 and max(abs(x) for x in a) > 4000,
                     "the whole second of tone is in it (%.2fs, peak %d of 8000)"
                     % (n / 22050.0, max(abs(x) for x in a) if a else 0))
        real_av = sys.modules.get("av")
        sys.modules["av"] = None                # `import av` now fails, as on a bare PC
        try:
            wav, why = svc.plain_wav(mp3 or eight, 22050)
        finally:
            if real_av is None:
                sys.modules.pop("av", None)
            else:
                sys.modules["av"] = real_av
        t.ok(wav is None and "av package is missing" in (why or ""),
             "without PyAV the helper says what is missing, in plain words", why)
    finally:
        srv.shutdown()
        srv.server_close()
