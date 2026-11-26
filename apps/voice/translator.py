"""Translation for the voice helper (moved out of Brain 2026-11-21; Brain inherits Translator).

Uses from Brain: _lock, _ensure_llm, _complete, _resources, supported_langs.
"""
import json

from langs import detect_lang


class Translator:
    """Any language in, any language out: Google first, the local model as fallback."""

    def _divert_to_cpu(self):
        """EXPERIMENT (MICE_VRAM_STRATEGY=hybrid): True when a background helper job should run on the CPU
        because the GPU is busy with, or has queued, live work."""
        import os
        if (os.environ.get("MICE_VRAM_STRATEGY") or "").lower() != "hybrid":
            return False
        try:
            gpu = self._sched.status()["resources"]["gpu"]
        except Exception:                          # noqa: BLE001
            return False
        return bool(gpu["running"] or gpu["waiting"])

    def translate(self, text):
        """Any language in, English out - or (None, why-not).

        A separate persona from /ask: the helper answers in the visitor's
        language, the translator always answers in English. One model, two
        system prompts - never both at once.
        """
        if self._divert_to_cpu():
            if not self.cfg.get("llm", {}).get("enabled"):
                return None, "the local model is switched off in config/voice.json"
            try:
                return self._complete([
                    {"role": "system", "content":
                        "You are a translator at a robot show. Translate the "
                        "message to English exactly - keep the meaning, plain "
                        "wording. Reply with ONLY the English translation."},
                    {"role": "user", "content": text}], model=self._cpu_llm()), None
            except Exception as e:              # noqa: BLE001
                return None, "%s: %s" % (e.__class__.__name__, e)
        with self._gpu("helper"):
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
        with self._gpu("translate"):
            ok, _ = self._ensure_llm()
            if ok:
                target_names = {
                    "th": "Thai",
                    "en": "English",
                    "ja": "Japanese",
                    "zh": "Chinese",
                    "ko": "Korean",
                    "fr": "French",
                    "de": "German",
                    "es": "Spanish",
                    "ru": "Russian",
                    "ar": "Arabic",
                    "hi": "Hindi",
                    "vi": "Vietnamese",
                    "id": "Indonesian",
                    "ms": "Malay",
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
        """Return dict of {lang: ...} across all configured languages for given text."""
        langs = self.supported_langs() if hasattr(self, "supported_langs") else ("th", "en", "ja", "zh")
        src = detect_lang(text) if source in ("auto", "") else source
        results = {src: text.strip()}
        targets = [t for t in langs if t != src]
        def translate(target):
            try:
                trans, _ = self.translate_text(text, target=target, source=src)
                return target, trans or text.strip()
            except Exception:
                return target, text.strip()
        for target, translated in self._resources.map(translate, targets):
            results[target] = translated
        for t in langs:
            if t not in results:
                results[t] = text.strip()
        return results
