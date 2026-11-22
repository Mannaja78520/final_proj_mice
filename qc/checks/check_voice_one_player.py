"""Voice page: one voice at a time, never stuck on "saying…" (user 2026-11-22).

Sound bugs hunted in apps/voice/app.js speak(): a second Try or answer layered
a second voice over the first; a helper that never answered left "saying…"
for ever (no fetch limit); a decode error after play() started left the
speaking card on screen; a closed page's audio kept playing.
The limit uses AbortController, because AbortSignal.timeout does not exist in
the Chrome 75 of the Android TV.
"""
import qc as F

AREA = "tools"
TITLE = "Voice speak(): older voice stopped first, request gives up, errors reset the card"


def run(t):
    s = (F.CODE / "apps/voice/app.js").read_text(encoding="utf-8", errors="replace")
    i = s.find("async speak(text, lang, try_ = null)")
    if not t.ok(i >= 0, "speak() found"):
        return
    body = s[i:i + 4200]
    t.contains(body, "this.stopOwnVoice()", "the previous voice is stopped before a new one starts")
    t.contains(body, "new AbortController()", "the request has a time limit")
    t.contains(body, "setTimeout(() => giveUp.abort()", "...which aborts a helper that never answers")
    t.contains(body, "player.onerror", "a playback error resets the speaking card")
    t.ok("AbortSignal.timeout(" not in s, "no AbortSignal.timeout (missing in Chrome 75)")
    t.contains(s, 'addEventListener("pagehide", () => this.stopOwnVoice())',
               "a closed page stops its voice")
