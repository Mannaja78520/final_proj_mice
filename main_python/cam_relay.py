"""One connection to a camera, many people watching it.

Asked for 2026-08-21: *now it cannot use 1 cam more than 1 viewer fix that
too*. The second person to open the live view was told *someone is already
watching — one live view at a time*.

WHY THE BOARD IS RIGHT TO REFUSE
--------------------------------
It has ONE frame buffer. PSRAM is deliberately off for the camera build
(platformio.ini records it being measured twice: with PSRAM any large HTTP
response kills the board), so there is no room for a second frame, and
CamModule::take() reclaims whatever frame is out on loan. Two streams would
pull frames out from under each other and both would tear. The limit is not a
bug to remove — it is the hardware, said honestly.

SO THE HUB WATCHES ONCE, AND EVERYONE WATCHES THE HUB
-----------------------------------------------------
This holds a single connection to the board and hands the newest frame to
every viewer. The board sees one watcher however many people are looking, and
nobody is told to wait their turn.

THE TWO FAILURES IT IS BUILT AROUND
-----------------------------------
* A SLOW VIEWER MUST NOT HOLD ANYONE UP. There is no queue per viewer: each
  one is handed whatever frame is current when it is ready for another. A
  phone on bad WiFi therefore drops frames instead of building a backlog that
  costs memory and delays everybody else.
* THE BOARD CAN GO QUIET WITHOUT CLOSING. A module that loses power or WiFi
  mid-frame leaves a socket that is open and silent, and a plain read would
  wait on it forever. A frame that does not arrive within `STALL` seconds ends
  the connection, and the viewers are told rather than left staring at a
  picture that has quietly stopped being now.
"""
import http.client
import re
import subprocess
import sys
import threading
import time

STALL = 8.0          # no frame for this long: the board has gone quiet
IDLE_CLOSE = 2.0     # last viewer left; hold the board briefly for a reload
FRAME_WAIT = 12.0    # a viewer waiting this long with nothing is told so


class CamRelay:
    """The live view of ONE camera, shared. Use `get(address)`."""

    _all = {}
    _all_lock = threading.Lock()

    @classmethod
    def get(cls, addr, **how):
        with cls._all_lock:
            relay = cls._all.get(addr)
            if relay is None:
                relay = cls(addr, **how)
                cls._all[addr] = relay
            return relay

    @classmethod
    def watching(cls):
        """{address: viewers} — what the hub is holding open right now."""
        with cls._all_lock:
            return {a: r.viewers for a, r in cls._all.items() if r.viewers}

    def __init__(self, addr, path="/api/cam.stream"):
        self.addr = addr
        # The face watcher reads the HUB's relay of a board (A13-2), not the
        # board: the board takes one stream, and the hub already holds it.
        self.path = path
        self.cond = threading.Condition()
        self.frame = b""
        self.seq = 0                  # counts frames, so a viewer knows what is new
        self.viewers = 0
        self.error = ""
        self.thread = None

    # ---------------------------------------------------------- viewers
    def join(self):
        with self.cond:
            self.viewers += 1
            self.error = ""
            self.cond.notify_all()        # wake a puller holding on for a reload
            if self.thread is None or not self.thread.is_alive():
                self.thread = threading.Thread(target=self._pull, daemon=True)
                self.thread.start()

    def leave(self):
        with self.cond:
            self.viewers = max(0, self.viewers - 1)
            self.cond.notify_all()

    def next_frame(self, seen, timeout=FRAME_WAIT):
        """The newest frame once it is newer than `seen`.

        -> (seq, jpeg) or (seen, None) when nothing arrived in time. Never a
        backlog: a viewer that was away for ten frames gets the tenth, not the
        first, because the only frame worth showing is the current one.
        """
        end = time.time() + timeout
        with self.cond:
            while self.seq <= seen and not self.error:
                left = end - time.time()
                if left <= 0:
                    return seen, None
                self.cond.wait(min(left, 0.5))
            if self.error:
                return seen, None
            return self.seq, self.frame

    # ------------------------------------------------------------ puller
    def _pull(self):
        """Hold one connection to the board and publish every frame."""
        while True:
            with self.cond:
                if not self.viewers:
                    # Hold on a moment: a browser reload drops the last viewer
                    # and adds one again immediately, and reconnecting to the
                    # board for that costs a visible stall.
                    self.cond.wait(IDLE_CLOSE)
                    if not self.viewers:
                        self.thread = None
                        return
            try:
                self._read_stream()
            except Exception as e:                    # noqa: BLE001
                with self.cond:
                    self.error = "%s: %s" % (type(e).__name__, e)
                    self.cond.notify_all()
                # Do not hammer a board that is down; a viewer still waiting
                # will be told, and a new one starts this loop again.
                time.sleep(1.0)

    def _read_stream(self):
        up = http.client.HTTPConnection(self.addr, timeout=STALL)
        try:
            up.request("GET", self.path)
            r = up.getresponse()
            if r.status != 200:
                raise RuntimeError(
                    r.read().decode(errors="replace")[:150] or
                    ("the camera answered %d" % r.status))
            buf = b""
            idle_since = None
            while True:
                # THE RELOAD GRACE HOLDS THE BOARD, not just the thread. This
                # returned the moment the last viewer left, so _pull's wait
                # below held a closed connection and every reload reconnected;
                # under a loaded QC gate a viewer joining a beat late did too
                # (check_cam_viewers read "opened 2", 2026-10-10).
                with self.cond:
                    if self.viewers:
                        idle_since = None
                    elif idle_since is None:
                        idle_since = time.time()
                    elif time.time() - idle_since > IDLE_CLOSE:
                        return                        # nobody came back; free the board
                # READ1, NOT READ. `read(n)` waits until it has all n bytes,
                # so frames arrived in batches and every viewer saw the live
                # view lurch: measured 1.68 s per frame against a fake sending
                # one every 50 ms, because 4096 bytes took that long to
                # accumulate. read1 hands over whatever has arrived.
                chunk = r.read1(4096)
                if not chunk:
                    raise RuntimeError("the camera stopped sending")
                buf += chunk
                buf = self._take_frames(buf)
                # A part header names the length, so a runaway buffer means the
                # stream is not what it claims to be. Better to reconnect than
                # to grow without limit on a board that is misbehaving.
                if len(buf) > 512 * 1024:
                    raise RuntimeError("the camera sent a frame that never ended")
        finally:
            up.close()

    def _take_frames(self, buf):
        """Publish every complete part in `buf`; return what is left over."""
        while True:
            head_end = buf.find(b"\r\n\r\n")
            if head_end < 0:
                return buf
            head = buf[:head_end].decode(errors="replace")
            length = 0
            for line in head.splitlines():
                if line.lower().startswith("content-length:"):
                    try:
                        length = int(line.split(":", 1)[1].strip())
                    except ValueError:
                        length = 0
            if not length:
                # No length on this part: wait for more rather than guessing
                # where the picture ends.
                return buf
            start = head_end + 4
            if len(buf) < start + length:
                return buf
            self._publish(buf[start:start + length])
            buf = buf[start + length:]

    def _publish(self, jpeg):
        with self.cond:
            self.frame = jpeg
            self.seq += 1
            self.error = ""
            self.cond.notify_all()


# ---------------------------------------------------------------- this PC
# User 2026-10-15: *every camera usable by the other apps too*. Windows lets
# ONE program hold a webcam: with the Voice tab holding it, the face app's
# frames came back black (PC, real camera). So the hub opens it once, like a
# board, and every page watches the hub. Nobody watching = the reader ends =
# the webcam is free again for any other app.

def pc_devices(cfg):
    """This PC's webcams, by name, from the `list` command in
    config/faces.json pcCamera. Virtual ones (cfg `skip`) last."""
    try:
        r = subprocess.run(cfg.get("list") or [], capture_output=True, timeout=10,
                           **_quiet())
        text = (r.stdout + r.stderr).decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError, ValueError):
        return []
    names = list(dict.fromkeys(re.findall(r'"([^"]+)" \(video\)', text)))
    skip = [w.lower() for w in cfg.get("skip") or []]
    return sorted(names, key=lambda n: any(w in n.lower() for w in skip))


def pc_relay(cfg, name=""):
    """(relay, why-not) for this PC's webcam `name` ("" = the first real one)."""
    if not cfg.get("run"):
        return None, "config/faces.json has no pcCamera.run to read this PC's camera with"
    if not name:
        found = pc_devices(cfg)
        if not found:
            return None, "no camera was found on this PC"
        name = found[0]
    run = [str(a).replace("{device}", name) for a in cfg["run"]]
    return PcCamRelay.get("pc:" + name, run=run), ""


def _quiet():
    """No console window flashing up on Windows for each read."""
    return {"creationflags": 0x08000000} if sys.platform == "win32" else {}


class PcCamRelay(CamRelay):
    """This PC's webcam, read by one program (`run`, ffmpeg on the PC) that
    writes JPEG after JPEG. Viewers are handled exactly as for a board."""

    def __init__(self, addr, run=None):
        super().__init__(addr)
        self.run = list(run or [])
        self.got_at = 0.0

    def _read_stream(self):
        proc = subprocess.Popen(self.run, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                stderr=subprocess.DEVNULL, **_quiet())
        self.got_at = time.time()
        # A camera that stops sending leaves the read waiting forever, and
        # nothing else would end the reader: this ends it after STALL.
        stop = threading.Event()

        def watchdog():
            while not stop.wait(1.0):
                if time.time() - self.got_at > STALL:
                    proc.kill()
                    return
        threading.Thread(target=watchdog, daemon=True).start()
        try:
            buf = b""
            idle_since = None
            while True:
                with self.cond:                # the same reload grace as a board
                    if self.viewers:
                        idle_since = None
                    elif idle_since is None:
                        idle_since = time.time()
                    elif time.time() - idle_since > IDLE_CLOSE:
                        return                 # nobody watching: let the webcam go
                chunk = proc.stdout.read1(65536)
                if not chunk:
                    raise RuntimeError("this PC's camera stopped sending - is another "
                                       "app using it, or is it unplugged?")
                buf += chunk
                buf = self._take_jpegs(buf)
                if len(buf) > 4 * 1024 * 1024:
                    raise RuntimeError("the PC camera sent a picture that never ended")
        finally:
            stop.set()
            proc.kill()
            try:
                proc.wait(5)
            except subprocess.TimeoutExpired:
                pass

    def _take_jpegs(self, buf):
        """Publish every whole JPEG (FFD8 ... FFD9) in `buf`; return the rest."""
        while True:
            start = buf.find(b"\xff\xd8")
            if start < 0:
                return b""
            end = buf.find(b"\xff\xd9", start + 2)
            if end < 0:
                return buf[start:]
            self.got_at = time.time()
            self._publish(buf[start:end + 2])
            buf = buf[end + 2:]
