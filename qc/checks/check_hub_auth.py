"""Nothing the hub can DO is reachable without logging in.

The hub binds 0.0.0.0 so a phone on the venue WiFi can reach it. Until this
gate existed, that meant anyone on the venue WiFi could drive the servos or
reflash a board — no password anywhere, on a machine sitting on a network
shared with the public.

This drives the gate from OUTSIDE, with no session, exactly as a stranger on
that network would. It asserts three separate things, because getting any one
of them wrong is its own failure:

  * every route that CHANGES something refuses a caller with no session, and
    the servo-moving GETs are included — the obvious rule "GET is safe" is
    wrong here and would have left the robot open;
  * every route that only READS still works with no session, because someone
    glancing at the hub to see whether a board is alive must not have to type;
  * STOPPING a moving robot is never gated. A password prompt while an arm is
    about to hit someone is a safety failure, not security.

It also checks the secret itself: stored hashed, never echoed back, and a
wrong password gets slower rather than being guessable at leisure.
"""
import json
import urllib.error
import urllib.parse
import urllib.request

import fake_serial
import qc as F

# hub_auth lives beside the hub, which qc.py puts on the path when it starts
# one. Imported after F so that path exists.
import sys                                       # noqa: E402
sys.path.insert(0, str(F.HUB))
import hub_auth                                  # noqa: E402

AREA = "auth"
TITLE = "the hub does nothing for a stranger, but still tells them what it sees"
SLOW = False

# Reached with no session at all. Each carries arguments that would really do
# something if the gate were not there.
MUTATING = [
    ("GET", "/api/usb/cmd?port=COM99&c=" + urllib.parse.quote("POSE 90 90 90 90 90 90 90 90 90 90")),
    ("GET", "/api/robot/cmd?ip=127.0.0.1&c=RELAX"),
    ("GET", "/api/robot/delete?ip=127.0.0.1&path=/moves/show.yaml"),
    ("GET", "/api/usb/close?port=COM99"),
    ("POST", "/api/play"),
    ("POST", "/api/save"),
    ("POST", "/api/settings"),
    ("POST", "/api/rigdefault"),
    ("POST", "/api/export"),
    ("POST", "/api/flash"),
    ("POST", "/api/ota"),
]

READABLE = ["/api/ports", "/api/scan", "/api/mine", "/api/hubs", "/api/servos",
            "/api/apps", "/api/list", "/api/settings", "/api/flash/images",
            "/", "/help", "/mice.css", "/rgb.html"]


def _bare(url, method="GET", data=None):
    """A request with NO session — a stranger on the venue WiFi."""
    req = urllib.request.Request(url, data=data or (b"{}" if method == "POST" else None),
                                 method=method)
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:                       # noqa: BLE001
        return 0, repr(e)


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()
    fake_serial.reset()                          # forget what the login touched

    # ---- a stranger cannot make it do anything ------------------------
    for method, path in MUTATING:
        code, body = _bare(base + path, method)
        t.eq(code, 401, "no session: %s %s is refused" % (method, path.split("?")[0]))
        t.ok("need_login" in body,
             "and says a login is what is missing, not that it broke",
             body[:120])

    # The one that matters most, asserted on the WIRE and not on the reply:
    # a refused command must never have reached the module. A gate that
    # answers 401 after moving the arm has protected nothing.
    # wire is (when, command) pairs — joining the pairs themselves throws,
    # and it only ever worked here because nothing had reached the module.
    wire = " ".join(c for _, c in fake_serial.wire)
    t.ok("POSE" not in wire.upper(),
         "and the refused command never reached the module",
         "the module received: %s" % wire[-120:])

    # ---- but it can still SEE ----------------------------------------
    for path in READABLE:
        code, _ = _bare(base + path)
        t.eq(code, 200, "no session: %s still reads" % path)

    # ---- stopping is never gated -------------------------------------
    code, _ = _bare(base + "/api/play/stop")
    t.eq(code, 200,
         "STOPPING a moving robot needs no password")
    t.ok("/api/play/stop" in hub_auth.NEVER_GATED,
         "and that is written down as deliberate, not left to absence")

    # ---- the secret ---------------------------------------------------
    store = main.AUTH_STORE
    t.ok(store.is_file(), "the password is stored")
    raw = store.read_text(encoding="utf-8")
    t.ok(F.HUB_PASSWORD not in raw,
         "and stored HASHED, never in the clear",
         "people reuse passwords; a stolen file must not hand one over")
    saved = json.loads(raw)
    # Salts moved INSIDE each account when the hub gained users (A1-5). The
    # property is the same and now has to hold for every account, not one.
    accounts = saved.get("users", {})
    t.ok(accounts, "the file holds accounts", saved)
    for name, rec in accounts.items():
        t.ok(len(rec.get("salt", "")) >= 16,
             "%s's password has a salt of its own" % name,
             "one salt shared between accounts means two people with the same "
             "password have the same hash")
    salts = [r.get("salt") for r in accounts.values()]
    t.eq(len(set(salts)), len(salts), "and no two accounts share a salt")

    # whoami never leaks it either
    code, body = _bare(base + "/api/whoami")
    t.eq(code, 200, "anyone may ask whether they are logged in")
    t.ok(F.HUB_PASSWORD not in body, "and the answer does not contain the password")
    t.ok(json.loads(body)["authed"] is False, "a stranger is told they are not")

    # ---- the readable copy is on the PC, and ONLY on the PC ------------
    # The password is written in plain text next to the hash, on purpose: it is
    # printed once at first run and an operator who missed it was locked out of
    # their own robot. That is only acceptable while it stays off the network,
    # so every way a URL could reach it is tried here.
    plain = main.auth().plain_file()
    t.ok(plain.is_file(), "the password is written where a person can read it",
         "a password nobody can look up is a locked door with the key thrown away")
    if plain.is_file():
        t.contains(plain.read_text(encoding="utf-8"), F.HUB_PASSWORD,
                   "and it really is readable")

    for url in ("/hub_password.txt",
                "/hubweb/hub_password.txt",
                "/hubweb/../hub_password.txt",
                "/studio/../../main_python/hub_password.txt",
                "/app/studio/../../../main_python/hub_password.txt",
                "/hub_auth.json",
                "/hubweb/../hub_auth.json"):
        code, body = _bare(base + url)
        t.ok(code != 200 or F.HUB_PASSWORD not in body,
             "the network cannot read it at %s" % url,
             "the hub served the password over HTTP (%s)" % code)

    # ---- a wrong password gets slower, not endless ---------------------
    who = "10.9.9.9"                             # a caller of its own
    a = hub_auth.Auth(store, out=lambda *x: None)
    a.set_password("right")
    for i in range(4):
        tok, why = a.login("wrong", who)
        t.ok(tok is None, "wrong password #%d refused" % (i + 1))
        t.ok("left" in (why or ""), "and says how many tries remain", why)
    tok, why = a.login("wrong", who)
    t.ok(tok is None and "wait" in (why or ""),
         "after five, it locks instead of letting a guesser continue", why)
    t.ok(a.locked_for(who) > 0, "and the lock is real")
    tok, why = a.login("right", who)
    t.ok(tok is None, "even the RIGHT password waits out the lock",
         "otherwise the lock only slows down someone who is already correct")

    # a different caller is unaffected — one bad phone must not lock the room
    tok, why = a.login("right", "10.9.9.10")
    t.ok(tok, "another caller can still log in", why)

    # ---- and the session really opens the gate ------------------------
    a.set_password(F.HUB_PASSWORD)               # put it back for later checks
    F.login(base)
    code, _ = F.get(base + "/api/usb/cmd?port=COM99&c=PING")
    t.eq(code, 200, "logged in, the same call goes through")
