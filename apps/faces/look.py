"""The rig's own cameras, asked who is standing there (system A13-2).

Brief section 3: an ESP32-CAM board finds people by sending frames to the
face app's POST /api/look, which keeps nothing. The HUB sends, not the board:
their server listens on this PC only, the board takes one stream and four
connections, and the hub already holds that one stream (cam_relay.py). So
this reads the hub's relay of the board and passes the newest frame on.

Nong never turns toward anybody (user 2026-10-09): what a look finds only
tells the watcher who stands in front of which camera. Greeting goes through
the same rules and the same speaking queue as everything else.

THE RULES THE BRIEF SET, each held here:
* one request per camera at a time, at most `perSecond` - the next frame is
  taken only after the answer;
* 429 drops the frame, 503 waits for their model, 401 logs in again;
* an answer that does not say "kept": false STOPS this camera for good -
  their disk filling with frames is what this whole route exists to prevent.
Until their /openapi.json lists /api/look, nothing is sent at all.
"""
import sys
import threading
import time
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
sys.path.insert(0, str(HERE.parent.parent / "main_python"))
import friend_api                                        # noqa: E402
import cam_relay                                         # noqa: E402


def hub_frames(hub, dev):
    """next_frame(seen, timeout) over the hub's live view of board `dev`.

    Joined on the first frame asked for, so a board is not kept streaming
    while their app has no look to send it to."""
    relay = cam_relay.CamRelay(urlparse(hub).netloc or "127.0.0.1:8642",
                               "/api/dev/cam.stream?dev=" + quote(dev, safe=":"))

    def frames(seen, timeout):
        if not relay.viewers:
            relay.join()
        return relay.next_frame(seen, timeout)
    # Let the board rest again while their app has no look (step()).
    frames.rest = lambda: relay.viewers and relay.leave()
    return frames


class Looker:
    """One camera. step() is one round, so a check can drive it frame by frame."""

    def __init__(self, state, camera, frames, per_second=4.0, idle=30.0):
        self.state = state
        self.camera = camera
        self.frames = frames
        self.gap = 1.0 / max(0.1, float(per_second or 4))
        self.idle = idle
        self.stopped = False
        self.status = {"camera": camera, "state": "starting", "why": "",
                       "sent": 0, "at": ""}

    def _say(self, state, why=""):
        self.status.update(state=state, why=why,
                           at=datetime.now().isoformat(timespec="seconds"))

    def step(self, seen):
        """-> (seen, seconds to wait before the next round)."""
        if self.stopped:
            return seen, self.idle
        entry = self.state.entry()
        ok, why = friend_api.offers(entry, "look")
        if not ok:
            # Today's behaviour, unchanged: nothing is sent anywhere.
            getattr(self.frames, "rest", lambda: None)()
            self._say("waiting" if ok is False else "off",
                      why if ok is None else "the face app has no look yet (%s)" % why)
            return seen, self.idle
        seq, jpeg = self.frames(seen, 5.0)
        if jpeg is None:
            self._say("no picture", "camera %s sent nothing through the hub" % self.camera)
            return seen, 1.0
        token, why = self.state.token_now()
        if not token:
            self._say("no login", why)
            return seq, 5.0
        began = time.time()
        got, faces, detail = friend_api.look(entry, token, jpeg, self.camera)
        self.status["sent"] += 1
        if got == "ok":
            self.state.sighting(self.camera, faces, "look")
            self._say("looking", "%d face(s), %s" % (len(faces), detail))
            return seq, max(0.0, self.gap - (time.time() - began))
        if got == "kept":
            self.stopped = True
            getattr(self.frames, "rest", lambda: None)()
            self._say("stopped", "the face app did not promise to keep nothing, so "
                                 "this camera sends no more pictures until the watcher restarts")
            return seq, self.idle
        if got == "login":
            self.state.invalidate_token(token)
            self._say("no login", "the face app refused the login - logging in again")
            return seq, 1.0
        if got == "busy":                     # still on the last one: drop this frame
            return seq, self.gap
        self._say(got, detail)
        return seq, 2.0 if got in ("loading", "off") else self.gap

    def run(self):
        seen = 0
        while True:
            try:
                seen, wait = self.step(seen)
            except Exception as e:                       # noqa: BLE001
                self._say("error", "%s: %s" % (type(e).__name__, e))
                wait = 2.0
            time.sleep(wait)

    def start(self):
        threading.Thread(target=self.run, daemon=True).start()
        return self
