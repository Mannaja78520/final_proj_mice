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

# The end of a finished sentence, per language. Thai does not use a full stop,
# so a Thai sentence is finished when it ends on a polite particle - which is
# also why the particle rule below matters for more than manners.
SENTENCE_END = {
    "th": ("ครับ", "ค่ะ", "คะ", "นะครับ", "นะคะ", "จ้า", "!", "?", "\n"),
    "en": (".", "!", "?", "\n"),
    "ja": ("。", "！", "？", "\n"),
    "zh": ("。", "！", "？", "\n"),
    # Korean ends on 요/다/까 too, but those syllables also sit inside words
    # (다음, 까지), so cutting on them broke words. Punctuation only.
    "ko": (".", "!", "?", "。", "！", "？", "\n"),
    "ar": (".", "!", "?", "؟", "\n"),
    "hi": (".", "!", "?", "।", "\n"),
}


def answers_in(text, lang, particles=None):
    """Is this reply written in the language it was asked in?

    A very short Thai question - *ไวไฟ*, *ร้อนจัง* - gives a small model almost
    nothing to hold on to, and it answers in English or Chinese perhaps one
    time in five. The prompt already forbids it in four languages. This is the
    part that can actually be enforced: the scripts in the reply are a fact.

    Numbers, punctuation and a Latin product name inside a Thai sentence are
    fine - *รหัส WiFi คือ Welcome2024 ครับ* is a good Thai answer - so the test
    is not that the script stands alone, and not that it wins on character
    count either, which that sentence would lose.

    THE POLITE PARTICLE DOES NOT COUNT. Measured against the real 0.5B model
    2026-09-18: asked *ร้อนจัง* it answered `ครับ temperatures are hot today`,
    and asked *ไกลไหม* it answered `ครับ` and nothing else. Both carry Thai and
    both are worthless, because the only Thai in them is the ending. So the
    particles are taken off before looking, and what has to be Thai is what is
    left - which is the part that carries the answer.
    """
    bare = text or ""
    if lang == "th":
        for p in (particles or DEF_PARTICLES):
            bare = bare.replace(p, " ")
    got = scripts_in(bare)
    if not got:
        return False               # digits, punctuation or a bare particle
    if lang != "en" and got == {"en"} and re.fullmatch(r"[^\s]*\d[^\s]*[.!?]?", bare.strip()):
        return True                # the answer IS a code, e.g. a WiFi password: Welcome2024
    if lang in ("th", "ja", "zh", "ko", "ru", "ar", "hi"):
        return lang in got
    return "en" in got or not got - {"en"}


def trim_unfinished(text, lang, particles=None):
    """Cut a reply back to its last finished sentence, or return "".

    The model stops when it runs out of room, not when it has finished, so a
    tight token budget ends replies mid-word. Half a sentence read aloud is
    worse than a shorter whole one: the robot sounds like it broke.

    Only ever called when generation really hit the ceiling, so a reply that
    simply is short is never touched.
    """
    text = (text or "").strip()
    if not text:
        return ""
    ends = SENTENCE_END.get(lang) or SENTENCE_END["en"]
    if lang == "th":
        ends = tuple(particles or DEF_PARTICLES) + ("!", "?", "\n")
    if text.endswith(tuple(ends)):
        return text
    cut = -1
    for e in ends:
        i = text.rfind(e)
        if i >= 0:
            cut = max(cut, i + len(e))
    return text[:cut].strip() if cut > 0 else ""




# หนู is a first-person word too, and also means mouse - this robot is called
# Mice, so it is left OUT on purpose. One entry in politePronouns brings it back.




def unquote_whole(text):
    """Take the quotation marks off an answer that is entirely inside them.

    The model wraps a whole reply in " or “ ” perhaps one time in ten, which a
    speech voice reads as a pause and a person reads as the robot quoting
    somebody else. Only a pair that wraps EVERYTHING is removed - a quote
    inside a sentence is somebody's actual words and stays.
    """
    t = (text or "").strip()
    for a, b in (('"', '"'), ("“", "”"), ("'", "'"),
                 ("‘", "’"), ("«", "»")):
        if len(t) > 2 and t.startswith(a) and t.endswith(b) and b not in t[1:-1]:
            return t[1:-1].strip()
    return t






def format_multi_person(person, lang="th", address=("คุณ",)):
    """Format single or multiple detected persons gracefully."""
    p_str = str(person).strip()
    if not p_str:
        return ""
    raw_names = [n.strip() for n in re.split(r'\s+(?:และ|and)\s+|,\s*', p_str) if n.strip()]
    if not raw_names:
        return ""
    short_names = [short_person_name(n) for n in raw_names]

    if lang == "en":
        if len(short_names) == 1:
            return short_names[0]
        elif len(short_names) == 2:
            return f"{short_names[0]} and {short_names[1]}"
        else:
            return f"{short_names[0]}, {short_names[1]} and everyone"
    elif lang == "ja":
        if len(short_names) == 1:
            return f"{short_names[0]}さん"
        elif len(short_names) == 2:
            return f"{short_names[0]}さんと{short_names[1]}さん"
        else:
            return f"{short_names[0]}さん、{short_names[1]}さん、皆さん"
    elif lang == "zh":
        if len(short_names) == 1:
            return short_names[0]
        elif len(short_names) == 2:
            return f"{short_names[0]}和{short_names[1]}"
        else:
            return f"{short_names[0]}、{short_names[1]}和大家"
    else:  # th
        # A name that already carries its form of address (call_as "พี่บอส")
        # is not given a second one: config/voice.json face.addressWords.
        th_names = [n if n.startswith(tuple(address)) else f"คุณ{n}" for n in short_names]
        if len(th_names) == 1:
            return th_names[0]
        elif len(th_names) == 2:
            return f"{th_names[0]} และ{th_names[1]}"
        else:
            return f"{th_names[0]}, {th_names[1]} และทุกท่าน"


def personalize_answer(answer, person, lang="th", address=("คุณ",)):
    """Personalize an answer with the recognized person(s) naturally."""
    if not person or not answer or not str(answer).strip():
        return answer

    ans = str(answer).strip()
    l = lang or detect_lang(ans)

    s_names = [short_person_name(n) for n in re.split(r'\s+(?:และ|and)\s+|,\s*', str(person)) if n.strip()]
    if any(s.lower() in ans.lower() for s in s_names if s):
        return answer

    addressed = format_multi_person(person, lang=l, address=address)
    if not addressed:
        return answer

    if l == "en":
        m = re.match(r'^(hello|hi|good morning|good afternoon|good evening|welcome)[,!.\s]*', ans, re.I)
        if m:
            greeting = m.group(1)
            rest = ans[m.end():].lstrip()
            if rest:
                return f"{greeting} {addressed}, {rest}"
            return f"{greeting} {addressed}"
        return f"Hello {addressed}, {ans}"

    elif l == "ja":
        m = re.match(r'^(こんにちは|こんばんは|おはようございます|いらっしゃいませ)[、,！!\s]*', ans)
        if m:
            greeting = m.group(1)
            rest = ans[m.end():].lstrip()
            if rest:
                return f"{greeting}、{addressed}。{rest}"
            return f"{greeting}、{addressed}。"
        return f"{addressed}、{ans}"

    elif l == "zh":
        m = re.match(r'^(你好|您好|早上好|下午好|晚上好|欢迎)[，,！!\s]*', ans)
        if m:
            greeting = m.group(1)
            rest = ans[m.end():].lstrip()
            if rest:
                return f"{greeting}，{addressed}！{rest}"
            return f"{greeting}，{addressed}！"
        return f"{addressed}，{ans}"

    else:  # th
        m = re.match(r'^(สวัสดีครับ|สวัสดีค่ะ|สวัสดี)[!.\s]*', ans)
        if m:
            greeting = m.group(1)
            rest = ans[m.end():].lstrip()
            if rest:
                return f"{greeting}{addressed} {rest}"
            return f"{greeting}{addressed}"
        return f"{addressed}ครับ {ans}"


class Brain(FaceLink, Translator, Listener, Speaker):
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

    # Words that are a QUESTION, not a subject. Alone, "อะไร" (what) sits
    # inside "กินอะไรดี" and would answer every asker with the food desk.
    # In the store, so the next one costs no code.
    STOP_WORDS = ("อะไร", "ไหน", "ที่ไหน", "ยังไง", "อย่างไร", "ทำไม",
                  "เมื่อไหร่", "ใคร", "ไหม", "หรอ", "เหรอ", "ครับ", "ค่ะ",
                  "คะ", "นะ", "ได้", "何", "どこ", "什么", "哪里")

    def faq_stop_words(self):
        got = self.cfg.get("faqStopWords")
        return tuple(got) if isinstance(got, list) and got else self.STOP_WORDS

    def faq_best(self, text):
        """(best score, closest saved entry) - no translation, no writes, so a
        second hearing can be compared on it (A45-24)."""
        best, hit = 0.0, None
        # Thai-letter loanwords become the English word on BOTH sides, so
        # "ปาร์กกิ้ง" finds "parking" and a saved "ไวไฟ" still finds itself.
        got = intents.loanwords(text.strip().lower())
        # A stop word is matched as stored AND as mapped ("ไวไฟ" is "wifi" now).
        stops = set(self.faq_stop_words())
        stops |= {intents.loanwords(w.lower()) for w in stops}
        norm_got = re.sub(r'^(ช่วยบอกหน่อย|รบกวนถามหน่อย|อยากทราบว่า|อยากรู้ว่า|ขอถามหน่อย|สอบถามหน่อย|ช่วยแนะนำหน่อย|please tell me |can you tell me |could you tell me )', '', got)
        norm_got = re.sub(r'(ครับ|ค่ะ|คะ|หน่อยครับ|หน่อยค่ะ|หน่อย|จ้า|จ๊ะ| please)[.!?]*$', '', norm_got).strip()
        for item in self.faqs():
            for q in item.get("questions", []):
                qc = intents.loanwords(q.strip().lower())
                if item.get("wholeQuestion"):
                    short = lambda v: "".join(c for c in v if not c.isspace() and not unicodedata.category(c).startswith("P"))
                    nq, ng = short(qc), short(norm_got)
                    coverage = min(len(ng), len(nq)) / max(len(ng), len(nq), 1)
                    if coverage < 0.8:
                        continue
                s1 = SequenceMatcher(None, got, qc).ratio()
                s2 = SequenceMatcher(None, norm_got, qc).ratio() if norm_got else 0.0
                score = max(s1, s2)
                if len(qc) >= 6:
                    if qc in got or (norm_got and qc in norm_got):
                        coverage = len(qc) / max(len(got), 1)
                        sub_score = 0.80 + 0.15 * min(1.0, coverage)
                        score = max(score, sub_score)
                    elif (got in qc and len(got) >= 8) or (norm_got and norm_got in qc and len(norm_got) >= 8):
                        coverage = max(len(got), len(norm_got)) / max(len(qc), 1)
                        sub_score = 0.75 + 0.15 * min(1.0, coverage)
                        score = max(score, sub_score)
                elif len(qc) >= 3 and detect_lang(qc) in ("th", "ja", "zh", "ko"):
                    if qc in got or (norm_got and qc in norm_got):
                        coverage = len(qc) / max(len(got), 1)
                        sub_score = 0.80 + 0.15 * min(1.0, coverage)
                        score = max(score, sub_score)
                # A short word that IS a saved question's subject: Thai and
                # CJK write without spaces, so the eight-character floor above
                # never fires for a real word. "ไวไฟ" inside "รหัสไวไฟ" missed
                # the saved answer and the local model invented a greeting
                # instead (user 2026-09-18). Three characters and a third of
                # the saved question is the floor - below that a word like
                # "ไป" would match half the store. A quarter, because a saved
                # question is often long: "ไวไฟ" is 4 of the 14 in
                # "รหัสไวไฟคืออะไร".
                if (detect_lang(qc) in ("th", "ja", "zh", "ko") and len(got) >= 3
                        and got not in stops
                        and got in qc and len(got) / max(len(qc), 1) >= 0.25):
                    score = max(score, 0.76 + 0.15 * (len(got) / max(len(qc), 1)))
                if score > best:
                    best, hit = score, item
        return best, hit

    def supported_langs(self):
        """Every language configured in this store, th, en, ja, zh first.

        A key becomes a column name (answer_<code>), so only a real language
        code counts: "ko-KR" and "KO" are ko; " ", "../x" or "answer" are not
        languages and are skipped. A list instead of a map does not break
        this (other readers still expect a map).
        """
        out = ["th", "en", "ja", "zh"]
        cfg = getattr(self, "cfg", None) or {}
        tts = cfg.get("tts") if isinstance(cfg.get("tts"), dict) else {}
        stt = cfg.get("stt") if isinstance(cfg.get("stt"), dict) else {}
        ans = cfg.get("answer") if isinstance(cfg.get("answer"), dict) else {}
        for d in (tts.get("voices"), stt.get("languages"),
                  ans.get("onlyThisLanguage"), ans.get("cannotAnswer")):
            if not isinstance(d, (dict, list, tuple)):
                continue
            for k in d:
                code = str(k).strip().replace("_", "-").split("-")[0].lower()
                if 2 <= len(code) <= 3 and code.isascii() and code.isalpha() \
                        and code not in out:
                    out.append(code)
        return out

    def match_faq(self, text, lang=""):
        """The closest saved ENTRY over the threshold, or (None, score).

        The whole entry comes back, not just its answer: an entry may name
        a move and a module too (A20-10), and the caller passes them on.
        """
        th = float(self.cfg.get("faqThreshold", 0.75))
        best, hit = self.faq_best(text)
        if best >= th and hit:
            eff_lang = lang or detect_lang(text)
            ans_key = f"answer_{eff_lang}"
            ans = hit.get(ans_key)
            if not ans and eff_lang in self.supported_langs():
                base_ans = hit.get("answer", "")
                if base_ans:
                    base_lang = detect_lang(base_ans)
                    if base_lang != eff_lang:
                        translated, _ = self.translate_text(base_ans, target=eff_lang, source=base_lang)
                        if translated and detect_lang(translated) == eff_lang:
                            ans = translated
                            hit[ans_key] = translated
                            try:
                                self.write_store(self.faq_path, {"faqs": self.faqs()})
                            except Exception:
                                pass
            if not ans:
                ans = hit.get("answer", "")
            res = dict(hit)
            res["answer"] = ans
            res["lang"] = eff_lang if (detect_lang(ans) == eff_lang or not eff_lang) else detect_lang(ans)
            return (res, round(best, 2))
        return (None, round(best, 2))

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

    def llm_status(self):
        lcfg = self.cfg.get("llm", {})
        if not lcfg.get("enabled"):
            return "off in config/voice.json"
        if self._llm:
            return "loaded"
        if self._llm_loading:
            return "loading in background…"
        if self._llm_err:
            return "could not load: " + self._llm_err
        return "loads when first needed"


    # --- speaking out loud (A20-9) -------------------------------------
    # Windows' own synthesiser, reached through apps/voice/tts.ps1. No
    # internet, no pip install: the venue PC's own voices, named in the
    # store. Answers are cached by md5(text+voice) so a saved answer's
    # SECOND visitor hears it instantly - and a watcher thread pre-builds
    # every saved answer, re-running when qa_data.json is edited on disk.


    def _load_llm(self):
        # One load per model at a time (A55-1): the boot preload runs without
        # the GPU lock, so a first question used to load a SECOND copy beside
        # it - double VRAM on a 12 GB card the face app shares. A waiter finds
        # it loaded (or its error) and returns.
        lock = self.__dict__.setdefault("_load_lock_llm", threading.Lock())
        with lock:
            return self._load_llm_now()

    def _load_llm_now(self):
        if not self.cfg.get("llm", {}).get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._llm or self._llm_err:
            return
        self._llm_loading = True
        try:
            import torch                                    # noqa: F401
            from transformers import AutoConfig, AutoModelForCausalLM, AutoTokenizer
            mid = self.cfg.get("llm", {}).get("model", str(CODE / "llm"))
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=True)
            mdl = None
            resource_plan, memory_budget = self._resources.torch_plan(torch)
            if resource_plan["device"] == "cuda":
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                try:
                    mdl = AutoModelForCausalLM.from_pretrained(
                        mid, torch_dtype=dtype, device_map="auto", max_memory=memory_budget,
                        attn_implementation="sdpa",
                        trust_remote_code=True)
                except Exception:
                    torch.cuda.empty_cache()
                    try:
                        from transformers import BitsAndBytesConfig
                        quant = BitsAndBytesConfig(
                            load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16,
                            bnb_4bit_quant_type="nf4", bnb_4bit_use_double_quant=True)
                        mdl = AutoModelForCausalLM.from_pretrained(
                            mid, quantization_config=quant, device_map="auto", max_memory=memory_budget,
                            trust_remote_code=True)
                    except Exception:
                        mdl = self._resources.cpu_load(mid, AutoModelForCausalLM, AutoConfig, torch, resource_plan)
            else:
                mdl = self._resources.cpu_load(mid, AutoModelForCausalLM, AutoConfig, torch, resource_plan)
            self._resources.mark("llm:" + mid, resource_plan, str(mdl.device))
            self._llm = (tok, mdl)
            self._llm_loaded_model = mid
            if torch.cuda.is_available():
                try:
                    dummy_in = tok(["hi"], return_tensors="pt").to(mdl.device)
                    with torch.no_grad():
                        mdl.generate(**dummy_in, max_new_tokens=1)
                except Exception:
                    pass
        except Exception as e:                              # noqa: BLE001
            self._llm_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._llm_loading = False

    def preload(self, force=False):
        """Preload LLM and STT models in background so they are ready immediately."""
        self.maybe_reload()
        if force:
            if not self.cfg.get("llm", {}).get("enabled"):
                self.cfg.setdefault("llm", {})["enabled"] = True
            if not self.cfg.get("stt", {}).get("enabled"):
                self.cfg.setdefault("stt", {})["enabled"] = True
        if self._preload_thread and self._preload_thread.is_alive():
            return True

        def _worker():
            self._warm_local_ai(force)
            if force or self.cfg.get("llm", {}).get("enabled"):
                if not self._llm:
                    self._load_llm()
            if force or self.cfg.get("stt", {}).get("enabled"):
                if not self._stt:
                    self._load_stt()
                # A language's own hearing model too: its first load is a
                # download, which must not land on a visitor's first question.
                own = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage") or {}
                for lang in own:
                    try:
                        self._own_model(lang)
                    except Exception:                   # noqa: BLE001
                        pass              # _own_model keeps each model's error until retry succeeds

        self._preload_thread = threading.Thread(target=_worker, daemon=True)
        self._preload_thread.start()
        return True

    def _warm_local_ai(self, force):
        """Load the think model of a local server (Ollama) before the first question.

        At boot only if the server is already up (it is never started just for
        this); the Load-the-AI button (force) may start it, as any question would.
        """
        for pid in self.chain("think"):
            prov = self.service(pid)
            if not prov.get("autoStart"):
                continue
            if force:
                up, _ = local_ai.wake(prov)
            else:
                up = local_ai.is_up(prov["autoStart"]["ready"], local_ai.SHORT)
            if up:
                local_ai.warm(prov, prov["jobs"].get("think"))
            return

    def unload(self):
        """Unload LLM and STT models from memory and free GPU/RAM."""
        with self._lock:
            self._resources.clear()
            self._llm = None
            self._stt = None
            self._stt_own = {}
            self._stt_batches = {}
            self._stt_attempt_model = None
            self._stt_last = None
            self._stt_own_err = {}
            self._llm_err = None
            self._stt_err = None
            self._llm_loading = False
            self._stt_loading = False
            self._llm_loaded_model = None
            self._stt_loaded_model = None
            import gc
            gc.collect()
            try:
                import torch
                if torch.cuda.is_available():
                    torch.cuda.empty_cache()
            except Exception:
                pass
        return True

    def _complete(self, messages, max_tokens=None, details=False):
        """One model call on exactly the messages given - no persona added.

        Callers hold the lock and have already checked the model is loaded.

        `details=True` also says whether generation RAN OUT of room rather than
        finishing. That is a fact from the token count, not a guess at the
        text, and it is the only reliable way to tell "this reply is short" from
        "this reply was cut off" - which matters because Thai has no full stop
        to look for (user 2026-09-18: *it cuts replies off*).
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
        limit = max_tokens or int(self.cfg.get("llm", {}).get("maxTokens", 128))
        with torch.inference_mode():
            out = mdl.generate(
                **inputs,
                max_new_tokens=limit,
                do_sample=False,
                use_cache=True,
                pad_token_id=tok.eos_token_id)
        made = out[0][inputs.input_ids.shape[1]:]
        reply = tok.decode(made, skip_special_tokens=False)
        if details:
            # No end-of-text token in what came back = it stopped because the
            # budget ran out, not because it had finished.
            ran_out = len(made) >= limit and (
                tok.eos_token_id is None or int(made[-1]) != int(tok.eos_token_id))
            return self.clean(reply), bool(ran_out)
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

    def generate(self, history, lang="", person=""):
        """The answer, or (None, why-not) in plain words.

        Who answers is the `think` chain (A45-1): this PC's model, or a
        service. Every one gets the same instructions - the saved answers
        nearest the question, the scenario, the name - and every reply passes
        the same guards; one in the wrong language goes to the next in line.
        The Google path before A45-1 skipped the saved answers entirely.
        """
        # A name in `scenario` resolves to that scenario's prompt; plain
        # text is still its own prompt (active_scenario).
        scenario = self.active_scenario().get("prompt") or ""
        system, limit, is_verse = self._think_prompt(history, lang, person, scenario)

        def one(pid, prov):
            if prov.get("kind") == "local":
                return self._generate_local(system, history, limit, is_verse, lang)
            wire = providers.WIRES.get(prov.get("kind"), {}).get("think")
            if not wire:
                return None, "it cannot answer"
            reply, why = wire(prov, self.key_for(pid), prov["jobs"]["think"], system,
                              history, limit, timeout=20)
            if not reply:
                return None, why
            reply = self.tidy_answer(self.clean(reply), lang, verse=is_verse)
            if not reply:
                return None, "its answer was empty"
            if not is_verse and not answers_in(reply, lang, self.particles()):
                return None, "it answered in another language"
            return reply, None
        reply, why_not = self.run_job("think", one)
        if not reply:
            return None, why_not
        if person:
            reply = personalize_answer(reply, person, lang=lang,
                                       address=self.address_words())
            # the name is added with ครับ; a woman's voice must not say it
            # (PC test 2026-11-04: "คุณผู้ทดสอบครับ เดินตรงไป...ค่ะ")
            reply = self.manner_saved(reply, lang)
        return reply, None

    def free_think(self, system, text, limit=200):
        """One reply to exactly this instruction, no persona (A46-4: Studio
        asks for a talk gesture as JSON). The same `think` chain as answers,
        cloud or this PC, so nothing is tied to one service."""
        history = [{"role": "user", "content": str(text)}]

        def one(pid, prov):
            if prov.get("kind") == "local":
                with self._lock:
                    ok, why_not = self._ensure_llm()
                    if not ok:
                        return None, why_not
                    return self._complete([{"role": "system", "content": system}] + history,
                                          max_tokens=limit) or None, None
            wire = providers.WIRES.get(prov.get("kind"), {}).get("think")
            if not wire:
                return None, "it cannot answer"
            return wire(prov, self.key_for(pid), prov["jobs"]["think"], system,
                        history, limit, timeout=20)
        return self.run_job("think", one)

    def compose(self, history, lang=""):
        """A NEW verse on the asked topic, or (None, why-not) (A45-24).

        Its own `compose` chain, so a stronger service can write verse while
        this PC still answers the rest. The reply must LOOK like a new verse
        (intents.verse_problem): enough lines, no greeting, not a saved
        answer. One stricter retry per service; when none manages, an honest
        sorry is said instead of a greeting or the saved poem. No name is
        added: it would break the first line.
        """
        lang = lang or "th"
        system = intents.compose_text("prompt", lang)
        retry = intents.compose_text("retry", lang)
        limit = int((intents.table().get("compose") or {}).get("maxTokens") or 200)
        saved = [it.get(k) or "" for it in self.faqs()
                 for k in ("answer", "answer_en", "answer_ja", "answer_zh")]
        problems = []

        def check(reply):
            reply = self.tidy_answer(self.clean(reply or ""), lang, verse=True)
            why = intents.verse_problem(reply, saved, lang=lang)
            if not why and not answers_in(reply, lang, self.particles()):
                why = "it wrote in another language"
            return (reply, "") if not why else (None, why)

        def one(pid, prov):
            for i, prompt in enumerate((system, system + "\n" + retry)):
                if prov.get("kind") == "local":
                    with self._lock:
                        ok, why_not = self._ensure_llm()
                        if not ok:
                            return None, why_not
                        raw, _ran_out = self._complete([{"role": "system", "content": prompt}] + history,
                                                       max_tokens=limit, details=True)
                else:
                    wire = providers.WIRES.get(prov.get("kind"), {}).get("think")
                    if not wire:
                        return None, "it cannot write"
                    raw, why = wire(prov, self.key_for(pid), prov["jobs"]["compose"], prompt,
                                    history, limit, timeout=20)
                    if not raw:
                        return None, why
                reply, why = check(raw)
                if reply:
                    return reply, None
                problems.append("%s try %d: %s" % (pid, i + 1, why))
            return None, problems[-1]
        reply, why_not = self.run_job("compose", one)
        if reply:
            return reply, None
        if not problems:
            return None, why_not            # nobody could write at all (not loaded, no key)
        # A writer answered but never with a verse: say so, honestly.
        self._compose_why = why_not
        return intents.compose_text("failed", lang) or self.cannot_answer(lang), None

    def _think_prompt(self, history, lang, person, scenario):
        """(system prompt, room for the reply, is it a verse) for a question."""
        # The saved questions ride along, so a near-miss can still be
        # answered from them - the prototype's trick that made it useful
        # on a laptop.
        # Only keep top-2 nearest FAQ items to keep prompt short and fast
        last_q = ""
        for m in reversed(history):
            if m.get("role") == "user":
                last_q = m.get("content", "").strip().lower()
                break
        norm_last_q = re.sub(r'^(ช่วยบอกหน่อย|รบกวนถามหน่อย|อยากทราบว่า|อยากรู้ว่า|ขอถามหน่อย|สอบถามหน่อย|ช่วยแนะนำหน่อย|please tell me |can you tell me |could you tell me )', '', last_q)
        norm_last_q = re.sub(r'(ครับ|ค่ะ|คะ|หน่อยครับ|หน่อยค่ะ|หน่อย|จ้า|จ๊ะ| please)[.!?]*$', '', norm_last_q).strip()

        scored = []
        for item in self.faqs():
            s = 0.0
            for cand in item.get("questions", []):
                qc = cand.strip().lower()
                s1 = SequenceMatcher(None, last_q, qc).ratio() if last_q else 0.0
                s2 = SequenceMatcher(None, norm_last_q, qc).ratio() if norm_last_q else 0.0
                sc = max(s1, s2)
                if len(qc) >= 6 and last_q:
                    if qc in last_q or (norm_last_q and qc in norm_last_q):
                        sub_score = 0.80 + 0.15 * min(1.0, len(qc) / max(len(last_q), 1))
                        sc = max(sc, sub_score)
                    elif (last_q in qc and len(last_q) >= 8) or (norm_last_q and norm_last_q in qc and len(norm_last_q) >= 8):
                        sub_score = 0.75 + 0.15 * min(1.0, max(len(last_q), len(norm_last_q)) / max(len(qc), 1))
                        sc = max(sc, sub_score)
                if sc > s:
                    s = sc
            if s >= 0.35:
                scored.append((s, item))
        scored.sort(key=lambda x: x[0], reverse=True)
        top_items = [it for _, it in scored[:2]] if scored else []

        faq_lines = []
        for i, item in enumerate(top_items, 1):
            qs = item.get("questions", [])
            q = ""
            for candidate in qs:
                if detect_lang(candidate) == lang:
                    q = candidate
                    break
            if not q and qs:
                q = qs[0]
            ans = ""
            if lang == "en":
                ans = item.get("answer_en") or item.get("answer")
            elif lang == "ja":
                ans = item.get("answer_ja") or item.get("answer")
            elif lang == "zh":
                ans = item.get("answer_zh") or item.get("answer")
            elif lang == "ko":
                ans = item.get("answer_ko") or item.get("answer")
            else:
                ans = item.get("answer")
            faq_lines.append("%d. %s\n   %s" % (i, q, ans))

        scenario_hint = ("\nScenario / Persona: %s\n" % scenario) if scenario else ""
        person_hint = ""
        if person:
            s_name = short_person_name(person)
            if lang == "en":
                person_hint = f"\nThe user speaking to you has been recognized as '{s_name}'. Address them politely by their name (e.g. 'Hello {s_name}, ...').\n"
            elif lang == "ja":
                person_hint = f"\n利用者の名前は「{s_name}」です。お名前（{s_name}さん）を呼んで回答してください。\n"
            elif lang == "zh":
                person_hint = f"\n向你提问的用户已被识别为「{s_name}」。请礼貌地称呼其名字回答。\n"
            else:
                thai_title = s_name if s_name.startswith("คุณ") else f"คุณ{s_name}"
                person_hint = f"\nผู้ใช้ที่กำลังคุยกับคุณได้รับการระบุชื่อคือ '{thai_title}' จงกล่าวทักทายหรือเรียกชื่อ{thai_title}อย่างสุภาพในคำตอบด้วย\n"
        is_verse = bool(re.search(r'(กลอน|บทกลอน|กาพย์|โคลง|ฉันท์|กวี|คำประพันธ์|verse|poem|poetry|rhyme)', last_q, re.I) or
                        (scenario and re.search(r'(กลอน|บทกลอน|กาพย์|โคลง|ฉันท์|กวี|verse|poem|poetry)', scenario, re.I)))

        if lang == "en":
            system = ("You are the Mice robot assistant. "
                      "Style: Caveman — direct, plain-spoken, concise. Zero filler words. Absolutely NO emojis. Maximum 1 short sentence.\n"
                      + scenario_hint
                      + person_hint
                      + ("\nRelevant FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "Always follow the created FAQ answers as closely as possible, never deviate off-topic. If question matches or relates to FAQ, answer from it. Otherwise answer directly in 1 short sentence as the Mice robot. NEVER invent a password, price, time, floor, place or EVENT that is not in the FAQ above - say you do not know, and to ask a member of staff.")
        elif lang == "ja":
            system = ("あなたはMiceロボットです。\n"
                      "スタイル：簡潔、直接的、絵文字なし。最大1文で短く答えてください。\n"
                      + scenario_hint
                      + person_hint
                      + ("\n関連FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "作成されたFAQ回答にできる限り忠実に従い、脱線しないでください。FAQに関連していればそれに従い、それ以外はMiceロボットとして1文で簡潔に答えてください。FAQにないパスワード・料金・時間・場所・イベントを作り出さないでください。分からない場合は分からないと答えてください。")
        elif lang == "zh":
            system = ("你是Mice机器人助手。\n"
                      "风格：简明扼要、直接清晰、绝不使用表情符号。最多1句简短回答。\n"
                      + scenario_hint
                      + person_hint
                      + ("\n相关FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "请尽可能紧密依据所给的FAQ答案回答，切勿偏离主题。如果问题与FAQ相关则按FAQ回答，否则作为Mice机器人用1句简短回答。不要编造FAQ中没有的密码、价格、时间、地点或活动；不知道就说不知道，请询问工作人员。")
        elif lang == "ko":
            system = ("You are the Mice robot assistant. Answer ONLY in Korean, in one short polite sentence, no emojis.\n"
                      + scenario_hint
                      + person_hint
                      + ("\nRelevant FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "Follow the FAQ answers closely. NEVER invent a password, price, time, floor, place or event that is not in the FAQ above - say in Korean that you do not know and to ask a member of staff.")
        elif is_verse and lang == "th":
            system = ("คุณคือหุ่นยนต์ Mice เมื่อผู้ใช้ขอให้อ่านหรือท่องบทกลอน จงท่องบทกลอนภาษาไทยที่ไพเราะ 1 บท (4 วรรค) แบ่งบรรทัดละวรรค ห้ามปฏิเสธ ไม่มีคำเยิ่นเย้อ ไม่มีอีโมจิ\n"
                      + scenario_hint
                      + person_hint)
        else:
            # ONE PARTICLE, said before anything else. The model ended one
            # sentence ครับ and the next ค่ะ, which in Thai reads as two
            # different people. one_particle() fixes what gets through, but
            # asking for it costs nothing and gives the model the character
            # to write in (user 2026-09-18).
            keep, me, wording = self.manner_answer("th")
            not_end = " ".join(p for p in ("ครับ", "ค่ะ", "คะ", "จ้า") if p != keep)
            not_me = " หรือ ".join(p for p in ("ผม", "ฉัน", "ดิฉัน") if p != me)
            system = ("คุณคือหุ่นยนต์ Mice ให้ข้อมูลบริการและสถานที่ จงตอบเป็นภาษาไทยเท่านั้น สั้นๆ ตรงประเด็น 1 ประโยคจบในตัว ห้ามตอบเป็นภาษาอังกฤษหรือภาษาอื่น ไม่มีคำเยิ่นเย้อ ไม่มีอีโมจิ\n"
                      + ("ลงท้ายประโยคด้วยคำว่า '%s' เสมอ ห้ามใช้คำลงท้ายอื่น เช่น %s และเรียกตัวเองว่า '%s' เสมอ ห้ามใช้ %s เพราะคุณเป็นหุ่นยนต์ตัวเดียวและต้องพูดด้วยน้ำเสียงเดียวกันทุกประโยค\n" % (keep, not_end, me, not_me))
                      + ((wording + "\n") if wording else "")
                      + scenario_hint
                      + person_hint
                      + ("\nFAQ ที่เกี่ยวข้อง:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "จงตอบโดยยึดตามข้อมูลคำตอบที่สร้างไว้ (FAQ) ให้ใกล้เคียงที่สุดเสมอ หากคำถามเกี่ยวข้องกับ FAQ ให้ตอบตามนั้น หากไม่ตรงให้ตอบสั้นๆ ในฐานะหุ่นยนต์ Mice 1 ประโยคเป็นภาษาไทย ห้ามแต่งรหัสผ่าน ราคา เวลา ชั้น สถานที่ หรือกิจกรรม/ข่าวที่ไม่มีใน FAQ ถ้าไม่รู้ให้บอกว่าไม่ทราบและให้สอบถามเจ้าหน้าที่")
        # ROOM TO FINISH A SENTENCE, per language. 32 tokens was chosen for
        # speed and is fine for English; Thai costs two to four tokens per
        # word, so the same budget stopped Thai answers in the middle of a
        # word (user 2026-09-18: *it cuts replies off*). The budget is DATA
        # so it can be tuned per language without touching this file.
        if lang in ("en", "ja", "zh", "ko"):
            wording = self.manner_answer(lang)[2]
            if wording:
                system += "\n" + wording
        shots = (self.answer_cfg().get("examples") or {}).get(lang) or []
        if shots and not is_verse:
            # Three short Q/A pairs per language: on the PC bench (2026-11-04)
            # Typhoon 4B went Thai 24 -> 28 of 30 and invented 4 -> 0 facts. They
            # sit AFTER the FAQ and hold no facts, only manner and "I do not know".
            system += "\n\n" + self.answer_cfg().get("examplesTitle", {}).get(lang, "Examples:") + "\n" + "\n".join(
                "Q: %s\nA: %s" % (q, a) for q, a in shots)
        limit = 96 if is_verse else self.token_budget(lang)
        return system, limit, is_verse

    def _generate_local(self, system, history, limit, is_verse, lang):
        """This PC's model, with its one wrong-language retry."""
        with self._lock:
            ok, why_not = self._ensure_llm()
            if not ok:
                return None, why_not
            messages = [{"role": "system", "content": system}] + history
            reply, ran_out = self._complete(messages, max_tokens=limit, details=True)
            reply = self.tidy_answer(reply, lang, ran_out=ran_out, verse=is_verse)
            if not reply:
                # Nothing whole survived. Saying so is the honest answer: a
                # robot reading half a sentence aloud sounds broken, and one
                # that invents the rest breaks the rule that matters most.
                return self.cannot_answer(lang), None
            if not answers_in(reply, lang, self.particles()) and not is_verse:
                # ONE retry, with the language demand on its own line where a
                # small model cannot lose it among the FAQ and the persona.
                # The FAQ stays: with only the language line a small model invented
                # facts (opens 9:00, parking in the basement; PC bench 2026-11-04).
                again = [{"role": "system", "content": system + "\n" + self.only_this_language(lang)}] + history
                reply2, ran2 = self._complete(again, max_tokens=limit, details=True)
                reply2 = self.tidy_answer(reply2, lang, ran_out=ran2)
                reply = reply2 if reply2 and answers_in(reply2, lang, self.particles()) else ""
            if not reply:
                return self.cannot_answer(lang), None
            return reply, None

    # ---- the three guards, as small pieces that can be tested alone --------
    def answer_cfg(self):
        return self.cfg.get("answer") or {}

    def token_budget(self, lang):
        a = self.answer_cfg()
        by = a.get("maxTokensByLang") or {}
        fallback = int(self.cfg.get("llm", {}).get("maxTokens", 32))
        try:
            return max(1, int(by.get(lang, fallback)))
        except (TypeError, ValueError):
            return fallback

    def particles(self):
        a = self.answer_cfg()
        return tuple(a.get("politeParticles") or DEF_PARTICLES)

    def ask_words(self):
        return tuple(self.answer_cfg().get("askWords") or ())

    def pronouns(self):
        a = self.answer_cfg()
        return tuple(a.get("politePronouns") or DEF_PRONOUNS)

    def cannot_answer(self, lang):
        """What the robot says when it has nothing whole to say."""
        said = (self.answer_cfg().get("cannotAnswer") or {})
        got = (said.get(lang) or said.get("th")
               or "ขออภัยครับ ผมยังไม่เข้าใจคำถามนี้ ลองถามใหม่อีกครั้งได้ไหมครับ")
        # saved in the male ending: a female voice says it with its own
        return self.manner_saved(got, lang) if lang in said or lang == "th" else got

    def only_this_language(self, lang):
        said = (self.answer_cfg().get("onlyThisLanguage") or {})
        return (said.get(lang) or said.get("th")
                or "ตอบเป็นภาษาไทยเท่านั้น สั้นๆ 1 ประโยค")

    def tidy_answer(self, reply, lang, ran_out=False, verse=False):
        """Whole sentences, in one voice. "" when nothing whole survives."""
        reply = unquote_whole(reply)
        if not reply:
            return ""
        if lang == "th":
            keep, me, _w = self.manner_answer("th")
            reply = one_particle(reply, keep, self.particles(), self.ask_words())
            reply = one_pronoun(reply, me, self.pronouns())
        # A verse is lines, not sentences - trimming it to a particle would eat
        # the poem. Its budget is larger for the same reason.
        if ran_out and not verse:
            reply = trim_unfinished(reply, lang, self.particles())
        return reply.strip()


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
        text = (req.get("text") or "").strip()
        history = req.get("history") or []
        req_lang = (req.get("lang") or "").strip()
        person = (req.get("person") or req.get("name") or "").strip()
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
