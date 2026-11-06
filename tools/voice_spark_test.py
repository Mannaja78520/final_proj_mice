#!/usr/bin/env python3
"""Does a recorded reference make the feeling voice clearer than Edge? (whisper CER)

    python tools/voice_spark_test.py <clips_dir> <out_dir> --runtime <.local/tts_spark> \
        --variant A=clip_0001.wav,clip_0002.wav --variant B=clip_0009.wav [--gender male]

For every --variant: speaker.py (Spark venv) turns the clips into a speaker,
the running feeling server (127.0.0.1:8779, started here if down) says the
test sentences with it, and the Thai whisper hears them back. The same
sentences by Edge are the baseline. Prints one JSON of raw numbers
(sentence, heard text, CER %, seconds to make, seconds of audio).
CER = character edit distance / reference length, spaces and punctuation ignored.
The wavs it writes are in <out_dir> (under .local): they are a person's voice.
"""
import argparse
import asyncio
import json
import re
import subprocess
import sys
import time
import urllib.request
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
import registry  # noqa: E402
import voice_clips  # noqa: E402

PORT = 8779
SENTENCES = [
    "สวัสดีครับ ยินดีต้อนรับสู่ตู้มหัศจรรย์ วันนี้ให้ผมช่วยอะไรดีครับ",
    "ห้องน้ำอยู่ชั้นสองทางซ้ายมือ เดินตรงไปแล้วเลี้ยวซ้ายได้เลยครับ",
    "ขอบคุณที่มาร่วมสนุกกับเรา แล้วพบกันใหม่นะครับ",
]
EDGE = {"male": "th-TH-NiwatNeural", "female": "th-TH-PremwadeeNeural"}


def clean(text):
    return re.sub(r"[\s\W_]+", "", text)


def cer(ref, hyp):
    a, b = clean(ref), clean(hyp)
    row = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        new = [i]
        for j, cb in enumerate(b, 1):
            new.append(min(row[j] + 1, new[j - 1] + 1, row[j - 1] + (ca != cb)))
        row = new
    return 100.0 * row[-1] / max(len(a), 1)


def post(path, body, timeout=600):
    req = urllib.request.Request("http://127.0.0.1:%d%s" % (PORT, path), json.dumps(body).encode(),
                                 {"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def server_up(venv_python, runtime):
    def alive():
        try:
            urllib.request.urlopen("http://127.0.0.1:%d/health" % PORT, timeout=3).read()
            return True
        except OSError:
            return False
    if alive():
        return None
    proc = subprocess.Popen([venv_python, str(HERE.parent / "apps/voice/tts_spark/server.py"),
                             "--runtime", str(runtime), "--port", str(PORT), "--device", "cpu"],
                            creationflags=voice_clips.NO_WINDOW)
    for _ in range(300):
        time.sleep(2)
        if alive():
            return proc
    raise SystemExit("the feeling server did not start")


def seconds_of(wav):
    import io
    with wave.open(io.BytesIO(wav)) as w:
        return w.getnframes() / w.getframerate()


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("clips_dir")
    ap.add_argument("out_dir")
    ap.add_argument("--runtime", required=True)
    ap.add_argument("--variant", action="append", default=[], help="NAME=clip,clip")
    ap.add_argument("--gender", default="male")
    ap.add_argument("--temperature", type=float, default=0.3)
    a = ap.parse_args()
    out, runtime = Path(a.out_dir), Path(a.runtime)
    out.mkdir(parents=True, exist_ok=True)
    venv_python = str(runtime / "venv" / "Scripts" / "python.exe")
    voice_clips.cuda_libs()
    from faster_whisper import WhisperModel
    model_id = registry.load(registry.CODE / "config" / "voice_providers.json")[
        "providers"]["local"]["jobs"]["hear"]["byLanguage"]["th"]
    ear = WhisperModel(model_id, device="cpu", compute_type="int8", cpu_threads=16)

    def hear(path):
        return "".join(s.text for s in voice_clips.hear(ear, path, 1))

    rows = []

    def record(name, k, wav, made):
        path = out / ("%s_%d.wav" % (name, k))
        path.write_bytes(wav)
        heard = hear(path)
        rows.append({"voice": name, "sentence": SENTENCES[k], "heard": heard,
                     "cerPct": round(cer(SENTENCES[k], heard), 1), "madeSeconds": round(made, 1),
                     "audioSeconds": round(seconds_of(wav), 1)})
        print(rows[-1], flush=True)

    import edge_tts
    for k, text in enumerate(SENTENCES):
        mp3 = out / ("edge_%d.mp3" % k)
        t0 = time.time()
        asyncio.run(edge_tts.Communicate(text, EDGE[a.gender]).save(str(mp3)))
        made = time.time() - t0
        wav = out / ("edge_%d.wav" % k)
        subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", str(mp3), "-ac", "1", "-ar", "24000", str(wav)],
                       check=True, creationflags=voice_clips.NO_WINDOW)
        record("edge", k, wav.read_bytes(), made)

    proc = server_up(venv_python, runtime)
    try:
        for spec in a.variant:
            name, names = spec.split("=", 1)
            sp = out / ("speaker_%s.json" % name)
            subprocess.run([venv_python, str(HERE.parent / "apps/voice/tts_spark/speaker.py"), a.clips_dir,
                            "--runtime", str(runtime), "--names", *names.split(","), "--out", str(sp)],
                           check=True, creationflags=voice_clips.NO_WINDOW)
            tokens = json.loads(sp.read_text(encoding="utf-8"))["speaker"]
            for k, text in enumerate(SENTENCES):
                t0 = time.time()
                wav = post("/speak", {"text": text, "emotion": "neutral", "speaker": tokens,
                                      "gender": a.gender, "tune": {"temperature": a.temperature}})
                record("spark_" + name, k, wav, time.time() - t0)
    finally:
        if proc:
            proc.terminate()
    by = {}
    for r in rows:
        by.setdefault(r["voice"], []).append(r["cerPct"])
    print(json.dumps({"meanCerPct": {k: round(sum(v) / len(v), 1) for k, v in by.items()}, "rows": rows},
                     ensure_ascii=False, indent=1))


if __name__ == "__main__":
    main()
