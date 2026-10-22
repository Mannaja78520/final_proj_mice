"""The last word is said to the end, and each event picks its manner (A45-26).

User 2026-10-22: *คำสุดท้ายมันจบไวไป ไม่มีลากเสียง ... ออกแค่ครึ่งคำแล้วหายไป*
and *เสียงรวบเกินฟังไม่รู้เรื่อง*. Measured on 30 clips of the feeling voice
(apps/voice/tts_spark): 16 had under 100 ms after the last sound and one
ended at full volume - the speaker and the browser drop the end of a buffer,
so the last word was heard cut in half. Now:

  * every clip ends in a quiet tail (`tailMs`) and starts with a short lead,
    the speech itself is kept whole (only a few-ms fade against a click);
  * a long line may be said piece by piece at Thai spaces with a pause
    (`split`, `pauseMs`), a lone short word joins its neighbour;
  * the knobs are DATA: the feeling speak job's `tune` in
    voice_providers.json, sent with each line, every key one the server
    knows - and a new tune is a new cache name, so a clip cut by the old
    settings is never replayed;
  * a scenario (one event) has its own speaking manner on the Voice page.

Whether the result sounds clear is measured by ear and by whisper in
scratch/voice-clear-2026-10-22 (PC only, not in git). Tested against fakes here.
"""
import importlib.util
import io
import json
import re
import wave

import qc as F

AREA = "tools"
TITLE = "the last word is said to the end, and each event picks its manner"


def _load(name, rel):
    spec = importlib.util.spec_from_file_location(name, F.CODE / rel)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


def _jsonc(rel):
    text = (F.CODE / rel).read_text(encoding="utf-8")
    return json.loads(re.sub(r"^\s*//.*$", "", text, flags=re.M))


def run(t):
    import numpy as np
    srv = _load("mice_tts_spark_tail", "apps/voice/tts_spark/server.py")
    rate = 16000
    tune = {"leadMs": 60, "tailMs": 450, "fadeMs": 6, "pauseMs": 180}
    loud = np.full(rate // 2, 0.5, dtype="float32")          # ends at full volume, like the cut clip
    wav = srv.to_wav({"rate": rate}, [loud], tune)
    with wave.open(io.BytesIO(wav)) as w:
        x = np.frombuffer(w.readframes(w.getnframes()), "<i2")
    lead, tail, fade = int(rate * .06), int(rate * .45), int(rate * .006)
    t.ok(len(x) == lead + len(loud) + tail, "the clip is lead + the whole speech + tail",
         "%d samples, wanted %d" % (len(x), lead + len(loud) + tail))
    t.ok(not x[-tail:].any() and not x[:lead].any(), "a quiet tail after the last word, a quiet lead before",
         "the end or start is not silent")
    body = x[lead + fade:lead + len(loud) - fade]
    t.ok(len(body) and int(body.min()) == int(0.5 * 32767), "the speech itself is not cut or faded",
         "the middle of the speech changed")
    two = srv.to_wav({"rate": rate}, [loud, loud], tune)
    t.ok(len(two) - len(wav) == 2 * (len(loud) + int(rate * .18)),
         "two pieces are joined by one pause", "%d bytes more" % (len(two) - len(wav)))

    got = srv.pieces("สวัสดีค่ะ ยินดีต้อนรับสู่งานของเรา นะคะ", 12)
    t.ok(got == ["สวัสดีค่ะ ยินดีต้อนรับสู่งานของเรา นะคะ"],
         "a lone short word joins its neighbour", repr(got))
    t.ok(srv.pieces("ห้องน้ำอยู่ชั้นหนึ่ง เดินตรงไปแล้วเลี้ยวซ้ายค่ะ", 12)
         == ["ห้องน้ำอยู่ชั้นหนึ่ง", "เดินตรงไปแล้วเลี้ยวซ้ายค่ะ"],
         "a long line is split where Thai takes a breath", "not split at the space")
    t.ok(srv.pieces("a b c", 0) == ["a b c"], "split 0 keeps one piece", "split 0 still split")

    provs = _jsonc("config/voice_providers.json")["providers"]
    feel = [p for p in provs.values() if p.get("kind") == "feeling"]
    job = feel[0]["jobs"]["speak"] if feel else {}
    t.ok(job.get("tune") and set(job["tune"]) <= set(srv.TUNE),
         "the feeling voice's tune is data, every key one the server knows",
         "tune %r, server knows %r" % (job.get("tune"), sorted(srv.TUNE)))
    t.ok((job.get("tune") or {}).get("tailMs", 0) >= 300,
         "the configured tail is long enough for a speaker to play the last word",
         "tailMs %r" % (job.get("tune") or {}).get("tailMs"))

    prov = _load("mice_voice_providers_tail", "apps/voice/providers.py")
    sent = {}
    prov._call = lambda url, body=None, **k: sent.update(body) or b"RIFF" + b"\0" * 200
    prov.feeling_speak({"base": "http://x"}, "", {"tune": {"tailMs": 450}}, "สวัสดี", "th", "", 5,
                       emotion="happy")
    t.ok(sent.get("tune") == {"tailMs": 450}, "the tune reaches the feeling server with the line",
         "sent %r" % sent)

    code = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    t.ok('"|tune=" + json.dumps(sjob["tune"]' in code,
         "a new tune is a new cache name: an old cut clip is never replayed",
         "the feeling cache name ignores the tune")

    page = (F.CODE / "apps" / "voice" / "index.html").read_text(encoding="utf-8")
    t.ok('id="scenStyle"' in page and "fillScenarioStyle" in page
         and len(re.findall(r'style: \(this\.\$\("scenStyle"\)', page)) == 2,   # new + saved
         "each event (scenario) picks its own speaking manner on the Voice page",
         "no manner box, or it is not saved with the scenario")
