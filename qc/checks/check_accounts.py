"""Accounts: shipped defaults marked, own account self-service, super_admin runs the rest.

Asked 2026-09-17: *super_admin: admin123, admin: admin123, but mark it so this
is the default user and pass please change ... each user can change it own
pass and user but super_admin is can change everyone user and pass also can
delete or add new user*. Codex reviewed the design first: authority is the
ROLE on the record, never the account name, and the last super_admin can never
be removed.

Driven through a throwaway Auth store and the real hub routes (a second login
is its own cookie), never the PC's own accounts.
"""
import http.cookiejar
import json
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import qc as F

AREA = "hub"
TITLE = "default accounts are marked, users edit themselves, super_admin edits all"


class Session:
    def __init__(self, base):
        self.base = base
        self.op = urllib.request.build_opener(
            urllib.request.HTTPCookieProcessor(http.cookiejar.CookieJar()))

    def call(self, path, body=None):
        data = None if body is None else json.dumps(body).encode()
        req = urllib.request.Request(self.base + path, data=data,
                                     method="POST" if body is not None else "GET")
        try:
            with self.op.open(req, timeout=15) as r:
                return r.status, json.loads(r.read() or b"{}")
        except urllib.error.HTTPError as e:
            return e.code, json.loads(e.read() or b"{}")


def run(t):
    import sys
    sys.path.insert(0, str(F.CODE / "main_python"))
    import hub_auth                                          # noqa: E402

    # ---- the model, on a fresh store ---------------------------------
    store = Path(tempfile.mkdtemp(prefix="qc_accounts_")) / "auth.json"
    A = hub_auth.Auth(store, out=lambda *a: None)
    acc = {x["name"]: x for x in A.accounts()}
    t.ok(set(acc) >= {"super_admin", "admin"}, "a fresh hub has super_admin and admin", acc)
    t.ok(acc.get("super_admin", {}).get("role") == "super_admin"
         and acc.get("admin", {}).get("role") == "user",
         "super_admin runs the accounts; admin is an ordinary user", acc)
    t.ok(all(x["mustChange"] for x in acc.values()),
         "both are marked as still on the shipped password", acc)
    ok, why = A.rename_user("super_admin", "boss")
    t.ok(ok and A.is_super("boss"), "renaming super_admin keeps its authority (role, not name)", why)
    ok, why = A.remove_user("boss")
    t.ok(not ok and "last super_admin" in (why or ""),
         "the last super_admin can never be removed", why)

    # ---- the routes, as the real pages call them ----------------------
    base, _main = F.start_hub()
    boss = Session(base)
    code, j = boss.call("/api/login", {"password": F.HUB_PASSWORD})
    if not t.ok(code == 200 and j.get("ok"), "super_admin logs in", j):
        return
    for name in ("qc_user_a", "qc_user_b"):
        boss.call("/api/users/remove", {"user": name})
    code, j = boss.call("/api/users/add", {"user": "qc_user_a", "password": "admin123"})
    t.ok(code == 200 and j.get("ok"), "super_admin adds a user", j)

    user = Session(base)
    code, j = user.call("/api/login", {"user": "qc_user_a", "password": "admin123"})
    t.ok(code == 200 and j.get("ok"), "the new user logs in", j)
    code, who = user.call("/api/whoami")
    t.ok(who.get("user") == "qc_user_a" and who.get("role") == "user"
         and who.get("mustChange") is True,
         "whoami says who, their role, and that the password is still the default", who)

    code, j = user.call("/api/users/add", {"user": "qc_user_b", "password": "whatever123"})
    t.ok(code >= 400 and not j.get("ok"), "an ordinary user cannot add accounts", j)
    code, j = user.call("/api/users/password", {"user": "super_admin", "password": "stolen1234"})
    t.ok(code >= 400 and not j.get("ok"), "nor change someone else's password", j)
    code, j = user.call("/api/users/rename", {"user": "super_admin", "new": "mine"})
    t.ok(code >= 400 and not j.get("ok"), "nor rename someone else", j)

    code, j = user.call("/api/users/password", {"old": "wrong-one", "password": "newpass123"})
    t.ok(code >= 400 and not j.get("ok"), "changing your own password needs the current one", j)
    code, j = user.call("/api/users/password", {"old": "admin123", "password": "newpass123"})
    t.ok(code == 200 and j.get("ok"), "a user changes their own password", j)
    code, who = user.call("/api/whoami")
    t.ok(who.get("authed") and who.get("mustChange") is False,
         "and stays logged in, no longer marked as default", who)

    code, j = user.call("/api/users/rename", {"new": "qc_user_b"})
    code2, who = user.call("/api/whoami")
    t.ok(code == 200 and who.get("authed") and who.get("user") == "qc_user_b",
         "a user renames themselves and stays logged in", (j, who))

    code, j = boss.call("/api/users/password", {"user": "qc_user_b", "password": "reset12345"})
    t.ok(code == 200 and j.get("ok"), "super_admin resets anyone's password without the old one", j)
    code, j = boss.call("/api/users")
    t.ok(any(x["name"] == "qc_user_b" for x in j.get("accounts", [])),
         "super_admin sees every account", j)
    code, j = boss.call("/api/users/remove", {"user": "qc_user_b"})
    t.ok(code == 200 and j.get("ok"), "and removes one", j)

    # a SECOND super_admin, with its own name and password (user 2026-09-17)
    boss.call("/api/users/remove", {"user": "qc_boss2"})
    code, j = boss.call("/api/users/add", {"user": "qc_boss2", "password": "second123", "role": "super_admin"})
    boss2 = Session(base)
    boss2.call("/api/login", {"user": "qc_boss2", "password": "second123"})
    code2, who2 = boss2.call("/api/whoami")
    code3, j3 = boss2.call("/api/users/add", {"user": "qc_user_d", "password": "fourth1234"})
    t.ok(code == 200 and who2.get("role") == "super_admin" and code3 == 200,
         "super_admin adds another super_admin, who can manage accounts too", (j, who2, j3))
    code, j = user.call("/api/users/add", {"user": "qc_sneak", "password": "sneaky1234", "role": "super_admin"})
    t.ok(code >= 400, "an ordinary user cannot make themselves or anyone a super_admin", j)
    boss.call("/api/users/remove", {"user": "qc_user_d"})
    boss.call("/api/users/remove", {"user": "qc_boss2"})
    hub_page = (F.CODE / "main_python" / "web" / "hub.html").read_text(encoding="utf-8")
    t.ok('id="uRole"' in hub_page and "role:$('uRole').value" in hub_page,
         "the Accounts card lets super_admin choose the role when adding")

    # renamed, super_admin keeps its powers through the routes too
    code, j = boss.call("/api/users/rename", {"new": "qc_boss"})
    code2, j2 = boss.call("/api/users/add", {"user": "qc_user_c", "password": "another123"})
    t.ok(code == 200 and code2 == 200 and j2.get("ok"),
         "a renamed super_admin can still add accounts", (j, j2))
    boss.call("/api/users/remove", {"user": "qc_user_c"})
    boss.call("/api/users/rename", {"new": "super_admin"})

    # ---- every page shows the default-password warning -----------------
    js = (F.CODE / "shared" / "web" / "mice.js").read_text(encoding="utf-8")
    t.ok('warn.hidden = !(who.authed && who.mustChange);' in js
         and 'who.mustChange = !!j.mustChange;' in js,
         "the login card on every page warns while the password is the default",
         "whoami reports mustChange; the shared card must show it")

    # ---- a board warns about the SAME default it ships with ------------
    # Codex review 2026-09-17: boards seeded admin123 but compared against
    # 12345678, so a fresh board never said "please change".
    import re as _re
    h = (F.FIRMWARE / "src" / "core" / "UserStore.h").read_text(encoding="utf-8")
    cpp = (F.FIRMWARE / "src" / "core" / "UserStore.cpp").read_text(encoding="utf-8")
    m = _re.search(r'shippedPassword\(\)\s*\{\s*return\s*"([^"]+)"', h)
    seeds = set(_re.findall(r'users_\["[^"]+"\]\s*=\s*"([^"]+)"', cpp))
    t.ok(m and seeds == {m.group(1)} and m.group(1) == hub_auth.DEFAULT_PASSWORD,
         "boards seed and check the same default password as the hub",
         (m.group(1) if m else None, seeds, hub_auth.DEFAULT_PASSWORD))
