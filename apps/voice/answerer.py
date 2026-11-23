"""Writing an answer: the prompt, the think chain, the three guards (moved out of Brain 2026-11-21; Brain inherits Answerer).

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
from face_link import short_person_name
from speaker import one_particle, one_pronoun
from langs import DEF_PARTICLES, DEF_PRONOUNS, detect_lang, scripts_in, drop_ghosts, drop_repeats

CODE = Path(__file__).resolve().parents[2]


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


class Answerer:
    """Writing an answer: the prompt, the think chain, the three guards."""

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
            system = ("You are the MICE robot assistant. "
                      "Style: Caveman — direct, plain-spoken, concise. Zero filler words. Absolutely NO emojis. Maximum 1 short sentence.\n"
                      + scenario_hint
                      + person_hint
                      + ("\nRelevant FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "Always follow the created FAQ answers as closely as possible, never deviate off-topic. If question matches or relates to FAQ, answer from it. Otherwise answer directly in 1 short sentence as the MICE robot. NEVER invent a password, price, time, floor, place or EVENT that is not in the FAQ above - say you do not know, and to ask a member of staff.")
        elif lang == "ja":
            system = ("あなたはMICEロボットです。\n"
                      "スタイル：簡潔、直接的、絵文字なし。最大1文で短く答えてください。\n"
                      + scenario_hint
                      + person_hint
                      + ("\n関連FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "作成されたFAQ回答にできる限り忠実に従い、脱線しないでください。FAQに関連していればそれに従い、それ以外はMICEロボットとして1文で簡潔に答えてください。FAQにないパスワード・料金・時間・場所・イベントを作り出さないでください。分からない場合は分からないと答えてください。")
        elif lang == "zh":
            system = ("你是MICE机器人助手。\n"
                      "风格：简明扼要、直接清晰、绝不使用表情符号。最多1句简短回答。\n"
                      + scenario_hint
                      + person_hint
                      + ("\n相关FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "请尽可能紧密依据所给的FAQ答案回答，切勿偏离主题。如果问题与FAQ相关则按FAQ回答，否则作为MICE机器人用1句简短回答。不要编造FAQ中没有的密码、价格、时间、地点或活动；不知道就说不知道，请询问工作人员。")
        elif lang == "ko":
            system = ("You are the MICE robot assistant. Answer ONLY in Korean, in one short polite sentence, no emojis.\n"
                      + scenario_hint
                      + person_hint
                      + ("\nRelevant FAQ:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "Follow the FAQ answers closely. NEVER invent a password, price, time, floor, place or event that is not in the FAQ above - say in Korean that you do not know and to ask a member of staff.")
        elif is_verse and lang == "th":
            system = ("คุณคือหุ่นยนต์ MICE เมื่อผู้ใช้ขอให้อ่านหรือท่องบทกลอน จงท่องบทกลอนภาษาไทยที่ไพเราะ 1 บท (4 วรรค) แบ่งบรรทัดละวรรค ห้ามปฏิเสธ ไม่มีคำเยิ่นเย้อ ไม่มีอีโมจิ\n"
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
            system = ("คุณคือหุ่นยนต์ MICE ให้ข้อมูลบริการและสถานที่ จงตอบเป็นภาษาไทยเท่านั้น สั้นๆ ตรงประเด็น 1 ประโยคจบในตัว ห้ามตอบเป็นภาษาอังกฤษหรือภาษาอื่น ไม่มีคำเยิ่นเย้อ ไม่มีอีโมจิ\n"
                      + ("ลงท้ายประโยคด้วยคำว่า '%s' เสมอ ห้ามใช้คำลงท้ายอื่น เช่น %s และเรียกตัวเองว่า '%s' เสมอ ห้ามใช้ %s เพราะคุณเป็นหุ่นยนต์ตัวเดียวและต้องพูดด้วยน้ำเสียงเดียวกันทุกประโยค\n" % (keep, not_end, me, not_me))
                      + ((wording + "\n") if wording else "")
                      + scenario_hint
                      + person_hint
                      + ("\nFAQ ที่เกี่ยวข้อง:\n" + "\n".join(faq_lines) + "\n\n" if faq_lines else "\n")
                      + "จงตอบโดยยึดตามข้อมูลคำตอบที่สร้างไว้ (FAQ) ให้ใกล้เคียงที่สุดเสมอ หากคำถามเกี่ยวข้องกับ FAQ ให้ตอบตามนั้น หากไม่ตรงให้ตอบสั้นๆ ในฐานะหุ่นยนต์ MICE 1 ประโยคเป็นภาษาไทย ห้ามแต่งรหัสผ่าน ราคา เวลา ชั้น สถานที่ หรือกิจกรรม/ข่าวที่ไม่มีใน FAQ ถ้าไม่รู้ให้บอกว่าไม่ทราบและให้สอบถามเจ้าหน้าที่")
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
