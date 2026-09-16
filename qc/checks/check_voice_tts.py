"""Speech-out speaks locally, honestly, and only once per sentence.

A20-9: edge-tts (cloud) and mpg123 are gone. The venue PC speaks with
Windows' own voice through apps/voice/tts.ps1 - no internet, no pip install.
The store maps language -> voice NAME, so a new language is one entry in
config/voice.json.

Real chain where the machine allows it, faked where it cannot:

  1. the route is GATED like every command;
  2. through the hub, a spoken answer comes back as audio/wav starting with
     RIFF (the hub used to force application/json on everything - the page
     would have received a download it refuses to play);
  3. the SECOND call for the same words is served from the cache file, not
     rebuilt (mtime unchanged);
  4. tts switched off -> plain words naming the switch; a language with no
     voice -> words telling where to add one;
  5. in process: the watcher's sync pre-builds saved answers and prunes only
     STALE strangers - today's dynamic model audio survives the night sweep,
     and the empty/no-voice refusals stay honest at handler level too.

The engine itself is probed first: on a PC without WinRT voices the real-
synthesis phases are skipped with a printed reason instead of lying green.
"""
import hashlib
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
TITLE = "speech-out is gated, local, cached, and honest when it cannot speak"

PORT = F._free_port()
CACHE = F.CODE / "apps" / "voice" / "tts_cache"


def boot_helper(cfg, tmp):
    log = open(tmp / "svc.log", "wb")
    proc = subprocess.Popen(
        [sys.executable, str(F.CODE / "apps" / "voice" / "service.py"),
         "--config", str(cfg), "--faq", str(tmp / "qa.json"),
         "--port", str(PORT)],
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


def post_json(base, path, obj, cookie=None):
    req = urllib.request.Request(
        base + path, data=json.dumps(obj).encode("utf-8"), method="POST")
    req.add_header("Content-Type", "application/json")
    if cookie:
        req.add_header("Cookie", cookie)
    try:
        with urllib.request.urlopen(req, timeout=120) as r:
            return r.status, dict(r.headers), r.read()
    except urllib.error.HTTPError as e:
        return e.code, dict(e.headers), e.read()


def load_service_module():
    spec = importlib.util.spec_from_file_location(
        "mice_voice_service_tts", F.CODE / "apps" / "voice" / "service.py")
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def engine_probe(tmp):
    """Can THIS PC actually synthesise? One honest word through tts.ps1."""
    out = tmp / "probe.wav"
    try:
        r = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
             "-File", str(F.CODE / "apps" / "voice" / "tts.ps1"),
             "-Text", "ok", "-Out", str(out)],
            capture_output=True, timeout=90)
    except (OSError, subprocess.TimeoutExpired):
        return False
    ok = (r.returncode == 0 and out.exists()
          and out.read_bytes()[:4] == b"RIFF")
    out.unlink(missing_ok=True)
    return ok


def run(t):
    tmp = Path(tempfile.mkdtemp(prefix="mice_tts_qc_"))
    (tmp / "qa.json").write_text(json.dumps({"faqs": [
        {"questions": ["what are your hours"],
         "answer": "We open at nine every morning."},
    ]}, ensure_ascii=False), encoding="utf-8")
    cfg = tmp / "voice.json"
    cfg.write_text(json.dumps({
        "service": "http://127.0.0.1:%d" % PORT,
        "faqThreshold": 0.75,
        "stt": {"enabled": False}, "llm": {"enabled": False},
        # A language with a voice AND one without: the map has to tell
        # them apart, not guess.
        "tts": {"enabled": True, "language": "th",
                "voices": {"th": "Microsoft Pattara", "en": ""}},
    }, ensure_ascii=False), encoding="utf-8")
    os.environ["MICE_VOICE_CONFIG"] = str(cfg)

    # -- static: the two halves of the voice address must agree ----------
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src.find("def voice_service_url")
    t.ok(i >= 0 and ":8767" in src[i:i + 1200],
         "a portless voice address resolves to the helper's default port",
         "the hub used to ask :80 while service.py answers on 8767 - "
         "same saved address, two different destinations (2026-08-26)")
    svc = (F.CODE / "apps/voice/service.py").read_text(encoding="utf-8")
    t.ok(".part%d" in svc and "_tmp_seq" in svc,
         "voice store saves use one temp name per writer",
         "threading server: two saves sharing one .part name can publish "
         "a half-written file")

    base, _main = F.start_hub()
    cookie = F.login(base)
    before = {p.name for p in CACHE.glob("*.wav")} if CACHE.is_dir() else set()

    # ---- 1: the gate ---------------------------------------------------
    st, _h, body = post_json(base, "/api/voice/say", {"text": "hello"})
    t.eq(st, 401, "making the rig speak without logging in is refused")
    t.ok(json.loads(body).get("need_login"),
         "...with the login request", body[:100])

    live = engine_probe(tmp)

    # ---- 2+3: sound through the hub, cached on the second ask ----------
    proc = None
    try:
        if live:
            proc = boot_helper(cfg, tmp)
            if t.ok(proc is not None, "the real helper came up"):
                st, h, wav = post_json(base, "/api/voice/say",
                                       {"text": "สวัสดีครับ"}, cookie)
                t.eq(st, 200, "a spoken answer arrives")
                t.eq(h.get("Content-Type"), "audio/wav",
                     "...typed as audio, not forced json")
                t.ok(wav[:4] == b"RIFF" and len(wav) > 44,
                     "...and is a real wave file", "%d bytes %r" % (len(wav), wav[:4]))

                key = hashlib.md5("Microsoft Pattara\nสวัสดีครับ"
                                  .encode("utf-8")).hexdigest()
                cached = CACHE / (key + ".wav")
                t.ok(cached.exists(),
                     "the answer was written to the cache under its md5",
                     str(cached))
                mtime = cached.stat().st_mtime
                _st, _h, wav2 = post_json(base, "/api/voice/say",
                                          {"text": "สวัสดีครับ"}, cookie)
                t.ok(wav2[:4] == b"RIFF"
                     and cached.stat().st_mtime == mtime,
                     "the second ask is served from the file, not rebuilt")

                st, h, body = post_json(base, "/api/voice/say",
                                        {"text": "hello there", "lang": "en"},
                                        cookie)
                t.ok(st == 200 and body[:4] == b"RIFF",
                     "a listed language with an EMPTY voice lets Windows "
                     "pick its own",
                     "%s %r" % (st, body[:60]))
        else:
            print("   (no usable speech engine on this PC - "
                  "real-synthesis phases skipped)")

        # ---- 4: switched off says so, through the hub ------------------
        off = tmp / "off.json"
        off.write_text(json.dumps({
            "service": "http://127.0.0.1:%d" % PORT,
            "stt": {"enabled": False}, "llm": {"enabled": False},
            "tts": {"enabled": False},
        }, ensure_ascii=False), encoding="utf-8")
        if proc:
            proc.terminate()
            proc = None
            time.sleep(0.5)
        os.environ["MICE_VOICE_CONFIG"] = str(off)
        proc = boot_helper(off, tmp)
        if t.ok(proc is not None, "the switched-off helper came up"):
            st, _h, body = post_json(base, "/api/voice/say",
                                     {"text": "hello"}, cookie)
            got = json.loads(body)
            t.ok(not got.get("ok")
                 and "switched off" in got.get("error", ""),
                 "speech-off is said in plain words",
                 body[:150])

        _st, body = F.get(base + "/api/voice/health")
        parts = (json.loads(body) or {}).get("parts", {})
        t.ok("tts" in parts, "health reports the speaking half too", body[:150])
    finally:
        os.environ["MICE_VOICE_CONFIG"] = str(cfg)
        if proc:
            proc.terminate()

    # ---- 5: in process - the map, the cache key, the watcher -----------
    svc = load_service_module()
    brain = svc.Brain(cfg, tmp / "qa.json")

    ident, name = brain.resolve_voice("")
    t.eq((ident, name), ("Microsoft Pattara", "Microsoft Pattara"),
         "the store language picks its voice from the map")
    ident_en, _n = brain.resolve_voice("en")
    t.ok(ident_en == "<windows default en>",
         "an empty name means WINDOWS picks for that language",
         repr(ident_en))
    p1 = brain._cache_path(ident, "same words")
    p2 = brain._cache_path(ident, "same words")
    p3 = brain._cache_path(ident, "other words")
    t.ok(p1 == p2 and p1 != p3,
         "the cache key follows the words, not the time of day")

    got, why = brain.say("   ")
    t.ok(got is None and "nothing to speak" in why,
         "empty text is refused before any engine runs", repr(why))

    def handler_call(obj_in, result):
        body = json.dumps(obj_in).encode("utf-8")
        h = SimpleNamespace(
            brain=brain, path="/say",
            headers={"Content-Length": str(len(body))},
            rfile=io.BytesIO(body))
        h._json = lambda o, code=200: result.append((o, code))
        svc.VoiceHandler.do_say(h)
        return result[-1]

    out = []
    obj, code = handler_call({}, out)
    t.eq(code, 400, "nothing to speak is refused before any engine runs")
    t.ok("nothing to speak" in obj.get("error", ""),
         "...in visitor words", json.dumps(obj)[:120])
    obj, _c = handler_call({"text": "hi", "lang": "xx"}, out)
    t.ok(not obj.get("ok") and "add one under tts" in obj.get("error", ""),
         "an unknown language tells where to fix it",
         json.dumps(obj, ensure_ascii=False)[:150])

    # the watcher: pre-build saved answers, prune only stale strangers
    CACHE.mkdir(exist_ok=True)
    real_say = brain.say
    built = []

    def fake_say(text, lang=""):
        i, _v = brain.resolve_voice(lang)
        p = brain._cache_path(i, text)
        p.write_bytes(b"RIFFfake")
        built.append(p.name)
        return b"RIFFfake", None

    brain.say = fake_say
    brain.sync_faq_audio()
    t.ok(built and all((CACHE / n).exists() for n in built),
         "sync pre-built every saved answer",
         "%d built" % len(built))

    stranger_old = CACHE / ("deadbeef_old.wav")
    stranger_new = CACHE / ("deadbeef_new.wav")
    stranger_old.write_bytes(b"RIFFold")
    stranger_new.write_bytes(b"RIFFnew")
    old_t = time.time() - 48 * 3600
    os.utime(stranger_old, (old_t, old_t))
    brain.sync_faq_audio()
    t.ok(not stranger_old.exists(),
         "yesterday's unclaimed audio is pruned by the sweep")
    t.ok(stranger_new.exists(),
         "today's dynamic model audio SURVIVES the sweep")
    for n in built:
        (CACHE / n).unlink(missing_ok=True)
    stranger_new.unlink(missing_ok=True)

    brain.say = real_say

    # ---- leave no generated audio or environment behind ----------------
    os.environ.pop("MICE_VOICE_CONFIG", None)
    if CACHE.is_dir():
        for p in CACHE.glob("*.wav"):
            if p.name not in before:
                p.unlink(missing_ok=True)
