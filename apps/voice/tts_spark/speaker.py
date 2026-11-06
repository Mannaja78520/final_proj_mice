"""Turn the user's reference clips into ONE speaker for the feeling voice.

    <spark venv python> apps/voice/tts_spark/speaker.py <voice_folder> [--runtime DIR]

Reads config/voice_clips.json `reference` (clips = names inside <voice_folder>,
text = what they say), joins the clips with a short pause (about 30 s at most:
Spark-TTS's own reference limit), runs the codec and writes
<voice_folder>/speaker.json = {"speaker": [32 tokens], "clips": [...], "text": ...}.
apps/voice/user_voice.py lists it as the voice "person:user-voice" once
`reference.enabled` is true. The folder is a character's `voice/` folder under
.local: the tokens are made from a real person's voice, so never in Git.
Runs in the Spark venv (the codec needs its torch), like server.py.
"""
import argparse
import json
import sys
import tempfile
import wave
from pathlib import Path

HERE = Path(__file__).resolve().parent
CODE = HERE.parents[2]
PAUSE = 0.3          # seconds of silence between joined clips
LONGEST = 30.0       # seconds of reference Spark-TTS is meant to be given


def joined(folder, names, rate=16000):
    """The named clips as one mono 16-bit wav (path of a temp file) and its seconds."""
    import numpy as np
    pieces, total = [], 0.0
    for name in names:
        with wave.open(str(folder / name)) as w:
            x = np.frombuffer(w.readframes(w.getnframes()), dtype="<i2")
            seconds = w.getnframes() / w.getframerate()
            if w.getframerate() != rate:
                x = np.interp(np.arange(0, len(x), w.getframerate() / rate), np.arange(len(x)), x).astype("<i2")
        if pieces and total + seconds > LONGEST:
            break
        pieces += [x, np.zeros(int(rate * PAUSE), dtype="<i2")]
        total += seconds + PAUSE
    handle = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
    handle.close()
    with wave.open(handle.name, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(np.concatenate(pieces).tobytes())
    return handle.name, total


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("folder")
    ap.add_argument("--runtime", default=str(CODE / ".local" / "tts_spark"))
    ap.add_argument("--names", nargs="*", help="clip names instead of the config's")
    a = ap.parse_args()
    sys.path.insert(0, str(CODE / "tools"))
    import registry
    ref = registry.load(CODE / "config" / "voice_clips.json").get("reference") or {}
    names = a.names or ref.get("clips") or []
    if not names:
        sys.exit("no clips: set reference.clips in config/voice_clips.json or pass --names")
    folder = Path(a.folder)
    path, seconds = joined(folder, names)
    runtime = Path(a.runtime)
    sys.path.insert(0, str(runtime / "Spark-TTS"))
    import torch
    from sparktts.models.audio_tokenizer import BiCodecTokenizer
    codec = BiCodecTokenizer(str(runtime / "Spark-TTS-0.5B"), device=torch.device("cpu"))
    with torch.inference_mode():
        tokens, _sem = codec.tokenize(path)
    out = {"speaker": [int(v) for v in tokens.squeeze().tolist()], "clips": names,
           "seconds": round(seconds, 1), "text": ref.get("text") or ""}
    (folder / "speaker.json").write_text(json.dumps(out, ensure_ascii=False), encoding="utf-8")
    print("speaker.json: %d tokens from %d clips (%.1f s)" % (len(out["speaker"]), len(names), seconds))


if __name__ == "__main__":
    main()
