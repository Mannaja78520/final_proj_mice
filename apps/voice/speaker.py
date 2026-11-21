"""Speaking: voices, saved-sound cache, manner and the Edge/Windows engines (moved out of Brain 2026-11-21).

Brain inherits Speaker. Uses from Brain: cfg, service(), chain(), run_job(), faqs(), _resources,
_tts_lock, and the scenario/voice helpers defined here.
"""
import hashlib
import itertools
import json
import os
import re
import subprocess
import sys
import tempfile
import threading
import types
import time
import unicodedata
from pathlib import Path

import providers
import registry
import friend_api
from langs import DEF_PARTICLES, DEF_PRONOUNS, detect_lang, scripts_in
from user_voice import UserVoice, PERSON as USER_PERSON

CODE = Path(__file__).resolve().parents[2]
import urllib.request                                 # noqa: E402
import urllib.parse                                   # noqa: E402
import itertools                                      # noqa: E402

NO_WINDOW = getattr(subprocess, "CREATE_NO_WINDOW", 0) if os.name == "nt" else 0
_tmp_seq = itertools.count()                        # one temp name per writer
EMOJI_RE = re.compile(r"[\U0001F000-\U0001FAFF\u2600-\u27BF\u2300-\u23FF\u2B50\u200D\uFE0F]")
RATE_RE = re.compile(r"^[+-]\d{1,3}%$")
PITCH_RE = re.compile(r"^[+-]\d{1,3}Hz$")


def one_particle(text, keep, particles=None, ask_words=None):
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
    # Two particles in a row (ครับค่ะ) are one ending said twice: PC test
    # 2026-11-04 on #118, the model copied "...ประชาสัมพันธ์ครับ" and a ค่ะ was added.
    every = sorted({p for p in (particles or DEF_PARTICLES) if p} | {keep}, key=len, reverse=True)
    run = re.compile("(?:%s){2,}(?=$|[\\s\\.,!?ฯ])" % "|".join(re.escape(p) for p in every))
    pat = re.compile("(?:%s)(?=$|[\\s\\.,!?ฯ])" % "|".join(re.escape(p) for p in others))
    out = pat.sub(keep, run.sub(keep, text or ""))
    if keep == "ค่ะ" and ask_words:
        # A woman says คะ after นะ / ไหม / อะไร, not ค่ะ (PC test 2026-11-04 found
        # "นะค่ะ", "ไหมค่ะ"). The words are DATA: answer.askWords in voice.json.
        out = re.sub("(%s)ค่ะ" % "|".join(re.escape(w) for w in ask_words), r"\1คะ", out)
    return out


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
    others = [p for p in (pronouns or DEF_PRONOUNS) if p and p != keep]
    if not others:
        return text or ""
    # keep joins the list so a longer pronoun that CONTAINS a shorter one
    # (ดิฉัน holds ฉัน) is matched whole and put back as itself, not as ดิ+ดิฉัน
    # (PC test 2026-11-04: every female-voice answer said "ดิดิฉัน").
    every = sorted(set(others) | {keep}, key=len, reverse=True)
    pat = re.compile(r"(?:%s)(?!ท)" % "|".join(re.escape(p) for p in every))
    return pat.sub(keep, text or "")


def main_lang(text):
    """The language most of a line is written in, by letters ("" if none).

    detect_lang says "th" for ANY Thai letter, so an English welcome with one
    Thai name was counted Thai. For choosing who READS a mixed line, the bulk
    of it decides (A42-2).
    """
    count = {}
    for ch in text or "":
        got = scripts_in(ch)
        for k in got:
            count[k] = count.get(k, 0) + 1
    return max(count, key=count.get) if count else ""


def voice_lang(name):
    """"th-TH-PremwadeeNeural" -> "th"; "" for a name with no language in it
    (a Windows voice such as "Pattara")."""
    m = re.match(r"^([a-z]{2,3})-[A-Za-z]{2,4}-", str(name or ""))
    return m.group(1) if m else ""


class Speaker:
    """Which voice, in which manner, made once and cached; plus the scenario that picks them."""

    def _m(self):
        """The module this Brain lives in: its CODE root and subprocess (a check swaps both)."""
        g = type(self).__init__.__globals__           # works for a module no one registered
        return types.SimpleNamespace(CODE=g["CODE"], subprocess=g["subprocess"])

    _made = threading.local()       # the sound file say() last used, per thread

    # How THIS thread's last line was said (manner, how, by whom). Per thread:
    # the saved-answer sweep speaks in the background and, shared, it wrote
    # its own manner into a visitor's X-Voice-Style (2026-10-21).
    @property
    def _style_done(self):
        return getattr(self._made, "style", None) or {}

    @_style_done.setter
    def _style_done(self, value):
        self._made.style = value
        self._style_last = value              # /styles "last" shows any thread's


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
            mixed = self.mixed_voice((lang or "").strip() or main_lang(text))
            if mixed:
                return mixed, mixed
        voices = tcfg.get("voices") or {}
        lang = (lang or "").strip()
        if not lang and text:
            detected = detect_lang(text)
            if detected in voices:
                lang = detected
        if not lang:
            lang = self.main_language()
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
                        "pitch": str(s.get("pitch") or "").strip(),
                        "language": str(s.get("language") or "").strip(),
                        "style": str(s.get("style") or "").strip()}   # A45-25 manner
        return {"name": "", "prompt": want, "voice": "", "rate": "", "pitch": "",
                "language": "", "style": ""}

    def main_language(self):
        """The language to fall back on: the scenario's own (a global event
        leans English, user 2026-10-19), else the Voice tab's, else Thai."""
        return (self.active_scenario().get("language")
                or str((self.cfg.get("tts") or {}).get("language") or "").strip() or "th")

    def mixed_voice(self, lang=""):
        """The voice for a line that holds more than one language, or "".

        A NATIVE voice of the line's own language (user 2026-10-15: *each
        language may not be spoken by that language's voice*). The old
        pick - the first multilingual voice the service listed, whatever its
        language - read a Thai answer holding the word "WiFi" with a foreign
        accent. So: `tts.mixedVoice` if it is of this language, else the
        language's own voice if it reads everything, else a multilingual voice
        of this language. "" = the language's own voice reads the line.
        """
        tcfg = self.cfg.get("tts") or {}
        named = str(tcfg.get("mixedVoice") or "").strip()
        if named and (not lang or voice_lang(named) in ("", lang)):
            return named
        if not lang:
            return ""
        own = str((tcfg.get("voices") or {}).get(lang) or "")
        if "Multilingual" in own:
            return own
        for v in self.speaking_voices():
            if voice_lang(v["name"]) == lang:
                return v["name"]
        return ""

    def _edge_voices(self):
        """The speech service's own voice list, raw. Cached: it is a network
        call and it never changes during a run. Offline gives [] and the
        saved names still speak."""
        got = getattr(self, "_edge_list", None)
        if got is not None:
            return got
        try:
            import asyncio
            import edge_tts
            got = list(asyncio.run(edge_tts.list_voices()))
        except Exception:                               # noqa: BLE001
            got = []                                    # offline: the map still works
        self._edge_list = got
        return got

    @staticmethod
    def _voice_row(v):
        """One voice in words a designer reads: "Premwadee - Thai (Thailand)"."""
        name = str(v.get("ShortName") or "")
        says = str(v.get("FriendlyName") or name)
        says = re.sub(r"^Microsoft\s+|\s+Online\s+\(Natural\)|(?<=\w)Multilingual\b",
                      "", says).strip()
        return {"name": name, "says": says or name,
                "gender": str(v.get("Gender") or ""),
                "locale": str(v.get("Locale") or "")}

    def speaking_voices(self):
        """Every voice that can speak ALL languages, from the voice service
        itself - so the list in the settings screen is never a list typed
        into this file.
        """
        # Microsoft's own name for the voices that are not tied to one
        # language. There is no other flag in their list.
        return [self._voice_row(v) for v in self._edge_voices()
                if "Multilingual" in str(v.get("ShortName") or "")]

    def voices_by_lang(self):
        """{lang: [voice, ...]} for every language the store maps (A42-1).

        The page offered two names per language, typed into it; Thai alone
        has three. The languages are the store's tts.voices keys, so a fifth
        language is an entry there and no code.
        """
        langs = list(((self.cfg.get("tts") or {}).get("voices") or {}).keys())
        out = {l: [] for l in langs}
        # This PC's saved voices first (A45-29): {"name": "person:<id>", "own": true}.
        for pid, p in (self.people().get("people") or {}).items():
            for l in p.get("languages") or []:
                if l in out:
                    out[l].append({"name": "person:" + pid, "says": p.get("says") or pid,
                                   "gender": {"female": "Female", "male": "Male"}.get(p.get("gender"), ""),
                                   "locale": l, "own": True, "note": p.get("note") or ""})
        for v in self._edge_voices():
            loc = str(v.get("Locale") or "")
            for l in langs:
                if loc.split("-")[0].lower() == l.lower():
                    out[l].append(self._voice_row(v))
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

    def voice_heard(self):
        """Which voice really spoke the last line, in words (A42-2).

        User 2026-10-15, after the rebuild: *the voice is not natural at all*.
        When the online neural voice fails, the PC's own flat voice stands in
        - silently, so a missing package or a dropped connection sounded
        like "the voices are bad". The page now says which one it was, and
        why. {"natural": None} = nothing spoken yet.
        """
        if "edge" in self.chain("speak") and not self._edge_installed():
            return {"natural": False, "why": "the natural voice is not installed on this PC",
                    "tech": "%s -m pip install edge-tts" % sys.executable}
        return dict(getattr(self, "_heard", None) or {"natural": None})

    @staticmethod
    def _edge_installed():
        import importlib.util
        return importlib.util.find_spec("edge_tts") is not None

    def _cache_path(self, ident, text, rate=None, pitch=None):
        if rate is None:
            rate = str(self.cfg.get("tts", {}).get("rate") or "").strip()
        if pitch is None:
            pitch = str(self.cfg.get("tts", {}).get("pitch") or "").strip()
        extra = ("\n%s\n%s" % (rate, pitch)) if (rate or pitch) else ""
        key = hashlib.md5(("%s\n%s%s" % (ident, text, extra))
                          .encode("utf-8")).hexdigest()
        return getattr(self, "cache_dir", self._m().CODE / "apps" / "voice" / "tts_cache") / (key + ".wav")

    def steps(self, rate=None, pitch=None):
        """(speed, pitch) a line is spoken at: given, else the scenario's,
        else the store's. A step the speech service cannot read fails the
        WHOLE line and the PC's flat backup voice speaks instead, so it is
        dropped and the voice kept."""
        tcfg = self.cfg.get("tts", {})
        act = self.active_scenario()
        if rate is None:
            rate = act.get("rate") or str(tcfg.get("rate") or "").strip()
        if pitch is None:
            pitch = act.get("pitch") or str(tcfg.get("pitch") or "").strip()
        return (rate if RATE_RE.match(rate or "") else "",
                pitch if PITCH_RE.match(pitch or "") else "")

    @staticmethod
    def _cached(path, voice):
        """The saved sound for this line, or None.

        A neural voice answers mp3; a RIFF file under its name is the PC's
        backup voice kept by an older helper during an outage, and is built
        again rather than played flat for ever (A42-1).
        """
        try:
            got = path.read_bytes()
        except OSError:
            return None
        if "Neural" in (voice or "") and got.startswith(b"RIFF"):
            return None
        if providers.silent(got):
            return None        # an empty sound kept by an older helper: build again
        return got

    def say(self, text, lang="", voice="", rate=None, pitch=None, prebuild=False, style=None):
        """Text -> sound bytes, or (None, why-not) in plain words.

        rate / pitch given (the page's "Try it", A42-1) win over the store,
        so a speed can be heard before it is saved. Who speaks is the `speak`
        chain (A45-1); each service's sound is cached under its own name, so
        a backup's line is never played as if the chosen voice said it.
        `prebuild` = the start-up sweep of saved answers, which skips services
        with a small daily allowance.
        """
        tcfg = self.cfg.get("tts", {})
        if not tcfg.get("enabled"):
            return None, "speaking is switched off in config/voice.json"
        text = EMOJI_RE.sub("", text or "").strip()
        if not text:
            return None, "there was nothing to speak"
        if voice:
            ident, named = voice, voice
        else:
            ident, named = self.resolve_voice(lang, text=text)
            if not ident:
                return None, named
        # A scenario may set its own speed and pitch - a poem read at shop
        # speed is the complaint this answers.
        rate, pitch = self.steps(rate, pitch)
        # A saved voice of the feeling voice (A45-29): that service first; the
        # others speak its `backup` (same gender) if it is off or starting.
        who = self.person(named)
        if who:
            named = str(who.get("backup") or "")
        natural = "Neural" in (named or "")
        # The speaking manner (A45-25): what it changes depends on the
        # service, read from its `styles` capability - never assumed.
        skey, sty = self.style_choice(style)
        self._style_done = {"style": skey, "how": "", "by": ""}
        order = self.speak_order(skey, who)

        def one(pid, prov):
            kind = prov.get("kind")
            if prebuild and prov.get("prebuild") is False:
                return None, "not used to pre-speak saved answers"
            sjob = (prov.get("jobs") or {}).get("speak") or {}
            can = sjob.get("styles") or "none"
            how = can if skey else ""
            langs = sjob.get("languages")
            if langs and (lang or main_lang(text)) not in langs:
                return None, "it speaks only %s" % ", ".join(langs)
            self._style_done = {"style": skey, "how": how, "by": pid}
            r, p = (self.style_steps(rate, pitch, sty) if how == "prosody" else (rate, pitch))
            tag = ("|style=%s:%s" % (skey, how)) if skey else ""   # never replay another manner
            if kind == "local":
                # The PC's own voice: the named one if it is a Windows voice.
                mine = "" if natural else named
                own = ident if not natural else "<windows %s>" % (lang or voice_lang(named))
                return self._spoken(own + tag, text, rate, pitch,
                                    lambda: self._windows_speak(text, lang or voice_lang(named), mine))
            if kind in ("edge", "azure"):
                if not natural:
                    return None, "the chosen voice is not one of its voices"
                if kind == "edge":
                    return self._spoken(named + tag, text, r, p,
                                        lambda: self._edge_speak(named, text, r, p))
                return self._spoken("azure:" + named + tag, text, r, p,
                                    lambda: providers.azure_speak(
                                        prov, self.key_for(pid), prov["jobs"]["speak"], text,
                                        lang, named, timeout=10, rate=r, pitch=p))
            if kind == "feeling":
                if not self.feeling_ready(pid, prov):
                    return None, getattr(self, "_feeling_why", {}).get(pid) or "it is starting"
                feel = (sty.get("emotion") if skey else "") or "neutral"
                # New clarity settings = new sound: never replay a clip cut by the old ones (A45-26).
                tune = ("|tune=" + json.dumps(sjob["tune"], sort_keys=True)) if sjob.get("tune") else ""
                tempo = self.tempo_of(rate)
                tune += ("|person=%s" % who["id"]) if who else ""
                tune += ("|tempo=%.2f" % tempo) if abs(tempo - 1) >= 0.01 else ""
                return self._spoken("%s:%s%s%s" % (pid, feel, tag, tune), text, "", "",
                                    lambda: providers.feeling_speak(
                                        prov, "", sjob, text, lang, "",
                                        timeout=float(sjob.get("timeoutSeconds") or 20), emotion=feel,
                                        person=who, tempo=tempo))
            wire = providers.WIRES.get(kind, {}).get("speak")
            if not wire:
                return None, "it cannot speak"
            job = prov["jobs"]["speak"]
            # Its own voices, not Microsoft's names; speed and pitch do not apply.
            told = sty.get("instruct", "") if how == "instruct" else ""
            return self._spoken("%s:%s:%s%s" % (pid, job.get("model"), job.get("voice"), tag),
                                text, "", "",
                                lambda: wire(prov, self.key_for(pid), job, text,
                                             lang or main_lang(text), "", timeout=20,
                                             **({"style": told} if told else {})))
        got, why = self.run_job("speak", one, order=order)
        did = (getattr(self, "_jobs", None) or {}).get("speak") or {}
        if got is not None and not prebuild:
            if did.get("by") != "local":
                self._heard = {"natural": True}
            elif did.get("tried"):
                # The backup stood in, silently - the page names it (A42-2).
                self._heard = {"natural": False,
                               "why": "the natural voice did not answer - is this PC online?",
                               "tech": "; ".join("%s: %s" % (t["by"], t["why"])
                                                 for t in did["tried"])[-300:]}
            else:
                self._heard = {"natural": False, "why": "this PC's own voice is chosen"}
        return got, why

    def styles(self):
        """config/voice_styles.json, re-read when it changes on disk."""
        p = getattr(self, "styles_path", self._m().CODE / "config" / "voice_styles.json")
        try:
            m = (str(p), p.stat().st_mtime_ns)
        except OSError:
            return {"styles": {}}
        got = getattr(self, "_styles", None)
        if not got or got[0] != m:
            try:
                got = (m, registry.load(p) or {})
            except (OSError, ValueError):
                got = (m, {"styles": {}})
            self._styles = got
        return got[1]

    def people(self):
        """config/voice_people.json - saved voices of this PC's Thai feeling
        voice (A45-29), re-read when it changes on disk. {"people": {id: entry}}."""
        p = self._m().CODE / "config" / "voice_people.json"
        try:
            m = p.stat().st_mtime
        except OSError:
            return {"people": {}}
        got = getattr(self, "_people", None)
        if not got or got[0] != m:
            try:
                got = (m, registry.load(p) or {})
            except (OSError, ValueError):
                got = (m, {"people": {}})
            self._people = got
        mine = self.user_voice_folder()
        extra = UserVoice(self._m().CODE / "config" / "voice_clips.json").person(mine)
        if extra:                                    # the user's own recorded voice, if switched on
            return dict(got[1], people=dict(got[1].get("people") or {}, **{USER_PERSON: extra}))
        return got[1]

    def user_voice_folder(self):
        """The active character's `voice/` folder (the user's recorded clips), or None."""
        store = getattr(self, "profiles", None)
        if not store:
            return None
        try:
            return store.confined(store.folder(store.active) / "voice")
        except (OSError, ValueError):
            return None

    def person(self, name):
        """The saved voice a voice name means ("person:<id>"), or None."""
        name = str(name or "")
        if not name.startswith("person:"):
            return None
        entry = (self.people().get("people") or {}).get(name[len("person:"):])
        return dict(entry, id=name[len("person:"):]) if entry else None

    @staticmethod
    def tempo_of(rate):
        """"-10%" -> 0.9: the chosen speed for a voice that has no rate of its own."""
        try:
            return max(0.5, min(2.0, 1 + int(re.sub(r"[^0-9+-]", "", str(rate or "")) or 0) / 100.0))
        except ValueError:
            return 1.0

    def style_extra(self, key):
        """A key a character's snapshot may predate (`featured`, `speeds`,
        A45-29): the character's own voice_styles, else the shipped one."""
        got = self.styles().get(key)
        if got is None:
            try:
                got = (registry.load(self._m().CODE / "config" / "voice_styles.json") or {}).get(key)
            except (OSError, ValueError):
                got = None
        return got

    def style_choice(self, style=None):
        """(key, entry) of the manner a line is said in: the request's, else
        the scenario's, else tts.style. ("", {}) = none, as before A45-25.
        An unknown name is none, so a typo never mutes the voice."""
        if style is None:
            style = self.active_scenario().get("style") or (self.cfg.get("tts") or {}).get("style")
        key = style or ""
        key = str(key or "").strip()
        entry = (self.styles().get("styles") or {}).get(key)
        return (key, entry) if entry else ("", {})

    def speak_order(self, skey, who=None):
        """The speak chain, with a manner's preferred services first (voice_styles
        `prefer`) - the chosen order stays as the backup, so a line is never
        left unsaid when the feeling voice is off or still starting. A saved
        voice (`who`) puts the feeling services first."""
        chain = self.chain("speak")
        known = self.services().get("providers") or {}
        if who:
            first = [p for p, v in known.items() if v.get("kind") == "feeling"
                     and "speak" in (v.get("jobs") or {}) and p not in chain]
            return first + chain
        if not skey:
            return chain
        # A manner's own `prefer` wins over the shared one (A45-26: clarity first,
        # the feeling voice only where a manner asks for it).
        entry = (self.styles().get("styles") or {}).get(skey) or {}
        want = entry["prefer"] if "prefer" in entry else self.styles().get("prefer")
        first = [p for p in (want or [])
                 if p in known and "speak" in (known[p].get("jobs") or {}) and p not in chain]
        return first + chain

    def feeling_ready(self, pid, prov):
        """Is the feeling server up? If not and it is installed, start it in the
        background and say so; this line goes to the next service meanwhile.
        Never blocks a visitor on a 20 s model load."""
        if not hasattr(self, "_feeling_why"):
            self._feeling_why, self._feeling_proc = {}, {}
        job = (prov.get("jobs") or {}).get("speak") or {}
        base = (prov.get("base") or "").rstrip("/")
        try:
            with urllib.request.urlopen(base + "/health", timeout=0.5) as r:
                if json.loads(r.read()).get("ok"):
                    return True
        except Exception:                           # noqa: BLE001
            pass
        st = job.get("start") or {}
        proc = self._feeling_proc.get(pid)
        if proc is not None and proc.poll() is None:
            self._feeling_why[pid] = "it is still starting"
            return False
        pys = st.get("python") or []
        py = next((self._m().CODE / x for x in (pys if isinstance(pys, list) else [pys]) if (self._m().CODE / x).exists()), None)
        if not py or not st.get("script"):
            self._feeling_why[pid] = "it is not installed (python apps/voice/tts_spark/setup.py)"
            return False
        env = dict(os.environ, **{k: str(self._m().CODE / v) for k, v in (st.get("env") or {}).items()})
        logs = self._m().CODE / ".local" / "tts_spark"
        logs.mkdir(parents=True, exist_ok=True)
        log = open(logs / "server.log", "ab")
        self._feeling_proc[pid] = self._m().subprocess.Popen(
            [str(py), "-u", str(self._m().CODE / st["script"])] + [str(a) for a in st.get("args") or []],
            cwd=str(self._m().CODE), env=env, stdout=log, stderr=self._m().subprocess.STDOUT, creationflags=NO_WINDOW)
        self._feeling_why[pid] = "it was asleep and is starting now"
        return False

    def feeling_up(self):
        """Are the manner's preferred feeling services up? Starts them if not
        (so the model loads at boot, not at the first visitor)."""
        skey, _ = self.style_choice()
        if not skey:
            return False
        up = False
        for pid in self.speak_order(skey):
            prov = self.service(pid)
            if prov.get("kind") == "feeling":
                up = self.feeling_ready(pid, prov) or up
        return up

    def manner_answer(self, lang):
        """(particle, pronoun, wording line) the current manner asks of a
        model answer (voice_styles `answer`), or the store's defaults. A45-25:
        the sassy เจ๊ manner speaks as เจ๊ ending ค่ะ - by choice, opt-in."""
        a = self.answer_cfg()
        _key, sty = self.style_choice()
        own = sty.get("answer") or {}
        # A45-29 (user 2026-10-22: *เสียงไทยชายหญิงมีลงท้ายต่างกัน ครับ/ค่ะ*): the
        # voice's gender sets the ending and self-word; a manner's own wins.
        g = self.gender_words("th")
        return (own.get("particle") or g.get("particle") or a.get("politeParticle") or "ครับ",
                own.get("pronoun") or g.get("pronoun") or a.get("politePronoun") or "ผม",
                ((own.get("wording") or {}).get(lang) or "").strip())

    def voice_gender(self, lang):
        """"female" / "male" / "" - the gender of the voice that speaks `lang`:
        a saved voice says it, an Edge voice from Microsoft's own list."""
        try:
            ident, named = self.resolve_voice(lang)
        except Exception:                               # noqa: BLE001
            return ""
        if not ident:
            return ""
        who = self.person(named)
        if who:
            return str(who.get("gender") or "")
        for v in self._edge_voices():
            if v.get("ShortName") == named:
                return str(v.get("Gender") or "").lower()
        return ""

    def gender_words(self, lang, gender=None):
        """{"particle", "pronoun"} that agree with the speaking voice
        (config/voice_people.json `agree`), or {} when unknown."""
        agree = ((self.people().get("agree") or {}).get(lang) or {})
        if not agree:
            return {}
        return agree.get(self.voice_gender(lang) if gender is None else gender) or {}

    def agree_text(self, text, lang, voice=""):
        """The page's Try (`agree`): a sample said with the ending and self-word
        of THAT voice's gender, so a man's voice never tries ค่ะ."""
        if lang != "th":
            return text
        g = ""
        who = self.person(voice)
        if who:
            g = str(who.get("gender") or "")
        elif voice:
            g = next((str(v.get("Gender") or "").lower() for v in self._edge_voices()
                      if v.get("ShortName") == voice), "")
        w = self.gender_words("th", g if voice else None)
        if not w:
            return text
        text = one_particle(text, w.get("particle") or "", self.particles(), self.ask_words())
        return one_pronoun(text, w.get("pronoun") or "", self.pronouns())

    def manner_saved(self, text, lang):
        """A saved Thai answer in the manner's own ending and self-word, ONLY
        when the manner says `answer.saved` (the เจ๊ manner: a เจ๊ voice saying
        ครับ sounded wrong, 2026-10-21). The rest of the words stay as saved."""
        _key, sty = self.style_choice()
        if lang != "th" or not ((sty.get("answer") or {}).get("saved") or self.gender_words("th")):
            return text
        keep, me, _w = self.manner_answer("th")
        text = one_particle(text, keep, self.particles(), self.ask_words())
        return one_pronoun(text, me, self.pronouns())

    def style_steps(self, rate, pitch, sty):
        """The manner's speed and pitch steps ADDED to the chosen ones, kept
        inside `limits` ("+0%" chosen + friendly 3 = "+3%")."""
        lim = self.styles().get("limits") or {}
        pro = sty.get("prosody") or {}

        def add(base, step, unit, bounds):
            try:
                v = int(re.sub(r"[^0-9+-]", "", base or "") or 0) + int(step or 0)
            except ValueError:
                v = int(step or 0)
            lo, hi = (bounds or [-50, 50])[:2]
            v = max(lo, min(hi, v))
            return "%+d%s" % (v, unit)
        return (add(rate, pro.get("rate"), "%", lim.get("rate")),
                add(pitch, pro.get("pitch"), "Hz", lim.get("pitch")))

    def styles_view(self):
        """Every manner and, per speaking service, what it would really do."""
        out = {}
        for key, sty in (self.styles().get("styles") or {}).items():
            out[key] = {"says": sty.get("says") or key, "prosodyNote": sty.get("prosodyNote") or "",
                        "emotion": sty.get("emotion") or "", "emotionNote": sty.get("emotionNote") or "",
                        "by": {pid: ((self.service(pid)["jobs"].get("speak") or {}).get("styles") or "none")
                               for pid in self.speak_order(key)}}
        chosen, _ = self.style_choice()
        up = {}
        for pid in self.speak_order(chosen or "friendly"):
            prov = self.service(pid)
            if prov.get("kind") == "feeling":
                try:
                    with urllib.request.urlopen((prov.get("base") or "").rstrip("/") + "/health",
                                                timeout=0.3) as r:
                        up[pid] = bool(json.loads(r.read()).get("ok"))
                except Exception:                   # noqa: BLE001
                    up[pid] = False
        return {"styles": out, "chosen": chosen, "up": up,
                "recommended": self.styles().get("recommended") or "",
                # The quick choices on the Voice tab (A45-29): the 3 tones shown
                # as tiles, the speeds, and the saved default tone.
                "featured": [k for k in self.style_extra("featured") or [] if k in out],
                "speeds": self.style_extra("speeds") or {},
                "default": str((self.cfg.get("tts") or {}).get("style") or ""),
                "why": getattr(self, "_feeling_why", {}),
                "last": getattr(self, "_style_last", None) or {}}

    def _spoken(self, ident, text, rate, pitch, make):
        """The cached sound for this line in this voice, else make() it and
        keep it. A background line leaves one slot for a visitor."""
        path = self._cache_path(ident, text, rate=rate, pitch=pitch)
        self._made.path = path               # what the saved-answer sweep keeps
        got = self._cached(path, ident)
        if got:
            return got, None
        with self._tts_lock:
            if not hasattr(self, "_tts_keys"):
                self._tts_keys = {}
                self._tts_slots = threading.BoundedSemaphore(2)
            entry = self._tts_keys.setdefault(str(path), [threading.Lock(), 0])
            entry[1] += 1
        try:
            with entry[0], self._tts_slots:
                got = self._cached(path, ident)
                if got:
                    return got, None
                data, why = make()
                if not data:
                    return None, why
                if providers.silent(data):
                    # A header and no sound (the Windows voice on the PC test,
                    # 2026-10-19: 46 bytes, sent as "spoken"). Silence is a
                    # failure, so the next speaker in line gets the line.
                    return None, "it gave back an empty sound (%d bytes)" % len(data)
                path.parent.mkdir(exist_ok=True)
                tmpf = path.with_suffix(".part%d" % next(_tmp_seq))
                tmpf.write_bytes(data)
                os.replace(tmpf, path)   # atomic - a reader never sees half a file
                return data, None
        finally:
            with self._tts_lock:
                entry[1] -= 1
                if not entry[1]:
                    self._tts_keys.pop(str(path), None)

    def _edge_speak(self, voice, text, rate, pitch, _tried=()):
        """Microsoft's natural voice, IN this process.

        It used to start `python -m edge_tts` for every new line: a second
        Python plus its imports, 0.4 s on the cloud box and more on Windows
        (measured 2026-10-19), before the service was even asked. Speed and
        pitch go as arguments, so the old "--rate -10%" trap (A42-1) cannot
        come back. A bounded spare request shortens stalls before audio
        arrives; both timings are provider settings.
        """
        try:
            import asyncio
            import edge_tts
        except ImportError:
            return None, "the natural voice is not installed on this PC"
        clean = re.sub(r"[ \t]+", " ", re.sub(r"\r", "", text))
        clean = re.sub(r"\n\s*\n+", "\n", clean).strip()
        kw = {}
        if rate:
            kw["rate"] = rate
        if pitch:
            kw["pitch"] = pitch

        async def go():
            out = bytearray()
            async for ch in edge_tts.Communicate(clean, voice, **kw).stream():
                if ch.get("type") == "audio":
                    out += ch.get("data") or b""
            return bytes(out)
        job = self.service("edge")["jobs"]["speak"]
        hedge = max(0.001, float(job["hedgeSeconds"]))
        timeout = max(hedge, float(job["timeoutSeconds"]))

        async def race():
            # Some Edge requests stall before their first byte. Start at most
            # one spare after the configured wait, or immediately on failure.
            # Only a complete, nonempty response wins; always close the loser.
            pending = {asyncio.create_task(go())}
            tasks = set(pending)
            loop = asyncio.get_running_loop()
            started = loop.time()
            spare = False
            err = "no sound came back"
            try:
                while pending:
                    left = timeout - (loop.time() - started)
                    if left <= 0:
                        return None, "the natural voice timed out"
                    wait = left if spare else min(left, max(0, hedge - (loop.time() - started)))
                    done, pending = await asyncio.wait(pending, timeout=wait,
                                                       return_when=asyncio.FIRST_COMPLETED)
                    for task in done:
                        try:
                            got = task.result()
                            if not providers.silent(got):
                                return got, None
                        except Exception as e:                      # noqa: BLE001
                            err = "%s: %s" % (e.__class__.__name__, e)
                    if not spare:
                        task = asyncio.create_task(go())
                        pending.add(task)
                        tasks.add(task)
                        spare = True
                return None, err
            finally:
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)

        got, why = asyncio.run(race())
        if got or "NoAudioReceived" not in (why or ""):
            return got, why
        # The service answers nothing for one voice while others work (PC,
        # 2026-11-21: th-TH-PremwadeeNeural failed, th-TH-NiwatNeural did with
        # the same text and edge-tts 7.3.1). A line in another voice of the same
        # language beats silence; the list is data (config/voice.json tts.fallbackVoices).
        tried = tuple(_tried) + (voice,)
        alts = (self.cfg.get("tts") or {}).get("fallbackVoices") or {}
        for alt in alts.get(voice.split("-")[0], ()):
            if alt not in tried:
                got2, why2 = self._edge_speak(alt, text, rate, pitch, tried)
                if got2:
                    return got2, None
        return got, why

    def _windows_speak(self, text, lang, voice):
        """The PC's own voice through tts.ps1: no internet, but flat."""
        try:
            r = self._m().subprocess.run(
                ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass",
                 "-File", str(self._m().CODE / "apps" / "voice" / "tts.ps1"),
                 "-Text", text, "-Lang", lang, "-Voice", voice],
                capture_output=True, timeout=60, creationflags=NO_WINDOW)
        except (OSError, self._m().subprocess.TimeoutExpired) as e:
            return None, "the voice could not run (%s: %s)" % (e.__class__.__name__, e)
        wav = r.stdout
        if r.returncode != 0 or len(wav) < 44 or not wav.startswith(b"RIFF"):
            why = (r.stderr or b"").decode("utf-8", "replace").strip()
            return None, "the voice could not speak that (%s)" % why[-200:]
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
                        self._made.path = None
                        self.say(ans, lang=lang_code, prebuild=True)
                        rate, pitch = self.steps()
                        keep.add(self._cache_path(ident, ans, rate=rate, pitch=pitch).stem)
                        made = getattr(self._made, "path", None)
                        if made:
                            keep.add(made.stem)     # a backup's or a service's own file
        cache = getattr(self, "cache_dir", self._m().CODE / "apps" / "voice" / "tts_cache")
        if not cache.is_dir():
            return
        cutoff = time.time() - 24 * 3600
        for f in cache.glob("*.wav"):
            if f.stem not in keep and f.stat().st_mtime < cutoff:
                f.unlink(missing_ok=True)
