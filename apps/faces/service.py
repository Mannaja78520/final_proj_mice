#!/usr/bin/env python3
"""The watcher: reads who an outside app recognised, and says what it can see.

Run it beside the hub:

    python apps/faces/service.py

WHY THIS IS A SEPARATE PROGRAM, AND NOT PART OF THE HUB

The hub is one stdlib program frozen into MiceHub.exe. This is the piece that
has to keep up with an app that updates about every day, so it must be able to
change without a rebuild. It will also hold a login for that app, and a login
belongs beside the process that uses it. `apps/voice/service.py` is the same
shape and the same reason.

LOOPBACK ONLY, AND IT REFUSES ANYTHING ELSE

The voice helper warns when it is shared beyond this PC. This one refuses.
The difference is what it holds: a login for an outside app, and - once the
later steps land - the ability to make the rig move and speak. Anything that
could reach this port could do both without a password. Remote callers come
through the hub, where the login gate already is.

WHAT IT DOES TODAY

Nothing moves. It answers /health and /state and says plainly that it is not
watching anybody yet. Logging in, reading their history and the live feed are
the next steps (system A3-2 onward in docs/system_integral.html). Shipping the
skeleton first means there is somewhere honest to look before there is anything
to look at.
"""
import argparse
import base64
import json
import os
import sys
import threading
import time
import urllib.error
import urllib.request

from collections import OrderedDict
from datetime import datetime, timedelta
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlparse

sys.path.insert(0, str(Path(__file__).resolve().parent))
import wsclient                                          # noqa: E402

HERE = Path(__file__).resolve().parent
# The tree this copy belongs to. A working copy runs its own copy of this file
# and reads the config beside it, which is what lets QC boot the real thing.
CODE = HERE.parent.parent

STARTED = time.time()
LOOPBACK = ("127.0.0.1", "localhost", "::1")

# THE LOGIN LIVES HERE, AND NOWHERE NEAR apps/.
# Every file in an app folder is served by the hub with NO login at all, so a
# credentials file under apps/faces/ would be handed to anyone on the venue
# WiFi who asked for it. A plan review caught that placement before it shipped.
# This sits beside hub_auth.json instead: out of the served tree, out of
# promotion (promote.py SKIP_FILES) and out of the exe.
LOGIN_FILE = "main_python/faces_login.json"

# Ask for a new token this long before the old one dies, so a greeting is
# never the thing that discovers the session expired.
RENEW_MARGIN = 300


def _jwt_expiry(token):
    """When this token dies, read from the token itself.

    Their lifetime is an ENVIRONMENT SETTING - `JWT_EXPIRE_MINUTES`, default
    480 (their backend/app/config.py:96) - so hardcoding eight hours is a
    guess that is wrong on any machine where somebody changed it. The payload
    carries `exp`; read that instead.

    The signature is deliberately NOT checked. We are not validating their
    token - only asking when to go and get another one.
    """
    try:
        payload = token.split(".")[1]
        payload += "=" * (-len(payload) % 4)
        got = json.loads(base64.urlsafe_b64decode(payload).decode("utf-8"))
        return float(got.get("exp") or 0)
    except Exception:                                        # noqa: BLE001
        return 0.0


def _when(text):
    """Their `detected_at`, as a datetime.

    It is written with `datetime.now()` (their models/models.py:64), so it is
    LOCAL time with no timezone on it. Compare it with our own local clock -
    treating it as UTC would shift every arrival by the machine's offset and
    silently empty the window this poll depends on.
    """
    try:
        return datetime.fromisoformat(str(text).replace("Z", ""))
    except Exception:                                        # noqa: BLE001
        return None


def load(rel, default=None):
    """A config file, or a default. A broken file is reported, never fatal."""
    path = CODE / rel
    try:
        sys.path.insert(0, str(CODE / "tools"))
        import registry
        return registry.load(path), ""
    except Exception as e:                                   # noqa: BLE001
        return (default if default is not None else {}), "%s: %s" % (rel, e)


class State:
    """What the watcher knows. Today: which partner it would watch, and that
    it is not watching. Every later step adds to this rather than to a
    screen, so one place answers *what does the rig think is happening*."""

    def __init__(self, partner):
        self._events_lock = threading.RLock()
        self._auth_lock = threading.RLock()
        self.partner_id = partner
        self.partners, self.partners_error = load("config/partners.json")
        self.watching = False
        self.last_error = ""
        self.token = ""
        self.token_dies = 0.0
        self.login_error = ""
        # The cursor. `seen` is what decides what is new; `checkpoint` only
        # decides how far back to look. See poll_once for why it is that way
        # round and not the other.
        self.seen = OrderedDict()
        # person key -> the arrival we already reported, for accept()
        self.recent = OrderedDict()
        self.checkpoint = None
        self.people = []
        self.poll_error = ""
        self.polls = 0
        self.live = False
        self.live_error = ""

    def partner(self):
        return (self.partners or {}).get(self.partner_id) or {}

    # ---- logging in to the outside app -------------------------------

    def credentials(self):
        """(who, why-not). A missing login is normal on a fresh machine, so
        the answer says exactly what to write and where."""
        # MICE_FACES_LOGIN points this at a throwaway file, the same way
        # MICE_HUB_AUTH does for the hub password: QC must never read, write
        # or overwrite the real credentials on somebody's machine.
        path = Path(os.environ.get("MICE_FACES_LOGIN") or (CODE / LOGIN_FILE))
        if not path.is_file():
            return None, (
                "no login yet: write %s as "
                '{"%s": {"username": "...", "password": "..."}}. '
                "Never put it under apps/ - every file there is served with "
                "no login at all." % (LOGIN_FILE, self.partner_id))
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
        except Exception as e:                               # noqa: BLE001
            return None, "%s could not be read (%s)" % (LOGIN_FILE, e)
        who = data.get(self.partner_id) or {}
        if not who.get("username") or not who.get("password"):
            return None, ("%s has no username and password for %r"
                          % (LOGIN_FILE, self.partner_id))
        return who, ""

    def token_now(self):
        with self._auth_lock:
            return self._token_now()

    def _token_now(self):
        """A usable token, fetching a new one before the old one runs out."""
        if self.token and time.time() < self.token_dies - RENEW_MARGIN:
            return self.token, ""
        return self.login()

    def login(self):
        with self._auth_lock:
            return self._login()

    def _login(self):
        who, why = self.credentials()
        if not who:
            self.token, self.login_error = "", why
            return "", why
        p = self.partner()
        name = p.get("name") or self.partner_id
        cfg = p.get("login") or {}
        url = (p.get("api") or "").rstrip("/") + (cfg.get("path")
                                                  or "/api/auth/login")
        body = json.dumps({"username": who["username"],
                           "password": who["password"]}).encode("utf-8")
        req = urllib.request.Request(
            url, data=body, headers={"Content-Type": "application/json"})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                got = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            # Their own words are the useful half here: 401 means the password
            # is wrong, and saying so beats saying the request failed.
            self.token = ""
            self.login_error = ("%s refused the login (%s). Check the user "
                                "and password in %s." % (name, e.code, LOGIN_FILE))
            return "", self.login_error
        except Exception as e:                               # noqa: BLE001
            self.token = ""
            self.login_error = ("%s is not answering at %s (%s). Start it "
                                "first, and give it about fifteen seconds to "
                                "load its face model." % (name, url, e))
            return "", self.login_error

        tok = got.get("access_token") or ""
        if not tok:
            self.token = ""
            self.login_error = ("%s answered the login without a token - the "
                                "shape of its answer has changed" % name)
            return "", self.login_error

        self.token = tok
        # Their setting, our fallback: read the token's own `exp` and only
        # fall back to the number in the registry when it has none.
        exp = _jwt_expiry(tok)
        self.token_dies = exp or (time.time()
                                  + float(cfg.get("expires_min") or 480) * 60)
        self.login_error = ""
        return tok, ""

    # ---- one person, seen twice, is one arrival ----------------------

    def invalidate_token(self, rejected):
        """An old request must not erase a newer login."""
        with self._auth_lock:
            if self.token == rejected:
                self.token = ""

    def real_camera(self, camera):
        """Is this a PLACE, or only a label?

        Their kiosk publishes with `node_id` set to the literal string
        "kiosk" (their api/recognition.py:139-145), and their own comment
        above it says the kiosk never registers itself as a node - it is a
        tag, not a station. A greeting placed at it would put somebody at a
        door that does not exist.

        Which labels are not places is DATA: the next one will not be called
        kiosk, and finding out should cost one entry in the registry.
        """
        if not camera:
            return False
        return camera not in (self.partner().get("notACamera") or [])

    def accept(self, event):
        with self._events_lock:
            return self._accept(event)

    def _accept(self, event):
        """The one door every source passes through.

        Returns (event_or_None, was_duplicate).

        THEIR APP PUBLISHES THE SAME MATCH TWICE. A central-inference match
        goes out under the real camera (their api/nodes.py:332-338), and the
        background persistence publishes it again with `node_id` set to the
        literal string `"kiosk"` (their api/recognition.py:139-145). Greeting
        somebody twice, or naming the wrong door, are both worse than being a
        second late, so the two copies are merged and the one that knows a
        real camera wins.

        A STRANGER IS NEVER MERGED. An unknown face has no identity at all -
        no participant id and no name - so merging on timing alone would fold
        two different strangers into one person. `known` is what decides,
        because an id on a face nobody recognised identifies nobody.
        """
        # Normalise first: no source gets to DECLARE that it knows a place.
        event["hasCamera"] = self.real_camera(event.get("camera"))

        key = event.get("id") or event.get("who") or ""
        if not event.get("known") or not key:
            return event, False

        window = float(self.partner().get("dedupeSeconds") or 20)
        now = _when(event.get("when")) or datetime.now()
        old = self.recent.get(key)
        if old and abs((now - old["when"]).total_seconds()) <= window:
            if event.get("hasCamera") and not old["event"].get("hasCamera"):
                # Same arrival, better information. The stored event is the
                # same object `people` holds, so improving it here shows up
                # on the screen without reporting the person again.
                old["event"]["camera"] = event.get("camera")
                old["event"]["hasCamera"] = True
                old["event"]["source"] = event.get("source")
            return None, True

        self.recent[key] = {"when": now, "event": event}
        while len(self.recent) > 500:
            self.recent.popitem(last=False)
        return event, False

    # ---- their live feed ---------------------------------------------

    def ws_source(self):
        for s in (self.partner().get("events") or []):
            if s.get("kind") == "ws":
                return s
        return None

    def from_ws(self, src, raw):
        """One of their live frames, in our shape.

        Every field name comes from the registry's `map`, never from here:
        when their payload changes, that is one line in config/partners.json.
        """
        m = src.get("map") or {}
        who = raw.get(m.get("who") or "name") or ""
        return {
            "who": who,
            "id": raw.get(m.get("id") or "participant_id") or "",
            # Their feed publishes ONLY matched faces (api/nodes.py:331 and
            # api/recognition.py:130), so anything arriving here is known.
            "known": True,
            "status": "matched",
            "when": str(raw.get(m.get("when") or "at") or ""),
            "camera": str(raw.get(m.get("camera") or "node_id") or ""),
            # accept() decides this: a camera field can hold a label that is
            # not a place, and no source gets to declare otherwise.
            "hasCamera": False,
            "repeat": raw.get(m.get("repeat") or "checkin") or "",
            "source": "ws",
        }

    def note(self, event):
        with self._events_lock:
            return self._note(event)

    def _note(self, event):
        """One arrival from any source, through the same door as the poll."""
        kept, dup = self.accept(event)
        if kept is not None and not dup:
            self.people = ([kept] + self.people)[:200]
        return kept

    # ---- reading their history ---------------------------------------

    def poll_source(self):
        for s in (self.partner().get("events") or []):
            if s.get("kind") == "poll":
                return s
        return None

    def _fetch(self, src, token, page):
        p = self.partner()
        path = (src.get("path") or "").replace("{page}", str(page))
        url = (p.get("api") or "").rstrip("/") + path
        req = urllib.request.Request(
            url, headers={"Authorization": "Bearer " + token})
        try:
            with urllib.request.urlopen(req, timeout=10) as r:
                got = json.loads(r.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            if e.code == 401:
                # The session ended under us. Say so plainly; the next poll
                # logs in again rather than looping on a dead token.
                self.invalidate_token(token)
                return [], "the session ended - logging in again next time"
            return [], "their history refused page %d (%s)" % (page, e.code)
        except Exception as e:                               # noqa: BLE001
            return [], "their history is not answering (%s)" % e
        items = got.get(src.get("items") or "items")
        return (items if isinstance(items, list) else []), ""

    def poll_once(self, max_pages=20):
        """Read their history and return only the rows we had not seen.

        THREE THINGS MAKE THIS MORE THAN ONE GET, and each was paid for by
        reading their code rather than guessing:

        * Their history is NEWEST FIRST and pages from 1
          (their api/history.py:30,68). A burst of arrivals spreads over
          pages, so stopping at page one drops the older half of a rush -
          which is exactly the moment it matters.

        * `detected_at` is stamped when the row is BUILT, not when it commits
          (their models/models.py:64). A row can therefore appear carrying a
          time OLDER than one already read. A cursor that trusts the newest
          time it has seen would step straight over that person. So the
          checkpoint only decides how far back to look, and the window
          reaches `lagSeconds` behind it.

        * The window means rows come back more than once, so a SEEN-SET of
          row ids decides what is actually new. Their ids are random
          (`new_id()`), so a range would mean nothing - only the set works.
        """
        # These two early exits must record the reason like any other. They
        # did not, and the caller reads `poll_error` to decide whether it is
        # watching - so with no login at all the watcher reported itself as
        # watching, which is the one thing this whole helper exists to be
        # honest about. Caught by check_faces_loopback, 2026-09-10.
        src = self.poll_source()
        if not src:
            self.poll_error = "this app has no history to read"
            return [], self.poll_error
        token, why = self.token_now()
        if not token:
            self.poll_error = why
            return [], why

        mapping = src.get("map") or {}
        k_when = mapping.get("when") or "detected_at"
        k_row = mapping.get("row") or "id"
        k_who = mapping.get("who") or "name"
        k_id = mapping.get("id") or "participant_id"
        k_status = mapping.get("status") or "status"
        lag = float(src.get("lagSeconds") or 120)
        floor = (self.checkpoint - timedelta(seconds=lag)
                 if self.checkpoint else None)

        fresh, newest, why = [], self.checkpoint, ""
        for page in range(1, max_pages + 1):
            rows, why = self._fetch(src, token, page)
            if why or not rows:
                break
            older_than_window = False
            for row in rows:
                when = _when(row.get(k_when))
                if floor and when and when < floor:
                    # Newest first, so everything below this is older too.
                    older_than_window = True
                    continue
                rid = row.get(k_row)
                if rid is None or rid in self.seen:
                    continue
                self.seen[rid] = time.time()
                who = row.get(k_who) or ""
                event = {
                    "who": who,
                    "id": row.get(k_id) or "",
                    "known": bool(who),
                    "status": row.get(k_status) or "",
                    "when": when.isoformat() if when else "",
                    # HISTORY ROWS CARRY NO CAMERA. Their row is built at
                    # api/history.py:71-84 and has no node_id in it, so this
                    # can be counted and must never be read as somebody
                    # standing at a particular door.
                    "camera": "",
                    "hasCamera": False,
                    "source": "poll",
                }
                kept, _dup = self.accept(event)
                if kept is not None:
                    fresh.append(kept)
                if when and (newest is None or when > newest):
                    newest = when
            if older_than_window:
                break

        self.polls += 1
        self.poll_error = why
        if newest:
            self.checkpoint = newest
        # Keep the seen-set bounded: it exists to drop repeats inside the
        # window, so anything far older than the window is dead weight.
        while len(self.seen) > 4000:
            self.seen.popitem(last=False)
        if fresh:
            with self._events_lock:
                self.people = (fresh + self.people)[:200]
        return fresh, why

    def health(self):
        p = self.partner()
        return {
            "ok": True,
            "watching": self.watching,
            "partner": self.partner_id,
            "partnerKnown": bool(p),
            "seenPeople": len(self.people),
            "polls": self.polls,
            "pollError": self.poll_error,
            "upSeconds": round(time.time() - STARTED, 1),
            # Whether we are logged in, and how long that lasts - never the
            # token and never the password. This answer is read by a page.
            "loggedIn": bool(self.token),
            "tokenExpiresIn": (max(0, round(self.token_dies - time.time()))
                               if self.token else 0),
            "loginError": self.login_error,
            "live": self.live,
            "liveError": self.live_error,
            # Say what is wrong in the same answer, rather than leaving a
            # screen to guess from a healthy-looking silence.
            "error": self.partners_error or self.last_error or "",
        }

    def snapshot(self):
        with self._events_lock:
            return self._snapshot()

    def _snapshot(self):
        p = self.partner()
        return {
            "ok": True,
            "watching": self.watching,
            "partner": self.partner_id,
            "name": p.get("name") or self.partner_id,
            # WHAT EACH SOURCE CAN AND CANNOT REPORT, copied from the registry
            # rather than restated here. A screen that shows this cannot
            # promise the rig sees strangers when the only live source is
            # known-faces-only.
            "sources": [
                {"kind": s.get("kind"), "reports": s.get("reports") or [],
                 "hasCamera": bool(s.get("hasCamera"))}
                for s in (p.get("events") or [])
            ],
            "people": [dict(event) for event in self.people],
            "polls": self.polls,
            "live": self.live,
            "liveError": self.live_error,
            "since": self.checkpoint.isoformat() if self.checkpoint else "",
            "pollError": self.poll_error,
            "error": self.partners_error or self.last_error or "",
        }


class Handler(BaseHTTPRequestHandler):
    state = None

    def _json(self, body, code=200):
        raw = json.dumps(body).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_GET(self):                                        # noqa: N802
        path = urlparse(self.path).path
        if path == "/health":
            return self._json(self.state.health())
        if path == "/state":
            return self._json(self.state.snapshot())
        return self._json({"ok": False, "error": "no such address: %s" % path,
                           "try": ["/health", "/state"]}, 404)

    def log_message(self, *a):
        """Quiet by default: this is polled, and a line per poll buries the
        one message that matters."""


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--partner", default="reconize",
                    help="which entry in config/partners.json to watch")
    ap.add_argument("--port", type=int, help="override the configured port")
    ap.add_argument("--interval", type=float, default=3.0,
                    help="seconds between reads of their history")
    ap.add_argument("--catchup", type=float, default=30.0,
                    help="seconds between reads while the live feed is up - the poll is only filling gaps then")
    a = ap.parse_args(argv)

    cfg, why = load("config/faces.json", {})
    if why:
        print("[faces] %s" % why)
    svc = (cfg or {}).get("service") or "http://127.0.0.1:8769"
    u = urlparse(svc)
    host = u.hostname or "127.0.0.1"
    port = a.port or u.port or 8769

    # THE REFUSAL, not a warning. This process holds a login for an outside
    # app and can reach the hub; a port open to the venue WiFi is a way to
    # move the robot without a password.
    if host not in LOOPBACK:
        print("[faces] REFUSING to answer on %s." % host)
        print("[faces] This helper holds a login and can drive the rig, so it")
        print("[faces] listens only on this PC. Callers from anywhere else go")
        print("[faces] through the hub, which asks for a password first.")
        print("[faces] Fix config/faces.json: service must be 127.0.0.1.")
        return 2

    state = State(a.partner)
    Handler.state = state
    if state.partners_error:
        print("[faces] %s" % state.partners_error)
    elif not state.partner():
        print("[faces] config/partners.json has no entry called %r - add one "
              "and this helper watches it, with no code change." % a.partner)

    # Try once at startup so /health is meaningful immediately. A failure here
    # is normal and never fatal: the app may simply not be running yet.
    _tok, why = state.token_now()
    print("[faces] %s" % (why or "logged in to %s"
                          % (state.partner().get("name") or a.partner)))

    # The poll runs on its own thread so a slow or stopped app never holds up
    # an answer to /health - the one thing a person checks when it looks stuck.
    def watch():
        while True:
            try:
                state.poll_once()
                state.watching = not state.poll_error
            except Exception as e:                           # noqa: BLE001
                state.poll_error = "the poll stopped with %s" % e
                state.watching = False
            # DEMOTED WHILE THE LIVE FEED IS UP. The poll is then only there
            # to collect what the feed cannot carry - their feed publishes no
            # strangers at all - so hammering their history every three
            # seconds buys nothing and costs them a query each time.
            time.sleep(max(1.0, a.catchup if state.live else a.interval))

    def live_feed():
        """Their push channel, with a reconnect that backs off.

        Kept in its own thread because a feed that goes quiet must never hold
        up an answer to /health - that is the one thing somebody checks when
        it looks stuck.
        """
        src = state.ws_source()
        if not src:
            state.live_error = "this app has no live feed to listen to"
            return
        wait = 1.0
        while True:
            feed = None
            try:
                token, why = state.token_now()
                if not token:
                    raise wsclient.FeedClosed(why)
                url = wsclient.ws_url(state.partner().get("api") or "",
                                      src.get("path") or "", token)
                feed = wsclient.connect(url)
                state.live, state.live_error = True, ""
                connected_at = time.monotonic()
                for msg in feed.messages(idle_timeout=30):
                    if time.monotonic() - connected_at >= 30:
                        wait = 1.0
                    if msg:
                        state.note(state.from_ws(src, msg))
            except wsclient.FeedClosed as e:
                # THEIR REFUSAL IS NOT A NETWORK PROBLEM. A token the feed
                # will not take comes back as close 4401, or as a 403 on the
                # handshake because they close before upgrading
                # (their api/nodes.py:486). Either way the answer is a new
                # login, not a faster retry.
                said = str(e)
                if getattr(e, "code", 0) == wsclient.CLOSE_BAD_TOKEN \
                        or "403" in said or "401" in said:
                    state.invalidate_token(token)
                    said = "the live feed refused the login - getting a new one"
                state.live, state.live_error = False, said
            except Exception as e:                           # noqa: BLE001
                state.live = False
                state.live_error = "the live feed dropped (%s)" % e
            finally:
                if feed is not None:
                    feed.close()
            time.sleep(wait)
            wait = min(30.0, wait * 2)

    threading.Thread(target=watch, daemon=True).start()
    threading.Thread(target=live_feed, daemon=True).start()

    httpd = ThreadingHTTPServer((host, port), Handler)
    print("[faces] answering on http://%s:%d  (/health, /state)" % (host, port))
    print("[faces] reading their history every %ss - nothing moves yet"
          % a.interval)
    print("[faces] Ctrl+C to stop")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[faces] stopped")
    return 0


if __name__ == "__main__":
    sys.exit(main())
