"""ONE login that works on every PC, paired the way a TV is paired (A14-1).

Each PC runs its own hub with its own accounts, so a person with an account on
the studio PC was a stranger on the second one. A sign-in from Google or
Facebook cannot fix that here: OAuth needs internet AT LOGIN TIME, a registered
redirect URL and HTTPS, while this hub is plain HTTP on a LAN address that
changes, at a venue that often has no internet — so on show day nobody could
log in to stop a robot. Decided 2026-08-19; the reasoning is in the plan.

So the accounts are COPIED, once, after a person proves on both machines that
these two PCs belong together: one shows a code, the other types it. What
travels is the salt and the PBKDF2 hash, never a password.

THE FOUR THINGS THAT MAKE THIS SAFE, each asserted below
--------------------------------------------------------
1. /api/pair/claim is the ONE route outside the login, and it has to be — the
   hub asking has no account here yet. The code is the credential, so a wrong
   code must be refused and a spent code must be refused too.
2. Five wrong codes kill THE CODE, not the caller's address. A per-IP lockout
   is the usual answer and it is wrong on a LAN, where an attacker picks a new
   address for free and the code cannot move.
3. The other three pair routes ARE gated. /api/pair/status is a GET and still
   gated: it hands back the code on the screen, which is the only secret in
   the exchange.
4. An import never deletes and never silently overwrites.

THE CASE THAT LOOKED FINE AND WAS NOT
-------------------------------------
Every hub generates the same DEFAULT_USER account on first run, so a clash is
the NORMAL case, not the rare one. Skipping it silently made pairing do
nothing at all when both PCs were new — and the person cannot remove the local
account first, because remove_user refuses the last one. Found by driving it
2026-08-21, before any of this shipped. So a clash is REPORTED, and replacing
is a second, deliberate press that ends every session here.
"""
import json
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import fake_serial
import qc as F

sys.path.insert(0, str(F.HUB))
import hub_auth                                  # noqa: E402
import hub_pair                                  # noqa: E402

AREA = "auth"
TITLE = "one login works on every PC, after a person pairs them with a code"
SLOW = False


def _bare(url, data=None):
    """A POST with NO session — which is how the far hub really arrives."""
    req = urllib.request.Request(url, data=data or b"{}", method="POST",
                                 headers={"Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            return r.status, r.read().decode(errors="replace")
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")
    except Exception as e:                       # noqa: BLE001
        return 0, repr(e)


def _password_in(auth):
    """The generated password, read the way a person at that PC would.

    Through plain_file(), never a fixed name: the file is named after its own
    store since 2026-09-07, so that a QC run cannot write its throwaway
    password over the real hub_password.txt.
    """
    m = re.search(r"user: \S+\s+(\S+)",
                  auth.plain_file().read_text(encoding="utf-8"))
    return m.group(1) if m else ""


def run(t):
    # ---- 1. two hubs, no HTTP: the accounts really move ---------------
    # Separate folders on purpose: hub_password.txt sits beside the store, so
    # two hubs sharing a folder overwrite each other's and the test reads the
    # wrong password while every assertion still passes.
    da, db = (Path(tempfile.mkdtemp(prefix="qc_pair_a_")),
              Path(tempfile.mkdtemp(prefix="qc_pair_b_")))
    a = hub_auth.Auth(da / "a.json", out=lambda *x: None)
    b = hub_auth.Auth(db / "b.json", out=lambda *x: None)
    a.add_user("bob", "bobs-password")
    b.set_password("b-old-password", "super_admin")
    a_default, b_default = "admin123", "b-old-password"

    sent = a.export_accounts()
    t.ok(all("salt" in r and "hash" in r for r in sent.values()),
         "what travels is a salt and a hash",
         "and never a password: people reuse them")
    t.ok(not any(p and p in json.dumps(sent)
                 for p in ("bobs-password", a_default)),
         "no password appears anywhere in what is sent")

    first = b.import_accounts(sent)
    t.eq(first["added"], ["bob"], "the other PC's accounts arrive")
    t.ok(b.login("bobs-password", "1.1.1.1", user="bob")[0] is not None,
         "and that person can log in here with the SAME password",
         "which is the whole point of A14-1")
    t.eq(sorted(first["clashed"]), sorted(["admin", "super_admin"]),
         "a name both PCs already had is REPORTED, not overwritten")
    t.ok(b.login(b_default, "1.1.1.2", user=hub_auth.DEFAULT_USER)[0] is not None,
         "so this PC's own account still works after the first pass",
         "a copy that locks out the person sitting here is worse than no copy")

    # ---- 2. replacing is the second, deliberate press -----------------
    again = b.import_accounts(sent, replace=True)
    t.eq(sorted(again["replaced"]), sorted(["admin", "super_admin"]),
         "asked twice, the clashing account is replaced")
    t.ok(b.login(a_default, "2.1.1.1", user=hub_auth.DEFAULT_USER)[0] is not None,
         "the other PC's password now works for that name too")
    t.ok(b.login(b_default, "2.1.1.2", user=hub_auth.DEFAULT_USER)[0] is None,
         "and the password it replaced does not",
         "a replaced account keeping its old password is a door left open")

    third = b.import_accounts(sent, replace=True)
    t.ok(not third["added"] and not third["replaced"],
         "pairing twice changes nothing the second time",
         "an import that reports work it did not do ends every session for "
         "nothing — replaced accounts log everyone out")

    # ---- 3. junk cannot get in ----------------------------------------
    junk = b.import_accounts({"eve": {"salt": "nothex", "hash": "nothex"},
                              "bad name": {"salt": "00" * 16, "hash": "11" * 32}})
    t.eq(sorted(junk["skipped"]), ["bad name", "eve"],
         "a record that is not a real account is refused")
    t.ok("eve" not in b.users(),
         "and never written",
         "a salt that is not hex raises inside the login and takes it down")

    # ---- 4. the readable file stops lying -----------------------------
    # hub_password.txt says THIS PC's login. After pairing that is no longer
    # the whole truth, and someone reading it to get in would be told about
    # one account out of five.
    b.note_paired("MSI", ["bob"])
    note = b.plain_file().read_text(encoding="utf-8")
    t.contains(note, "MSI", "the password file says which PC was paired with")
    t.contains(note, "bob", "and which accounts came from it")

    # ---- 5. the code itself --------------------------------------------
    p = hub_pair.Pairing()
    code, secs = p.start()
    t.eq(len(code), hub_pair.CODE_LEN, "a code is %d characters"
         % hub_pair.CODE_LEN)
    t.ok(secs <= 600, "and it expires", "seconds=%d" % secs)
    t.ok(not any(c in code for c in "ILOU"),
         "with no I, L, O or U in it",
         "those are the characters people misread carrying a code across a room")
    t.ok(p.claim(hub_pair.pretty(code).lower())[0],
         "typed back in lower case, with the dash, it is accepted",
         "a code that works but looks broken is a support call")
    t.ok(not p.claim(code)[0], "and it is spent — one code, one use")

    p2 = hub_pair.Pairing()
    live, _ = p2.start()
    for _ in range(hub_pair.MAX_TRIES):
        p2.claim("00000000")
    t.ok(not p2.claim(live)[0],
         "%d wrong tries kill the CODE, not the caller's address"
         % hub_pair.MAX_TRIES,
         "an attacker on a LAN picks a new address for free; the code cannot "
         "move, so the code is what must die")

    # ---- 6. the routes, on a live hub ---------------------------------
    fake_serial.reset()
    base, main = F.start_hub()

    for path in ("/api/pair/start", "/api/pair/stop", "/api/pair/link"):
        code_, body = _bare(base + path)
        t.eq(code_, 401, "no session: %s is refused" % path)
        t.ok("need_login" in body, "and says a login is what is missing",
             body[:120])
    t.ok(hub_auth.gated("/api/pair/status", "GET"),
         "/api/pair/status needs a login even as a GET",
         "it hands back the code on the screen, which is the one secret here")

    t.ok("/api/pair/claim" not in hub_auth.GATED,
         "/api/pair/claim is deliberately outside the login",
         "the hub asking has no account here yet — that is what pairing fixes")
    t.eq(sorted(hub_auth.CODE_GATED), ["/api/pair/claim"],
         "and it is the ONLY route proved by something other than a session")

    # A stranger with no code gets nothing, however many times they ask.
    status, body = _bare(base + "/api/pair/claim",
                         json.dumps({"code": "ABCD1234"}).encode())
    t.eq(status, 401, "a code nobody is showing is refused")
    t.ok("salt" not in body and "hash" not in body,
         "and no account leaves the PC",
         "hub answered: " + body[:160])

    # ---- 7. the whole round trip, hub to hub --------------------------
    # Paired with ITSELF over real HTTP, the way check_flash_remote sends
    # firmware to 127.0.0.1: both halves run, no second machine needed.
    live_code = json.loads(F.post(base + "/api/pair/start", b"{}")[1])
    t.ok(live_code.get("showing"), "a hub can show a code",
         json.dumps(live_code)[:160])
    t.contains(live_code.get("code", ""), "-",
               "shown in two halves, which is how a person carries it")

    got = json.loads(F.post(base + "/api/pair/link", json.dumps({
        "ip": "127.0.0.1", "code": live_code["code"]}).encode())[1])
    t.ok(got.get("ok"), "and another hub can spend it",
         json.dumps(got)[:200])
    t.ok(not got.get("added") and not got.get("replaced"),
         "pairing a hub with itself changes nothing",
         "same accounts, same salts — an import that 'replaced' them would "
         "log the operator out for nothing")

    spent = json.loads(F.post(base + "/api/pair/link", json.dumps({
        "ip": "127.0.0.1", "code": live_code["code"]}).encode())[1])
    t.ok(spent.get("ok") is False, "the same code cannot be used again",
         json.dumps(spent)[:200])
