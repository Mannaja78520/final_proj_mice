"""A saved answer must win, and the model must not invent facts.

A26-68 (user 2026-09-18, from a real session on the rig): asking *ไวไฟ* did
not reach the saved WiFi answer, so the local model answered instead and made
up a password - `รหัสไวไฟคือ 3587`, where the saved answer says `Welcome2024`.
The user spotted it: *ไม่ใช่ เว็วคั้มหรอ*. Two holes, both guarded here:

  * Thai and CJK write without spaces, so the eight-character floor in
    match_faq never fired for a real word inside a saved question. A short
    word that IS the subject now matches - but a bare question word like
    *อะไร* must not, or every asker gets the food desk;
  * and every system prompt now forbids inventing a password, price, time,
    floor or place that is not in the FAQ. That is a prompt, not a promise -
    it cannot be tested here beyond its presence, which is why the first rule
    matters more.
"""
import json
import re

import qc as F

AREA = "tools"
TITLE = "a saved answer wins, and nothing invents a password"

FAQS = [
    # No bare "ไวไฟ" here on purpose: the short-word rule is what has to
    # find it, so breaking that rule must fail this check.
    {"questions": ["รหัสไวไฟคืออะไร", "wifi password"],
     "answer": "รหัส WiFi คือ Welcome2024 ครับ"},
    {"questions": ["กินอะไรดี", "where to eat"],
     "answer": "โรงอาหารอยู่ชั้น 1 ครับ"},
]


def _brain(cfg=None):
    import importlib.util
    import sys
    path = F.CODE / "apps" / "voice" / "service.py"
    spec = importlib.util.spec_from_file_location("voice_answers_check", path)
    mod = importlib.util.module_from_spec(spec)
    sys.modules["voice_answers_check"] = mod
    spec.loader.exec_module(mod)
    b = mod.Brain.__new__(mod.Brain)
    b.cfg = cfg or {"faqThreshold": 0.75}
    b.faqs = lambda: json.loads(json.dumps(FAQS))
    return b


def run(t):
    b = _brain()
    hit, score = b.match_faq("ไวไฟ")
    t.ok(hit is not None and "Welcome2024" in (hit.get("answer") or ""),
         "one Thai word reaches the saved answer it belongs to",
         "scored %.2f, got %r" % (score, hit and hit.get("answer")))
    hit, _ = b.match_faq("รหัสไวไฟ")
    t.ok(hit is not None and "Welcome2024" in (hit.get("answer") or ""),
         "and so does the longer way of asking it", "got %r" % (hit,))

    hit, score = b.match_faq("อะไร")
    t.ok(hit is None, "a bare question word answers nothing",
         "it matched %r at %.2f" % (hit and hit.get("answer"), score))
    hit, score = b.match_faq("ไป")
    t.ok(hit is None, "and a two-letter word does not either",
         "it matched %r at %.2f" % (hit and hit.get("answer"), score))

    # The stop words are data, so the next one costs no code.
    b2 = _brain({"faqThreshold": 0.75, "faqStopWords": ["ไวไฟ"]})
    # Without the exact question in the store, only the short-word rule can
    # match "ไวไฟ" - and the store has just called it a question word.
    b2.faqs = lambda: [{"questions": ["รหัสไวไฟคืออะไร"], "answer": "Welcome2024"}]
    hit, _ = b2.match_faq("ไวไฟ")
    t.ok(hit is None, "the store decides which words are only questions",
         "faqStopWords was ignored")

    src = (F.CODE / "apps" / "voice" / "service.py").read_text(encoding="utf-8")
    for words, lang in ((("NEVER invent a password",), "English"),
                        (("ห้ามแต่งรหัสผ่าน",), "Thai"),
                        (("不要编造",), "Chinese"),
                        (("作り出さないで",), "Japanese")):
        t.ok(all(w in src for w in words),
             "the %s prompt forbids inventing a password or a price" % lang,
             "the rule is missing from the %s prompt" % lang)

    # ---- the three things a 0.5B model gets wrong in Thai ---------------
    # A26-69, user 2026-09-18: *the local model writes weak Thai - it mixes
    # ครับ and ค่ะ, cuts replies off, and sometimes answers in the wrong
    # language on very short questions*. None of the three is fixable by asking
    # the prompt more nicely; each is CHECKED after the answer comes back, and
    # a bad answer is refused rather than spoken. These run without a model,
    # because the three guards are plain functions of text.
    import importlib.util
    import sys
    spec = importlib.util.spec_from_file_location(
        "voice_guards_check", F.CODE / "apps" / "voice" / "service.py")
    v = importlib.util.module_from_spec(spec)
    sys.modules["voice_guards_check"] = v
    spec.loader.exec_module(v)

    # ONE VOICE. The robot is one character and every saved answer ends ครับ;
    # the model ended one sentence ครับ and the next ค่ะ, which in Thai reads
    # as two different people talking.
    t.eq(v.one_particle("สวัสดีค่ะ ยินดีต้อนรับค่ะ", "ครับ"),
         "สวัสดีครับ ยินดีต้อนรับครับ",
         "every polite particle in one answer becomes the same one")
    t.eq(v.one_particle("ห้องน้ำอยู่ทางซ้ายนะคะ", "ครับ"),
         "ห้องน้ำอยู่ทางซ้ายนะครับ", "นะคะ becomes นะครับ, not นะครับครับ")
    t.eq(v.one_particle("เปิด 8 โมงครับ", "ครับ"), "เปิด 8 โมงครับ",
         "an answer already in one voice is left alone")

    # NEVER HALF A SENTENCE. Thai has no full stop, so a finished Thai sentence
    # is one that ends on its particle.
    t.eq(v.trim_unfinished("ห้องน้ำอยู่ทางซ้ายครับ แล้วเดินตรงไปอีกสิบ", "th"),
         "ห้องน้ำอยู่ทางซ้ายครับ",
         "a reply cut off mid-word goes back to its last finished sentence")
    t.eq(v.trim_unfinished("เดินตรงไปอีกสิบเมตรแล้ว", "th"), "",
         "and when nothing whole survives, nothing is spoken")
    t.eq(v.trim_unfinished("The toilet is on the left. Then walk twen", "en"),
         "The toilet is on the left.", "the same in English, on the full stop")

    # THE LANGUAGE THAT WAS ASKED. A two-word Thai question gives a small model
    # almost nothing, and it answers in English perhaps one time in five.
    t.ok(v.answers_in("รหัส WiFi คือ Welcome2024 ครับ", "th"),
         "a Thai answer with a Latin name in it still counts as Thai",
         "a product name or a number must not make an answer look foreign")
    t.ok(not v.answers_in("The wifi password is Welcome2024", "th"),
         "an English answer to a Thai question is refused",
         "this is the wrong-language reply the user saw on short questions")
    t.ok(not v.answers_in("你好，欢迎光临", "th"),
         "and so is a Chinese one")
    t.ok(not v.answers_in("123 456", "th"),
         "digits alone are not an answer in any language")
    t.ok(v.answers_in("Hello, how can I help?", "en"),
         "an English question still gets its English answer")

    # ONE WORD FOR ITSELF. Measured against the real model 2026-09-18: one
    # answer said ครับ ฉันสามารถ... and the next ผมสามารถ.... In Thai the
    # first-person word carries as much character as the ending, and two of
    # them in one conversation is the same fault as ครับ/ค่ะ.
    t.eq(v.one_pronoun("ครับ ฉันช่วยได้", "ผม"), "ครับ ผมช่วยได้",
         "the robot calls itself the same thing in every answer")
    t.ok(v.one_pronoun("เพื่อให้ฉันสามารถ", "ผม") == "เพื่อให้ผมสามารถ",
         "including mid-sentence, where Thai has no space to mark it off",
         "a rule that only looked after a space missed exactly these")
    t.eq(v.one_pronoun("ท่องฉันท์ให้ฟัง", "ผม"), "ท่องฉันท์ให้ฟัง",
         "but ฉันท์ is a kind of verse, not the robot talking about itself")
    t.eq(v.one_pronoun("มีฉันทะในการทำงาน", "ผม"), "มีฉันทะในการทำงาน",
         "and neither is ฉันทะ")
    t.ok("หนู" not in v.DEF_PRONOUNS,
         "หนู is left off the shipped pronoun list on purpose",
         "it is a first-person word AND the word for mouse, and this robot is "
         "called Mice - replacing it would rewrite real answers about mice")

    # A WHOLE ANSWER IN QUOTES is the model quoting itself; a voice reads the
    # marks as a pause and a person reads it as the robot quoting somebody.
    t.eq(v.unquote_whole('"ผมคือหุ่นยนต์ครับ"'), "ผมคือหุ่นยนต์ครับ",
         "quotation marks around a whole answer come off")
    t.eq(v.unquote_whole('เขาบอกว่า "ดี" ครับ'), 'เขาบอกว่า "ดี" ครับ',
         "a quote INSIDE a sentence is somebody's words and stays")

    # THE PARTICLE IS NOT AN ANSWER. Both of these came back from the real
    # model on very short questions and both carry Thai.
    t.ok(not v.answers_in("ครับ temperatures are hot today", "th"),
         "an English sentence with a Thai ending stuck on it is refused",
         "the model really answered this to ร้อนจัง on 2026-09-18")
    t.ok(not v.answers_in("ครับ", "th"),
         "and a bare polite particle is not an answer either",
         "the model really answered this to ไกลไหม")

    # THE WORDS AND THE BUDGETS ARE DATA, so the next particle or a different
    # apology costs an entry in config/voice.json, not a code change.
    cfg = json.loads((F.CODE / "config" / "voice.json").read_text(encoding="utf-8"))
    a = cfg.get("answer") or {}
    t.ok(a.get("politeParticle"), "the store says which particle the robot uses")
    t.ok(a.get("politeParticles") and len(a["politeParticles"]) >= 4,
         "and lists the ones it must never mix in", a.get("politeParticles"))
    t.ok(a.get("politePronoun"), "the store says what the robot calls itself")
    t.ok(a.get("politePronouns") and len(a["politePronouns"]) >= 3,
         "and lists the words it must never use instead", a.get("politePronouns"))
    by = a.get("maxTokensByLang") or {}
    t.ok(int(by.get("th", 0)) > int(cfg.get("llm", {}).get("maxTokens", 32)),
         "Thai gets more room to finish a sentence than the flat budget",
         "Thai costs two to four tokens a word, so 32 stopped it mid-word - "
         "got th=%r against maxTokens=%r" % (by.get("th"), cfg.get("llm", {}).get("maxTokens")))
    for lang in ("th", "en", "ja", "zh"):
        t.ok((a.get("cannotAnswer") or {}).get(lang),
             "there is a plain %s sentence for having nothing to say" % lang)
        t.ok((a.get("onlyThisLanguage") or {}).get(lang),
             "and a %s line that asks for that language alone" % lang)

    b3 = _brain(cfg)
    t.eq(b3.token_budget("th"), int(by["th"]), "the brain reads the Thai budget from the store")
    t.eq(b3.token_budget("xx"), int(cfg["llm"]["maxTokens"]),
         "an unknown language falls back to the flat budget")
    t.contains(b3.cannot_answer("th"), "ขออภัย",
               "and says it cannot answer in Thai, politely")
    t.eq(b3.tidy_answer("สวัสดีค่ะ ผมคือหุ่นยนต์ Mice คร", "th", ran_out=True),
         "สวัสดีครับ",
         "one answer, both guards: the particle is fixed and the fragment is dropped")
    # THE CALL SITE, not only the function. unquote_whole tested alone passed
    # while tidy_answer had stopped calling it (2026-09-18).
    t.eq(b3.tidy_answer('"ผมคือหุ่นยนต์ Mice ครับ"', "th"), "ผมคือหุ่นยนต์ Mice ครับ",
         "an answer the model wrapped in quotes is unwrapped before it is spoken")
    t.eq(b3.tidy_answer("ครับ ฉันช่วยได้ครับ", "th"), "ครับ ผมช่วยได้ครับ",
         "and the pronoun is normalised on the way through, not only in the helper")
    t.eq(b3.tidy_answer("สวัสดีค่ะ ผมคือหุ่นยนต์ Mice คร", "th", ran_out=False),
         "สวัสดีครับ ผมคือหุ่นยนต์ Mice คร",
         "a reply that did NOT run out is never trimmed - only cut-offs are")

    # EVERY SAVED ANSWER IN ONE VOICE. The store is what the robot says when it
    # is right, so a ค่ะ in there would defeat the whole guard.
    faqs = json.loads((F.CODE / "apps" / "voice" / "qa_data.json")
                      .read_text(encoding="utf-8"))["faqs"]
    t.ok(len(faqs) >= 15,
         "the store carries the questions a visitor really asks (%d)" % len(faqs),
         "seven answers meant the model wrote most of what the robot said")
    keep = a["politeParticle"]
    wrong = []
    for item in faqs:
        th = item.get("answer") or ""
        for p in a["politeParticles"]:
            if p != keep and re.search(re.escape(p) + r"(?=$|[\s\.,!?])", th):
                wrong.append((item.get("questions", [""])[0], p))
    t.ok(not wrong, "and every Thai answer in it ends in the same particle", wrong[:5])
