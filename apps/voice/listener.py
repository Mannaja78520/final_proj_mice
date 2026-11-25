"""Listening: speech-to-text for the voice helper (moved out of Brain 2026-11-21; Brain inherits Listener).

Uses from Brain: cfg, _lock, _resources, _stt*, service(), chain(), run_job(), key_for().
"""
import json
import os
import re
import tempfile
import threading
import time
from pathlib import Path

import providers
import registry
import intents
from langs import detect_lang, drop_ghosts, drop_repeats


class Listener:
    """Model loading, language choice and transcription for one microphone clip."""

    def stt_status(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return "off in config/voice.json"
        if self._stt:
            # Every model in memory and the one that heard last: "small
            # loaded" while the Thai model did the hearing hid the switch
            # (PC test 2026-10-19).
            own = getattr(self, "_stt_own", None) or {}
            mine = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage") or {}
            names = [self._stt_loaded_model or scfg.get("model", "small")]
            names += ["%s for %s" % (mid, lang) for lang, mid in mine.items() if mid in own]
            said = ", ".join(names) + " loaded"
            if getattr(self, "_stt_last", None):
                said += "; last heard by " + self._stt_last
            if getattr(self, "_stt_own_err", None):
                said += "; own model could not load: " + "; ".join(
                    "%s: %s" % item for item in self._stt_own_err.copy().items())
            return said
        if self._stt_loading:
            return "loading in background…"
        if self._stt_err:
            return "could not load: " + self._stt_err
        return "loads when first needed"

    def _load_stt(self):
        # One load per model at a time (A55-1): the boot preload runs without
        # the GPU lock, so a first question used to load a SECOND copy beside
        # it - double VRAM on a 12 GB card the face app shares. A waiter finds
        # it loaded (or its error) and returns.
        lock = self.__dict__.setdefault("_load_lock_stt", threading.Lock())
        with lock:
            return self._load_stt_now()

    def _load_stt_now(self):
        scfg = self.cfg.get("stt", {})
        if not scfg.get("enabled"):
            return                      # switched off is a decision, not a fault
        if self._stt or self._stt_err:
            return
        self._stt_loading = True
        try:
            mid = scfg.get("model", "small")
            self._stt = self._whisper_model(mid, self._drop_main_stt)
            self._stt_loaded_model = mid
        except Exception as e:                              # noqa: BLE001
            self._stt_err = "%s: %s" % (e.__class__.__name__, e)
        finally:
            self._stt_loading = False

    def _whisper_model(self, mid, unload=None):
        """Honor this machine's budget on primary and language-specific loads."""
        from faster_whisper import WhisperModel
        return self._resources.whisper(mid, WhisperModel, unload=unload)

    def _drop_main_stt(self):
        """The GPU planner needed this room for something more valuable: reload lazily (CPU or GPU, by then)."""
        self._stt = None
        self._stt_loaded_model = None

    def _drop_own_stt(self, mid):
        (getattr(self, "_stt_own", None) or {}).pop(mid, None)

    def _own_model(self, lang):
        """The model trained for this one language, loaded once, or None.

        Measured 2026-10-19 on 30 Thai clips with room noise added: whisper
        "small" got 28% of the letters wrong, the Thai-trained Thonburian
        medium 2.3%. It hears Thai only, so it takes over only once the
        language is known (`local.hear.byLanguage` in voice_providers.json).
        """
        mid = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage", {}).get(lang)
        if not mid:
            return None
        got = getattr(self, "_stt_own", None)
        if got is None:
            got = self._stt_own = {}
        errors = getattr(self, "_stt_own_err", None)
        if errors is None:
            errors = self._stt_own_err = {}
        if mid not in got:
            try:
                got[mid] = self._whisper_model(mid, lambda mid=mid: self._drop_own_stt(mid))
            except Exception as e:                      # noqa: BLE001
                errors[mid] = "%s: %s" % (e.__class__.__name__, e)
                raise
        errors.pop(mid, None)
        return got[mid]

    def _detect(self, path, scfg):
        """The language spoken, by the general model's quick look. Unsure =
        the main language (scenario's, else stt.fallback's)."""
        from faster_whisper import decode_audio
        lang, prob, _all = self._stt.detect_language(decode_audio(path))
        fb = scfg.get("fallback") or {}
        if fb.get("language") and (lang not in (fb.get("when_not_in") or [lang])
                                   or prob < fb.get("min_probability", 0.0)):
            return self.active_scenario().get("language") or fb["language"]
        return lang

    def _decode(self, lang):
        """Whisper's anti-repeat settings for this language (local.hear in
        voice_providers.json). Thai gets none: they cost it 28% vs 2.3%."""
        hear = self.service("local")["jobs"].get("hear") or {}
        own = (hear.get("decodeByLanguage") or {}).get(lang)
        return dict(own if own is not None else hear.get("decode") or {})

    def _fallback_transcribe(self, path, segs, info, resolved, scfg):
        """A second pass in a set language when detection is unsure (A26-80).

        DATA, not code: stt.fallback in config/voice.json - language,
        when_not_in, min_probability. No fallback key, no second pass.
        """
        fb = scfg.get("fallback")
        if resolved or not fb or not fb.get("language"):
            return segs, info
        # A scenario's own main language wins: the same rig at a global event.
        lang = self.active_scenario().get("language") or fb["language"]
        unsure = (info.language not in (fb.get("when_not_in") or []) or
                  getattr(info, "language_probability", 1.0) < fb.get("min_probability", 0.0))
        if not unsure:
            return segs, info
        try:
            own = self._own_model(lang)
        except Exception:
            own = None       # an unavailable specialist still has a general fallback
        model = own or self._stt
        mine = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage") or {}
        self._stt_attempt = mine[lang] if own else self._stt_loaded_model or scfg.get("model", "small")
        self._stt_attempt_model = model
        return self._transcribe(model, path, lang, scfg)

    def _transcribe(self, model, path, lang, scfg, prompt=None):
        """Ten-second batches kept a 30 s Thai clip's tail (2026-10-20)."""
        hear = self.service("local")["jobs"].get("hear") or {}
        bias = ((scfg.get("languages") or {}).get(lang) or {}).get("bias") if lang else None
        context = (hear.get("contextByLanguage") or {}).get(lang)
        prompt = prompt or " ".join(str(x) for x in (bias, context) if x) or None
        options = dict(language=lang or None, temperature=0,
                       beam_size=int(scfg.get("beam") or 1), condition_on_previous_text=False,
                       vad_filter=True, vad_parameters={"min_silence_duration_ms": 500, "threshold": 0.6},
                       initial_prompt=prompt, **self._decode(lang))
        chunk = max(1, min(30, int(hear.get("chunkSeconds") or 10)))
        size = max(1, min(16, int(hear.get("batchSize") or 8)))
        if size > 1:
            try:
                from faster_whisper import BatchedInferencePipeline
            except ImportError:
                BatchedInferencePipeline = None
            if BatchedInferencePipeline is not None:
                batches = getattr(self, "_stt_batches", None)
                if batches is None:
                    batches = self._stt_batches = {}
                if id(model) not in batches:
                    batches[id(model)] = BatchedInferencePipeline(model=model)
                try:
                    segments, info = batches[id(model)].transcribe(
                        path, chunk_length=chunk, batch_size=size, **options)
                    return list(segments), info
                except RuntimeError as e:
                    if "out of memory" not in str(e).lower():
                        raise
                    batches.pop(id(model), None)    # one serial retry needs less memory
        segments, info = model.transcribe(path, chunk_length=chunk, **options)
        return list(segments), info

    def listen(self, audio, hint=""):
        """Speech bytes -> ({text, language}, None) or (None, why-not).

        The language is the request's hint, else the store's stt.language,
        else DETECTED per utterance - never a hardcoded code here. Who listens
        is the `hear` chain (A45-1): this PC's whisper, or a service.
        """
        scfg = self.cfg.get("stt", {})
        # A switched-off listener must not be outrun by its own cache.
        if not scfg.get("enabled"):
            return None, "listening is switched off in config/voice.json"
        hint_s = (hint or "").strip().lower()
        if hint_s in ("auto", "detect", "none"):
            resolved = None
        elif hint_s:
            resolved = hint_s
        else:
            cfg_lang = (scfg.get("language") or "").strip().lower()
            resolved = None if cfg_lang in ("auto", "detect", "none", "") else cfg_lang

        def one(pid, prov):
            if prov.get("kind") == "local":
                return self._listen_local(audio, resolved, scfg)
            wire = providers.WIRES.get(prov.get("kind"), {}).get("hear")
            if not wire:
                return None, "it cannot listen"
            text, why = wire(prov, self.key_for(pid), prov["jobs"]["hear"], audio,
                             resolved or "", timeout=20)
            if text is None:
                return None, why
            text = drop_repeats(text)
            return {"text": text, "language": resolved or (detect_lang(text) if text else "")}, None
        return self.run_job("hear", one)

    def _whisper(self, path, lang, scfg):
        """One whisper pass (and the unsure-language second pass). A language
        with its own trained model is heard by that model (A45-1)."""
        model, used = self._stt, self._stt_loaded_model or scfg.get("model", "small")
        mine = (self.service("local")["jobs"].get("hear") or {}).get("byLanguage")
        if mine:
            try:
                if not lang:
                    lang = self._detect(path, scfg)
                own = self._own_model(lang)
                if own:
                    model, used = own, mine[lang]
            except Exception:                           # noqa: BLE001
                pass               # no quick look, or no own model: as before
        self._stt_attempt, self._stt_attempt_model = used, model
        segments, info = self._transcribe(model, path, lang, scfg)
        segments, info = self._fallback_transcribe(path, segments, info, lang, scfg)
        valid = [seg.text for seg in segments if getattr(seg, "no_speech_prob", 0) <= 0.6]
        self._stt_last = self._stt_attempt
        return drop_ghosts(drop_repeats("".join(valid)), scfg.get("ghostPhrases")), info

    def _listen_local(self, audio, resolved, scfg):
        """This PC's whisper. Bias words apply only when the language is
        already known: detecting it first just to pick a prompt would double
        every wait."""
        with self._gpu("live"):
            self._load_stt()
            if not self._stt:
                return None, ("speech-in is not available (%s)"
                              % self.stt_status())
            with tempfile.NamedTemporaryFile(suffix=".webm", delete=False) as tf:
                tf.write(audio)
                path = tf.name
            try:
                try:
                    text, info = self._whisper(path, resolved, scfg)
                except Exception as e:
                    err_s = str(e).lower()
                    if not ("cublas" in err_s or "cuda" in err_s
                            or "not found" in err_s or "driver" in err_s):
                        raise
                    # The graphics card's libraries are missing: the CPU hears.
                    from faster_whisper import WhisperModel
                    mid = getattr(self, "_stt_attempt", None) or scfg.get("model", "small")
                    failed = getattr(self, "_stt_attempt_model", self._stt)
                    cpu = self._resources.whisper(mid, WhisperModel, force_cpu=True)
                    if failed is self._stt:
                        self._stt, self._stt_loaded_model = cpu, mid
                    else:
                        self._stt_own[mid] = cpu
                    (getattr(self, "_stt_batches", None) or {}).pop(id(failed), None)
                    text, info = self._whisper(path, resolved, scfg)
                text, heard_lang = self._code_switch(path, text, info.language, resolved, scfg)
            finally:
                os.unlink(path)
            return {"text": text, "language": heard_lang}, None

    def _saved_words(self, lang, cs):
        """The saved questions in `lang`, as the listener's word hint: the
        English hearing of a mixed clip wrote "restroom" right but the rest
        as "so what do you waste" (2026-10-21). From the store, so a new
        saved question is a new hint. Social replies are left out."""
        got = [q for it in self.faqs() if not it.get("wholeQuestion")
               for q in it.get("questions", []) if detect_lang(q) == lang]
        room = int(cs.get("hintChars") or 400)
        out, size = [], 0
        for q in got:
            if size + len(q) + 2 > room:
                break
            out.append(q)
            size += len(q) + 2
        return ". ".join(out) or None

    def _language_share(self, path, lang, cs):
        """The highest chance, over the `windows` of the clip (fractions of
        its length), that `lang` is what is spoken there. A greeting leads,
        so the question's language shows in the later part. 0.0 = no look."""
        try:
            from faster_whisper import decode_audio
            audio = decode_audio(path)
        except Exception:                           # noqa: BLE001
            return 0.0
        n, best = len(audio), 0.0
        for lo, hi in cs.get("windows") or [[0, 1]]:
            part = audio[int(lo * n):int(hi * n)]
            if len(part) < 16000 * 0.8 or not self._stt:
                continue                  # under a second says nothing reliable
            try:
                _l, _p, every = self._stt.detect_language(part)
            except Exception:                       # noqa: BLE001
                continue
            best = max(best, dict(every).get(lang, 0.0))
        return best

    def _code_switch(self, path, text, lang, resolved, scfg):
        """Hear a mixed Thai-English question again in English (A45-24).

        The Thai listener writes spoken English as Thai words: "where is the
        restroom" came out as a question about a bedroom, and no saved answer
        fit. Rules in voice_intents.json `codeSwitch`. Only when the language
        was detected (not picked on the page), it is one of `when`, and no
        saved answer fits. The other hearing wins when it comes closer to a
        saved answer by `margin` and reaches `minScore`; it need not reach the
        saved-answer threshold, because the model still answers from the
        nearest saved answers. Scores 2026-10-21: the Thai hearing of "สวัสดี
        where is the restroom" 0.37, its English hearing 0.62.
        """
        cs = intents.code_switch()
        if resolved or not text or lang not in (cs.get("when") or []):
            return text, lang
        floor = float(cs.get("faqBelow") or self.cfg.get("faqThreshold", 0.75))
        best = self.faq_best(text)[0]
        if best >= floor:
            return text, lang
        # A social reply (wholeQuestion: hello, thanks) never wins: the
        # English hearing of "Hello ห้องน้ำ..." kept only "Hello" (2026-10-21).
        pick = (text, lang, best)
        need = max(float(cs.get("minScore") or floor), best + float(cs.get("margin") or 0.0))
        for other in cs.get("languages") or []:
            if other == lang:
                continue
            # Only when part of the clip SOUNDS like that language. Asked for
            # English, the listener translates Thai speech: "Hello ห้องน้ำ
            # ทางไหน" came back as "hello. where is the restroom" and was
            # answered in English (2026-10-21).
            share = self._language_share(path, other, cs)
            if share < float(cs.get("minShare") or 0.0):
                continue
            try:
                model = self._own_model(other) or self._stt
                segs, _info = self._transcribe(model, path, other, scfg,
                                               prompt=self._saved_words(other, cs))
            except Exception:                       # noqa: BLE001
                continue           # no second listener: the first hearing stands
            again = drop_repeats("".join(seg.text for seg in segs
                                         if getattr(seg, "no_speech_prob", 0) <= 0.6))
            score, hit = self.faq_best(again) if again else (0.0, None)
            if hit and hit.get("wholeQuestion"):
                continue
            if score >= need and score > pick[2]:
                pick = (again, other, score)
        self._code_switched = {"first": text, "picked": pick[0], "language": pick[1],
                               "score": round(pick[2], 2), "at": time.time()}
        return pick[0], pick[1]
