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
