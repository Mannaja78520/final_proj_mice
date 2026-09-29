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
import uuid
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
NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0

# What the page says when nothing answers at the face app's address. The page
# turns this one sentence into a Start button, so the words name the fix.
FACE_APP_OFF = "the face app is not running yet - start it and look again"

# What the page says when the face app would STORE the frame. The page stops
# looking on this sentence, so it names the two ways that still work.
FACE_APP_KEEPS = ("the face app would keep this picture, so it was not sent - "
                  "pick a camera the face app watches, or use Open Reconize")

_tmp_seq = itertools.count()                        # one temp name per writer
THINK_RE = re.compile(r"<think>.*?</think>", re.DOTALL)
SPECIAL_RE = re.compile(r"<\|[^|]+\|>")             # <|im_end|> and friends
MARKUP_RE = re.compile(r"[*#_`]")                   # spoken text wears no markdown
EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B50\u200D\uFE0F]")

sys.path.insert(0, str(CODE / "tools"))
import registry                                      # noqa: E402


def detect_lang(text):
    """Detect 'th', 'ja', 'zh', or 'en' based on script analysis."""
    has_thai = False
    has_kana = False
    has_cjk = False
    has_latin = False
    for ch in text or "":
        cp = ord(ch)
        if 0x0E00 <= cp <= 0x0E7F:
            has_thai = True
            break
        elif (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            has_kana = True
        elif 0x4E00 <= cp <= 0x9FFF:
            has_cjk = True
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            has_latin = True

    if has_thai:
        return "th"
    if has_kana:
        return "ja"
    if has_cjk:
        return "zh"
    if has_latin:
        return "en"
    return "th"


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
}
DEF_PARTICLES = ("ครับ", "คร้าบ", "ค่ะ", "คะ", "ฮะ", "จ้า", "จ้ะ", "จ๊ะ")


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
    if lang in ("th", "ja", "zh"):
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


def one_particle(text, keep, particles=None):
    """One voice, one polite particle.

    The robot is one character, and the saved answers all end in ครับ. The
    model does not know that and ends one sentence ครับ and the next ค่ะ, which
    in Thai reads as two different people talking - the single thing that made
    the answers sound wrong even when they were right.

    Replaces any OTHER particle where a particle belongs: at the end of the
    text, or before a space or punctuation. Never inside a word, so ค่ะ in a
    quoted sentence somebody asked about is left alone.
    """
    keep = (keep or "").strip()
    if not keep:
        return text or ""
    others = [p for p in (particles or DEF_PARTICLES) if p and p != keep]
    if not others:
        return text or ""
    pat = re.compile("(?:%s)(?=$|[\\s\\.,!?ฯ])" % "|".join(re.escape(p) for p in others))
    return pat.sub(keep, text or "")


# หนู is a first-person word too, and also means mouse - this robot is called
# Mice, so it is left OUT on purpose. One entry in politePronouns brings it back.
DEF_PRONOUNS = ("ผม", "ฉัน", "ดิฉัน", "กระผม", "ข้าพเจ้า")


def one_pronoun(text, keep, pronouns=None):
    """One robot, one word for itself.

    Measured against the real model 2026-09-18: one answer said ครับ ฉันสามารถ
    ... and the next ผมสามารถ .... In Thai the first-person word carries as
    much character as the ending does, and two of them in one conversation is
    the same fault as ครับ/ค่ะ - it sounds like two speakers.

    Thai is written without spaces, so a pronoun is not marked off by one - it
    turns up mid-sentence as often as at the start (*เพื่อให้ฉันสามารถ*), and a
    rule that only looked after a space missed exactly those. So it is swapped
    anywhere EXCEPT before ท, which is what tells ฉัน apart from ฉันท์, a kind
    of verse the rig is asked to recite, and from ฉันทะ.

    What is on the list matters more than this code: หนู is a first-person word
    in Thai and also means mouse, and this robot is called Mice, so it is
    deliberately NOT shipped in politePronouns. It is one entry away for
    anybody who wants it.
    """
    keep = (keep or "").strip()
    if not keep:
        return text or ""
    others = sorted((p for p in (pronouns or DEF_PRONOUNS) if p and p != keep),
                    key=len, reverse=True)      # ดิฉัน before ฉัน
    if not others:
        return text or ""
    pat = re.compile(r"(?:%s)(?!ท)"
                     % "|".join(re.escape(p) for p in others))
    return pat.sub(keep, text or "")


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


def scripts_in(text):
    """Which writing systems one line really holds, e.g. {"th", "en"}.

    detect_lang answers "which ONE language is this", which is the wrong
    question for a sentence like *Hello พุฒิพงศ์, welcome*: it is two, and a
    voice tied to either one drops the other half (user 2026-09-18: *make TTS
    can read all lang in the same time*).
    """
    found = set()
    for ch in text or "":
        cp = ord(ch)
        if 0x0E00 <= cp <= 0x0E7F:
            found.add("th")
        elif (0x3040 <= cp <= 0x309F) or (0x30A0 <= cp <= 0x30FF):
            found.add("ja")
        elif 0x4E00 <= cp <= 0x9FFF:
            found.add("zh")
        elif ("a" <= ch <= "z") or ("A" <= ch <= "Z"):
            found.add("en")
    return found


def short_person_name(person):
    """Extract a friendly conversational first/short name."""
    if not person:
        return ""
    p = str(person).strip().strip("'\"[]")
    parts = p.split()
    return parts[0] if parts else p


def format_multi_person(person, lang="th"):
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
        th_names = [n if n.startswith("คุณ") else f"คุณ{n}" for n in short_names]
        if len(th_names) == 1:
            return th_names[0]
        elif len(th_names) == 2:
            return f"{th_names[0]} และ{th_names[1]}"
        else:
            return f"{th_names[0]}, {th_names[1]} และทุกท่าน"


def personalize_answer(answer, person, lang="th"):
    """Personalize an answer with the recognized person(s) naturally."""
    if not person or not answer or not str(answer).strip():
        return answer

    ans = str(answer).strip()
    l = lang or detect_lang(ans)

    s_names = [short_person_name(n) for n in re.split(r'\s+(?:และ|and)\s+|,\s*', str(person)) if n.strip()]
    if any(s.lower() in ans.lower() for s in s_names if s):
        return answer

    addressed = format_multi_person(person, lang=l)
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


class Brain:
    """What answers. The FAQ is always there; the model arrives lazily."""

    def __init__(self, cfg_path, faq_path=None):
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
        self._preload_thread = None
        self._tts_lock = threading.Lock()   # one PowerShell synth at a time
        self.faq_err = ""            # why the answers file could not be read
        self._lock = threading.Lock()   # one GPU: answers and listening queue
        self._cached_person = ""
        self._cached_person_at = 0.0
        self._reconize_token = ""
        self._reconize_token_exp = 0.0

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
        defaults = {"stt": "small", "llm": r"E:\final_proj\mice\code\llm"}
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

    # Words that are a QUESTION, not a subject. Alone, "อะไร" (what) sits
    # inside "กินอะไรดี" and would answer every asker with the food desk.
    # In the store, so the next one costs no code.
    STOP_WORDS = ("อะไร", "ไหน", "ที่ไหน", "ยังไง", "อย่างไร", "ทำไม",
                  "เมื่อไหร่", "ใคร", "ไหม", "หรอ", "เหรอ", "ครับ", "ค่ะ",
                  "คะ", "นะ", "ได้", "何", "どこ", "什么", "哪里")

    def faq_stop_words(self):
        got = self.cfg.get("faqStopWords")
        return tuple(got) if isinstance(got, list) and got else self.STOP_WORDS

    def match_faq(self, text, lang=""):
        """The closest saved ENTRY over the threshold, or (None, score).

        The whole entry comes back, not just its answer: an entry may name
        a move and a module too (A20-10), and the caller passes them on.
        """
        th = float(self.cfg.get("faqThreshold", 0.75))
        best, hit = 0.0, None
        got = text.strip().lower()
        norm_got = re.sub(r'^(ช่วยบอกหน่อย|รบกวนถามหน่อย|อยากทราบว่า|อยากรู้ว่า|ขอถามหน่อย|สอบถามหน่อย|ช่วยแนะนำหน่อย|please tell me |can you tell me |could you tell me )', '', got)
        norm_got = re.sub(r'(ครับ|ค่ะ|คะ|หน่อยครับ|หน่อยค่ะ|หน่อย|จ้า|จ๊ะ| please)[.!?]*$', '', norm_got).strip()
        for item in self.faqs():
            for q in item.get("questions", []):
                qc = q.strip().lower()
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
                elif len(qc) >= 3 and detect_lang(qc) in ("th", "ja", "zh"):
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
                if (detect_lang(qc) in ("th", "ja", "zh") and len(got) >= 3
                        and got not in self.faq_stop_words()
                        and got in qc and len(got) / max(len(qc), 1) >= 0.25):
                    score = max(score, 0.76 + 0.15 * (len(got) / max(len(qc), 1)))
                if score > best:
                    best, hit = score, item
        if best >= th and hit:
            eff_lang = lang or detect_lang(text)
            ans_key = f"answer_{eff_lang}"
            ans = hit.get(ans_key)
            if not ans and eff_lang in ("th", "en", "ja", "zh"):
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

    def stt_status(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return "off in config/voice.json"
        if self._stt:
            return "%s loaded" % scfg.get("model", "small")
        if self._stt_loading:
            return "loading in background…"
        if self._stt_err:
            return "could not load: " + self._stt_err
        return "loads when first needed"

    def _load_stt(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._stt or self._stt_err:
            return
        self._stt_loading = True
        try:
            from faster_whisper import WhisperModel
            mid = scfg.get("model", "small")
            try:
                self._stt = WhisperModel(mid, device="cuda", compute_type="float16")
            except Exception:
                try:
                    self._stt = WhisperModel(mid, device="auto", compute_type="auto")
                except Exception:
                    self._stt = WhisperModel(mid, device="cpu", compute_type="int8")
            self._stt_loaded_model = mid
        except Exception as e:                              # noqa: BLE001
            self._stt_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._stt_loading = False

    def _fallback_transcribe(self, path, segs, info, resolved, scfg):
        """A second pass in a set language when detection is unsure (A26-80).

        DATA, not code: stt.fallback in config/voice.json - language,
        when_not_in, min_probability. No fallback key, no second pass.
        """
        fb = scfg.get("fallback")
        if resolved or not fb or not fb.get("language"):
            return segs, info
        lang = fb["language"]
        unsure = (info.language not in (fb.get("when_not_in") or []) or
                  getattr(info, "language_probability", 1.0) < fb.get("min_probability", 0.0))
        if not unsure:
            return segs, info
        bias = ((scfg.get("languages") or {}).get(lang) or {}).get("bias")
        return self._stt.transcribe(
            path, language=lang, temperature=0, beam_size=1,
            condition_on_previous_text=False, vad_filter=True,
            vad_parameters={"min_silence_duration_ms": 500, "threshold": 0.6},
            repetition_penalty=1.2, no_repeat_ngram_size=3, initial_prompt=bias)

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
            hint_s = (hint or "").strip().lower()
            if hint_s in ("auto", "detect", "none"):
                resolved = None
            elif hint_s:
                resolved = hint_s
            else:
                cfg_lang = (scfg.get("language") or "").strip().lower()
                resolved = None if cfg_lang in ("auto", "detect", "none", "") else cfg_lang
            bias = ((scfg.get("languages") or {}).get(resolved) or {}).get("bias") if resolved else None
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tf:
                tf.write(audio)
                path = tf.name
            try:
                segments, info = self._stt.transcribe(
                    path, language=resolved or None,
                    temperature=0,
                    beam_size=1,
                    condition_on_previous_text=False,
                    vad_filter=True,
                    vad_parameters={"min_silence_duration_ms": 500, "threshold": 0.6},
                    repetition_penalty=1.2,
                    no_repeat_ngram_size=3,
                    initial_prompt=bias)

                segments, info = self._fallback_transcribe(path, segments, info, resolved, scfg)

                valid = []
                for s in segments:
                    if getattr(s, "no_speech_prob", 0) > 0.6:
                        continue
                    valid.append(s.text)
                text = "".join(valid).strip()
                text = re.sub(r'(\b\S+)(?:\s+\1\b)+', r'\1', text)
                text = re.sub(r'(.{3,25}?)\1{2,}', r'\1', text).strip()
            except Exception as e:
                err_s = str(e).lower()
                if "cublas" in err_s or "cuda" in err_s or "not found" in err_s or "driver" in err_s:
                    from faster_whisper import WhisperModel
                    mid = scfg.get("model", "small")
                    self._stt = WhisperModel(mid, device="cpu", compute_type="int8")
                    self._stt_loaded_model = mid
                    segments, info = self._stt.transcribe(
                        path, language=resolved or None,
                        temperature=0,
                        beam_size=1,
                        condition_on_previous_text=False,
                        vad_filter=True,
                        vad_parameters={"min_silence_duration_ms": 500, "threshold": 0.6},
                        repetition_penalty=1.2,
                        no_repeat_ngram_size=3,
                        initial_prompt=bias)
                    segments, info = self._fallback_transcribe(path, segments, info, resolved, scfg)
                    valid = []
                    for s in segments:
                        if getattr(s, "no_speech_prob", 0) > 0.6:
                            continue
                        valid.append(s.text)
                    text = "".join(valid).strip()
                    text = re.sub(r'(\b\S+)(?:\s+\1\b)+', r'\1', text)
                    text = re.sub(r'(.{3,25}?)\1{2,}', r'\1', text).strip()
                else:
                    raise
            finally:
                os.unlink(path)
            return {"text": text, "language": info.language}, None

    # --- speaking out loud (A20-9) -------------------------------------
    # Windows' own synthesiser, reached through apps/voice/tts.ps1. No
    # internet, no pip install: the venue PC's own voices, named in the
    # store. Answers are cached by md5(text+voice) so a saved answer's
    # SECOND visitor hears it instantly - and a watcher thread pre-builds
    # every saved answer, re-running when qa_data.json is edited on disk.
    def resolve_voice(self, lang, text=""):
        """(cache identity, voice name-or-empty), or (None, why-not).

        A listed-but-EMPTY name means Windows picks its own voice for that
        language - a PC without Pattara still speaks with its default. A
        language MISSING from the map is a mistake and says so instead.
        """
        tcfg = self.cfg.get("tts", {})
        # ONE voice for every language, when one is chosen. A per-language map
        # cannot say a Thai name inside an English answer: the English voice
        # reads the Thai letters as nothing (user 2026-09-18, with Multi-lang
        # on and their own name in the reply). A multilingual voice speaks the
        # whole sentence, so the choice is a voice, not a language.
        # The scenario's own voice first, then the one-voice-for-everything,
        # then the per-language map.
        one = (self.active_scenario().get("voice")
               or str(tcfg.get("oneVoice") or "").strip())
        if one:
            return one, one
        # Nobody chose one, but this line is in two languages at once. A voice
        # from the map can only read its own half, so borrow a voice that
        # reads everything for this line rather than dropping words.
        if len(scripts_in(text)) > 1:
            mixed = self.mixed_voice()
            if mixed:
                return mixed, mixed
        voices = tcfg.get("voices") or {}
        lang = (lang or "").strip()
        if not lang and text:
            detected = detect_lang(text)
            if detected in voices:
                lang = detected
        if not lang:
            lang = (tcfg.get("language") or "").strip()
        if lang not in voices:
            return None, ("no voice named for language %r - add one under "
                          "tts in config/voice.json" % (lang or "?"))
        name = str(voices[lang]).strip()
        return (name or "<windows default %s>" % lang), name

    def scenarios(self):
        """The scenarios in the store, as a list. Always data, never code."""
        got = self.cfg.get("scenarios")
        return [s for s in got if isinstance(s, dict)] if isinstance(got, list) else []

    def active_scenario(self):
        """The scenario in use: what the rig is pretending to be, and how it
        should sound while doing it.

        `scenario` in the store is either the NAME of one in `scenarios`, or -
        as it was before scenarios existed - the prompt itself. Both keep
        working, so an old config is not broken by this.

        User 2026-09-18: *in senario i will promt what senario and the voice
        it run sound like that*. A scenario therefore carries its own voice,
        rate and pitch: a poem is read slower than a shop greeting, and both
        may want the same one voice for every language, because *when
        different people come in same event it have different country person
        ... when it use different tone voice people will confuse*.
        """
        want = str(self.cfg.get("scenario")
                   or (self.cfg.get("llm") or {}).get("scenario") or "").strip()
        for s in self.scenarios():
            if str(s.get("name") or "").strip() == want and want:
                return {"name": want, "prompt": str(s.get("prompt") or "").strip(),
                        "voice": str(s.get("voice") or "").strip(),
                        "rate": str(s.get("rate") or "").strip(),
                        "pitch": str(s.get("pitch") or "").strip()}
        return {"name": "", "prompt": want, "voice": "", "rate": "", "pitch": ""}

    def mixed_voice(self):
        """The voice used for a line that holds more than one language.

        `tts.mixedVoice` names it; left empty, the first voice the speech
        service itself reports as multilingual is used, so this works on a
        fresh install with nothing configured and no name written in here.
        Empty (and offline) means the old behaviour: the detected language's
        own voice, reading its own half.
        """
        named = str((self.cfg.get("tts") or {}).get("mixedVoice") or "").strip()
        if named:
            return named
        got = self.speaking_voices()
        return got[0]["name"] if got else ""

    def speaking_voices(self):
        """Every voice that can speak ALL languages, from the voice service
        itself - so the list in the settings screen is never a list typed
        into this file. Cached: it is a network call and it never changes
        during a run.
        """
        got = getattr(self, "_voice_list", None)
        if got is not None:
            return got
        out = []
        try:
            import asyncio
            import edge_tts
            for v in asyncio.run(edge_tts.list_voices()):
                name = str(v.get("ShortName") or "")
                # Microsoft's own name for the voices that are not tied to
                # one language. There is no other flag in their list.
                if "Multilingual" in name:
                    out.append({"name": name,
                                "says": str(v.get("FriendlyName") or name),
                                "gender": str(v.get("Gender") or "")})
        except Exception:                               # noqa: BLE001
            out = []                                    # offline: the map still works
        self._voice_list = out
        return out

    def tts_status(self):
        tcfg = self.cfg.get("tts", {})
        if not tcfg.get("enabled"):
            return "off in config/voice.json"
        ident, _name = self.resolve_voice("")
        if not ident:
            return "no voices listed - add one under tts"
        if str(tcfg.get("oneVoice") or "").strip():
            return "%s speaking (every language)" % ident
        n = len(tcfg.get("voices") or {})
        return "%s speaking (%d mapped)" % (ident, n)

    def _cache_path(self, ident, text, rate=None, pitch=None):
        if rate is None:
            rate = str(self.cfg.get("tts", {}).get("rate") or "").strip()
        if pitch is None:
            pitch = str(self.cfg.get("tts", {}).get("pitch") or "").strip()
        extra = ("\n%s\n%s" % (rate, pitch)) if (rate or pitch) else ""
        key = hashlib.md5(("%s\n%s%s" % (ident, text, extra))
                          .encode("utf-8")).hexdigest()
        return CODE / "apps" / "voice" / "tts_cache" / (key + ".wav")

    def say(self, text, lang="", voice=""):
        """Text -> wav bytes, or (None, why-not) in plain words."""
        tcfg = self.cfg.get("tts", {})
        if not tcfg.get("enabled"):
            return None, "speaking is switched off in config/voice.json"
        text = EMOJI_RE.sub("", text or "").strip()
        if not text:
            return None, "there was nothing to speak"
        if voice:
            ident = voice
        else:
            ident, voice = self.resolve_voice(lang, text=text)
            if not ident:
                return None, voice
        # A scenario may set its own speed and pitch - a poem read at shop
        # speed is the complaint this answers.
        act = self.active_scenario()
        rate = act.get("rate") or str(tcfg.get("rate") or "").strip()
        pitch = act.get("pitch") or str(tcfg.get("pitch") or "").strip()
        path = self._cache_path(ident, text, rate=rate, pitch=pitch)
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
                    # Strictly preserve the selected neural voice - never switch gender or identity
                    clean_text = re.sub(r'\r', '', text).strip()
                    clean_text = re.sub(r'[ \t]+', ' ', clean_text)
                    clean_text = re.sub(r'\n\s*\n+', '\n', clean_text)
                    cmd = [sys.executable, "-m", "edge_tts", "--voice", voice, "--text", clean_text]
                    if rate:
                        cmd.extend(["--rate", rate])
                    if pitch:
                        cmd.extend(["--pitch", pitch])
                    for attempt in range(2):
                        try:
                            r = subprocess.run(cmd, capture_output=True, timeout=15,
                                               creationflags=NO_WINDOW)
                            if r.returncode == 0 and len(r.stdout) >= 100:
                                wav = r.stdout
                                break
                        except Exception:
                            pass
                if wav is None:
                    local_voice = voice if "Neural" not in voice else ""
                    r = subprocess.run(
                        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                         "-File", str(CODE / "apps" / "voice" / "tts.ps1"),
                         "-Text", text, "-Lang", lang, "-Voice", local_voice],
                        capture_output=True, timeout=60, creationflags=NO_WINDOW)
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
        """Pre-build every saved answer across all 4 languages, then prune what is stale.

        Pruning keeps today's dynamic (model) audio: only files older than a
        day that no saved answer claims are deleted, so yesterday's demo
        dies overnight and nothing a visitor just heard does.
        """
        if not (self.cfg.get("tts") or {}).get("enabled"):
            return
        keep = set()
        for item in self.faqs():
            for lang_code, key in (("th", "answer"), ("en", "answer_en"), ("ja", "answer_ja"), ("zh", "answer_zh")):
                ans = (item.get(key) or "").strip()
                if not ans and key != "answer":
                    base_ans = (item.get("answer") or "").strip()
                    if base_ans:
                        trans, _ = self.translate_text(base_ans, target=lang_code)
                        if trans:
                            ans = trans
                            item[key] = trans
                if ans:
                    ident, _name = self.resolve_voice(lang_code, text=ans)
                    if ident:
                        self.say(ans, lang=lang_code)
                        keep.add(self._cache_path(ident, ans).stem)
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
        if self._llm or self._llm_err:
            return
        self._llm_loading = True
        try:
            import torch                                    # noqa: F401
            from transformers import AutoModelForCausalLM, AutoTokenizer
            mid = self.cfg.get("llm", {}).get("model", r"E:\final_proj\mice\code\llm")
            tok = AutoTokenizer.from_pretrained(mid, trust_remote_code=True)
            mdl = None
            if torch.cuda.is_available():
                dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16
                try:
                    mdl = AutoModelForCausalLM.from_pretrained(
                        mid, torch_dtype=dtype, device_map="cuda",
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
                            mid, quantization_config=quant, device_map="auto",
                            trust_remote_code=True)
                    except Exception:
                        mdl = AutoModelForCausalLM.from_pretrained(
                            mid, torch_dtype=dtype, device_map="auto",
                            trust_remote_code=True)
            else:
                mdl = AutoModelForCausalLM.from_pretrained(
                    mid, torch_dtype=torch.float32, device_map="cpu",
                    trust_remote_code=True)
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
            if force or self.cfg.get("llm", {}).get("enabled"):
                if not self._llm:
                    self._load_llm()
            if force or self.cfg.get("stt", {}).get("enabled"):
                if not self._stt:
                    self._load_stt()

        self._preload_thread = threading.Thread(target=_worker, daemon=True)
        self._preload_thread.start()
        return True

    def unload(self):
        """Unload LLM and STT models from memory and free GPU/RAM."""
        with self._lock:
            self._llm = None
            self._stt = None
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

    def _ask_google_studio(self, history, lang="th", scenario="", faq_lines=None, person=""):
        api_key = (self.cfg.get("googleApiKey") or
                   os.environ.get("GEMINI_API_KEY") or
                   os.environ.get("GOOGLE_API_KEY") or "").strip()
        if not api_key:
            return None, "Google AI Studio API key not configured (set googleApiKey in config/voice.json)"
        model = self.cfg.get("googleModel") or "gemini-2.0-flash"
        faq_sec = ("\nRelevant FAQ:\n" + "\n".join(faq_lines) + "\n") if faq_lines else ""
        system = ("You are the Mice robot assistant. Answer in language code: %s. "
                  "Keep answers strictly to 1 concise sentence. Direct, plain-spoken, absolutely NO emojis.\n"
                  % (lang or "th"))
        if scenario:
            system += ("Scenario / Persona: %s\n" % scenario)
        if person:
            s_name = short_person_name(person)
            if lang == "en":
                system += f"\nThe user speaking to you has been recognized as '{s_name}'. Address them politely by their name (e.g. 'Hello {s_name}, ...').\n"
            elif lang == "ja":
                system += f"\n利用者の名前は「{s_name}」です。お名前（{s_name}さん）を呼んで回答してください。\n"
            elif lang == "zh":
                system += f"\n向你提问的用户已被识别为「{s_name}」。请礼貌地称呼其名字回答。\n"
            else:
                thai_title = s_name if s_name.startswith("คุณ") else f"คุณ{s_name}"
                system += f"\nผู้ใช้ที่กำลังคุยกับคุณได้รับการระบุชื่อคือ '{thai_title}' จงกล่าวทักทายหรือเรียกชื่อ{thai_title}อย่างสุภาพในคำตอบด้วย\n"
        if faq_sec:
            system += faq_sec + "Always follow the created FAQ answers as closely as possible."
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        contents = []
        for m in history:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        payload = {
            "system_instruction": {"parts": [{"text": system}]},
            "contents": contents,
            "generationConfig": {
                "maxOutputTokens": 48,
                "temperature": 0.2
            }
        }
        try:
            req = urllib.request.Request(
                url,
                data=json.dumps(payload).encode("utf-8"),
                headers={"Content-Type": "application/json"}
            )
            with urllib.request.urlopen(req, timeout=8) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                ans = data["candidates"][0]["content"]["parts"][0]["text"]
                return self.clean(ans), None
        except Exception as e:
            return None, "Google AI Studio error (%s: %s)" % (e.__class__.__name__, e)

    def generate(self, history, lang="", person=""):
        """The model's answer, or (None, why-not) in plain words."""
        with self._lock:
            # A name in `scenario` resolves to that scenario's prompt; plain
            # text is still its own prompt (active_scenario).
            scenario = self.active_scenario().get("prompt") or ""
            use_google = (self.cfg.get("llm", {}).get("provider") == "google_studio" or
                          (self.cfg.get("googleApiKey") and not self.cfg.get("llm", {}).get("enabled")))
            if use_google:
                g_ans, g_err = self._ask_google_studio(history, lang=lang, scenario=scenario, person=person)
                if g_ans:
                    if person:
                        g_ans = personalize_answer(g_ans, person, lang=lang)
                    return g_ans, None
                if not self.cfg.get("llm", {}).get("enabled"):
                    return None, g_err

            ok, why_not = self._ensure_llm()
            if not ok:
                return None, why_not
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
                keep = (self.answer_cfg().get("politeParticle") or "ครับ")
                me = (self.answer_cfg().get("politePronoun") or "ผม")
                system = ("คุณคือหุ่นยนต์ Mice ให้ข้อมูลบริการและสถานที่ จงตอบเป็นภาษาไทยเท่านั้น สั้นๆ ตรงประเด็น 1 ประโยคจบในตัว ห้ามตอบเป็นภาษาอังกฤษหรือภาษาอื่น ไม่มีคำเยิ่นเย้อ ไม่มีอีโมจิ\n"
                          + ("ลงท้ายประโยคด้วยคำว่า '%s' เสมอ ห้ามใช้คำลงท้ายอื่น เช่น ค่ะ คะ จ้า และเรียกตัวเองว่า '%s' เสมอ ห้ามใช้ ฉัน หรือ ดิฉัน เพราะคุณเป็นหุ่นยนต์ตัวเดียวและต้องพูดด้วยน้ำเสียงเดียวกันทุกประโยค\n" % (keep, me))
                          + scenario_hint
                          + person_hint
                          + ("\nFAQ ที่เกี่ยวข้อง:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                          + "จงตอบโดยยึดตามข้อมูลคำตอบที่สร้างไว้ (FAQ) ให้ใกล้เคียงที่สุดเสมอ หากคำถามเกี่ยวข้องกับ FAQ ให้ตอบตามนั้น หากไม่ตรงให้ตอบสั้นๆ ในฐานะหุ่นยนต์ Mice 1 ประโยคเป็นภาษาไทย ห้ามแต่งรหัสผ่าน ราคา เวลา ชั้น สถานที่ หรือกิจกรรม/ข่าวที่ไม่มีใน FAQ ถ้าไม่รู้ให้บอกว่าไม่ทราบและให้สอบถามเจ้าหน้าที่")
            # ROOM TO FINISH A SENTENCE, per language. 32 tokens was chosen for
            # speed and is fine for English; Thai costs two to four tokens per
            # word, so the same budget stopped Thai answers in the middle of a
            # word (user 2026-09-18: *it cuts replies off*). The budget is DATA
            # so it can be tuned per language without touching this file.
            limit = 96 if is_verse else self.token_budget(lang)
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
                again = [{"role": "system", "content": self.only_this_language(lang)}] + history
                reply2, ran2 = self._complete(again, max_tokens=limit, details=True)
                reply2 = self.tidy_answer(reply2, lang, ran_out=ran2)
                reply = reply2 if reply2 and answers_in(reply2, lang, self.particles()) else ""
            if not reply:
                return self.cannot_answer(lang), None
            if person:
                reply = personalize_answer(reply, person, lang=lang)
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

    def pronouns(self):
        a = self.answer_cfg()
        return tuple(a.get("politePronouns") or DEF_PRONOUNS)

    def cannot_answer(self, lang):
        """What the robot says when it has nothing whole to say."""
        said = (self.answer_cfg().get("cannotAnswer") or {})
        return (said.get(lang) or said.get("th")
                or "ขออภัยครับ ผมยังไม่เข้าใจคำถามนี้ ลองถามใหม่อีกครั้งได้ไหมครับ")

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
            a = self.answer_cfg()
            reply = one_particle(reply, a.get("politeParticle"), self.particles())
            reply = one_pronoun(reply, a.get("politePronoun"), self.pronouns())
        # A verse is lines, not sentences - trimming it to a particle would eat
        # the poem. Its budget is larger for the same reason.
        if ran_out and not verse:
            reply = trim_unfinished(reply, lang, self.particles())
        return reply.strip()

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

    def translate_text(self, text, target="en", source="auto"):
        """Translate text from source to target language (th, en, ja, zh)."""
        if not text or not text.strip():
            return "", None
        src_lang = detect_lang(text) if source in ("auto", "") else source
        lang_map = {
            "th": "th",
            "en": "en",
            "ja": "ja",
            "zh": "zh-CN",
        }
        tl = lang_map.get(target, target)
        sl = lang_map.get(src_lang, "auto") if source == "auto" else lang_map.get(source, "auto")

        if src_lang == target:
            return text.strip(), None

        import urllib.request
        import urllib.parse
        try:
            url = ("https://translate.googleapis.com/translate_a/single?client=gtx&sl=%s&tl=%s&dt=t&q=%s"
                   % (sl, tl, urllib.parse.quote(text)))
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=4) as r:
                data = json.loads(r.read().decode("utf-8"))
                if data and data[0]:
                    res = "".join(x[0] for x in data[0] if x and x[0])
                    if res:
                        return res.strip(), None
        except Exception:
            pass

        # Fallback to local LLM if available (short reply only)
        with self._lock:
            ok, _ = self._ensure_llm()
            if ok:
                target_names = {
                    "th": "Thai",
                    "en": "English",
                    "ja": "Japanese",
                    "zh": "Chinese",
                }
                tname = target_names.get(target, target)
                messages = [
                    {"role": "system", "content":
                     f"You are a translator. Translate the text into {tname} accurately and concisely. Reply ONLY with the translated text, no explanation."},
                    {"role": "user", "content": text}
                ]
                try:
                    res = self._complete(messages, max_tokens=48)
                    if res:
                        return res.strip(), None
                except Exception:
                    pass

        return text.strip(), "translation unavailable"

    def translate_all(self, text, source="auto"):
        """Return dict of {th: ..., en: ..., ja: ..., zh: ...} for given text."""
        src = detect_lang(text) if source in ("auto", "") else source
        results = {src: text.strip()}
        targets = [t for t in ("th", "en", "ja", "zh") if t != src]
        import concurrent.futures
        with concurrent.futures.ThreadPoolExecutor(max_workers=len(targets)) as ex:
            futs = {ex.submit(self.translate_text, text, target=t, source=src): t for t in targets}
            for fut in concurrent.futures.as_completed(futs):
                t = futs[fut]
                try:
                    trans, _ = fut.result()
                    results[t] = trans or text.strip()
                except Exception:
                    results[t] = text.strip()
        for t in ("th", "en", "ja", "zh"):
            if t not in results:
                results[t] = text.strip()
        return results

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

    def _query_faces_service(self, camera=""):
        """Query loopback faces service at :8769/state.

        `camera` keeps only what one station saw. Their feed carries the
        station in each event (apps/faces/service.py from_ws), which is what
        makes one camera usable by both apps at once: the face app scans, and
        Voice reads the result for the camera the designer picked.
        """
        import urllib.request
        from datetime import datetime
        # The watcher's address is data: apps/faces/service.py is normally on
        # :8769 of this PC, but a check points this at its own.
        where = str((self.cfg.get("face") or {}).get("watcher")
                    or os.environ.get("MICE_FACES_STATE")
                    or "http://127.0.0.1:8769/state")
        try:
            req = urllib.request.Request(where)
            with urllib.request.urlopen(req, timeout=1.0) as r:
                if r.status == 200:
                    data = json.loads(r.read().decode("utf-8"))
                    people = data.get("people") or []
                    active = []
                    seen = set()
                    for p in people:
                        who = (p.get("who") or "").strip()
                        when_str = p.get("when") or ""
                        if camera and str(p.get("camera") or "") != camera:
                            continue
                        if who and p.get("known", True) and when_str:
                            try:
                                w_dt = datetime.fromisoformat(str(when_str).replace("Z", ""))
                                if abs((datetime.now() - w_dt).total_seconds()) <= 120:
                                    s = short_person_name(who)
                                    if s and s.lower() not in seen:
                                        seen.add(s.lower())
                                        active.append(s)
                            except Exception:
                                pass
                    if active:
                        return " และ ".join(active[:2]) if len(active) <= 2 else f"{active[0]}, {active[1]} และทุกท่าน"
        except Exception:
            pass
        return ""

    def _reconize_api(self):
        """Where Reconize answers, from config/partners.json - the one list.

        Their port moves with an update of theirs, and a second copy of the
        address in this file is how the two would disagree.
        """
        return str(self._reconize_entry().get("api") or "").rstrip("/")

    def _reconize_entry(self):
        """Reconize's whole entry in config/partners.json, {} when unreadable."""
        try:
            # MICE_PARTNERS is what the hub honours too, and it is what lets a
            # check point this at a fake face app instead of the real one.
            path = os.environ.get("MICE_PARTNERS") or (CODE / "config" / "partners.json")
            return registry.load(path).get("reconize") or {}
        except Exception:                               # noqa: BLE001
            return {}

    def look_allowed(self):
        """Whether the face app PROMISES to keep nothing of one frame.

        Their upload stores the frame, a history row and an attendance row.
        `persist=false` was a local patch to their code, never theirs, and
        resetting their folder to their own version removed it (2026-09-29).
        FastAPI ignores a query it does not know, so sending the flag proves
        nothing: only their own /openapi.json listing it counts. Returns
        (True|False|None, why, detail); None = could not ask (app off).
        """
        import urllib.error
        import urllib.request
        api = self._reconize_api()
        look = self._reconize_entry().get("look") or {}
        name = str(look.get("dontKeep") or "").partition("=")[0]
        if not api or not look.get("path") or not name or not look.get("spec"):
            return False, "config/partners.json does not say how to ask the face app about one picture", ""
        try:
            with urllib.request.urlopen(api + look["spec"], timeout=5) as r:
                doc = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:             # it answered: no description
            return False, FACE_APP_KEEPS, "%s answered %s" % (look["spec"], e.code)
        except OSError as e:
            return None, FACE_APP_OFF, str(e)
        except ValueError as e:                         # not JSON: cannot tell, so no
            return False, FACE_APP_KEEPS, "%s is not readable: %s" % (look["spec"], e)
        op = ((doc.get("paths") or {}).get(look["path"]) or {}).get("post") or {}
        if any(isinstance(p, dict) and p.get("name") == name and p.get("in") == "query"
               for p in (op.get("parameters") or [])):
            return True, "", ""
        return False, FACE_APP_KEEPS, "POST %s has no %s option (%s)" % (
            look["path"], name, look["spec"])

    def _faces_login_path(self):
        """Where the saved face-app login lives.

        The real file never leaves the real tree (promote.py SKIP_FILES keeps
        the password out of every copy), so a check running in .staging found
        nothing and stopped at the first line of every face test. The override
        lets it point at a throwaway login, exactly as MICE_PARTNERS points at
        a fake face app.
        """
        return Path(os.environ.get("MICE_FACES_LOGIN")
                    or (CODE / "main_python" / "faces_login.json"))

    def _reconize_login(self, timeout=3.0):
        """A Reconize token, cached for half an hour. '' when it cannot log in."""
        import urllib.request
        l_path = self._faces_login_path()
        if not l_path.is_file():
            return ""
        creds = json.loads(l_path.read_text(encoding="utf-8")).get("reconize") or {}
        u, p = creds.get("username"), creds.get("password")
        if not u or not p:
            return ""
        now = time.time()
        tok = getattr(self, "_reconize_token", "")
        if tok and now < getattr(self, "_reconize_token_exp", 0.0) - 60:
            return tok
        api = self._reconize_api()
        if not api:
            return ""
        body = json.dumps({"username": u, "password": p}).encode("utf-8")
        req = urllib.request.Request(api + "/api/auth/login", data=body,
                                     headers={"Content-Type": "application/json"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            tok = json.loads(r.read().decode("utf-8")).get("access_token") or ""
        self._reconize_token = tok
        self._reconize_token_exp = now + 1800
        return tok

    def camera_choice(self):
        """Which camera the Voice page should open, and how often to look.

        The camera is NOT a new setting here: Reconize already stores an
        app-wide default as the device LABEL (their settings camera_label -
        a browser deviceId means nothing on another machine, which is why
        they chose the label). Voice reads that one, so a designer who picks
        the camera once in the face app has picked it here too.
        config/voice.json can override it per PC, and the page keeps a local
        override of its own, exactly like their kiosk does.
        """
        import urllib.request
        face = self.cfg.get("face") or {}
        label = str(face.get("cameraLabel") or "")
        where = "voice.json" if label else ""
        if not label:
            api = self._reconize_api()
            try:
                tok = self._reconize_login()
                if api and tok:
                    req = urllib.request.Request(api + "/api/settings",
                                                 headers={"Authorization": "Bearer " + tok})
                    with urllib.request.urlopen(req, timeout=3) as r:
                        label = str(json.loads(r.read().decode("utf-8")).get("camera_label") or "")
                        where = "the face app" if label else ""
            except Exception:                           # noqa: BLE001
                pass                                    # no default is fine - the browser picks
        ok, why, detail = self.look_allowed()
        return {"label": label, "from": where, "stations": self.face_stations(),
                "seconds": float(face.get("autoSeconds") or 5),
                "look": {"ok": ok, "why": why, "detail": detail}}

    def face_stations(self):
        """The cameras the face app is ALREADY watching.

        User 2026-09-18: *in face regconize already make the program that we
        can use 1 camera for many task or program just read it*. Their
        stations - the kiosk, a CCTV node, a phone, the multi-camera local
        agent - all publish what they see to one live feed, and
        apps/faces/service.py already listens to it. So Voice does not have
        to open a second camera to know who is there: picking a station here
        means reading that feed instead, and one camera serves both apps.
        """
        import urllib.request
        out = []
        try:
            api = self._reconize_api()
            tok = self._reconize_login()
            if not api or not tok:
                return out
            req = urllib.request.Request(api + "/api/node/status",
                                         headers={"Authorization": "Bearer " + tok})
            with urllib.request.urlopen(req, timeout=3) as r:
                got = json.loads(r.read().decode("utf-8"))
        except Exception:                                   # noqa: BLE001
            return out
        for n in (got.get("nodes") or []):
            nid = str(n.get("node_id") or "")
            if not nid:
                continue
            out.append({"id": nid,
                        "name": str(n.get("camera_label") or n.get("name") or nid),
                        "online": bool(n.get("online"))})
        return out

    def identify(self, jpeg):
        """Asks Reconize who is in ONE frame, and saves NOTHING.

        User 2026-09-18: *do not save the picture of it because it took my
        rom*. Their upload writes the frame, a history row and an attendance
        row, so the frame goes only to a face app that promises to keep none
        of it (look_allowed); otherwise nothing is sent and the page is told
        why. The name is cached here exactly like a face seen through their
        camera, so the next answer greets the person by name.
        """
        import urllib.error
        import urllib.request
        api = self._reconize_api()
        if not api:
            return "", "config/partners.json does not say where the face app is", ""
        try:
            tok = self._reconize_login()
        except urllib.error.HTTPError as e:             # it answered, and said no
            return "", "the face app did not accept the saved login", str(e)
        except OSError as e:                            # nothing was listening
            # WinError 10061 is a REFUSED CONNECTION, not a refused password.
            # Saying "did not accept the saved login" sent the user looking for
            # a wrong password that was never wrong (user 2026-09-18). Nothing
            # is running: the fix is to start it, so the page offers that.
            return "", FACE_APP_OFF, str(e)
        if not tok:
            return "", "no saved login for the face app - see main_python/faces_login.json", ""
        ok, why, detail = self.look_allowed()
        if not ok:
            return "", why, detail
        look = self._reconize_entry()["look"]
        b = uuid.uuid4().hex
        body = b"".join([
            ('--%s\r\nContent-Disposition: form-data; name="%s"; '
             'filename="frame.jpg"\r\nContent-Type: image/jpeg\r\n\r\n'
             % (b, look.get("field") or "photo")).encode(),
            jpeg, ("\r\n--%s--\r\n" % b).encode()])
        req = urllib.request.Request(
            api + look["path"] + "?" + look["dontKeep"], data=body,
            headers={"Authorization": "Bearer " + tok,
                     "Content-Type": "multipart/form-data; boundary=" + b})
        try:
            with urllib.request.urlopen(req, timeout=60) as r:
                got = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return "", "the face app refused to look at that picture", str(e)
        except OSError as e:
            return "", FACE_APP_OFF, str(e)
        names = []
        for m in (got.get("results") or got.get("matches") or []):
            if str(m.get("status") or "matched") != "matched":
                continue
            who = short_person_name((m.get("name") or m.get("first_name") or "").strip())
            if who and who not in names:
                names.append(who)
        if not names:
            # Nobody there, or nobody known: drop the name NOW rather than
            # letting the remembered one ride on. The badge said a name while
            # the same look reported an empty frame (user 2026-09-18: *when
            # don't have face why it still said phuthiphong*).
            self.forget_person()
            faces = got.get("faces_total") or got.get("faces") or 0
            return "", ("nobody the face app knows was in that picture"
                        if faces else "no face in that picture - move into the light"), ""
        person = " และ ".join(names[:2]) if len(names) <= 2 else "%s, %s และทุกท่าน" % (names[0], names[1])
        self._seen_person = person
        self._seen_at = time.time()
        return person, "", ""

    def _query_reconize_direct(self):
        """Fallback: query Reconize directly at :8000/api/history if faces service isn't answering."""
        import urllib.request
        from datetime import datetime
        try:
            l_path = self._faces_login_path()
            if not l_path.is_file():
                return ""
            creds = json.loads(l_path.read_text(encoding="utf-8")).get("reconize") or {}
            u, p = creds.get("username"), creds.get("password")
            if not u or not p:
                return ""
            now = time.time()
            tok = getattr(self, "_reconize_token", "")
            exp = getattr(self, "_reconize_token_exp", 0.0)
            if not tok or now >= exp - 60:
                body = json.dumps({"username": u, "password": p}).encode("utf-8")
                l_req = urllib.request.Request("http://127.0.0.1:8000/api/auth/login", data=body,
                                               headers={"Content-Type": "application/json"})
                with urllib.request.urlopen(l_req, timeout=1.5) as lr:
                    l_data = json.loads(lr.read().decode("utf-8"))
                    tok = l_data.get("access_token") or ""
                    self._reconize_token = tok
                    self._reconize_token_exp = now + 1800
            if not tok:
                return ""
            h_req = urllib.request.Request("http://127.0.0.1:8000/api/history?page_size=5&page=1",
                                           headers={"Authorization": "Bearer " + tok})
            with urllib.request.urlopen(h_req, timeout=1.5) as hr:
                h_data = json.loads(hr.read().decode("utf-8"))
                items = h_data.get("items") or []
                active = []
                seen = set()
                for item in items:
                    who = (item.get("name") or "").strip()
                    when_str = item.get("detected_at") or ""
                    if who and when_str:
                        try:
                            w_dt = datetime.fromisoformat(str(when_str).replace("Z", ""))
                            if abs((datetime.now() - w_dt).total_seconds()) <= 120:
                                s = short_person_name(who)
                                if s and s.lower() not in seen:
                                    seen.add(s.lower())
                                    active.append(s)
                        except Exception:
                            pass
                if active:
                    return " และ ".join(active[:2]) if len(active) <= 2 else f"{active[0]}, {active[1]} และทุกท่าน"
        except Exception:
            pass
        return ""

    def seen_seconds(self):
        """How long a face from this page's own camera counts as present.

        It has to be a memory of its own: a look keeps nothing, so there is
        no history row, the next poll finds nothing and the name would vanish
        two seconds later. It is a SETTING because the right length depends on
        the room - user 2026-09-18, after the badge kept naming somebody who
        had walked away: *make can setting by my self in setting to setting
        the time out time*.
        """
        try:
            return max(2.0, float((self.cfg.get("face") or {}).get("rememberSeconds") or 120))
        except Exception:                               # noqa: BLE001
            return 120.0

    def forget_person(self):
        """A look that saw nobody means nobody is there - say so at once."""
        self._seen_person = ""
        self._seen_at = 0.0
        self._cached_person = ""
        self._cached_person_at = time.time()

    def get_detected_person(self, req_person=None, camera=""):
        if req_person and str(req_person).strip():
            return str(req_person).strip()
        if camera:
            # One station only, and never the frame this page took itself:
            # asking for a camera means "who does THAT camera see".
            return self._query_faces_service(camera)
        now = time.time()
        seen_at = getattr(self, "_seen_at", 0.0)
        if getattr(self, "_seen_person", "") and (now - seen_at < self.seen_seconds()):
            return self._seen_person
        if hasattr(self, "_cached_person_at") and (now - self._cached_person_at < 2.0):
            return getattr(self, "_cached_person", "")
        person = self._query_faces_service()
        if not person:
            person = self._query_reconize_direct()
        self._cached_person = person or ""
        self._cached_person_at = now
        return self._cached_person


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

    def do_GET(self):                               # noqa: N802
        if self.refuse_web():
            return
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
        if path == "/face":
            want = parse_qs(urlparse(self.path).query).get("camera", [""])[0]
            return self._json({"ok": True,
                               "person": self.brain.get_detected_person(camera=want)})
        if path == "/camera":
            return self._json(dict({"ok": True}, **self.brain.camera_choice()))
        if path == "/voices":
            try:
                return self._json({"ok": True, "voices": self.brain.speaking_voices()})
            except Exception as e:                      # noqa: BLE001
                return self._json({"ok": False, "error": "the voice list could not be "
                                                         "read: %s" % e}, 500)
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
            if key == "config":
                existing = dict(self.brain.cfg or {})
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
        return self._json({"ok": True})

    def do_POST(self):                              # noqa: N802
        if self.refuse_web():
            return
        path = urlparse(self.path).path
        self.brain.maybe_reload()
        if path == "/config":
            return self.do_store(self.brain.cfg_path, "config")
        if path == "/faq":
            return self.do_store(self.brain.faq_path, "faqs")
        if path == "/identify":
            return self.do_identify()
        if path == "/transcribe":
            return self.do_transcribe()
        if path == "/say":
            return self.do_say()
        if path == "/translate":
            return self.do_translate()
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
        text = (req.get("text") or "").strip()
        history = req.get("history") or []
        req_lang = (req.get("lang") or "").strip()
        person = (req.get("person") or req.get("name") or "").strip()
        if not person:
            person = self.brain.get_detected_person()
        auto_detect = req.get("autoDetect", True)
        if not auto_detect:
            eff_lang = req_lang or self.brain.cfg.get("tts", {}).get("language") or "th"
        else:
            eff_lang = req_lang or detect_lang(text)
        if not text:
            return self._json({"ok": False, "error": "there was no question in "
                                                    "that - say it again"}, 400)
        try:
            read_match = re.match(r'^(?:ช่วย)?(?:อ่าน|ท่อง)(?:กลอน|บทกลอน|ข้อความ|เนื้อหา)?(?:นี้)?(?:ให้ฟังหน่อย|หน่อย)?(?:\s*[:：\-]\s*|\s+)(.+)$', text, re.DOTALL | re.I)
            if read_match and len(read_match.group(1).strip()) >= 6:
                read_target = read_match.group(1).strip()
                read_target = re.sub(r'^(?:บทกลอน|กลอน)(?:\s*[:：\-]\s*|\s+)', '', read_target).strip()
                out = {"ok": True, "answer": read_target, "source": "read", "lang": eff_lang}
                if person:
                    out["person"] = person
                return self._json(out)

            hit, score = self.brain.match_faq(text, lang=eff_lang)
            if hit:
                faq_ans = hit.get("answer") or ""
                if person:
                    faq_ans = personalize_answer(faq_ans, person, lang=hit.get("lang") or eff_lang)
                out = {"ok": True, "answer": faq_ans,
                       "source": "faq", "score": score,
                       "lang": hit.get("lang") or eff_lang}
                if person:
                    out["person"] = person
                # An answer may also MOVE a robot. The service only NAMES
                # the move - it never holds the password; the page, which
                # does, drives the show clock itself.
                for k in ("move", "module", "moves"):
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

    # Audio arrives as the request BODY, not JSON - a browser's MediaRecorder
    # stream is binary, and decoding it as text would destroy it.
    def do_identify(self):
        """One frame in, a name out, nothing kept. See Brain.identify."""
        length = int(self.headers.get("Content-Length") or 0)
        if length > 8 * 1024 * 1024:
            return self._json({"ok": False, "error":
                               "that picture is too big to look at"}, 400)
        jpeg = self.rfile.read(length) if length else b""
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
            wav, why_not = self.brain.say(text, req.get("lang") or "", voice=voice_name)
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
        ctype = "audio/wav" if wav.startswith(b"RIFF") else "audio/mpeg"
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(wav)))
        self.end_headers()
        self.wfile.write(wav)

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
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor(max_workers=min(4, len(texts))) as ex:
                res_list = list(ex.map(lambda t: self.brain.translate_all(str(t).strip(), source=req.get("source", "auto")), texts))
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
            trans, err = self.brain.translate_text(text, target=tgt, source=req.get("source", "auto"))
            return self._json({"ok": True, "text": trans, "target": tgt})

        # Default complaints translation (A21-8): keeps words and gains English twin
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
