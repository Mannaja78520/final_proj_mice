"""QC framework: what a check is, and the tools every check may use.

A check is one file in `checks/` named `check_*.py` that defines:

    AREA  = "connection"          # which part of the system it guards
    TITLE = "USB cable sharing"
    SLOW  = False                 # True if it drives a real browser (~30 s)

    def run(t):                   # t is a Case
        t.eq(actual, expected, "what this proves")

Nothing registers it — `run_qc.py` finds every `check_*.py` by itself, so
adding a new area of the project to QC is just dropping a file in. See
`qc/README.md`.
"""
import os
import sys
import time
import traceback


class Failure(Exception):
    """A check gave up early (a precondition it needs is missing)."""


class Case:
    """Collects results for one check. Never raises on a failed assertion —
    a check keeps going so one run reports every problem, not just the first."""

    def __init__(self, name):
        self.name = name
        self.results = []          # (ok, label, detail)

    # ---- assertions -------------------------------------------------
    def ok(self, cond, label, detail=""):
        self.results.append((bool(cond), label, "" if cond else str(detail)))
        return bool(cond)

    def eq(self, got, want, label):
        return self.ok(got == want, label, "got %r, want %r" % (got, want))

    def contains(self, hay, needle, label):
        return self.ok(needle in hay, label,
                       "%r not found in %r" % (needle, str(hay)[:300]))

    def under(self, value, limit, label, unit=""):
        return self.ok(value <= limit, label,
                       "%.1f%s exceeds the %.1f%s budget" % (value, unit, limit, unit))

    def give_up(self, why):
        raise Failure(why)

    # ---- reporting --------------------------------------------------
    @property
    def failed(self):
        return [r for r in self.results if not r[0]]

    @property
    def passed(self):
        return [r for r in self.results if r[0]]


# ---------------------------------------------------------------- paths
from pathlib import Path  # noqa: E402

QC = Path(__file__).resolve().parent.parent
CODE = QC.parent
HUB = CODE / "main_python"
STUDIO = CODE / "nong" / "main_python_set_nong"
STUDIO_WEB = STUDIO / "web"
FIRMWARE = CODE / "firmware"
GENERATED = FIRMWARE / "generated"

_generated_done = [False]


def generated(rel=""):
    """A generated firmware header (command table, servo table, module page).

    These are built per ENV now — one binary per module type — so they live in
    the build folder, not in `src/`. `python firmware/tools/gen_tables.py` with
    no arguments writes the all-types set to `firmware/generated/`, which is
    what QC reads: it is the same generator the firmware build runs, so a check
    that passes here is checking what the board really gets.

    Generated once per QC run, on first use.
    """
    if not _generated_done[0]:
        import subprocess
        r = subprocess.run([sys.executable, str(FIRMWARE / "tools" / "gen_tables.py")],
                           capture_output=True, text=True, timeout=120)
        if r.returncode != 0:
            raise Failure("gen_tables.py failed: %s"
                          % ((r.stderr or r.stdout or "").strip()[-300:]))
        _generated_done[0] = True
    return GENERATED / rel if rel else GENERATED


# The registries live in code/tools. Put them on the path HERE, once, so any
# check can `import registry` — otherwise it only works in checks that run
# after one which happened to insert the path, and the suite passes or fails
# depending on the order the files are discovered in.
sys.path.insert(0, str(CODE / "tools"))


# ---------------------------------------------------------------- hub
# Where this run's hubs start. Two staging trees verified at once are two
# processes, and both starting at 8700 meant they fought over ports — or worse,
# one tree's hub answered the other tree's request, which does not fail loudly,
# it silently tests the wrong tree. The pid spreads them out; the range stays
# well clear of the real hub on 8642.
def _free_port():
    """A port the OS says is free, right now.

    It used to be derived from the pid: `8700 + (os.getpid() % 40) * 25`. That
    was fine for two processes and wrong for a pool - Windows hands out pids in
    multiples of 4, so `pid % 40` has only TEN possible values and workers
    collide. A collision here does not fail loudly: one worker's hub answers
    another worker's request, and the check quietly tests the wrong tree.
    Asking the OS removes the guess entirely.
    """
    import socket
    s = socket.socket()
    try:
        s.bind(("127.0.0.1", 0))
        return s.getsockname()[1]
    finally:
        s.close()


_hub_port = [_free_port()]


def start_hub(fake=True):
    """Boot the hub in-process on a free port, with the fake module on COM99.

    Returns (base_url, main_module). Import order matters: the fake `serial`
    has to be in sys.modules BEFORE main.py imports it.
    """
    import threading
    # The hub keeps its password hash in a file. Point it at a throwaway one
    # per run: QC must never read, write or invalidate the real password on
    # this machine, and a check that changed it would lock the user out of
    # their own hub.
    import os
    import tempfile
    os.environ["MICE_HUB_AUTH"] = str(Path(tempfile.gettempdir())
                                      / ("mice_qc_auth_%d.json" % _hub_port[0]))
    if fake:
        sys.path.insert(0, str(QC / "lib"))
        import fake_serial
        fake_serial.install()
    sys.path.insert(0, str(HUB))
    import webbrowser
    webbrowser.open = lambda *a, **k: None      # never pop a browser in QC
    import main
    import socketserver
    main.Handler.log_message = lambda *a, **k: None   # QC output stays readable
    # A browser that navigates away mid-request leaves a half-written response,
    # which the stdlib server dumps as a traceback. Expected here, and it
    # drowns the actual results.
    socketserver.BaseServer.handle_error = lambda *a, **k: None
    _hub_port[0] = _free_port()
    main.PORT = _hub_port[0]
    threading.Thread(target=main.main, daemon=True).start()
    base = "http://127.0.0.1:%d" % main.PORT
    for _ in range(60):                          # wait for the socket
        try:
            get(base + "/api/ports", timeout=2)
            break
        except Exception:
            time.sleep(0.1)
    # Set a known password and LOG IN, exactly the way the page does — the
    # cookie then rides on every later call through get/post/cmd. Checks that
    # assert the gate itself (check_hub_auth) drive it without this session.
    main.auth().set_password(HUB_PASSWORD)
    login(base)
    return base, main


def hub_serial(main, port="COM99"):
    """The live Serial object the hub holds for `port`, or None.

    Lets a check push bytes at the hub the way a real board does — including
    the awkward ones, like a log line that has not finished printing yet.
    """
    ent = main._usb_open.get(port)          # noqa: SLF001 - QC looks inside
    return ent["ser"] if ent else None


# The password QC sets on the throwaway store, and the cookie it gets back.
HUB_PASSWORD = "qc-test-password"
_cookie = [""]


def login(base, password=None):
    """Log in for real and keep the cookie. Returns the Set-Cookie value."""
    import json as _json
    import urllib.request
    req = urllib.request.Request(
        base + "/api/login",
        data=_json.dumps({"password": password or HUB_PASSWORD}).encode(),
        method="POST")
    with urllib.request.urlopen(req, timeout=10) as r:
        _cookie[0] = (r.headers.get("Set-Cookie") or "").split(";")[0]
    return _cookie[0]


def logout_qc():
    """Forget the session — for checks that need to be logged OUT."""
    _cookie[0] = ""


def _with_cookie(req):
    if _cookie[0]:
        req.add_header("Cookie", _cookie[0])
    return req


def get(url, timeout=30):
    """GET -> (status, body). An HTTP error is a result, not an exception:
    checks assert on the status themselves."""
    import urllib.request
    import urllib.error
    try:
        with urllib.request.urlopen(_with_cookie(urllib.request.Request(url)),
                                    timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def raw_get(url, timeout=30):
    """GET without following redirects -> (status, Location or body).

    `get()` uses urlopen, which follows a 302 silently — so a check written
    with it cannot tell "the page is served here" from "the browser was sent
    somewhere else", which is exactly the difference a redirect check is about.
    """
    import urllib.request
    import urllib.error

    class _NoFollow(urllib.request.HTTPRedirectHandler):
        def redirect_request(self, *a, **k):
            return None

    opener = urllib.request.build_opener(_NoFollow)
    try:
        with opener.open(_with_cookie(urllib.request.Request(url)),
                         timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        if e.code in (301, 302, 303, 307, 308):
            return e.code, e.headers.get("Location", "")
        return e.code, e.read().decode(errors="replace")


def post(url, data=b"", timeout=30):
    """POST -> (status, body), same contract as get(): an HTTP error is a
    result the check asserts on, not an exception it has to catch."""
    import urllib.request
    import urllib.error
    req = _with_cookie(urllib.request.Request(url, data=data, method="POST"))
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def cmd(base, c, port="COM99", bus=0, timeout=30):
    """Send one module command the way Nong Studio does."""
    import urllib.parse
    return get("%s/api/usb/cmd?port=%s&id=%d&c=%s"
               % (base, port, bus, urllib.parse.quote(c)), timeout)


# ---------------------------------------------------------------- runner
def run_check(mod):
    """Run one check module, return (Case, seconds, crash-or-None)."""
    t = Case(getattr(mod, "TITLE", mod.__name__))
    t0 = time.time()
    crash = None
    try:
        mod.run(t)
    except Failure as e:
        crash = "gave up: %s" % e
    except Exception:
        crash = traceback.format_exc(limit=6)
    return t, time.time() - t0, crash
