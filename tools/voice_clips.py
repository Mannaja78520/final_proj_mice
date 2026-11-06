#!/usr/bin/env python3
"""Cut a long recording of one person into clean speech clips, measure and rank them.

    python tools/voice_clips.py cut        <recording> <out_dir>
    python tools/voice_clips.py transcribe <out_dir>        (Thai whisper, writes clips.json)
    python tools/voice_clips.py rank       <out_dir>        (marks `keep`, orders by `rank`)

Every number comes from config/voice_clips.json (cut/keep). The audio, the
transcripts and clips.json are personal data: keep <out_dir> under .local,
never in Git (public repo). Needs ffmpeg on PATH and numpy; `transcribe` also
needs faster-whisper (the voice helper's Python has it).
"""
import argparse
import json
import re
import subprocess
import sys
import wave
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import registry  # noqa: E402

CONFIG = registry.CODE / "config" / "voice_clips.json"
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0)
FRAME = 0.02   # seconds per loudness frame


def settings():
    return registry.load(CONFIG)


def decode(path, rate):
    """Whole file as mono float32 at `rate`."""
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", str(path), "-ac", "1", "-ar", str(rate),
                          "-f", "f32le", "-"], capture_output=True, check=True,
                         creationflags=NO_WINDOW).stdout
    return np.frombuffer(raw, dtype="<f4").copy()


def silences(path, noise_db, seconds):
    """[(start, end)] of every quiet gap, as ffmpeg silencedetect reports them."""
    err = subprocess.run(["ffmpeg", "-nostats", "-i", str(path), "-af",
                          "silencedetect=noise=%ddB:d=%s" % (noise_db, seconds), "-f", "null", "-"],
                         capture_output=True, text=True, creationflags=NO_WINDOW).stderr
    starts = [float(v) for v in re.findall(r"silence_start: (-?[\d.]+)", err)]
    ends = [float(v) for v in re.findall(r"silence_end: ([\d.]+)", err)]
    return list(zip(starts, ends))


def speech_runs(gaps, total):
    """The stretches between the gaps."""
    runs, at = [], 0.0
    for start, end in gaps:
        if start - at > 0.05:
            runs.append((at, max(start, at)))
        at = end
    if total - at > 0.05:
        runs.append((at, total))
    return runs


def envelope(x, rate):
    """RMS per FRAME, smoothed over 5 frames, to find the quietest spot in a run."""
    n = int(rate * FRAME)
    frames = x[:len(x) // n * n].reshape(-1, n)
    rms = np.sqrt((frames ** 2).mean(axis=1) + 1e-12)
    return np.convolve(rms, np.ones(5) / 5, mode="same")


def split_long(start, end, env, cut):
    """Split one run longer than maxSeconds at its quietest points."""
    lo, hi = cut["minSeconds"], cut["maxSeconds"] - cut["leadSeconds"] - cut["tailSeconds"]
    parts = []
    while end - start > hi:
        a = start + max(lo, hi * 0.5)
        b = min(start + hi, end - lo)
        i0, i1 = int(a / FRAME), int(b / FRAME)
        at = (i0 + int(np.argmin(env[i0:i1 + 1]))) * FRAME
        parts.append((start, at))
        start = at
    parts.append((start, end))
    return parts


def plan(runs, env, cut, join_gap=1.0):
    """[(start, end, cut_before, cut_after)]: clips of minSeconds..maxSeconds.

    cut_* = the edge is a split inside speech, so no lead/tail is added there
    (it would repeat the neighbour's words)."""
    lo, hi = cut["minSeconds"], cut["maxSeconds"] - cut["leadSeconds"] - cut["tailSeconds"]
    pieces = []
    for s, e in runs:
        if e - s > hi:
            sub = split_long(s, e, env, cut)
            for k, (a, b) in enumerate(sub):
                pieces.append((a, b, k > 0, k < len(sub) - 1))
        else:
            pieces.append((s, e, False, False))
    clips = []
    for piece in pieces:
        last = clips[-1] if clips else None
        if (last and not last[3] and not piece[2] and piece[0] - last[1] < join_gap
                and piece[1] - last[0] <= hi):
            clips[-1] = (last[0], piece[1], last[2], piece[3])
        else:
            clips.append(piece)
    return [c for c in clips if c[1] - c[0] + cut["leadSeconds"] + cut["tailSeconds"] >= lo]


def write_wav(path, x, rate):
    pcm = (np.clip(x, -1, 1) * 32767).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm.tobytes())


def cmd_cut(a):
    cfg = settings()["cut"]
    out = Path(a.out_dir)
    out.mkdir(parents=True, exist_ok=True)
    rate = cfg["rate"]
    x = decode(a.recording, rate)
    total = len(x) / rate
    runs = speech_runs(silences(a.recording, cfg["noiseDb"], cfg["silenceSeconds"]), total)
    clips = plan(runs, envelope(x, rate), cfg)
    rows = []
    for k, (s, e, cut_before, cut_after) in enumerate(clips):
        s0 = max(0.0, s - (0 if cut_before else cfg["leadSeconds"]))
        e0 = min(total, e + (0 if cut_after else cfg["tailSeconds"]))
        name = "clip_%04d.wav" % k
        write_wav(out / name, x[int(s0 * rate):int(e0 * rate)], rate)
        rows.append({"file": name, "start": round(s0, 2), "end": round(e0, 2),
                     "duration": round(e0 - s0, 2)})
    (out / "cut.json").write_text(json.dumps(rows, indent=1), encoding="utf-8")
    spoken = sum(r["duration"] for r in rows)
    print("%d clips, %.0f s of %.0f s recording (%d speech runs)" % (len(rows), spoken, total, len(runs)))


def loudness(x, rate):
    """rms dBFS, share of samples at full scale, and how steady the speech level is."""
    n = int(rate * 0.1)
    frames = x[:len(x) // n * n].reshape(-1, n)
    levels = 20 * np.log10(np.sqrt((frames ** 2).mean(axis=1)) + 1e-6)
    talk = levels[levels > levels.max() - 25]            # frames that are speech, not the gap
    spread = float(np.percentile(talk, 90) - np.percentile(talk, 10)) if len(talk) > 3 else 0.0
    return {"rmsDb": round(float(20 * np.log10(np.sqrt((x ** 2).mean()) + 1e-6)), 1),
            "clipFraction": round(float((np.abs(x) >= 0.99).mean()), 5),
            "levelSpreadDb": round(spread, 1)}


def cuda_libs():
    """cublas ships inside torch on Windows; ctranslate2 only finds it on PATH
    (the same fix as apps/voice/service.py, which the voice helper runs with)."""
    import os
    try:
        import torch
    except ImportError:
        return
    lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(lib):
        os.environ["PATH"] = lib + os.pathsep + os.environ.get("PATH", "")
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(lib)


def hear(model, path, beam):
    segs, _ = model.transcribe(str(path), language="th", beam_size=beam,
                               condition_on_previous_text=False, vad_filter=False)
    return list(segs)


def cmd_transcribe(a):
    cuda_libs()
    from faster_whisper import WhisperModel
    out = Path(a.out_dir)
    done = out / "clips.json"      # resumable: a CPU run of 88 clips takes a while
    rows = json.loads(((done if done.is_file() else out / "cut.json")).read_text(encoding="utf-8"))
    model_id = registry.load(registry.CODE / "config" / "voice_providers.json")[
        "providers"]["local"]["jobs"]["hear"]["byLanguage"]["th"]
    def load(device, compute):
        # cpu_threads: the default 4 left 20 of 24 cores idle (PC 2026-11-06, ~45 s per clip)
        return WhisperModel(model_id, device=device, compute_type=compute, cpu_threads=16)

    model = load("cuda", "float16")
    for row in rows:
        path = out / row["file"]
        if "text" in row:
            continue
        try:
            segs = hear(model, path, a.beam)
        except RuntimeError:                             # PC 2026-11-06: cublas64_12.dll missing (CPU torch) -> CPU
            model = load("cpu", "int8")
            segs = hear(model, path, a.beam)
        weight = sum(s.end - s.start for s in segs) or 1.0
        row.update({
            "text": "".join(s.text for s in segs).strip(),
            "avgLogprob": round(sum(s.avg_logprob * (s.end - s.start) for s in segs) / weight, 3) if segs else -9.0,
            "noSpeechProb": round(max((s.no_speech_prob for s in segs), default=1.0), 3),
            "compression": round(max((s.compression_ratio for s in segs), default=9.0), 2),
        })
        with wave.open(str(path)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2").astype("float32") / 32768
            row.update(loudness(x, w.getframerate()))
        print(row["file"], row["duration"], row["avgLogprob"], flush=True)
        done.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    (out / "clips.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")


def cmd_rank(a):
    keep = settings()["keep"]
    out = Path(a.out_dir)
    rows = json.loads((out / "clips.json").read_text(encoding="utf-8"))
    for r in rows:
        why = []
        if not r["text"]:
            why.append("no words")
        if r["avgLogprob"] < keep["minLogprob"]:
            why.append("unsure words")
        if r["noSpeechProb"] > keep["maxNoSpeech"]:
            why.append("maybe no speech")
        if r["clipFraction"] > keep["maxClipFraction"]:
            why.append("clipping")
        if r["levelSpreadDb"] > keep["maxLevelSpreadDb"]:
            why.append("uneven level")
        if r["compression"] > keep["maxCompression"]:
            why.append("looping text (noise or music)")
        r["keep"], r["why"] = not why, why
        r["score"] = round(r["avgLogprob"] - 0.5 * r["noSpeechProb"] - 0.02 * r["levelSpreadDb"], 3)
    order = sorted(rows, key=lambda r: (not r["keep"], -r["score"]))
    for k, r in enumerate(order):
        r["rank"] = k + 1
    (out / "clips.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")
    good = [r for r in rows if r["keep"]]
    print("%d of %d clips kept; best: %s" % (len(good), len(rows), ", ".join(r["file"] for r in order[:5])))


def main():
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("cut")
    p.add_argument("recording")
    p.add_argument("out_dir")
    p.set_defaults(fn=cmd_cut)
    for name, fn in (("transcribe", cmd_transcribe), ("rank", cmd_rank)):
        p = sub.add_parser(name)
        p.add_argument("out_dir")
        p.add_argument("--beam", type=int, default=1, help="whisper beam size (transcribe); 1 is 3-4x faster on CPU")
        p.set_defaults(fn=fn)
    a = ap.parse_args()
    a.fn(a)


if __name__ == "__main__":
    main()
