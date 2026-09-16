"""One job at a time means ONE thread doing it — proved on real threads.

Three places could hand one job to two workers:

  * ShowPlayer.stop joins for 3 s, but one serial command can hold longer.
    It then gave up, set thread=None and reported stopped while the old clock
    was still inside dev_cmd — and starting a new show CLEARED THE SHARED
    stop event, which is the very thing that wakes the old thread. Two clocks
    played one arm. Now every run carries its OWN event; an abandoned run
    keeps a set event and dies at its next wake-up instead of coming back.
  * Flasher._claim released the lock before assigning self.thread, so a
    second POST landing in that gap also found nothing running and claimed.
    Claiming and starting now happen under the same lock.
  * dev_download treated any board reply starting with ERR as end-of-file,
    so a mid-read error shipped the bytes collected so far as a complete
    download, 200. A truncated file arrived looking fine.

The ShowPlayer half runs REAL threads against a stubbed dev_cmd that holds
one POSE past stop()'s join window — the shape a busy cable produces on the
bench — and counts what the abandoned clock sends afterwards.
"""
import base64
import re
import threading
import time

import qc as F

AREA = "hub"
TITLE = "a stopped show stays stopped, flashes cannot double-start, downloads are whole"


def _steps(*angles):
    return [{"pose": [a] * 10, "t": 250, "hold": 0} for a in angles]


def test_showplayer(t, main):
    sp = main.ShowPlayer()
    lock = threading.Lock()
    calls = []              # (thread ident, command)
    stuck = []              # ident of the POSE we are holding
    release = threading.Event()

    def fake_dev_cmd(dev, c):
        ident = threading.get_ident()
        with lock:
            calls.append((ident, c))
        # Hold the FIRST pose past stop()'s 3 s join - what a busy cable
        # does without needing one.
        if c.startswith("POSE") and not stuck:
            stuck.append(ident)
            release.wait(8.0)
        return "OK"

    saved = main.dev_cmd
    main.dev_cmd = fake_dev_cmd
    try:
        sp.start("usb:FAKE", _steps(10, 90), name="A")
        deadline = time.time() + 4
        while not stuck and time.time() < deadline:
            time.sleep(0.02)
        if not t.ok(stuck, "show A's first pose went out"):
            return
        st = sp.stop()
        t.ok("finishing" in (st.get("error") or ""),
             "stop admits when it gave up waiting",
             str(st.get("error")))
        t.eq(st["running"], False, "and still reports the show as stopped")

        # A NEW SHOW while A's thread is still stuck inside its command -
        # exactly the sequence that resurrected the old clock.
        sp.start("usb:FAKE", _steps(50, 130, 170), name="B")
        release.set()
        sp.thread.join(5)
        time.sleep(1.0)         # let any zombie wake and hang itself
        with lock:
            poses = [(i, c) for i, c in calls if c.startswith("POSE")]
        mine = stuck[0]
        a_poses = [c for i, c in poses if i == mine]
        t.ok(len(a_poses) == 1,
             "the abandoned clock sent ONE pose and never came back (%d: %s)"
             % (len(a_poses), a_poses[:3]))
        t.ok(sum(1 for i, c in poses if i != mine) >= 2,
             "and the new show really played through")
    finally:
        main.dev_cmd = saved
        release.set()


def test_download(t, main):
    # Exactly one FULL 120-byte chunk (the size FREAD asks for), so the loop
    # goes round again and reaches the error mid-file.
    full = base64.b64encode(bytes(range(120))).decode()
    tail = base64.b64encode(bytes(range(10))).decode()
    replies = {"err": [full, "ERR sd read failed"],
               "ok": [full, tail]}

    saved = main.usb_cmd
    try:
        main.usb_cmd = lambda addr, c, bus=0: replies["err"].pop(0)
        try:
            main.dev_download("usb:FAKE", "/moves/x.yaml")
            t.ok(False, "a mid-file error refuses to ship partial bytes")
        except RuntimeError as e:
            t.ok("stopped" in str(e),
                 "and it says why instead of serving a short file", str(e))

        main.usb_cmd = lambda addr, c, bus=0: replies["ok"].pop(0)
        got = main.dev_download("usb:FAKE", "/moves/x.yaml")
        t.eq(len(got), 130, "a file that really ends comes down whole")
    finally:
        main.usb_cmd = saved


def test_flash_claim(t, main):
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    claim = src[src.find("def _claim"):]
    claim = claim[:claim.find("def status")]
    t.ok("self.thread = threading.Thread" in claim,
         "flashing starts INSIDE the claim lock")
    # No start path may build a thread outside _claim any more.
    outside = [m for m in _claim_sites(src)
               if "threading.Thread" in m.body]
    # t.eq takes no detail - say it in the label or use t.ok.
    t.ok(not outside,
         "no start path builds its own thread any more: %s"
         % ("; ".join(repr(m) for m in outside) or "clean"))


class _Site:
    def __init__(self, body):
        self.body = body

    def __repr__(self):
        head = self.body.strip().splitlines()[0][:70]
        return "call site: %s" % head


def _claim_sites(src):
    """Each `self._claim(...)` call plus the lines up to the thread spawn."""
    sites = []
    i = 0
    while True:
        i = src.find("self._claim(", i + 1)
        if i < 0:
            return sites
        sites.append(_Site(src[i:i + 260]))


def test_one_hub(t):
    # Two hubs on one port used to fight for it silently - whichever bound
    # second served half the requests. Now the new one asks first and opens
    # the running one's page instead of fighting.
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    probe = src.find('http://127.0.0.1:%d/api/version" % PORT')
    bind = src.find("ThreadingHTTPServer((HOST, PORT), Handler)")
    t.ok(0 <= probe < bind,
         "the hub asks whether another hub is up BEFORE it binds the port")
    t.ok(0 < src.find("already running on port", probe) < bind,
         "and hands the visitor to the hub that is already there")


def test_temp_cleanup(t):
    # start_received makes a temp folder before anything can go wrong twice:
    # a bad payload mid-download, and a refused flash slot after it. Each
    # refusal must remove the folder AND re-raise, or the venue PC collects
    # firmware folders and the sender hears silence.
    src = (F.HUB / "main.py").read_text(encoding="utf-8")
    fn = src[src.find("def start_received"):]
    fn = fn[:fn.find("\n    def ")]
    cleans = [m.start() for m in re.finditer(r"shutil\.rmtree\(d", fn)]
    claim = fn.find("self._claim(")
    t.ok(len(cleans) >= 2,
         "the received-image temp folder is cleaned on EVERY refusal")
    t.ok(any(c > claim for c in cleans),
         "...including when the flash slot is refused AFTER the download")
    for c in cleans:
        t.ok("raise" in fn[c:c + 120],
             "each cleanup re-raises so the sender learns why")


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415

    test_showplayer(t, main)
    test_download(t, main)
    test_flash_claim(t, main)
    test_one_hub(t)
    test_temp_cleanup(t)
