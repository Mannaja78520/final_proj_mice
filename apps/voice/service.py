#!/usr/bin/env python3
"""The voice helper - the heavy half of the Voice app, as its own process.

Grown from the working prototype code/llm/test.py (kept as the reference).
The hub is stdlib-only and frozen into one exe, so torch and a 4B model can
never live inside it: this runs separately, answers on 127.0.0.1, and the hub
proxies /api/voice/* here - saying plainly when nothing is listening.

FAQ first: a question close enough to a saved one is answered straight out of
qa_data.json with no model at all - instant, and it works on any PC. Only a
miss wakes the LLM, imported lazily so a machine without torch still gets the
FAQ half. Speech in (whisper) and speech out (Windows voices via tts.ps1)
import lazily the same way.

Run it from the code folder:

    python apps\\voice\\service.py
"""
import argparse
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import time
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

# Windows defaults stdout to cp1252, which cannot encode Thai or the UI's
# Unicode markers — that turned answers into "i8" garbage and crashed any
# print() of transcribed/LLM text. Force UTF-8 so stdout matches the data.
if sys.stdout.encoding.lower() not in ("utf-8", "utf8"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

CODE = Path(__file__).resolve().parents[2]          # apps/voice/service.py -> code
_tmp_seq = itertools.count()                        # one temp name per writer
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
SPECIAL_RE = re.compile(r"<\|[^|]+\|>")             # <|im_end|> and friends
MARKUP_RE = re.compile(r"[*#_`]")                   # spoken text wears no markdown

sys.path.insert(0, str(CODE / "tools"))
import registry                                      # noqa: E402


class Brain:
    """What answers. The FAQ is always there; the model arrives lazily."""

    def __init__(self, cfg_path, faq_path=None):
        self.cfg_path = Path(cfg_path)
        self.cfg = registry.load(self.cfg_path)
        self._cfg_mtime = None
        self.faq_path = Path(faq_path or (CODE / "apps" / "voice" / "qa_data.json"))
        self._llm = None             # (tokenizer, model) once loaded
        self._llm_err = None
        self._llm_loading = False
        self._llm_loaded_model = None
        self._stt = None             # the whisper model once loaded
        self._stt_err = None
        self._stt_loading = False
        self._stt_loaded_model = None
        self._tts_lock = threading.Lock()   # one PowerShell synth at a time
        self.faq_err = ""            # why the answers file could not be read
        self._lock = threading.Lock()   # one GPU: answers and listening queue

    def maybe_reload(self):
        """Pick up an edited voice.json without a restart - A20-12's promise.

        faqs() re-reads per call already; this is the same courtesy for the
        config. A model whose id changed is dropped here, so a designer's
        switch reaches the NEXT question instead of after a reboot. The drop
        takes the GPU lock - listen() may be holding the very object being
        cleared. A broken edit keeps the old brain and retries next call.
        """
        try:
            m = self.cfg_path.stat().st_mtime
        except OSError:
            return
        if m == self._cfg_mtime:
            return
        try:
            fresh = registry.load(self.cfg_path)
        except Exception:                          # noqa: BLE001
            self._cfg_mtime = None
            return
        self._cfg_mtime = m
        self.cfg = fresh
        # Missing model keys mean the SAME defaults the loaders would pick -
        # comparing against None here would drop a healthy model on every
        # save that did not name one.
        defaults = {"stt": "small", "llm": "Qwen/Qwen3.5-4B"}
        drop = []
        for kind in ("stt", "llm"):
            want = ((fresh.get(kind) or {}).get("model")
                    or defaults[kind])
            if want != getattr(self, "_%s_loaded_model" % kind):
                drop.append(kind)
        if drop:
            with self._lock:
                for kind in drop:
                    setattr(self, "_%s_loaded_model" % kind, None)
                    setattr(self, "_%s" % kind, None)
                    setattr(self, "_%s_err" % kind, None)

    def write_store(self, path, obj):
        """One data file rewritten atomically - a reader never sees half."""
        body = json.dumps(obj, ensure_ascii=False, indent=1)
        # The server is threading: two saves at once must not share one temp
        # name, or A's os.replace publishes B's half-written file.
        tmp = path.with_suffix(".part%d" % next(_tmp_seq))
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body + "\n")
        os.replace(tmp, path)

    def faqs(self):
        # Re-read every time: a designer editing answers must not need a
        # restart to hear them.
        try:
            raw = json.loads(self.faq_path.read_text(encoding="utf-8"))
            self.faq_err = ""
            return (raw or {}).get("faqs", [])
        except (OSError, ValueError) as e:
            # An empty list answers nothing, but a BROKEN file must not look
            # like an empty one - health carries the reason instead.
            self.faq_err = "%s: %s" % (e.__class__.__name__, e)
            return []

    def match_faq(self, text):
        """The closest saved ENTRY over the threshold, or (None, score).

        The whole entry comes back, not just its answer: an entry may name
        a move and a module too (A20-10), and the caller passes them on.
        """
        th = float(self.cfg.get("faqThreshold", 0.75))
        best, hit = 0.0, None
        got = text.strip().lower()
        for item in self.faqs():
            for q in item.get("questions", []):
                score = SequenceMatcher(None, got, q.strip().lower()).ratio()
                if score > best:
                    best, hit = score, item
        return (hit, round(best, 2)) if best >= th else (None, round(best, 2))

    def clean(self, text):
        text = SPECIAL_RE.sub("", THINK_RE.sub("", text or ""))
        # Fix TTS mispronouncing "8:00 - 17:00"
        import re
        text = re.sub(r'(\d+[:\.]\d+)\s*-\s*(\d+[:\.]\d+)', r'\1 ถึง \2', text)
        return MARKUP_RE.sub("", text).strip()

    def llm_status(self):
        lcfg = self.cfg.get("llm", {})
        if not lcfg.get("enabled"):
            return "off in config/voice.json"
        if self._llm:
            return "loaded"
        if self._llm_err:
            return "could not load: " + self._llm_err
        if self._llm_loading:
            return "loading..."
        return "loads when first needed"

    def stt_status(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return "off in config/voice.json"
        if self._stt:
            return "%s loaded" % scfg.get("model", "small")
        if self._stt_err:
            return "could not load: " + self._stt_err
        if self._stt_loading:
            return "%s loading..." % scfg.get("model", "small")
        return "loads when first needed"

    def _load_stt(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._stt or self._stt_err or self._stt_loading:
            return
        self._stt_loading = True
        try:
            from faster_whisper import WhisperModel
            self._stt = WhisperModel(scfg.get("model", "small"),
                                     device="auto", compute_type="auto")
            self._stt_loaded_model = scfg.get("model", "small")
        except Exception as e:                              # noqa: BLE001
            self._stt_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._stt_loading = False

    def listen(self, audio, hint=""):
        """Speech bytes -> ({text, language}, None) or (None, why-not).

        The language is the request's hint, else the store's stt.language,
        else DETECTED per utterance - never a hardcoded code here. Bias words
        apply only when the language is already known: detecting it first
        just to pick a prompt would double every wait.
        """
        with self._lock:
            scfg = self.cfg.get("stt", {})
            # A switched-off listener must not be outrun by its own cache.
            if not scfg.get("enabled"):
                return None, "listening is switched off in config/voice.json"
            self._load_stt()
            if not self._stt:
                return None, ("speech-in is not available (%s)"
                              % self.stt_status())
            resolved = (hint or scfg.get("language") or "").strip()
            bias = ((scfg.get("languages") or {}).get(resolved) or {}).get("bias")
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tf:
                tf.write(audio)
                path = tf.name
            try:
                segments, info = self._stt.transcribe(
                    path, language=resolved or None,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500},
                    initial_prompt=bias)
                text = "".join(s.text for s in segments).strip()
            finally:
                os.unlink(path)
            return {"text": text, "language": info.language}, None

    # --- speaking out loud (A20-9) -------------------------------------
    # Windows' own synthesiser, reached through apps/voice/tts.ps1. No
    # internet, no pip install: the venue PC's own voices, named in the
    # store. Answers are cached by md5(text+voice) so a saved answer's
    # SECOND visitor hears it instantly - and a watcher thread pre-builds
    # every saved answer, re-running when qa_data.json is edited on disk.
    def resolve_voice(self, lang):
        """(cache identity, voice name-or-empty), or (None, why-not).

        A listed-but-EMPTY name means Windows picks its own voice for that
        language - a PC without Pattara still speaks with its default. A
        language MISSING from the map is a mistake and says so instead.
        """
        tcfg = self.cfg.get("tts", {})
        lang = (lang or tcfg.get("language") or "").strip()
        voices = tcfg.get("voices") or {}
        if lang not in voices:
            return None, ("no voice named for language %r - add one under "
                          "tts in config/voice.json" % (lang or "?"))
        name = str(voices[lang]).strip()
        return (name or "<windows default %s>" % lang), name

    def tts_status(self):
        tcfg = self.cfg.get("tts", {})
        if not tcfg.get("enabled"):
            return "off in config/voice.json"
        ident, _name = self.resolve_voice("")
        if not ident:
            return "no voices listed - add one under tts"
        n = len(tcfg.get("voices") or {})
        return "%s speaking (%d mapped)" % (ident, n)

    def _cache_path(self, ident, text):
        key = hashlib.md5(("%s\n%s" % (ident, text))
                          .encode("utf-8")).hexdigest()
        return CODE / "apps" / "voice" / "tts_cache" / (key + ".wav")

    def say(self, text, lang="", voice=""):
        """Text -> wav bytes, or (None, why-not) in plain words."""
        tcfg = self.cfg.get("tts", {})
        if not tcfg.get("enabled"):
            return None, "speaking is switched off in config/voice.json"
        if not text.strip():
            return None, "there was nothing to speak"
        if voice:
            ident = voice
        else:
            ident, voice = self.resolve_voice(lang)
            if not ident:
                return None, voice
        path = self._cache_path(ident, text)
        try:
            return path.read_bytes(), None
        except OSError:
            pass
        with self._tts_lock:        # one PowerShell at a time; the waiter
            try:                    # may find the file already built
                return path.read_bytes(), None
            except OSError:
                pass
            path.parent.mkdir(exist_ok=True)
            wav = None
            try:
                if "Neural" in voice:
                    # Edge-TTS produces MP3, which the browser plays fine.
                    try:
                        r = subprocess.run(
                            [sys.executable, "-m", "edge_tts", "--voice", voice, "--text", text],
                            capture_output=True, timeout=20)
                        if r.returncode == 0 and len(r.stdout) >= 100:
                            wav = r.stdout
                    except Exception:
                        wav = None
                if wav is None:
                    local_voice = voice if "Neural" not in voice else ""
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                         "-File", str(CODE / "apps" / "voice" / "tts.ps1"),
                         "-Text", text, "-Lang", lang, "-Voice", local_voice],
                        capture_output=True, timeout=60)
                    wav = r.stdout
                    if r.returncode != 0 or len(wav) < 44 or not wav.startswith(b"RIFF"):
                        why = r.stderr.decode("utf-8", "replace").strip()
                        return None, ("the voice could not speak that (%s)" % why[-200:])
            except (OSError, subprocess.TimeoutExpired) as e:
                return None, ("the voice could not run (%s: %s)"
                              % (e.__class__.__name__, e))
            tmpf = path.with_suffix(".part")
            tmpf.write_bytes(wav)
            os.replace(tmpf, path)   # atomic - a reader never sees half a wav
            return wav, None

    def sync_faq_audio(self):
        """Pre-build every saved answer, then prune what is stale.

        Pruning keeps today's dynamic (model) audio: only files older than a
        day that no saved answer claims are deleted, so yesterday's demo
        dies overnight and nothing a visitor just heard does.
        """
        if not (self.cfg.get("tts") or {}).get("enabled"):
            return
        ident, _name = self.resolve_voice("")
        keep = set()
        for item in self.faqs():
            answer = (item.get("answer") or "").strip()
            if answer and ident:
                self.say(answer)
                keep.add(self._cache_path(ident, answer).stem)
        cache = CODE / "apps" / "voice" / "tts_cache"
        if not cache.is_dir():
            return
        cutoff = time.time() - 24 * 3600
        for f in cache.glob("*.wav"):
            if f.stem not in keep and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)


    def _load_llm(self):
        if not self.cfg.get("llm", {}).get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._llm or self._llm_err or self._llm_loading:
            return
        self._llm_loading = True
        try:
            import torch                                    # noqa: F401
            from transformers import (AutoModelForCausalLM, AutoTokenizer,
                                      BitsAndBytesConfig)
            mid = self.cfg.get("llm", {}).get("model") or "Qwen/Qwen3.5-4B"
            if mid == r"E:\final_proj\mice\code\llm" and not (Path(mid) / "config.json").is_file():
                mid = "Qwen/Qwen3.5-4B"
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=True)
            quant = BitsAndBytesConfig(
                load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
            mdl = AutoModelForCausalLM.from_pretrained(
                mid, quantization_config=quant, device_map="auto",
                trust_remote_code=True)
            self._llm = (tok, mdl)
            self._llm_loaded_model = mid
        except Exception as e:                              # noqa: BLE001
            self._llm_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._llm_loading = False

    def _complete(self, messages):
        """One model call on exactly the messages given - no persona added.

        Callers hold the lock and have already checked the model is loaded.
        """
        import torch
        tok, mdl = self._llm
        try:
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True,
                enable_thinking=False)          # Qwen3: skip the think block
        except (TypeError, ValueError):         # older template: no such arg
            text = tok.apply_chat_template(
                messages, tokenize=False, add_generation_prompt=True)
        inputs = tok([text], return_tensors="pt").to(mdl.device)
        with torch.no_grad():
            out = mdl.generate(
                **inputs,
                max_new_tokens=int(self.cfg.get("llm", {}).get("maxTokens", 512)),
                do_sample=True, temperature=0.7, top_p=0.9,
                repetition_penalty=1.1, pad_token_id=tok.eos_token_id)
        reply = tok.decode(out[0][inputs.input_ids.shape[1]:],
                           skip_special_tokens=False)
        return self.clean(reply)

    def _ensure_llm(self):
        """(ready, why-not): the model gate shared by every LLM caller."""
        if not self.cfg.get("llm", {}).get("enabled"):
            return False, ("the local model is switched off "
                           "in config/voice.json")
        self._load_llm()
        if not self._llm:
            return False, ("the local model is not available (%s)"
                           % self.llm_status())
        return True, ""

    def generate(self, history):
        """The model's answer, or (None, why-not) in plain words."""
        with self._lock:
            ok, why_not = self._ensure_llm()
            if not ok:
                return None, why_not
            # The saved questions ride along, so a near-miss can still be
            # answered from them - the prototype's trick that made it useful
            # on a laptop.
            lines = ["%d. %s\n   %s" % (i, item["questions"][0], item["answer"])
                     for i, item in enumerate(self.faqs(), 1)]
            system = ("คุณคือผู้ช่วยอัจฉริยะ ตอบเป็นภาษาไทย สั้นกระชับ\n"
                      "กฎพิเศษ:\n"
                      "- หากตอบเวลาที่มีขีด ให้ใช้คำว่า 'ถึง' แทนขีดเสมอ เช่น '8:00 ถึง 17:00 น.'\n"
                      "- หากผู้ใช้ถามย้ำรหัสผ่าน ให้สะกดทีละตัวอักษรบอกพิมพ์ใหญ่พิมพ์เล็ก เช่น 'W พิมพ์ใหญ่ e พิมพ์เล็ก...'\n\n"
                      "ข้อมูล FAQ ที่มีอยู่:\n"
                      + "\n".join(lines)
                      + "\n\nถ้าคำถามเกี่ยวข้องกับ FAQ ข้างต้น ให้ตอบตาม FAQ นั้นโดยตรง "
                      "ถ้าไม่เกี่ยวข้องกับ FAQ เลย ให้ตอบตามความรู้ของคุณตามปกติ")
            messages = [{"role": "system", "content": system}] + history
            return self._complete(messages), None

    def translate(self, text):
        """Any language in, English out - or (None, why-not).

        A separate persona from /ask: the helper answers in the visitor's
        language, the translator always answers in English. One model, two
        system prompts - never both at once.
        """
        with self._lock:
            ok, why_not = self._ensure_llm()
            if not ok:
                return None, why_not
            messages = [
                {"role": "system", "content":
                    "You are a translator at a robot show. Translate the "
                    "message to English exactly - keep the meaning, plain "
                    "wording. Reply with ONLY the English translation."},
                {"role": "user", "content": text}]
            try:
                return self._complete(messages), None
            except Exception as e:              # noqa: BLE001
                return None, "%s: %s" % (e.__class__.__name__, e)

    def health(self):
        n = len(self.faqs())
        if self.faq_err:
            faq = "answers file unreadable - " + self.faq_err
        elif n:
            faq = "%d saved answers" % n
        else:
            faq = "no saved answers yet"
        return {
            "ok": True,
            "service": "voice",
            "faqFile": self.faq_path.name,
            "parts": {"faq": faq, "llm": self.llm_status(),
                      "stt": self.stt_status(), "tts": self.tts_status()},
        }


class VoiceHandler(BaseHTTPRequestHandler):
    brain = None                                    # set in main()

    def log_message(self, fmt, *args):              # quiet unless it matters
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):                               # noqa: N802
        path = urlparse(self.path).path
        self.brain.maybe_reload()
        if path == "/health":
            try:
                return self._json(self.brain.health())
            except Exception as e:                  # noqa: BLE001
                return self._json({"ok": False, "error": str(e)}, 500)
        if path == "/config":
            # Reading is open - the same rule as every other read on the hub.
            return self._json({"ok": True, "config": self.brain.cfg})
        if path == "/faq":
            return self._json({"ok": True, "faqs": self.brain.faqs()})
        return self._json({"ok": False, "error": "unknown address"}, 404)

    def do_store(self, path, key):
        """A designer's save - the settings half of A20-12."""
        length = int(self.headers.get("Content-Length") or 0)
        # Same idea as /ask's cap: these stores are small, and once the
        # helper listens beyond this PC no peer should set its allocation.
        if length > 4 * 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that is too much to save"}, 400)
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except ValueError:
            return self._json({"ok": False, "error":
                               "that request was not readable"}, 400)
        data = req.get(key)
        # The page sends the settings object as it is, but the answers file
        # wraps its list: {faqs: [...]} on disk, a bare [ ... ] on the wire.
        looks_right = (isinstance(data, dict) if key == "config"
                       else isinstance(data, list))
        if not looks_right:
            return self._json({"ok": False, "error":
                               "that does not look like the %s" %
                               ("settings" if key == "config" else "answers")},
                              400)
        try:
            self.brain.write_store(
                path, data if key == "config" else {"faqs": data})
        except OSError as e:
            return self._json({"ok": False, "error":
                               "could not save: %s: %s"
                               % (e.__class__.__name__, e)}, 500)
        return self._json({"ok": True})

    def do_POST(self):                              # noqa: N802
        path = urlparse(self.path).path
        self.brain.maybe_reload()
        if path == "/stop":
            self._json({"ok": True, "message": "shutting down"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
        if path == "/config":
            return self.do_store(self.brain.cfg_path, "config")
        if path == "/faq":
            return self.do_store(self.brain.faq_path, "faqs")
        if path == "/transcribe":
            return self.do_transcribe()
        if path == "/say":
            return self.do_say()
        if path == "/translate":
            return self.do_translate()
        if path != "/ask":
            return self._json({"ok": False, "error": "unknown address"}, 404)
        try:
            length = int(self.headers.get("Content-Length") or 0)
            # Same cap idea as /say: a question (with its history) is small.
            # Once the helper listens beyond 127.0.0.1, trusting an unbounded
            # Content-Length would let any WiFi peer make it allocate memory.
            if length > 1024 * 1024:
                # Drain a modest overshoot so the asker can still READ the
                # refusal; past that, hanging up mid-upload IS the refusal.
                got = 0
                while got < min(length, 8 * 1024 * 1024):
                    c = self.rfile.read(min(length - got, 65536))
                    if not c:
                        break
                    got += len(c)
                return self._json({"ok": False, "error":
                                   "that question is too long to ask"}, 400)
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except ValueError:
            return self._json({"ok": False, "error": "that request was not readable"}, 400)
        text = (req.get("text") or "").strip()
        history = req.get("history") or []
        if not text:
            return self._json({"ok": False, "error": "there was no question in "
                                                    "that - say it again"}, 400)
        try:
            hit, score = self.brain.match_faq(text)
            if hit:
                out = {"ok": True, "answer": hit.get("answer"),
                       "source": "faq", "score": score}
                # An answer may also MOVE a robot. The service only NAMES
                # the move - it never holds the password; the page, which
                # does, drives the show clock itself.
                for k in ("move", "module"):
                    if hit.get(k):
                        out[k] = hit[k]
                return self._json(out)
            # Grey zone: close enough to suspect, not close enough to trust.
            # Asking again beats a confident wrong answer to a visitor.
            again = float(self.brain.cfg.get("faqAskAgain", 0))
            if again and score >= again:
                return self._json({"ok": False, "repeat": True, "score": score,
                                   "error": "I am not sure I heard that right "
                                            "- say it again"})
            reply, why_not = self.brain.generate(
                [{"role": r.get("role", "user"), "content": str(r.get("content", ""))}
                 for r in history][-8:] + [{"role": "user", "content": text}])
            if not reply:
                return self._json({"ok": False, "error": why_not})
            return self._json({"ok": True, "answer": reply, "source": "model"})
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "the answer failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)

    # Audio arrives as the request BODY, not JSON - a browser's MediaRecorder
    # stream is binary, and decoding it as text would destroy it.
    def do_transcribe(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 32 * 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that recording is too big to listen to"}, 400)
        audio = self.rfile.read(length) if length else b""
        if not audio:
            return self._json({"ok": False, "error":
                               "no sound arrived - press talk and speak again"},
                              400)
        hint = parse_qs(urlparse(self.path).query).get("lang", [""])[0]
        try:
            got, why_not = self.brain.listen(audio, hint)
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "listening failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)
        if why_not:
            return self._json({"ok": False, "error": why_not})
        if not got.get("text"):
            # The model ran fine; the recording just held no words it knew.
            return self._json({"ok": False, "error":
                               "that came out as no words - say it again"})
        return self._json({"ok": True, "text": got["text"],
                           "language": got.get("language")})

    # /say answers with SOUND, not json - the browser plays the body
    # directly, so the Content-Type must be audio/wav and errors stay json.
    def do_say(self):
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that text is too long to speak"}, 400)
        try:
            req = (json.loads(self.rfile.read(length).decode("utf-8"))
                   if length else {})
        except ValueError:
            return self._json({"ok": False, "error":
                               "that request was not readable"}, 400)
        text = str(req.get("text") or "").strip()
        if not text:
            return self._json({"ok": False, "error":
                               "there was nothing to speak"}, 400)
        try:
            voice_name = str(req.get("voice") or "").strip()
            wav, why_not = self.brain.say(text, req.get("lang") or "", voice=voice_name)
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "speaking failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)
        if why_not:
            return self._json({"ok": False, "error": why_not})
        self.send_response(200)
        self.send_header("Content-Type", "audio/wav")
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

    def do_translate(self):
        """Any language in, English out - by the local model, never a cloud."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that text is too long to translate"}, 400)
        try:
            req = (json.loads(self.rfile.read(length).decode("utf-8"))
                   if length else {})
        except ValueError:
            return self._json({"ok": False, "error":
                               "that request was not readable"}, 400)
        text = (req.get("text") or "").strip()
        if not text:
            return self._json({"ok": False, "error":
                               "there was nothing to translate"}, 400)
        # Already plain ASCII: nothing a translation could add. A report
        # written in English must come back byte-for-byte the same.
        if all(ord(c) < 128 for c in text):
            return self._json({"ok": True, "text": text, "translated": False})
        try:
            reply, why_not = self.brain.translate(text)
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "translation failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)
        if not reply:
            return self._json({"ok": False, "error": why_not})
        return self._json({"ok": True, "text": reply.strip(), "translated": True})


def watch_faq_audio(brain):
    """Rebuild saved answers' audio whenever qa_data.json changes on disk.

    A designer edits answers and the next visitor still hears them
    instantly - no restart. The mtime poll is what notices the edit; the
    first pass at startup is just the poll seeing a new file.
    """
    last = None
    while True:
        try:
            brain.maybe_reload()
            m = brain.faq_path.stat().st_mtime
            if m != last:
                last = m
                brain.sync_faq_audio()
        except OSError:
            pass
        time.sleep(5)


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--config", default=str(CODE / "config" / "voice.json"),
                    help="the store this helper AND the hub both read")
    ap.add_argument("--faq", default=None,
                    help="answers file (default: apps/voice/qa_data.json)")
    ap.add_argument("--port", type=int, default=None,
                    help="port to answer on (default: the one named by "
                         "`service` in the config)")
    args = ap.parse_args()

    brain = Brain(args.config, args.faq)
    VoiceHandler.brain = brain
    svc = brain.cfg.get("service") or "http://127.0.0.1:8767"
    u = urlparse(svc)
    port = args.port or u.port or 8767
    host = u.hostname or "127.0.0.1"

    httpd = ThreadingHTTPServer((host, port), VoiceHandler)
    print("[voice] answering on %s:%d" % (host, port))
    if host not in ("127.0.0.1", "localhost", "::1"):
        # The opt-in has a cost; say it where the person opting in looks.
        print("[voice] shared beyond this PC - this helper has no password")

    # load models automatically in background
    def load_bg():
        with brain._lock:
            brain._ensure_llm()
            brain._load_stt()
    print("[voice] loading models in background...")
    threading.Thread(target=load_bg, daemon=True).start()

    print("[voice] answers from %s (%s)" % (brain.faq_path, brain.llm_status()))
    if (brain.cfg.get("tts") or {}).get("enabled"):
        # Daemon: pre-building the saved answers must never hold the exit.
        threading.Thread(target=watch_faq_audio, args=(brain,),
                         daemon=True).start()
    print("[voice] speech %s" % brain.tts_status())
    print("[voice] Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[voice] stopped")


if __name__ == "__main__":
    main()
