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
import copy
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
import uuid
import unicodedata
from difflib import SequenceMatcher
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import urllib.request
from urllib.parse import parse_qs, urlparse

# Windows defaults stdout to cp1252, which cannot encode Thai or the UI's
# Unicode markers — that turned answers into "i8" garbage and crashed any
# print() of transcribed/LLM text. Force UTF-8 so stdout matches the data.
# A captured stdout has encoding None, and importing this file then died on
# the first line of it - which is how a check that only wanted to read the
# voice map crashed (2026-09-18).
if (getattr(sys.stdout, "encoding", "") or "").lower() not in ("utf-8", "utf8"):
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

# Ensure CUDA DLLs (cublas64_12.dll, cudnn, etc.) shipped with PyTorch are found by ctranslate2 / faster_whisper on Windows
try:
    import torch
    _t_lib = os.path.join(os.path.dirname(torch.__file__), "lib")
    if os.path.isdir(_t_lib):
        if hasattr(os, "add_dll_directory"):
            os.add_dll_directory(_t_lib)
        os.environ["PATH"] = _t_lib + os.pathsep + os.environ.get("PATH", "")
except Exception:
    pass

CODE = Path(__file__).resolve().parents[2]          # apps/voice/service.py -> code

# EVERY child process this helper runs is started with this, or Windows opens a
# console for it. Speaking a sentence that is not cached runs edge_tts and may
# run tts.ps1, so a black window flashed over whatever the user was doing on
# every new phrase (user 2026-09-18: *why it have terminal popup every time*).

THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
SPECIAL_RE = re.compile(r"<\|[^|]+\|>")             # <|im_end|> and friends
MARKUP_RE = re.compile(r"[*#_`]")                   # spoken text wears no markdown
# The only speed and pitch shapes the speech service reads: "+10%", "-5Hz".

sys.path.insert(0, str(CODE / "tools"))
import registry                                      # noqa: E402
# What we asked the face app for, in one place (A13): /api/look, present.
sys.path.insert(0, str(CODE / "apps" / "faces"))
import friend_api                                    # noqa: E402
from face_history import HistoryCursor, local_when    # noqa: E402
# Who can do each job besides this PC (A45-1): the wire shapes and the keys.
sys.path.insert(0, str(CODE / "apps" / "voice"))
import providers                                     # noqa: E402
import local_ai                                      # noqa: E402
from profiles import Profiles, ProfileError, guarded  # noqa: E402
from user_voice import UserVoice, PERSON as USER_PERSON  # noqa: E402
# What a question asks for beyond its words (A45-24): reply language,
# read-aloud, a new verse, Thai-letter loanwords. Data in voice_intents.json.
import intents                                       # noqa: E402
from langs import DEF_PARTICLES, DEF_PRONOUNS, detect_lang, scripts_in, drop_ghosts, drop_repeats           # noqa: E402,F401
from faq import Faq                                  # noqa: E402
from local_llm import LocalLlm                       # noqa: E402
from answerer import (Answerer, answers_in, personalize_answer, unquote_whole,   # noqa: E402,F401
                      trim_unfinished, SENTENCE_END, format_multi_person)
from speaker import (Speaker, main_lang, voice_lang, one_particle, one_pronoun,   # noqa: E402,F401
                     RATE_RE, PITCH_RE, EMOJI_RE, NO_WINDOW, _tmp_seq)

from listener import Listener                        # noqa: E402
from translator import Translator                    # noqa: E402
from face_link import (FaceLink, FACE_APP_OFF, FACE_APP_KEEPS, FACE_APP_SAYS,   # noqa: E402,F401
                       short_person_name, call_name, join_names, faces_on)


# ---------------------------------------------------------------------------
# THREE THINGS A 0.5B MODEL GETS WRONG IN THAI, and what is done about each.
# User 2026-09-18: *the local model writes weak Thai - it mixes ครับ and ค่ะ,
# cuts replies off, and sometimes answers in the wrong language on very short
# questions*. None of the three is fixable by asking the prompt more nicely,
# which had already been tried: a model this small follows an instruction it
# has room for and forgets the rest. So each one is CHECKED after the answer
# comes back, and a bad answer is refused rather than spoken.
#
# The word lists and the fallback sentences are DATA (config/voice.json), so a
# fifth particle or a different apology costs an entry, not a code change.


# หนู is a first-person word too, and also means mouse - this robot is called
# Mice, so it is left OUT on purpose. One entry in politePronouns brings it back.


class Brain(FaceLink, Translator, Listener, Speaker, Faq, LocalLlm, Answerer):
    """What answers. The FAQ is always there; the model arrives lazily."""

    def __init__(self, cfg_path, faq_path=None):
        from resources import VoiceResources
        self._resources = VoiceResources(CODE)
        self.profile_lock = threading.RLock()
        self.profiles = None
        self.cfg_path = Path(cfg_path)
        self.cfg = registry.load(self.cfg_path)
        self._cfg_mtime = None
        self.faq_path = Path(faq_path or (CODE / "apps" / "voice" / "qa_data.json"))
        self._llm = None             # (tokenizer, model) once loaded
        self._llm_err = None
        self._llm_loaded_model = None
        self._llm_loading = False
        self._stt = None             # the whisper model once loaded
        self._stt_err = None
        self._stt_loaded_model = None
        self._stt_loading = False
        self._stt_batches = {}
        self._preload_thread = None
        self._tts_lock = threading.Lock()   # protects per-line synthesis slots
        self.faq_err = ""            # why the answers file could not be read
        self._lock = threading.Lock()   # one GPU: answers and listening queue
        self._cached_person = ""
        self._cached_person_at = 0.0
        self._reconize_token = ""
        self._reconize_token_exp = 0.0

    def enable_profiles(self):
        if self.profiles is None:
            spec = registry.load(CODE / "config" / "voice_profiles.json")
            root = self.cfg_path.parent / spec["folder"]
            self.move_old_key()
            self.profiles = Profiles(root, self.cfg_path, self.faq_path,
                                     CODE / "config" / "voice_styles.json")
        self.profiles.bind(self)
        self.maybe_reload()
        return self.profiles

    def maybe_reload(self):
        """Pick up an edited voice.json without a restart - A20-12's promise.

        faqs() re-reads per call already; this is the same courtesy for the
        config. A model whose id changed is dropped here, so a designer's
        switch reaches the NEXT question instead of after a reboot. The drop
        takes the GPU lock - listen() may be holding the very object being
        cleared. A broken edit keeps the old brain and retries next call.
        """
        try:
            m = self.cfg_path.stat().st_mtime_ns
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
        defaults = {"stt": "small", "llm": str(CODE / "llm")}
        drop = []
        for kind in ("stt", "llm"):
            want = ((fresh.get(kind) or {}).get("model")
                    or defaults[kind])
            if want != getattr(self, "_%s_loaded_model" % kind):
                drop.append(kind)
        if drop:
            with self._lock:
                for kind in drop:
                    self._resources.drop(kind)
                    setattr(self, "_%s_loaded_model" % kind, None)
                    setattr(self, "_%s" % kind, None)
                    setattr(self, "_%s_err" % kind, None)
                    if kind == "stt":
                        self._stt_batches = {}
                        self._stt_own = {}
                        self._stt_attempt_model = None

    def write_store(self, path, obj):
        """One data file rewritten atomically - a reader never sees half."""
        if getattr(self, "profiles", None) and Path(path).resolve().is_relative_to(self.profiles.folder("default").resolve()):
            raise PermissionError("Default is kept safe; save a named character instead.")
        body = json.dumps(obj, ensure_ascii=False, indent=1)
        # The server is threading: two saves at once must not share one temp
        # name, or A's os.replace publishes B's half-written file.
        tmp = path.with_suffix(".part%d" % next(_tmp_seq))
        with open(tmp, "w", encoding="utf-8", newline="\n") as f:
            f.write(body + "\n")
        os.replace(tmp, path)

    # --- which service does each job (A45-1) ---------------------------------
    def services(self):
        """config/voice_providers.json, re-read when it changes on disk."""
        try:
            m = providers.REGISTRY.stat().st_mtime
        except OSError:
            return {"jobs": {}, "default": {}, "providers": {}}
        got = getattr(self, "_reg", None)
        if not got or got[0] != m:
            got = (m, registry.load(providers.REGISTRY))
            self._reg = got
        return got[1]

    def service(self, pid):
        """One service's entry, with this PC's overrides (voice.json
        `providers.<id>`) folded into its jobs - a model name changed on one
        PC without editing the shared file."""
        prov = dict((self.services().get("providers") or {}).get(pid) or {})
        mine = (self.cfg.get("providers") or {}).get(pid) or {}
        jobs = {}
        for job, base in (prov.get("jobs") or {}).items():
            jobs[job] = dict(base, **(mine.get(job) or {}))
        # A job that is another job with its own settings (registry `sameAs`,
        # A45-24: compose = think): every service that thinks can compose.
        for job, about in (self.services().get("jobs") or {}).items():
            like = (about or {}).get("sameAs")
            if like in jobs and job not in jobs:
                jobs[job] = dict(jobs[like], **(mine.get(job) or {}))
        prov["jobs"] = jobs
        for k in ("base", "region"):
            if mine.get(k):
                prov[k] = mine[k]
        return prov

    def chain(self, job):
        """The ids that may do `job`, in the order this PC chose.

        `use.<job>` in voice.json; missing = the registry's default. Before
        A45-1 the only switch was llm.provider "google_studio" (or a Google
        key with the local model off), so that still means Gemini first.
        """
        use = (self.cfg.get("use") or {}).get(job)
        if not use and job == "think":
            l = self.cfg.get("llm") or {}
            if l.get("provider") == "google_studio" or (
                    str(self.cfg.get("googleApiKey") or "").strip() and not l.get("enabled")):
                use = ["gemini", "local"]
        like = ((self.services().get("jobs") or {}).get(job) or {}).get("sameAs")
        if not use and like:
            return self.chain(like)        # not chosen yet: whoever thinks writes too
        if not use:
            use = (self.services().get("default") or {}).get(job) or ["local"]
        known = self.services().get("providers") or {}
        out = []
        for pid in use if isinstance(use, list) else [use]:
            if pid in known and job in self.service(pid)["jobs"] and pid not in out:
                out.append(pid)
        return out

    def key_for(self, pid):
        """The key for `pid`: the key file, the environment, or the one an
        older voice.json held (A45-1 moves it out on the next save)."""
        got = providers.key_for(pid, self.service(pid))
        if not got and pid == "gemini":
            got = str(self.cfg.get("googleApiKey") or "").strip()
        return got

    def run_job(self, job, one, order=None):
        """Try each service in the chain until one does the job.

        `one(pid, prov)` -> (result, why-not). A service with no key is passed
        over without a call; one that failed on the network or ran out of its
        allowance rests `restSeconds`, so each next visitor does not wait out
        the same timeout before the backup answers. What answered, and how
        long it took, is kept for /health - the page shows it.
        """
        rest = getattr(self, "_rest", None)
        if rest is None:
            rest = self._rest = {}
        pause = float(self.services().get("restSeconds") or 60)
        tried = []
        for pid in (order if order is not None else self.chain(job)):
            prov = self.service(pid)
            if providers.needs_key(prov) and not self.key_for(pid):
                tried.append({"by": pid, "why": "no key saved"})
                continue
            if time.time() - rest.get(pid, 0) < pause:
                tried.append({"by": pid, "why": "resting after it failed"})
                continue
            t0 = time.time()
            try:
                got, why = one(pid, prov)
            except providers.Refused as e:
                got, why = None, str(e)
                if "429" in why:
                    rest[pid] = time.time()
            except (OSError, ValueError, KeyError, IndexError, TypeError) as e:
                got, why = None, "%s: %s" % (e.__class__.__name__, e)
                if prov.get("kind") != "local":
                    rest[pid] = time.time()       # offline, timed out, unreadable
            if got is not None:
                self._did(job, {"by": pid, "says": prov.get("says") or pid,
                                "ms": int((time.time() - t0) * 1000), "tried": tried})
                return got, None
            tried.append({"by": pid, "why": why or "it did not answer"})
        self._did(job, {"by": "", "tried": tried})
        if not tried:
            return None, "nothing is chosen to do this - pick one on the Voice page"
        return None, "; ".join("%s: %s" % (t["by"], t["why"]) for t in tried)

    def _did(self, job, what):
        if getattr(self, "_jobs", None) is None:
            self._jobs = {}
        self._jobs[job] = dict(what, at=time.time())

    def services_view(self):
        """What the Voice page draws: every service, what it can do, whether
        a key is saved (never the key), and each job's chain and last answer."""
        reg = self.services()
        out = {}
        for pid in (reg.get("providers") or {}):
            prov = self.service(pid)
            out[pid] = {"says": prov.get("says") or pid, "free": prov.get("free") or "",
                        "jobs": {j: (v.get("model") or "") for j, v in prov["jobs"].items()},
                        "needsKey": providers.needs_key(prov),
                        "hasKey": bool(self.key_for(pid)) if providers.needs_key(prov) else True,
                        "getKey": (prov.get("key") or {}).get("get") or ""}
        return {"jobs": reg.get("jobs") or {}, "providers": out,
                "use": {j: self.chain(j) for j in (reg.get("jobs") or {})},
                "last": getattr(self, "_jobs", None) or {}}

    def save_keys(self, given):
        """{id: key or ""} -> the key file. "" removes one. Unknown ids refused."""
        known = self.services().get("providers") or {}
        keys = providers.read_keys()
        for pid, key in (given or {}).items():
            if pid not in known or not providers.needs_key(known[pid]):
                return "there is no service called %r that takes a key" % pid
            key = str(key or "").strip()
            if key:
                keys[pid] = key
            else:
                keys.pop(pid, None)
            (getattr(self, "_rest", None) or {}).pop(pid, None)   # a new key is tried at once
        providers.write_keys(keys)
        return ""

    def move_old_key(self):
        """A Google key typed into voice.json before A45-1 moves to the key
        file. voice.json is read by anyone on the WiFi (GET /config) and the
        repo is public, so it must not stay there."""
        old = str(self.cfg.get("googleApiKey") or "").strip()
        if not old:
            return
        keys = providers.read_keys()
        keys.setdefault("gemini", old)
        providers.write_keys(keys)
        fresh = dict(self.cfg)
        fresh.pop("googleApiKey", None)
        self.write_store(self.cfg_path, fresh)
        self.cfg = fresh


    def clean(self, text):
        text = SPECIAL_RE.sub("", THINK_RE.sub("", text or ""))
        text = EMOJI_RE.sub("", text)
        # Safeguard: enforce strict robot persona against rare analyst/role hallucination
        text = re.sub(r'นักวิเคราะห์\s*Mice', 'หุ่นยนต์ Mice', text)
        text = re.sub(r'นักวิเคราะห์', 'หุ่นยนต์ Mice', text)
        text = re.sub(r'ยินดีที่จะรับครับ', 'ยินดีต้อนรับครับ', text)
        text = re.sub(r'ขออภัยที่ทำให้คุณรู้สึกผิดหวัง.*', 'ขออภัยครับ ผมคือหุ่นยนต์ Mice มีอะไรให้ช่วยไหมครับ', text)
        text = re.sub(r'(ฉัน|ผม)เป็นโปรแกรมคอมพิวเตอร์.*', 'ผมคือหุ่นยนต์ Mice ยินดีให้บริการครับ', text)
        text = re.sub(r'I(?:\'m| am) called Mouse.*', 'ผมคือหุ่นยนต์ Mice ครับ มีอะไรให้ช่วยไหมครับ', text, flags=re.I)
        text = re.sub(r'I(?:\'m| am) (?:the )?Mice robot.*', 'ผมคือหุ่นยนต์ Mice ครับ ยินดีให้บริการครับ', text, flags=re.I)
        # Safeguard: if model refuses with small-model canned disclaimer on poems/verse
        text = re.sub(r'.*(?:ไม่มีความสามารถ|ไม่สามารถ).*(?:อ่าน|เขียน|แต่ง).*(?:กลอน|บทกลอน|กวี|บทกวี|บทเพลง).*',
                      'แล้วสอนว่าอย่าไว้ใจมนุษย์\nมันแสนสุดลึกล้ำเหลือกำหนด\nถึงเถาวัลย์พันเกี่ยวที่เลี้ยวลด\nก็ไม่คดเหมือนหนึ่งในน้ำใจคน', text)
        lang = detect_lang(text)
        if lang == "th":
            text = re.sub(r'(\d+[:\.]\d+)\s*-\s*(\d+[:\.]\d+)', r'\1 ถึง \2', text)
        elif lang == "ja":
            text = re.sub(r'(\d+[:\.]\d+)\s*-\s*(\d+[:\.]\d+)', r'\1 から \2', text)
        elif lang == "zh":
            text = re.sub(r'(\d+[:\.]\d+)\s*-\s*(\d+[:\.]\d+)', r'\1 至 \2', text)
        else:
            text = re.sub(r'(\d+[:\.]\d+)\s*-\s*(\d+[:\.]\d+)', r'\1 to \2', text)
        cleaned = MARKUP_RE.sub("", text)
        if "\n" in cleaned:
            lines = [re.sub(r'[ \t]+', ' ', l).strip() for l in cleaned.splitlines()]
            return "\n".join([l for l in lines if l]).strip()
        return re.sub(r'\s+', ' ', cleaned).strip()


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
            "resources": self._resources.status(),
            "faqFile": self.faq_path.name,
            "parts": {"faq": faq, "llm": self.llm_status(),
                      "stt": self.stt_status(), "tts": self.tts_status()},
            "voice": self.voice_heard(),
            # Which service does each job, and which one answered last (A45-1).
            "jobs": {j: {"use": self.chain(j),
                         "last": (getattr(self, "_jobs", None) or {}).get(j) or {}}
                     for j in (self.services().get("jobs") or {})},
        }


def plain_wav(data, rate=0):
    """Any sound the voice made -> a 16-bit WAV the hub can stream. -> (wav, why)

    The neural voices answer MP3 (cached under a .wav name - the cache key
    stays), which a browser plays and a robot's speaker cannot (A4-4). A
    16-bit WAV passes as it is; anything else is decoded by PyAV, which
    faster-whisper already installs, to mono at `rate` (0 = its own rate).
    """
    import io
    import wave
    if data[:4] == b"RIFF":
        try:
            with wave.open(io.BytesIO(data)) as w:
                if w.getsampwidth() == 2:
                    return data, None
        except (wave.Error, EOFError):
            pass
    try:
        import av
    except ImportError:
        return None, ("this PC cannot turn the neural voice into sound for a "
                      "robot - the av package is missing (faster-whisper brings it)")
    pcm = bytearray()
    try:
        with av.open(io.BytesIO(data)) as box:
            st = box.streams.audio[0]
            out_rate = int(rate or st.rate or 24000)
            rs = av.AudioResampler(format="s16", layout="mono", rate=out_rate)
            for frame in box.decode(st):
                for f in rs.resample(frame):
                    pcm += bytes(f.planes[0])[:f.samples * 2]
            for f in rs.resample(None):                 # what the resampler held
                pcm += bytes(f.planes[0])[:f.samples * 2]
    except Exception as e:                          # noqa: BLE001
        return None, "the voice's sound could not be read (%s)" % e
    if not pcm:
        return None, "the voice made no sound"
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(out_rate)
        w.writeframes(bytes(pcm))
    return buf.getvalue(), None


def web_page_refused(headers):
    """Why a request must be refused, or '' for a program on this PC.

    The helper has no password, so it answers programs only (the hub's proxy
    and speech queue, the face watcher). A website open on this PC reached it
    too: POST /config could pick a model that runs its own code (2026-09-29).
    Every browser request carries Origin or Sec-Fetch-*; a DNS-rebinding page
    names its own host in Host, never an IP.
    """
    import ipaddress
    from urllib.parse import urlsplit
    if headers.get("Origin") or any(k.lower().startswith("sec-fetch-")
                                    for k in headers.keys()):
        return "a web page cannot use the voice helper - go through the hub"
    host = (headers.get("Host") or "").strip()
    if not host:
        return ""
    try:
        name = urlsplit("//" + host).hostname or ""
    except ValueError:
        return "the voice helper answers only by IP address or localhost"
    if name.lower() == "localhost":
        return ""
    try:
        ipaddress.ip_address(name)
        return ""
    except ValueError:
        return "the voice helper answers only by IP address or localhost"


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

    def refuse_web(self):
        """True when the request was refused (and answered)."""
        why = web_page_refused(self.headers)
        if not why:
            return False
        n = int(self.headers.get("Content-Length") or 0)
        if 0 < n <= 1024 * 1024:
            self.rfile.read(n)          # read first, or Windows resets the socket
        self._json({"ok": False, "error": why}, 403)
        return True

    @guarded
    def do_GET(self):                               # noqa: N802
        if self.refuse_web():
            return
        path = urlparse(self.path).path
        self.brain.maybe_reload()
        if path == "/profiles":
            try:
                store = self.brain.enable_profiles()
                query = parse_qs(urlparse(self.path).query)
                if "kind" in query:
                    kind = query["kind"][0]
                    profile = query.get("profile", [store.active])[0]
                    asset = store.asset(profile, kind, query.get("name", [""])[0])
                    if kind != "motions":
                        raise ProfileError("Use the sound player to hear a sound file.")
                    return self._json({"ok": True, "text": asset.read_text(encoding="utf-8")})
                return self._json({"ok": True, **store.view(), "config": self.public_config(), "faqs": self.brain.faqs()})
            except (OSError, ValueError) as exc:
                return self._json({"ok": False, "error": str(exc)}, 400)
        if path == "/health":
            try:
                return self._json(self.brain.health())
            except Exception as e:                  # noqa: BLE001
                return self._json({"ok": False, "error": str(e)}, 500)
        if path == "/config":
            # Reading is open - the same rule as every other read on the hub.
            # So no key ever rides in it: an old Google key is left out.
            cfg = self.public_config()
            return self._json({"ok": True, "config": cfg, **self.profile_state()})
        if path == "/services":
            # Who can do each job and which keys are saved - never a key.
            return self._json(dict({"ok": True}, **self.brain.services_view()))
        if path == "/styles":
            # Speaking manners and what each speaking service really does (A45-25).
            return self._json(dict({"ok": True}, **self.brain.styles_view()))
        if path == "/faq":
            return self._json({"ok": True, "faqs": self.brain.faqs(), **self.profile_state()})
        if path == "/face":
            want = parse_qs(urlparse(self.path).query).get("camera", [""])[0]
            return self._json({"ok": True,
                               "person": self.brain.get_detected_person(camera=want),
                               "off": not self.brain.faces_on(),
                               "watcher": bool(getattr(self.brain, "_watcher_ok", False))})
        if path == "/camera":
            return self._json(dict({"ok": True}, **self.brain.camera_choice()))
        if path == "/voices":
            try:
                # voices: the ones that speak everything; byLang: every voice
                # of each language the store maps (A42-1).
                return self._json({"ok": True, "voices": self.brain.speaking_voices(),
                                   "byLang": self.brain.voices_by_lang()})
            except Exception as e:                      # noqa: BLE001
                return self._json({"ok": False, "error": "the voice list could not be "
                                                         "read: %s" % e}, 500)
        return self._json({"ok": False, "error": "unknown address"}, 404)

    def public_config(self):
        return {k: v for k, v in self.brain.cfg.items() if k != "googleApiKey"}

    def profile_state(self):
        store = getattr(self.brain, "profiles", None)
        return {"revision": store.revision(), "profile": store.active} if store else {}

    def do_profiles(self):
        try:
            length = int(self.headers.get("Content-Length") or 0)
            if length < 0 or length > 3 * 1024 * 1024:
                raise ProfileError("Choose a file smaller than 2 MB.")
            req = json.loads(self.rfile.read(length))
            if not isinstance(req, dict):
                raise ProfileError("That request could not be read.")
            store = self.brain.enable_profiles()
            store.check(req, writable=False)
            action = req.get("action")
            if action == "create":
                name = store.create(req.get("name"), store.active)
                store.select(name)
            elif action == "select":
                store.select(req.get("name"))
            elif action == "upload":
                store.upload(req)
            else:
                raise ProfileError("Choose a character action.")
            store.bind(self.brain)
            self.brain.maybe_reload()
            return self._json({"ok": True, **store.view()})
        except ProfileError as exc:
            return self._json({"ok": False, "error": str(exc)}, 409)
        except (OSError, ValueError, TypeError) as exc:
            return self._json({"ok": False, "error": str(exc)}, 400)

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
        if getattr(self.brain, "profiles", None):
            try:
                self.brain.profiles.check(req)
            except ProfileError as exc:
                return self._json({"ok": False, "error": str(exc)}, 409)
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
            if key == "config":
                # A key typed into the settings goes to the key file, never
                # into voice.json, which anyone on the WiFi can read (A45-1).
                old_key = str(data.pop("googleApiKey", "") or "").strip()
                if old_key:
                    self.brain.save_keys({"gemini": old_key})
                existing = dict(self.brain.cfg or {})
                existing.pop("googleApiKey", None)
                for k, v in data.items():
                    if isinstance(v, dict) and isinstance(existing.get(k), dict):
                        sub = dict(existing[k])
                        sub.update(v)
                        existing[k] = sub
                    elif v is not None:
                        existing[k] = v
                if "llm" in existing and "enabled" not in existing["llm"]:
                    existing["llm"]["enabled"] = True
                if "stt" in existing and "enabled" not in existing["stt"]:
                    existing["stt"]["enabled"] = True
                if "tts" in existing and "enabled" not in existing["tts"]:
                    existing["tts"]["enabled"] = True
                self.brain.write_store(path, existing)
            else:
                self.brain.write_store(path, {"faqs": data})
        except OSError as e:
            return self._json({"ok": False, "error":
                               "could not save: %s: %s"
                               % (e.__class__.__name__, e)}, 500)
        self.brain.maybe_reload()
        return self._json({"ok": True, **self.profile_state()})

    @guarded
    def do_POST(self):                              # noqa: N802
        if self.refuse_web():
            return
        path = urlparse(self.path).path
        self.brain.maybe_reload()
        if path == "/profiles":
            return self.do_profiles()
        if path == "/config":
            return self.do_store(self.brain.cfg_path, "config")
        if path == "/faq":
            return self.do_store(self.brain.faq_path, "faqs")
        if path == "/identify":
            return self.do_identify()
        if path == "/keys":
            return self.do_keys()
        if path == "/transcribe":
            return self.do_transcribe()
        if path == "/say":
            return self.do_say()
        if path == "/translate":
            return self.do_translate()
        if path == "/gesture":
            return self.do_gesture()
        if path == "/preload":
            self.brain.preload(force=True)
            return self._json({"ok": True, "llm": self.brain.llm_status(), "stt": self.brain.stt_status()})
        if path == "/unload":
            self.brain.unload()
            return self._json({"ok": True, "message": "models unloaded"})
        if path == "/stop":
            self._json({"ok": True, "message": "shutting down"})
            threading.Thread(target=self.server.shutdown, daemon=True).start()
            return
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
        take, why = self.brain.presence_gate()
        if not take:
            return self._json({"ok": False, "nobodyHere": True, "error": why}, 409)
        # A body that is a list, or a "text" that is a number, used to raise inside the
        # handler and drop the connection with no answer (found 2026-11-22, helpers_probe).
        if not isinstance(req, dict):
            return self._json({"ok": False, "error": "that request was not readable"}, 400)
        def _str(v):
            return v.strip() if isinstance(v, str) else ""
        text = _str(req.get("text"))
        history = req.get("history") if isinstance(req.get("history"), list) else []
        req_lang = _str(req.get("lang"))
        person = _str(req.get("person")) or _str(req.get("name"))
        if not person:
            person = self.brain.get_detected_person()
        auto_detect = req.get("autoDetect", True)
        if not auto_detect:
            eff_lang = req_lang or self.brain.main_language()
        else:
            eff_lang = req_lang or detect_lang(text)
        if not text:
            return self._json({"ok": False, "error": "there was no question in "
                                                    "that - say it again"}, 400)
        try:
            # "Please answer in English" said inside a Thai sentence: the
            # request wins over the script the words were written in, and
            # is taken out before the saved answers are searched (A45-24).
            asked_lang, question = intents.reply_language(text)
            if asked_lang:
                eff_lang = asked_lang
            # Read out EXACTLY: no model, no name added (A45-24: the English
            # form went to the model, which put the visitor's name in).
            read_target = intents.read_aloud(text)
            if read_target:
                out = {"ok": True, "answer": read_target, "source": "read",
                       "lang": asked_lang or (detect_lang(read_target) if auto_detect else eff_lang)}
                if person:
                    out["person"] = person
                return self._json(out)
            # A NEW verse skips the saved answers: the saved poem used to win
            # on the word "กลอน", and the model's greeting was spoken as one.
            if intents.wants_new_verse(text):
                reply, why_not = self.brain.compose(
                    [{"role": r.get("role", "user"), "content": str(r.get("content", ""))}
                     for r in history][-8:] + [{"role": "user", "content": text}], lang=eff_lang)
                if not reply:
                    return self._json({"ok": False, "error": why_not})
                out = {"ok": True, "answer": reply, "source": "verse", "lang": eff_lang}
                if person:
                    out["person"] = person
                return self._json(out)

            hit, score = self.brain.match_faq(question, lang=eff_lang)
            if hit:
                faq_ans = hit.get("answer") or ""
                if person:
                    faq_ans = personalize_answer(faq_ans, person, lang=hit.get("lang") or eff_lang,
                                                 address=self.brain.address_words())
                faq_ans = self.brain.manner_saved(faq_ans, hit.get("lang") or eff_lang)
                out = {"ok": True, "answer": faq_ans,
                       "source": "faq", "score": score,
                       "lang": hit.get("lang") or eff_lang}
                if person:
                    out["person"] = person
                # An answer may also MOVE a robot. The service only NAMES
                # the move - it never holds the password; the page, which
                # does, drives the show clock itself.
                for k in ("move", "module", "moves", "audio"):
                    if hit.get(k):
                        out[k] = hit[k]
                if getattr(self.brain, "profiles", None):
                    out["profile"] = self.brain.profiles.active
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
                 for r in history][-8:] + [{"role": "user", "content": text}],
                lang=eff_lang, person=person)
            if not reply:
                return self._json({"ok": False, "error": why_not})
            out = {"ok": True, "answer": reply, "source": "model",
                   "lang": eff_lang}
            if person:
                out["person"] = person
            return self._json(out)
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "the answer failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)

    def do_keys(self):
        """{keys: {service: key or ""}} -> the key file. The hub gates it like
        every save; nothing here ever sends a key back."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 64 * 1024:
            return self._json({"ok": False, "error": "that is too much to save"}, 400)
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except ValueError:
            return self._json({"ok": False, "error": "that request was not readable"}, 400)
        keys = req.get("keys")
        if not isinstance(keys, dict):
            return self._json({"ok": False, "error": "no keys were sent"}, 400)
        try:
            why = self.brain.save_keys(keys)
        except OSError as e:
            return self._json({"ok": False, "error": "could not save: %s" % e}, 500)
        if why:
            return self._json({"ok": False, "error": why}, 400)
        return self._json(dict({"ok": True}, **self.brain.services_view()))

    # Audio arrives as the request BODY, not JSON - a browser's MediaRecorder
    # stream is binary, and decoding it as text would destroy it.
    def do_identify(self):
        """One frame in, a name out, nothing kept. See Brain.identify."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 8 * 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that picture is too big to look at"}, 400)
        jpeg = self.rfile.read(length) if length else b""
        if not self.brain.faces_on():             # read first: no reset
            return self._json({"ok": False, "error":
                               "face recognition is switched off on the Voice page"})
        if not jpeg:
            return self._json({"ok": False, "error":
                               "no picture arrived - is the camera on?"}, 400)
        try:
            person, why_not, detail = self.brain.identify(jpeg)
        except Exception as e:                          # noqa: BLE001
            return self._json({"ok": False, "error": "looking failed: %s: %s"
                                                     % (e.__class__.__name__, e)}, 500)
        if why_not:
            # canStart is what turns the sentence into a button: only a face app
            # that is SILENT can be started, and a wrong password never can.
            # wouldKeep stops the page looking: every next frame would be refused too.
            return self._json({"ok": False, "error": why_not, "detail": detail,
                               "canStart": why_not == FACE_APP_OFF,
                               # Busy or still loading: nobody looked, so the
                               # name on the badge stands (it blinked off on
                               # every 429, PC 2026-10-19).
                               "noLook": why_not in FACE_APP_SAYS.values(),
                               "wouldKeep": why_not == FACE_APP_KEEPS})
        return self._json({"ok": True, "person": person})

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
            if req.get("agree"):
                text = self.brain.agree_text(text, req.get("lang") or "", voice_name)
            # "speed" / "pitch": the page's Try it, heard before saving.
            # Not "rate" - that is the robot speaker's sample rate below.
            folder = getattr(self.brain, "user_voice_folder", lambda: None)()
            recorded = UserVoice(CODE / "config" / "voice_clips.json").event_clip(folder, req.get("event"))
            if recorded:                            # a line the user recorded for this event
                wav, why_not = recorded.read_bytes(), ""
                self.brain._style_done = {}
            elif req.get("clip") and self.brain.profiles:
                store = getattr(self.brain, "profiles", None)
                path = store.asset(req.get("profile") or store.active, "audio", req["clip"])
                wav, why_not = path.read_bytes(), ""
                self.brain._style_done = {}
            else:
                wav, why_not = self.brain.say(
                text, req.get("lang") or "", voice=voice_name,
                rate=(str(req["speed"]) if req.get("speed") is not None else None),
                pitch=(str(req["pitch"]) if req.get("pitch") is not None else None),
                **({"style": str(req["style"])} if req.get("style") is not None else {}))
        except Exception as e:                      # noqa: BLE001
            return self._json({"ok": False,
                               "error": "speaking failed: %s: %s"
                                        % (e.__class__.__name__, e)}, 500)
        if why_not:
            return self._json({"ok": False, "error": why_not})
        if req.get("format") == "wav":
            # The hub's speaking queue: a robot's speaker plays 16-bit PCM
            # only, and so does the PC player (A4-4).
            try:
                rate = int(req.get("rate") or 0)
            except (TypeError, ValueError):
                rate = 0
            wav, why_not = plain_wav(wav, rate)
            if why_not:
                return self._json({"ok": False, "error": why_not})
        self.send_response(200)
        ctype = "audio/wav" if wav.startswith(b"RIFF") else ("audio/ogg" if wav.startswith(b"OggS") else "audio/mpeg")
        self.send_header("Content-Type", ctype)
        # How the manner was applied: instruct / prosody / none (A45-25).
        done = getattr(self.brain, "_style_done", None) or {}
        if done.get("style"):
            self.send_header("X-Voice-Style", "%s; %s; %s" % (done["style"], done.get("how") or "none",
                                                              done.get("by") or ""))
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

    def do_gesture(self):
        """POST {prompt, text} -> {ok, text}: the think chain's raw reply to a
        gesture request (A46-4). The hub cleans it (gestures.clean_made)."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 64 * 1024:
            return self._json({"ok": False, "error": "that request is too long"}, 400)
        try:
            req = json.loads(self.rfile.read(length).decode("utf-8")) if length else {}
        except ValueError:
            return self._json({"ok": False, "error": "that request was not readable"}, 400)
        prompt, text = str(req.get("prompt") or "").strip(), str(req.get("text") or "").strip()
        if not prompt or not text:
            return self._json({"ok": False, "error": "a prompt and a sentence are needed"}, 400)
        reply, why_not = self.brain.free_think(prompt, text)
        if not reply:
            return self._json({"ok": False, "error": why_not or "no service answered"})
        return self._json({"ok": True, "text": reply})

    def do_translate(self):
        """Translate text. Supports multi-target FAQ translation or complaints translation."""
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
        texts = req.get("texts")
        if texts and isinstance(texts, list):
            res_list = [self.brain.translate_all(str(t).strip(), source=req.get("source", "auto")) for t in texts]
            return self._json({"ok": True, "results": res_list})

        text = (req.get("text") or "").strip()
        if not text:
            return self._json({"ok": False, "error":
                               "there was nothing to translate"}, 400)

        # Multi-target FAQ auto-translation
        if req.get("all"):
            translations = self.brain.translate_all(text, source=req.get("source", "auto"))
            return self._json({"ok": True, "translations": translations})
        if req.get("target"):
            tgt = req.get("target")
            trans, err = self.brain._resources.map(lambda value: self.brain.translate_text(value, target=tgt, source=req.get("source", "auto")), [text])[0]
            return self._json({"ok": True, "text": trans, "target": tgt})

        # Default complaints translation (A21-8): keeps words and gains English twin
        if all(ord(c) < 128 for c in text):
            return self._json({"ok": True, "text": text, "translated": False})
        try:
            reply, why_not = self.brain._resources.map(self.brain.translate, [text])[0]
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
    last, felt = None, False
    while True:
        try:
            with brain.profile_lock:
                if brain.profiles:
                    brain.profiles.bind(brain)
                brain.maybe_reload()
                snapshot = copy.copy(brain)
                snapshot.cfg = copy.deepcopy(brain.cfg)
                m = (str(brain.faq_path), brain.faq_path.stat().st_mtime_ns,
                     brain.cfg_path.stat().st_mtime_ns,
                     getattr(brain, "styles_path", CODE / "config" / "voice_styles.json").stat().st_mtime_ns)

            # The feeling voice loads for ~20 s after boot: the first sweep is
            # spoken by the backup, so sweep again once it is up (A45-25).
            now = brain.feeling_up()
            if m != last or (now and not felt):
                last, felt = m, now
                snapshot.sync_faq_audio()
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
    try:
        brain.move_old_key()
    except OSError as e:
        print("[voice] the old Google key could not be moved: %s" % e)
    spec = registry.load(CODE / "config" / "voice_profiles.json")
    if (brain.cfg_path.parent / spec["folder"] / "active.json").exists():
        brain.enable_profiles()
    VoiceHandler.brain = brain
    svc = brain.cfg.get("service") or "http://127.0.0.1:8767"
    u = urlparse(svc)
    port = args.port or u.port or 8767
    host = u.hostname or "127.0.0.1"

    # The listen queue defaults to 5 connections. Measured 2026-11-21 with 200
    # clients at once: every burst past 5 waited for a SYN retry (1 s, 3 s, 7 s)
    # and a few timed out - a venue of phones and TVs all opening the page.
    ThreadingHTTPServer.request_queue_size = 256
    httpd = ThreadingHTTPServer((host, port), VoiceHandler)
    print("[voice] answering on %s:%d" % (host, port))
    if host not in ("127.0.0.1", "localhost", "::1"):
        # The opt-in has a cost; say it where the person opting in looks.
        print("[voice] shared beyond this PC - this helper has no password")

    # Preload models in background
    print("[voice] preloading models in background...")
    brain.preload(force=False)

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
