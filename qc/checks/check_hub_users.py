"""The hub has ACCOUNTS, the same shape the module has had for years.

Asked for after a lockout, 2026-08-18: "make like authority have the user and
pass, make can add user like the module". The hub had ONE password. At a venue
that means everybody shares it, and after the show nobody can be removed.

The module's rules are copied on purpose (firmware/src/core/UserStore.h) so the
two never disagree about what a valid account is. Two differences are
deliberate and both are asserted here: the hub HASHES (the module stores in the
clear), and the hub gives every account its own salt.

The part most likely to go wrong is not adding a user — it is MIGRATION. A hub
that already had a password must not be locked out by the upgrade, so the old
single-password file becomes an account and a login that sends no user name
still works. That is driven here against a real file in the old format.
"""
import hashlib
import json
import secrets
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "auth"
TITLE = "the hub has accounts, and an older hub is not locked out by them"
SLOW = False

sys.path.insert(0, str(F.HUB))


def run(t):
    import hub_auth

    # ---- an OLD hub still lets its owner in ---------------------------
    store = Path(tempfile.mktemp(suffix=".json"))
    salt = secrets.token_bytes(16)
    store.write_text(json.dumps({
        "salt": salt.hex(),
        "hash": hashlib.pbkdf2_hmac("sha256", b"old-password", salt,
                                    hub_auth._ITERATIONS).hex(),   # noqa: SLF001
        "set_at": "2026-08-18 18:35"}), encoding="utf-8")
    try:
        a = hub_auth.Auth(store, out=lambda *x: None)
        t.ok(a.login("old-password", "1.1.1.1")[0] is not None,
             "a hub that already had a password still logs in after the upgrade",
             "locking the owner out of their own hub on an upgrade is worse "
             "than having one account")
        t.eq(a.users(), [hub_auth.DEFAULT_USER],
             "its password became one named account")

        # ---- adding someone -------------------------------------------
        ok, why = a.add_user("bob", "bobs-password")
        t.ok(ok, "another person can be added", why)
        t.ok(a.login("bobs-password", "2.2.2.2", user="bob")[0] is not None,
             "and can log in with their own name")

        # ---- the rules the module also enforces ------------------------
        t.ok(not a.add_user("eve", "short")[0],
             "a password under %d characters is refused" % hub_auth.PASS_MIN)
        t.ok(not a.add_user("bob", "another-password")[0],
             "a name that already exists is refused")
        t.ok(not a.add_user("bad name", "long-enough-pass")[0],
             "a name with a space is refused")

        # ---- and the one that stops a dead hub -------------------------
        t.ok(a.remove_user("bob")[0], "someone can be removed")
        ok, why = a.remove_user(hub_auth.DEFAULT_USER)
        t.ok(not ok, "but never the last account",
             "a hub nobody can log into can only be fixed by deleting its "
             "password file on the PC — at a venue that is a dead hub")
        t.contains(why or "", "only account", "and it says why")

        # ---- a wrong NAME must look like a wrong password --------------
        # Different wording is how a stranger learns which names are real.
        bad_name = a.login("bobs-password", "3.3.3.3", user="nobody")[1]
        bad_pass = a.login("wrong-password", "4.4.4.4",
                           user=hub_auth.DEFAULT_USER)[1]
        t.eq(bad_name, bad_pass,
             "a wrong user and a wrong password give the SAME answer")

        # ---- nothing is stored in the clear ---------------------------
        raw = store.read_text(encoding="utf-8")
        t.ok("old-password" not in raw and "bobs-password" not in raw,
             "no password is written to the file",
             "people reuse passwords; a stolen file must not hand one over")
        accounts = json.loads(raw).get("users", {})
        salts = [r.get("salt") for r in accounts.values()]
        t.eq(len(set(salts)), len(salts),
             "and every account has its own salt")
    finally:
        store.unlink(missing_ok=True)
        store.with_name("hub_password.txt").unlink(missing_ok=True)

    # ---- the routes are gated ----------------------------------------
    # Deciding who may drive the robots is not something a stranger does.
    for route in ("/api/users/add", "/api/users/remove"):
        t.ok(hub_auth.gated(route, "POST"),
             "%s needs a login" % route)
