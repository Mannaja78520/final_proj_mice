"""Thai speech WITH a feeling, on this PC (A45-25, user 2026-10-21).

User: *ทำจริตเสียงด้วยเลยรออะไร* - real emotion, no key. Edge and Azure Thai
voices only move speed and pitch. SparkTTS-Thai-Emotion-Control (Spark-TTS
0.5B fine-tuned on THAI-SER, CC BY-NC-SA 4.0: non-commercial only) takes an
emotion token: neutral, happy, sad, angry, frustrated.

Runs in its OWN venv (code/.local/tts_spark/venv, made by setup.py)
because it needs transformers 4.57 while the voice helper uses 5.x. Nothing
here is in git except this code: venv, Spark-TTS clone, models and the
reference voice stay in .local (git-ignored, public repo, and NOT under
apps/: every file there is served to the WiFi with no login).

The VOICE (who it sounds like) comes from a reference clip: by default the
robot's own current voice saying one neutral line, so a feeling does not
turn the robot into somebody else. The feeling comes from the token.

    POST /speak {"text", "emotion", "gender"?, "seed"?, "tune"?} -> audio/wav
         tune: any of TUNE below, for this request only
    GET  /health
"""
import argparse
import hashlib
import io
import json
import re
import sys
import threading
import time
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

HERE = Path(__file__).resolve().parent


def load(runtime, checkpoint, reference, device_name):
    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer
    sys.path.insert(0, str(runtime / "Spark-TTS"))
    sys.path.insert(0, str(runtime / "thai-emotion"))
    from sparktts.models.audio_tokenizer import BiCodecTokenizer
    import thai_text_preprocess as pre

    device = torch.device(device_name if torch.cuda.is_available() or device_name == "cpu" else "cpu")
    dtype = torch.bfloat16 if device.type == "cuda" and torch.cuda.is_bf16_supported() else torch.float32
    codec = BiCodecTokenizer(str(runtime / "Spark-TTS-0.5B"), device=device)
    ck = runtime / "thai-emotion" / checkpoint
    tok = AutoTokenizer.from_pretrained(str(ck), use_fast=False)
    model = AutoModelForCausalLM.from_pretrained(str(ck), torch_dtype=dtype, low_cpu_mem_usage=True).to(device)
    model.eval()
    with torch.inference_mode():
        ref_global, _sem = codec.tokenize(str(reference))
    return {"torch": torch, "codec": codec, "tok": tok, "model": model, "pre": pre,
            "device": device, "ref": ref_global, "checkpoint": checkpoint,
            "rate": int(codec.config.get("sample_rate", 16000)),
            "emotion_tokens": pre.uses_emotion_tokens(checkpoint)}


def prompt(S, text, emotion, gender):
    parts = ["<|task_tts|>"]
    if S["emotion_tokens"] and emotion:
        parts.append("<|emotion_%s|>" % emotion)
    if gender:
        parts.append("<|gender_%s|>" % gender)
    parts += ["<|start_content|>", text, "<|end_content|>", "<|start_global_token|>"]
    parts += ["<|bicodec_global_%d|>" % int(i) for i in S["ref"].squeeze()]
    parts.append("<|end_global_token|>")
    return "".join(parts)


def _sample(logits, temperature, top_k=50, top_p=0.95):
    torch = __import__("torch")
    v, ix = torch.topk(logits / max(temperature, 1e-4), top_k)
    p = torch.softmax(v.float(), -1)
    keep = (torch.cumsum(p, -1) - p) < top_p           # the smallest set over top_p
    p = p * keep
    return ix.gather(-1, torch.multinomial(p / p.sum(-1, keepdim=True), 1))


def decode_fast(S, ids, max_new, temperature):
    """Token by token through ONE captured CUDA graph (2026-10-21, RTX 5070 Ti
    laptop): HF generate spent 50 ms a token launching kernels on Windows
    with the GPU at 20%; the replayed graph takes 5.5 ms. Teacher-forced
    against a full forward: top-5 overlap 4.78 of 5, the rest bf16 noise."""
    torch = S["torch"]
    from transformers import StaticCache
    L = S.get("cache_len") or 4096
    n0 = ids.shape[1]
    if n0 + max_new > L:
        max_new = L - n0
    if "graph" not in S:
        dev, m = S["device"], S["model"]
        S["cache"] = StaticCache(config=m.config, max_cache_len=L, max_batch_size=1, device=dev,
                                 dtype=next(m.parameters()).dtype)
        S["tok_buf"] = torch.zeros((1, 1), dtype=torch.long, device=dev)
        S["pos_buf"] = torch.zeros((1,), dtype=torch.long, device=dev)
        S["neg"] = torch.finfo(next(m.parameters()).dtype).min
        S["mask"] = torch.full((1, 1, 1, L), S["neg"], dtype=next(m.parameters()).dtype, device=dev)
    cache, tb, pb, mask, m = S["cache"], S["tok_buf"], S["pos_buf"], S["mask"], S["model"]
    cache.reset()
    mask.fill_(S["neg"])
    mask[..., :n0] = 0
    out = m(input_ids=ids, past_key_values=cache, cache_position=torch.arange(n0, device=ids.device),
            use_cache=True)
    nxt = _sample(out.logits[:, -1], temperature)

    def step():
        return m(input_ids=tb, past_key_values=cache, cache_position=pb, attention_mask=mask,
                 use_cache=True).logits
    if "graph" not in S:
        side = torch.cuda.Stream()
        side.wait_stream(torch.cuda.current_stream())
        with torch.cuda.stream(side):
            tb.copy_(nxt); pb.fill_(n0); mask[..., n0] = 0
            for _ in range(3):
                step()                      # warm up; position n0 is written again below
        torch.cuda.current_stream().wait_stream(side)
        S["graph"] = torch.cuda.CUDAGraph()
        with torch.cuda.graph(S["graph"]):
            S["logits"] = step()
    eos = m.generation_config.eos_token_id
    eos = eos[0] if isinstance(eos, (list, tuple)) else eos
    got = []
    for k in range(max_new):
        got.append(nxt)
        p = n0 + k
        tb.copy_(nxt); pb.fill_(p); mask[..., p] = 0
        S["graph"].replay()
        nxt = _sample(S["logits"][:, -1], temperature)
        if k % 16 == 15 and bool((torch.cat(got[-16:]) == eos).any()):
            break
    seq = torch.cat(got).view(-1).tolist()
    return seq[:seq.index(eos)] if eos in seq else seq


def speak(S, text, emotion, gender, seed, temperature, max_new, end=""):
    """One piece of text -> float samples (None = no sound)."""
    torch = S["torch"]
    if S["checkpoint"].startswith("raw"):
        model_text = S["pre"].preprocess_text(text)   # raw: no romanizer/phoneme models needed
    else:
        model_text = S["pre"].get_text_for_model(S["pre"].TTSDataProcessor().process(text), S["checkpoint"])
    if not model_text:
        return None
    if end and not model_text.endswith(end):
        model_text += end
    torch.manual_seed(seed)                # the same line + feeling sounds the same next time
    ids = S["tok"]([prompt(S, model_text, emotion, gender)], return_tensors="pt").to(S["device"])
    with torch.inference_mode():
        if S["device"].type == "cuda":
            out = decode_fast(S, ids.input_ids, max_new, temperature)
        else:
            out = S["model"].generate(**ids, max_new_tokens=max_new, do_sample=True,
                                      top_k=50, top_p=0.95, temperature=temperature)[0][ids.input_ids.shape[1]:]
    said = S["tok"].decode(out, skip_special_tokens=True)
    sem = [int(t) for t in re.findall(r"bicodec_semantic_(\d+)", said)]
    if not sem:
        return None
    with torch.inference_mode():
        wav = S["codec"].detokenize(S["ref"].to(S["device"]).squeeze(0),
                                    torch.tensor(sem).long().unsqueeze(0).to(S["device"]))
    import numpy as np
    return np.clip(np.asarray(wav, dtype="float32").squeeze(), -1, 1)


def pieces(text, least):
    """Thai writes a space where a speaker takes a breath. One long line in one
    go came out rushed and run together (user 2026-10-22: รวบเกินฟังไม่รู้เรื่อง);
    each piece said on its own, with a short pause between, is clearer.
    Pieces under `least` letters join the next one (a lone ครับ is no phrase)."""
    if least <= 0:
        return [text]
    out = []
    for word in text.split():
        if out and len(out[-1]) < least:
            out[-1] += " " + word
        else:
            out.append(word)
    if len(out) > 1 and len(out[-1]) < least:      # a short tail joins the piece before
        last = out.pop()
        out[-1] += " " + last
    return out


def to_wav(S, parts, tune):
    """Pieces -> one 16-bit WAV with a quiet lead and TAIL. Measured 2026-10-22:
    the model stops on the last sound of the last word (16 of 30 clips had
    under 100 ms after it, one ended at full volume) and a speaker or the
    browser drops the end of a buffer: the user heard the last word cut in
    half. The fade is a few ms only: it removes a click, not a word."""
    import numpy as np
    rate = S["rate"]
    ms = lambda v: np.zeros(int(rate * float(v) / 1000), dtype="float32")   # noqa: E731
    fade = int(rate * float(tune["fadeMs"]) / 1000)
    joined = [ms(tune["leadMs"])]
    for i, x in enumerate(parts):
        if fade and len(x) > 2 * fade:
            x = x.copy()
            x[:fade] *= np.linspace(0, 1, fade, dtype="float32")
            x[-fade:] *= np.linspace(1, 0, fade, dtype="float32")
        joined.append(x)
        joined.append(ms(tune["pauseMs"] if i < len(parts) - 1 else tune["tailMs"]))
    pcm = (np.concatenate(joined) * 32767).astype("<i2").tobytes()
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(rate)
        w.writeframes(pcm)
    return buf.getvalue()


# Every knob a request may change; the defaults come from the command line
# (voice_providers.json `start.args`) and a request's `tune` overrides them.
TUNE = {"temperature": float, "leadMs": float, "tailMs": float, "fadeMs": float, "pauseMs": float,
        "split": int, "end": str}


class Handler(BaseHTTPRequestHandler):
    S, lock, cfg = None, threading.Lock(), {}

    def log_message(self, fmt, *args):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode()
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                                 # noqa: N802
        if self.path.rstrip("/") == "/health":
            return self._json({"ok": True, "service": "tts-spark", "checkpoint": self.S["checkpoint"],
                               "device": str(self.S["device"]), "emotions": self.cfg["emotions"]})
        self._json({"ok": False, "error": "unknown address"}, 404)

    def do_POST(self):                                # noqa: N802
        if self.path.rstrip("/") != "/speak":
            return self._json({"ok": False, "error": "unknown address"}, 404)
        try:
            n = int(self.headers.get("Content-Length") or 0)
            if n > 64 * 1024:
                return self._json({"ok": False, "error": "that text is too long to speak"}, 400)
            req = json.loads(self.rfile.read(n).decode("utf-8")) if n else {}
        except ValueError:
            return self._json({"ok": False, "error": "that request was not readable"}, 400)
        text = str(req.get("text") or "").strip()
        emotion = str(req.get("emotion") or "neutral")
        if not text:
            return self._json({"ok": False, "error": "there was nothing to speak"}, 400)
        if emotion not in self.cfg["emotions"]:
            return self._json({"ok": False, "error": "it has no feeling called %r" % emotion}, 400)
        seed = int(req.get("seed") or int(hashlib.md5((text + emotion).encode()).hexdigest()[:8], 16))
        tune = dict(self.cfg["tune"])
        try:
            for k, v in (req.get("tune") or {}).items():
                if k in TUNE:
                    tune[k] = TUNE[k](v)
        except (TypeError, ValueError, AttributeError):
            return self._json({"ok": False, "error": "a tune setting was not readable"}, 400)
        t0 = time.time()
        with self.lock:                               # one GPU job at a time
            gender = str(req.get("gender") or self.cfg["gender"])
            parts = [speak(self.S, piece, emotion, gender, seed, tune["temperature"],
                           int(self.cfg["maxNewTokens"]), tune["end"])
                     for piece in pieces(text, tune["split"])]
        if not parts or any(x is None for x in parts):
            return self._json({"ok": False, "error": "it made no sound for that line"}, 500)
        wav = to_wav(self.S, parts, tune)
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.send_header("X-Seconds", "%.3f" % (time.time() - t0))
        self.end_headers()
        self.wfile.write(wav)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--port", type=int, default=8779)
    ap.add_argument("--runtime", default=str(HERE.parents[2] / ".local" / "tts_spark"))
    ap.add_argument("--checkpoint", default="raw")
    ap.add_argument("--reference", default="")
    ap.add_argument("--gender", default="female")
    ap.add_argument("--device", default="cuda")
    ap.add_argument("--temperature", type=float, default=0.8)
    ap.add_argument("--max-new-tokens", type=int, default=3000)
    ap.add_argument("--lead-ms", type=float, default=60)
    ap.add_argument("--tail-ms", type=float, default=450)
    ap.add_argument("--fade-ms", type=float, default=6)
    ap.add_argument("--pause-ms", type=float, default=180)
    ap.add_argument("--split", type=int, default=0, help="pieces under this many letters join the next; 0 = one piece")
    ap.add_argument("--end", default="", help="mark added to a line that does not end with it")
    a = ap.parse_args()
    runtime = Path(a.runtime)
    ref = Path(a.reference) if a.reference else runtime / "reference.wav"
    Handler.cfg = {"emotions": ["neutral", "happy", "sad", "angry", "frustrated"], "gender": a.gender,
                   "maxNewTokens": a.max_new_tokens,
                   "tune": {"temperature": a.temperature, "leadMs": a.lead_ms, "tailMs": a.tail_ms,
                            "fadeMs": a.fade_ms, "pauseMs": a.pause_ms, "split": a.split, "end": a.end}}
    Handler.S = load(runtime, a.checkpoint, ref, a.device)
    httpd = ThreadingHTTPServer(("127.0.0.1", a.port), Handler)
    print("[tts-spark] ready on 127.0.0.1:%d (%s, %s)" % (a.port, a.checkpoint, Handler.S["device"]), flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
