"""Which language a line is written in, from its letters (moved out of service.py 2026-11-21)."""


def scripts_in(text):
    """Which writing systems one line really holds, e.g. {"th", "en"}.

    detect_lang answers "which ONE language is this", which is the wrong
    question for a sentence like *Hello พุฒิพงศ์, welcome*: it is two, and a
    voice tied to either one drops the other half (user 2026-09-18: *make TTS
    can read all lang in the same time*).

    The ranges are the whole script, not only its common block: half-width
    katakana, CJK extension A, Arabic presentation forms, Vietnamese letters
    and full-width Latin all count (apps/voice/app.js askLang mirrors them).
    """
    ranges = (
        ("th", ((0x0E00, 0x0E7F),)),
        ("ko", ((0xAC00, 0xD7AF), (0x1100, 0x11FF), (0x3130, 0x318F), (0xA960, 0xA97F),
                (0xD7B0, 0xD7FF), (0xFFA0, 0xFFDC))),
        ("ja", ((0x3040, 0x309F), (0x30A0, 0x30FF), (0x31F0, 0x31FF), (0xFF66, 0xFF9F))),
        ("zh", ((0x4E00, 0x9FFF), (0x3400, 0x4DBF), (0xF900, 0xFAFF), (0x20000, 0x3134F))),
        ("ru", ((0x0400, 0x052F), (0x2DE0, 0x2DFF), (0xA640, 0xA69F))),
        ("ar", ((0x0600, 0x06FF), (0x0750, 0x077F), (0x08A0, 0x08FF), (0xFB50, 0xFDFF),
                (0xFE70, 0xFEFF))),
        ("hi", ((0x0900, 0x097F), (0xA8E0, 0xA8FF))),
        ("en", ((0x41, 0x5A), (0x61, 0x7A), (0x00C0, 0x024F), (0x1E00, 0x1EFF),
                (0xFF21, 0xFF3A), (0xFF41, 0xFF5A))),
    )
    found = set()
    for ch in text or "":
        cp = ord(ch)
        if cp == 0xD7 or cp == 0xF7:          # × and ÷ sit inside Latin-1
            continue
        for lang, spans in ranges:
            if any(a <= cp <= b for a, b in spans):
                found.add(lang)
                break
    return found


def detect_lang(text):
    """Detect 'th', 'ko', 'ja', 'zh', 'ru', 'ar', 'hi', or 'en' from the letters.

    One script per language family, so a script tells which column, not which
    exact language: Ukrainian reads as ru, Persian/Urdu as ar, Marathi/Nepali
    as hi, and French, German, Spanish or Vietnamese as en (same alphabet).
    Kanji with no kana is zh. Nothing readable (digits, emoji, "") is th, the
    robot's home language, as before.
    """
    found = scripts_in(text)
    for lang in ("th", "ko", "ja", "zh", "ru", "ar", "hi", "en"):
        if lang in found:
            return lang
    return "th"
