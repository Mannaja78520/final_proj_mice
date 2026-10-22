"""Online services the voice helper can hand a job to (A45-1).

User 2026-10-19: use Google AI Studio / Gemini by voice, and other services
too, keep a local backup, and "make it fit the situation - any service or
local, not fixed to one". So each of the three jobs (hear, think, speak) has
an ORDERED list in config/voice.json `use`; the first that works does it.

Who exists, what each can do and its model names are DATA in
config/voice_providers.json. This file is only the few wire shapes those
services speak: Gemini, the OpenAI shape (Groq, Typhoon, Ollama, OpenAI) and
Azure speech. A new service in one of those shapes is an entry there, no code.

Keys are never in config/voice.json: anyone on the WiFi can read that through
the hub, and the repo is public. They live in main_python/voice_keys.json
(git-ignored, promote.py SKIP_FILES) or the environment.

Stdlib only, like the helper's HTTP side. Every call returns (result, why-not).
"""
import base64
import json
import os
import struct
import urllib.error
import urllib.request
import uuid
from pathlib import Path
from xml.sax.saxutils import escape

CODE = Path(__file__).resolve().parents[2]
REGISTRY = CODE / "config" / "voice_providers.json"


def keys_path():
    """The per-machine key file. MICE_VOICE_KEYS points a check at a throwaway."""
    return Path(os.environ.get("MICE_VOICE_KEYS")
                or (CODE / "main_python" / "voice_keys.json"))


def read_keys():
    try:
        got = json.loads(keys_path().read_text(encoding="utf-8"))
        return got if isinstance(got, dict) else {}
    except (OSError, ValueError):
        return {}


def write_keys(keys):
    p = keys_path()
    p.parent.mkdir(parents=True, exist_ok=True)
    tmp = p.with_suffix(".part")
    with open(tmp, "w", encoding="utf-8", newline="\n") as f:
        f.write(json.dumps(keys, ensure_ascii=False, indent=1) + "\n")
    os.replace(tmp, p)


def key_for(pid, prov):
    """The saved key, else the first environment variable the registry names."""
    got = str(read_keys().get(pid) or "").strip()
    if got:
        return got
    for name in (prov.get("key") or {}).get("env") or []:
        if os.environ.get(name, "").strip():
            return os.environ[name].strip()
    return ""


def needs_key(prov):
    return bool(prov.get("key"))


# --- the wire -----------------------------------------------------------------

class Refused(Exception):
    """The service answered, but no. Carries its own words for the page."""


def _call(url, body=None, headers=None, timeout=20, raw=False):
    """POST json (or bytes) and read json (or bytes). Raises Refused / OSError."""
    data = body if isinstance(body, (bytes, type(None))) else json.dumps(body).encode("utf-8")
    hdr = {"Content-Type": "application/json"} if not isinstance(body, bytes) else {}
    hdr.update(headers or {})
    req = urllib.request.Request(url, data=data, headers=hdr,
                                 method="POST" if data is not None else "GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            got = r.read()
    except urllib.error.HTTPError as e:
        said = e.read().decode("utf-8", "replace")[:300]
        # 401/403 = the key; 429 = the free allowance for now; the rest as said.
        why = {401: "the key was refused", 403: "the key was refused",
               429: "its free allowance is used up for now"}.get(e.code, "it said no")
        raise Refused("%s (%d %s)" % (why, e.code, said.strip()))
    return got if raw else json.loads(got.decode("utf-8"))


def _multipart(fields, files):
    """(body, content-type) for a form upload - the OpenAI transcription shape."""
    edge = "mice" + uuid.uuid4().hex
    out = []
    for k, v in fields.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"\r\n\r\n%s\r\n"
                    % (edge, k, v)).encode("utf-8"))
    for k, (name, data, ctype) in files.items():
        out.append(("--%s\r\nContent-Disposition: form-data; name=\"%s\"; filename=\"%s\"\r\n"
                    "Content-Type: %s\r\n\r\n" % (edge, k, name, ctype)).encode("utf-8"))
        out.append(data + b"\r\n")
    out.append(("--%s--\r\n" % edge).encode("utf-8"))
    return b"".join(out), "multipart/form-data; boundary=" + edge


def pcm_wav(pcm, rate=24000):
    """Headerless 16-bit mono PCM -> a WAV the browser plays."""
    return (b"RIFF" + struct.pack("<I", 36 + len(pcm)) + b"WAVEfmt "
            + struct.pack("<IHHIIHH", 16, 1, 1, rate, rate * 2, 2, 16)
            + b"data" + struct.pack("<I", len(pcm)) + pcm)


def silent(sound):
    """True when the bytes hold no sound to hear: a WAV whose data chunk is
    under 50 ms, or any other file under 100 bytes."""
    if sound[:4] != b"RIFF" or sound[8:12] != b"WAVE":
        return len(sound) < 100
    at, per_s = 12, 0
    while at + 8 <= len(sound):
        tag, size = sound[at:at + 4], struct.unpack("<I", sound[at + 4:at + 8])[0]
        if size > len(sound) - at - 8:
            return True
        if tag == b"fmt " and size >= 16:
            per_s = struct.unpack("<I", sound[at + 16:at + 20])[0]   # bytes a second
        if tag == b"data":
            have = min(size, len(sound) - at - 8)
            return per_s <= 0 or have < max(per_s // 20, 1)
        at += 8 + size + (size & 1)
    return True


def audio_type(audio):
    """The browser's recording format, from its first bytes."""
    if audio[:4] == b"RIFF":
        return "audio/wav", "wav"
    if audio[:4] == b"OggS":
        return "audio/ogg", "ogg"
    if audio[:3] == b"ID3" or audio[:2] in (b"\xff\xfb", b"\xff\xf3"):
        return "audio/mpeg", "mp3"
    if audio[4:8] == b"ftyp":
        return "audio/mp4", "m4a"
    return "audio/webm", "webm"         # Chrome and Edge MediaRecorder


def to_wav16k(audio):
    """The recording as 16 kHz mono WAV, for services that refuse webm
    (Typhoon lists wav/mp3/flac/ogg only). PyAV comes with faster-whisper;
    without it the recording goes as it is and the service says so."""
    try:
        from faster_whisper import decode_audio
        import io
        import numpy as np
        x = decode_audio(io.BytesIO(audio), sampling_rate=16000)
        pcm = (np.clip(x, -1, 1) * 32767).astype("<i2").tobytes()
        return pcm_wav(pcm, 16000)
    except Exception:                                   # noqa: BLE001
        return audio


# --- Gemini (Google AI Studio), the Interactions shape (docs 2026-10-19) -------

def _gemini_texts(got):
    """Every text the model wrote, oldest step first. Tolerates the older
    generateContent shape too, so a base pointed at it still reads."""
    out = []
    for step in got.get("steps") or []:
        if step.get("type") in ("model_output", None):
            out += [c.get("text") or "" for c in step.get("content") or []
                    if c.get("type") == "text"]
    for cand in got.get("candidates") or []:
        out += [p.get("text") or "" for p in (cand.get("content") or {}).get("parts") or []]
    return "".join(out).strip()


def _gemini_audio(got):
    for step in got.get("steps") or []:
        for c in step.get("content") or []:
            if c.get("type") == "audio" and c.get("data"):
                return base64.b64decode(c["data"]), str(c.get("mime_type") or ""), c.get("sample_rate")
    for cand in got.get("candidates") or []:
        for p in (cand.get("content") or {}).get("parts") or []:
            inl = p.get("inlineData") or p.get("inline_data") or {}
            if inl.get("data"):
                return base64.b64decode(inl["data"]), str(inl.get("mimeType") or ""), None
    return None, "", None


def _gemini(prov, key, body, timeout):
    url = prov["base"].rstrip("/") + "/interactions"
    body = dict(body, store=False)
    return _call(url, body, {"x-goog-api-key": key}, timeout=timeout)


def gemini_think(prov, key, job, system, history, max_tokens, timeout):
    steps = [{"type": "user_input" if m.get("role") == "user" else "model_output",
              "content": [{"type": "text", "text": str(m.get("content") or "")}]}
             for m in history]
    gen = {"max_output_tokens": max(int(max_tokens or 0), int(job.get("maxTokens") or 0))}
    if job.get("thinking"):
        gen["thinking_level"] = job["thinking"]
    got = _gemini(prov, key, {"model": job["model"], "system_instruction": system,
                              "input": steps, "generation_config": gen}, timeout)
    text = _gemini_texts(got)
    return (text, None) if text else (None, "it sent back no words")


def gemini_hear(prov, key, job, audio, lang, timeout):
    mime, _ext = audio_type(audio)
    ask = job.get("prompt") or "Write down exactly what is said."
    got = _gemini(prov, key, {"model": job["model"], "input": [
        {"type": "text", "text": ask + ((" The speaker uses language code %s." % lang) if lang else "")},
        {"type": "audio", "data": base64.b64encode(audio).decode("ascii"), "mime_type": mime}],
        "generation_config": {"thinking_level": job["thinking"]} if job.get("thinking") else {}},
        timeout)
    return _gemini_texts(got), None


def gemini_speak(prov, key, job, text, lang, voice, timeout, style=""):
    sc = {"voice": voice or job.get("voice") or "Kore"}
    if lang:
        sc["language"] = lang
    part = {"type": "text", "text": text}
    if style:
        # A45-25: the manner rides as a speech_metadata annotation (Gemini
        # speech docs, read 2026-10-21). NOT yet heard: no key on this PC.
        part["annotations"] = [{"type": "speech_metadata", "style": style}]
    got = _gemini(prov, key, {"model": job["model"],
                              "input": [part],
                              "response_format": {"type": "audio"},
                              "generation_config": {"speech_config": sc}}, timeout)
    data, mime, rate = _gemini_audio(got)
    if not data:
        return None, "it sent back no sound"
    if data[:4] == b"RIFF" or "mp" in mime:
        return data, None
    return pcm_wav(data, int(rate or 24000)), None        # audio/l16: add the header


# --- the OpenAI shape: Groq, Typhoon, Ollama, OpenAI ---------------------------

def _auth(key):
    return {"Authorization": "Bearer " + key} if key else {}


def openai_think(prov, key, job, system, history, max_tokens, timeout):
    base = prov["base"].rstrip("/")
    model = job.get("model") or ""
    if not model:
        # Ollama: whichever model this PC already pulled, never a name typed here.
        got = _call(base + "/models", None, _auth(key), timeout=5)
        model = ((got.get("data") or [{}])[0]).get("id") or ""
        if not model:
            return None, "no model is installed there yet"
    msgs = [{"role": "system", "content": system}] + [
        {"role": "assistant" if m.get("role") != "user" else "user",
         "content": str(m.get("content") or "")} for m in history]
    body = {"model": model, "messages": msgs, "temperature": 0.2,
            "max_tokens": max(int(max_tokens or 0), int(job.get("maxTokens") or 0))}
    got = _call(base + "/chat/completions", body, _auth(key), timeout=timeout)
    text = ((((got.get("choices") or [{}])[0]).get("message") or {}).get("content") or "").strip()
    return (text, None) if text else (None, "it sent back no words")


def openai_hear(prov, key, job, audio, lang, timeout):
    if job.get("wav"):
        audio = to_wav16k(audio)
    mime, ext = audio_type(audio)
    fields = {"model": job["model"], "response_format": "json", "temperature": "0"}
    if lang:
        fields["language"] = lang
    if job.get("prompt"):
        fields["prompt"] = job["prompt"]
    body, ctype = _multipart(fields, {"file": ("speech." + ext, audio, mime)})
    hdr = dict(_auth(key), **{"Content-Type": ctype})
    got = _call(prov["base"].rstrip("/") + "/audio/transcriptions", body, hdr, timeout=timeout)
    return str(got.get("text") or "").strip(), None


def openai_speak(prov, key, job, text, lang, voice, timeout, style=""):
    body = {"model": job["model"], "voice": voice or job.get("voice") or "alloy",
            "input": text, "response_format": "mp3"}
    if style:
        body["instructions"] = style     # read by models that take a manner; others ignore it
    got = _call(prov["base"].rstrip("/") + "/audio/speech", body, _auth(key),
                timeout=timeout, raw=True)
    return (got, None) if len(got) > 100 else (None, "it sent back no sound")


# --- Azure speech: the same natural Thai voices as Edge, on a paid-grade line --

def azure_speak(prov, key, job, text, lang, voice, timeout, rate="", pitch=""):
    region = job.get("region") or prov.get("region") or "southeastasia"
    loc = "-".join(voice.split("-")[:2]) if voice.count("-") >= 2 else (lang or "th")
    body = escape(text)
    if rate or pitch:
        body = "<prosody%s%s>%s</prosody>" % (
            (' rate="%s"' % rate) if rate else "", (' pitch="%s"' % pitch) if pitch else "", body)
    ssml = ("<speak version='1.0' xml:lang='%s'><voice name='%s'>%s</voice></speak>"
            % (loc, voice, body)).encode("utf-8")
    base = prov.get("base") or "https://%s.tts.speech.microsoft.com" % region
    got = _call(base.rstrip("/") + "/cognitiveservices/v1", ssml,
                {"Ocp-Apim-Subscription-Key": key, "Content-Type": "application/ssml+xml",
                 "X-Microsoft-OutputFormat": job.get("format") or "audio-24khz-48kbitrate-mono-mp3",
                 "User-Agent": "mice-voice"}, timeout=timeout, raw=True)
    return (got, None) if len(got) > 100 else (None, "it sent back no sound")


# --- a speech server on this PC that takes a FEELING (A45-25) ----------------
# apps/voice/tts_spark/server.py: Thai with neutral/happy/sad/angry/frustrated.

def feeling_speak(prov, key, job, text, lang, voice, timeout, style="", emotion="", person=None,
                  tempo=1.0):
    """`person` = a saved voice from config/voice_people.json (its speaker
    tokens and gender, A45-27); `tempo` = the chosen speed, 1 = as made."""
    base = (job.get("base") or prov.get("base") or "").rstrip("/")
    body = {"text": text, "emotion": emotion or "neutral"}
    if job.get("tune"):              # clarity knobs, data in voice_providers.json (A45-26)
        body["tune"] = dict(job["tune"])
    if abs(float(tempo) - 1) >= 0.01:
        body["tune"] = dict(body.get("tune") or {}, tempo=round(float(tempo), 3))
    if person:
        body["speaker"] = person.get("speaker")
        if person.get("gender"):
            body["gender"] = person["gender"]
        if person.get("temperature") is not None:     # this voice's own clearest setting
            body["tune"] = dict(body.get("tune") or {}, temperature=float(person["temperature"]))
    got = _call(base + "/speak", body, timeout=timeout, raw=True)
    return (got, None) if len(got) > 100 else (None, "it sent back no sound")


# kind -> job -> function. A kind missing a job simply cannot do it.
WIRES = {
    "gemini": {"think": gemini_think, "hear": gemini_hear, "speak": gemini_speak},
    "openai": {"think": openai_think, "hear": openai_hear, "speak": openai_speak},
    "azure": {"speak": azure_speak},
    "feeling": {"speak": feeling_speak},
}
