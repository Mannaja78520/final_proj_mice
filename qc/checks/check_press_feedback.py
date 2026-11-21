"""A press that has nothing to show still answers, and a dropped friend feed says so in plain words.

Found 2026-11-21 by walking every hub page as a stranger: TV Refresh and Talk looked dead
without a service, and the faces page said only "not seeing anybody" when the friend's
feed had dropped (service state live=false), which reads like nobody is there.
"""
import qc as F

AREA = "web"
TITLE = "Talk, TV Refresh and a dropped face feed give the person a plain answer"
SLOW = False


def run(t):
    rd = lambda p: (F.CODE / p).read_text(encoding="utf-8", errors="replace")
    tv, voice, faces = rd("apps/tv/index.html"), rd("apps/voice/app.js"), rd("apps/faces/index.html")
    t.ok('"Refreshing…"' in tv and "Updated " in tv and "Could not reach the hub" in tv,
         "TV Refresh says refreshing, then when it updated or that the hub did not answer", "")
    t.ok('"opening the microphone…"' in voice.split("async talk()")[1][:400],
         "Talk answers at once, before the browser asks for the microphone", "")
    t.ok("state.live === false" in faces and "reconnecting by itself" in faces,
         "a dropped face feed says it is reconnecting and what to check", "")
