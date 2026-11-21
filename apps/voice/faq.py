"""The saved answers: reading qa_data.json and finding the nearest one (moved out of Brain 2026-11-21; Brain inherits Faq).

Uses from Brain: cfg, _lock, _resources, service(), chain(), run_job(), key_for() and its sibling mixins.
"""
import copy
import hashlib
import json
import os
import re
import threading
import time
import unicodedata
from difflib import SequenceMatcher
from pathlib import Path

import providers
import registry
import local_ai
import intents
from langs import DEF_PARTICLES, DEF_PRONOUNS, detect_lang, scripts_in, drop_ghosts, drop_repeats

CODE = Path(__file__).resolve().parents[2]


class Faq:
    """The saved answers: reading qa_data.json and finding the nearest one."""

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
