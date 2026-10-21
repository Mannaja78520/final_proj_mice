"""Install the Thai voice with feeling on this PC, once (A45-25).

    python apps/voice/tts_spark/setup.py           install or repair
    python apps/voice/tts_spark/setup.py --check   only say what is missing

Everything goes in code/.local/tts_spark (git-ignored: the repo is public
and these are big and licensed separately; NOT under apps/, which the hub
serves to the WiFi with no login - QC caught that, 2026-10-21):
  venv/            Python with the SYSTEM torch (no 2.5 GB torch download)
                   plus transformers 4.57 for this model only
  Spark-TTS/       SparkAudio code (Apache-2.0) at the commit the model used
  Spark-TTS-0.5B/  BiCodec + wav2vec2 parts of the base model
  thai-emotion/    Mametoyas/SparkTTS-Thai-Emotion-Control raw (CC BY-NC-SA 4.0)
  reference.wav    WHO it sounds like: the robot's current voice saying one
                   neutral line (asked from the running voice helper)
Measured 2026-10-21 on the PC: 3.8 GB, about 5 minutes on a fast line.
"""
import argparse
import json
import os
import subprocess
import sys
import urllib.request
from pathlib import Path

HERE = Path(__file__).resolve().parent
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0   # the project rule
RT = HERE.parents[2] / ".local" / "tts_spark"
SPARK_COMMIT = "2f1ea9082400547242641f5271b6f941c9f439d1"   # inference_colab.ipynb pins this
PINS = ["transformers==4.57.6", "tokenizers>=0.22,<0.23", "huggingface-hub>=0.34,<1.0",
        "einops==0.8.1", "einx==0.3.0", "omegaconf==2.3.0", "antlr4-python3-runtime==4.9.3",
        "soundfile", "soxr", "pythainlp", "frozendict", "tzdata"]
LINE = "สวัสดีครับ ยินดีต้อนรับสู่งานของเรา ห้องน้ำอยู่ทางซ้าย ถ้าต้องการอะไรบอกผมได้เลยนะครับ"


def venv_python():
    for p in (RT / "venv" / "Scripts" / "python.exe", RT / "venv" / "bin" / "python"):
        if p.exists():
            return p
    return None


def missing():
    out = []
    if not venv_python():
        out.append("venv")
    if not (RT / "Spark-TTS" / "sparktts").is_dir():
        out.append("Spark-TTS code")
    if not (RT / "Spark-TTS-0.5B" / "BiCodec").is_dir():
        out.append("base model")
    if not (RT / "thai-emotion" / "raw" / "model.safetensors").exists():
        out.append("Thai emotion model")
    if not (RT / "reference.wav").exists():
        out.append("reference voice")
    return out


def run(cmd, **kw):
    print("  $", " ".join(str(c) for c in cmd), flush=True)
    subprocess.run([str(c) for c in cmd], check=True, creationflags=NO_WINDOW, **kw)


def reference(helper):
    """The robot's own voice, from the running helper, as 16 kHz mono WAV."""
    body = json.dumps({"text": LINE, "lang": "th", "style": "", "format": "wav", "rate": 16000},
                      ensure_ascii=False).encode()
    req = urllib.request.Request(helper.rstrip("/") + "/say", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=60) as r:
        data = r.read()
    if not data.startswith(b"RIFF"):
        raise SystemExit("the voice helper did not send a WAV; is it running?")
    (RT / "reference.wav").write_bytes(data)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--helper", default="http://127.0.0.1:8767")
    a = ap.parse_args()
    gone = missing()
    if a.check or not gone:
        print("ready" if not gone else "missing: " + ", ".join(gone))
        return 0 if not gone else 1
    RT.mkdir(exist_ok=True)
    if not venv_python():
        run([sys.executable, "-m", "venv", "--system-site-packages", RT / "venv"])
    py = venv_python()
    run([py, "-m", "pip", "install", "-q", "--no-deps"] + PINS)
    run([py, "-m", "pip", "install", "-q", "--no-deps", "torchaudio==" + _torch_version(py),
         "--index-url", "https://download.pytorch.org/whl/" + _cuda_tag(py)])
    if not (RT / "Spark-TTS" / "sparktts").is_dir():
        run(["git", "clone", "-q", "https://github.com/SparkAudio/Spark-TTS", RT / "Spark-TTS"])
        run(["git", "-C", RT / "Spark-TTS", "checkout", "-q", SPARK_COMMIT])
    run([py, "-c",
         "from huggingface_hub import snapshot_download as s;"
         "s('SparkAudio/Spark-TTS-0.5B', local_dir=r'%s', allow_patterns=['config.yaml','BiCodec/*','wav2vec2-large-xlsr-53/*']);"
         "s('Mametoyas/SparkTTS-Thai-Emotion-Control', local_dir=r'%s', allow_patterns=['raw/*','thai_text_preprocess.py','README.md'])"
         % (RT / "Spark-TTS-0.5B", RT / "thai-emotion")])
    if not (RT / "reference.wav").exists():
        reference(a.helper)
    gone = missing()
    print("ready" if not gone else "still missing: " + ", ".join(gone))
    return 0 if not gone else 1


def _torch_version(py):
    v = subprocess.run([str(py), "-c", "import torch;print(torch.__version__)"], capture_output=True, text=True,
                       creationflags=NO_WINDOW).stdout
    return v.strip().split("+")[0]


def _cuda_tag(py):
    v = subprocess.run([str(py), "-c", "import torch;print(torch.version.cuda or '')"], capture_output=True, text=True,
                       creationflags=NO_WINDOW).stdout
    v = v.strip().replace(".", "")
    return ("cu" + v) if v else "cpu"


if __name__ == "__main__":
    sys.exit(main())
