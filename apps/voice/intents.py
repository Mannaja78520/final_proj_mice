"""What a question asks for beyond its words (A45-24).

The rules are DATA in config/voice_intents.json: the reply language asked
for, read-aloud, make up a new verse, Thai-letter loanwords and the mixed
Thai-English second hearing. Small pure functions, so each can be tested
alone (qc/checks/check_voice_intents.py); service.py decides what to do.
"""
import re
import sys
from pathlib import Path

CODE = Path(__file__).resolve().parents[2]
PATH = CODE / "config" / "voice_intents.json"
sys.path.insert(0, str(CODE / "tools"))
import registry                                      # noqa: E402

_cache = {"mtime": None, "data": {}, "rx": {}}


def table(path=None):
    """The intents file, read again when it changes. A broken file = no rules,
    never a crash: every question then goes the way it went before A45-24."""
    p = Path(path) if path else PATH
    try:
        m = p.stat().st_mtime
    except OSError:
        return {}
    if _cache["mtime"] != (p, m):
        try:
            data = registry.load(p) or {}
        except (OSError, ValueError):
            data = {}
        _cache.update(mtime=(p, m), data=data, rx={})
    return _cache["data"]


def _rx(pattern):
    got = _cache["rx"].get(pattern)
    if got is None:
        try:
            got = re.compile(pattern, re.I | re.DOTALL)
        except re.error:
            got = False                  # one bad entry must not stop the rest
        _cache["rx"][pattern] = got
    return got or None


def _tidy(text):
    text = re.sub(r"\s+", " ", text or "").strip()
    return text.strip(" ,.:;!?-，。、：").strip()


def reply_language(text, rules=None):
    """(language asked for, the question without that request) or ("", text)."""
    rules = (table() if rules is None else rules).get("replyLanguage") or {}
    for lang, pats in rules.items():
        for pat in pats or []:
            rx = _rx(pat)
            m = rx.search(text or "") if rx else None
            if m:
                rest = text[:m.start()] + " " + text[m.end():]
                rest = _tidy(re.sub(r"\s+[:：,，]\s*", " ", rest))
                return lang, rest or text
    return "", text


def read_aloud(text, rules=None):
    """The words to read out exactly, or None."""
    pats = (table() if rules is None else rules).get("readAloud") or []
    for pat in pats:
        rx = _rx(pat)
        m = rx.match((text or "").strip()) if rx else None
        if m and "text" in rx.groupindex and m.group("text").strip():
            return m.group("text").strip()
    return None


def wants_new_verse(text, rules=None):
    comp = (table() if rules is None else rules).get("compose") or {}
    for pat in comp.get("patterns") or []:
        rx = _rx(pat)
        if rx and rx.search(text or ""):
            return True
    return False


def loanwords(text, rules=None):
    """Thai-letter spellings of English words -> the English word."""
    words = (table() if rules is None else rules).get("loanwords") or {}
    pairs = sorted(((s, en) for en, spells in words.items() for s in spells or [] if s),
                   key=lambda p: -len(p[0]))
    for spelled, en in pairs:
        if spelled in text:
            text = text.replace(spelled, en)     # no added spaces: they change the length rules
    return re.sub(r"\s+", " ", text).strip()


def verse_lines(reply):
    return [ln.strip() for ln in (reply or "").splitlines() if ln.strip()]


# Letters that do not belong in a verse of that language (Latin is allowed:
# names and loanwords).
FOREIGN = {"th": "[぀-ヿ一-鿿]", "en": "[฀-๿぀-ヿ一-鿿]",
           "ja": "[฀-๿]", "zh": "[฀-๿぀-ヿ]"}


def verse_problem(reply, saved_answers=(), rules=None, lang=""):
    """Why `reply` is not a new verse, or "" when it is one.

    This checks the SHAPE only (lines, length, one script, not a list, not a
    greeting, not a saved answer). Rhyme and meter are not checked: a reply
    that passes is a verse-shaped text, not a proven กลอน.
    """
    comp = (table() if rules is None else rules).get("compose") or {}
    lines = verse_lines(reply)
    want = int(comp.get("minLines") or 4)
    if len(lines) < want:
        return "it gave %d line(s), not a %d-line verse" % (len(lines), want)
    marker = _rx(comp.get("listMarker") or r"^\s*(?:[-*•]|\d+[.)])\s*")
    if marker and sum(1 for ln in lines if marker.match(ln)) >= 2:
        return "it gave a list, not a verse"
    lo, hi = ((comp.get("lineChars") or {}).get(lang) or [0, 10000])[:2]
    short = [ln for ln in lines if not lo <= len(ln) <= hi]
    if short:
        return "a line is %d characters, a verse line here is %d to %d" % (len(short[0]), lo, hi)
    if FOREIGN.get(lang) and re.search(FOREIGN[lang], reply):
        return "it mixed in another language's letters"   # 0.5B wrote 欢迎 in Thai
    first = lines[0].lower()
    for start in comp.get("notVerseStart") or []:
        if start and first.startswith(start.lower()):
            return "it gave a greeting, not a verse"
    flat = re.sub(r"\s+", "", reply)
    for old in saved_answers:
        o = re.sub(r"\s+", "", old or "")
        if len(o) >= 20 and (o in flat or flat in o):
            return "it gave a saved answer again, not a new verse"
    return ""


def compose_text(key, lang, rules=None):
    """prompt / retry / failed text for `lang` (Thai when that one is missing)."""
    said = ((table() if rules is None else rules).get("compose") or {}).get(key) or {}
    return said.get(lang) or said.get("th") or ""


def code_switch(rules=None):
    return (table() if rules is None else rules).get("codeSwitch") or {}
