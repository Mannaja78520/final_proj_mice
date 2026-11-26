"""The hub's shipped login, choosing your own password, and getting back in.

User 2026-11-27: the factory login is admin / admin123 from a tracked default
file; a changed password lives only in the git-ignored store, hashed; the first
login asks to change it; a forgotten password is recovered with a code shown
once, or by a reset that only works on the hub PC.

WHAT IS PROVEN, AND AGAINST WHAT
  * the shipped login comes from main_python/hub_login.default.json and works,
    the store holds hashes only, and no readable password file is written;
  * an OLD store (one password, no flags) and its old plain-text file migrate:
    the owner still gets in, the plain file is deleted;
  * a recovery code is shown once, kept only as a hash, works ONCE, is replaced
    by a new one, and the old default password stops working after a change;
  * guessing is throttled per source and for everyone, the wait GROWS, the right
    code is refused while locked, an unknown name answers like a wrong code, and
    a spoofed X-Forwarded-For buys no extra tries (asserted on what a real hub
    answered over HTTP);
  * there is no network route that resets a password, with or without headers
    that claim to be the PC itself; the reset tool edits the local file and a
    running hub lets the owner in without a restart;
  * empty, huge and unicode passwords are handled, and a bad new password does
    not burn a good code.
"""
import json
import re
import sys
import tempfile
import urllib.error
import urllib.request
from pathlib import Path

import qc as F

AREA = "auth"
TITLE = "hub login: shipped default, own password, recovery code, local reset"
SLOW = False

sys.path.insert(0, str(F.HUB))
sys.path.insert(0, str(F.CODE / "tools"))

CODE_SHAPE = re.compile(r"^[A-Z2-9]{4}(-[A-Z2-9]{4}){3}$")


class Clock:
    def __init__(self):
        self.now = 1000.0

    def __call__(self):
        return self.now


def _call(base, path, body=None, cookie="", headers=None):
    req = urllib.request.Request(base + path, data=json.dumps(body or {}).encode(), method="POST")
    if cookie:
        req.add_header("Cookie", cookie)
    for k, v in (headers or {}).items():
        req.add_header(k, v)
    try:
        with urllib.request.urlopen(req, timeout=20) as r:
            return r.status, json.loads(r.read().decode() or "{}"), r.headers.get("Set-Cookie", "")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw or "{}"), ""
        except ValueError:
            return e.code, {"raw": raw}, ""


def _login(base, user, password):
    code, j, cookie = _call(base, "/api/login", {"user": user, "password": password})
    return code, cookie.split(";")[0]


def unit(t):
    import hub_auth
    import hub_recovery
    import hub_reset_password

    # ---- the shipped login comes from the tracked file ------------------
    default = F.CODE / "main_python" / "hub_login.default.json"
    data = json.loads(default.read_text(encoding="utf-8"))
    t.ok(default.is_file() and data["password"] == "admin123", "the shipped login file is in the repo",
         "user 2026-11-27: admin / admin123 from a tracked default file")
    t.eq(hub_auth.DEFAULT_PASSWORD, data["password"], "the hub reads its shipped password from that file")
    t.ok({"admin", "super_admin"} <= {n for n, _ in hub_auth.FACTORY_ACCOUNTS},
         "and ships the accounts admin and super_admin", str(hub_auth.FACTORY_ACCOUNTS))

    box = Path(tempfile.mkdtemp(prefix="qc_hublogin_"))
    try:
        store = box / hub_auth.DEFAULT_STORE_NAME
        a = hub_auth.Auth(store, out=lambda *x: None)
        t.ok(a.login("admin123", "1.1.1.1", user="admin")[0], "a fresh hub: admin / admin123 logs in")
        t.ok(a.login("admin123", "1.1.1.2", user="super_admin")[0], "and super_admin / admin123 too")
        t.ok(a.must_change("admin"), "the shipped login is flagged: the page asks to change it")
        t.ok(a.any_shipped(), "and the hub knows a shipped login still works")
        raw = store.read_text(encoding="utf-8")
        t.ok("admin123" not in raw, "the store holds only a salted hash, never the password",
             "people reuse passwords; a stolen file must not hand one over")
        t.ok(not (box / "hub_password.txt").exists(), "no readable password file is written beside it",
             "one was committed to a public repo by mistake in 2026-08")

        # ---- choosing your own password -------------------------------------
        t.ok(a.change_password("admin", "My-Own-Pass-1")[0], "choosing your own password works")
        t.ok(a.login("admin123", "2.2.2.2", user="admin")[0] is None, "then the old shipped password fails")
        t.ok(a.login("My-Own-Pass-1", "2.2.2.3", user="admin")[0], "and the new one works")
        t.ok(not a.must_change("admin"), "and the account is no longer asked to change it")
        code = a.issue_recovery_code("admin")
        t.ok(bool(CODE_SHAPE.match(code or "")), "a recovery code looks like XXXX-XXXX-XXXX-XXXX", str(code))
        raw = store.read_text(encoding="utf-8")
        t.ok(code not in raw and code.replace("-", "") not in raw,
             "the code is NOT in the store (only its hash is)", "a stolen file must not hand over the code")
        t.ok(a.has_recovery("admin") and not a.has_recovery("super_admin"),
             "only the account that has one is marked as having one")
        t.ok(not any(hub_auth.Auth.export_accounts(a).get("admin", {}).get(k) for k in ("recovery",)),
             "pairing copies hashes only, not the recovery code hash")

        # ---- using it: single use, replaced, wrong password does not burn ---
        ok, why, _n, wait = a.recover("admin", code, "short", "3.3.3.3")
        t.ok(not ok and wait == 0, "a too-short new password is refused", why)
        ok, why, _n, wait = a.recover("admin", code, "a b c d e f g h", "3.3.3.3")
        t.ok(not ok, "a password with spaces is refused", why)
        ok, why, _n, wait = a.recover("admin", code, "x" * 10000, "3.3.3.3")
        t.ok(not ok, "a 10000-character password is refused, not hashed", why[:60])
        ok, why, _n, wait = a.recover("admin", code, "", "3.3.3.3")
        t.ok(not ok, "an empty password is refused", why)
        ok, why, _n, wait = a.recover("admin", code, "admin123", "3.3.3.3")
        t.ok(not ok, "the shipped password cannot be chosen again", why)
        ok, why, fresh, wait = a.recover("admin", code.lower().replace("-", " "), "Пароль-ฮับ-🔒-123", "3.3.3.3")
        t.ok(ok and CODE_SHAPE.match(fresh or ""),
             "the code still works after those refusals (a bad password does not burn it) "
             "and a unicode password is accepted; typing it in lower case with spaces is fine", why)
        t.ok(a.login("Пароль-ฮับ-🔒-123", "3.3.3.4", user="admin")[0], "the unicode password logs in")
        ok, why, _n, wait = a.recover("admin", code, "Another-Pass-2", "3.3.3.5")
        t.ok(not ok, "the same code a second time fails (single use)", why)
        t.ok(a.login("My-Own-Pass-1", "3.3.3.6", user="admin")[0] is None, "the previous password is gone")
        ok, why, fresh2, _w = a.recover("admin", fresh, "Another-Pass-2", "3.3.3.7")
        t.ok(ok and fresh2 != fresh, "the NEW code works once and is replaced again", why)

        # ---- the answer is the same for an unknown name and a wrong code ----
        e1 = a.recover("nobody", "AAAA-AAAA-AAAA-AAAA", "Some-Pass-123", "4.4.4.1")[1]
        e2 = a.recover("admin", "AAAA-AAAA-AAAA-AAAA", "Some-Pass-123", "4.4.4.2")[1]
        e3 = a.recover("super_admin", "AAAA-AAAA-AAAA-AAAA", "Some-Pass-123", "4.4.4.3")[1]
        t.ok(e1 == e2 == e3 and e1, "unknown name, wrong code and no-code answer the same",
             "%r %r %r" % (e1, e2, e3))

        # ---- the lockout: per source, growing, and for everyone -------------
        clock = Clock()
        a._recovery_throttle = hub_recovery.Throttle(clock=clock)  # noqa: SLF001
        good = a.issue_recovery_code("admin")
        for _ in range(4):
            a.recover("admin", "BBBB-BBBB-BBBB-BBBB", "Some-Pass-123", "5.5.5.5")
        t.eq(a.recovery_wait("5.5.5.5"), 0, "four wrong tries: not locked yet")
        ok, why, _n, w1 = a.recover("admin", "BBBB-BBBB-BBBB-BBBB", "Some-Pass-123", "5.5.5.5")
        t.ok(w1 > 0, "the fifth wrong try locks that source", str(w1))
        ok, why, _n, w = a.recover("admin", good, "Some-Pass-123", "5.5.5.5")
        t.ok(not ok and w > 0, "while locked even the RIGHT code is refused", why)
        t.eq(a.recovery_wait("5.5.5.6"), 0, "another source is not locked by it")
        clock.now += w1 + 1
        for _ in range(5):
            a.recover("admin", "BBBB-BBBB-BBBB-BBBB", "Some-Pass-123", "5.5.5.5")
        w2 = a.recovery_wait("5.5.5.5")
        t.ok(w2 > w1, "the second lockout is LONGER than the first", "%s then %s" % (w1, w2))
        clock.now += 100000
        for i in range(hub_recovery.Throttle().all_tries):
            a.recover("admin", "CCCC-CCCC-CCCC-CCCC", "Some-Pass-123", "6.6.%d.%d" % (i // 250, i % 250))
        ok, why, _n, w = a.recover("admin", good, "Some-Pass-123", "7.7.7.7")
        t.ok(not ok and w > 0,
             "wrong tries from MANY sources lock everyone (a flood of addresses still hits a wall)", why)
        clock.now += 100000
        ok, why, _n, w = a.recover("admin", good, "Some-Pass-123", "7.7.7.7")
        t.ok(ok, "and the owner gets in after the wait", why)

        # ---- the reset tool: local file, no restart needed -------------------
        a2 = hub_auth.Auth(store, out=lambda *x: None)
        a2.add_user("bob", "bobs-password")
        a2.issue_recovery_code("admin")
        t.ok(a2.login("Some-Pass-123", "8.8.8.8", user="admin")[0], "before the reset admin uses his own password")
        hub_reset_password.main(["--yes", "--store", str(store)])
        t.ok(a2.login("admin123", "8.8.8.9", user="admin")[0],
             "after the reset a RUNNING hub lets admin / admin123 in without a restart",
             "the hub re-reads the file when a login fails")
        t.ok(a2.must_change("admin") and not a2.has_recovery("admin"),
             "the reset account must choose a new password and has no old recovery code")
        t.ok(a2.login("bobs-password", "8.8.8.10", user="bob")[0], "other accounts keep their own passwords")
        t.ok(a2.login("Some-Pass-123", "8.8.8.11", user="admin")[0] is None, "the old password no longer works")
        t.eq(hub_reset_password.main(["--yes", "--store", str(box / "none.json")]), 0,
             "a reset on a PC with no login file says so and changes nothing")
    finally:
        import shutil
        shutil.rmtree(box, ignore_errors=True)

    # ---- an OLD hub: its owner still gets in, the plain file is deleted ----
    import hashlib
    import secrets
    box = Path(tempfile.mkdtemp(prefix="qc_hublogin_old_"))
    try:
        salt = secrets.token_bytes(16)
        (box / hub_auth.DEFAULT_STORE_NAME).write_text(json.dumps({
            "salt": salt.hex(), "hash": hashlib.pbkdf2_hmac(
                "sha256", b"old-owner-pass", salt, hub_auth._ITERATIONS).hex()}), encoding="utf-8")  # noqa: SLF001
        (box / "hub_password.txt").write_text("This PC's MICE hub login:" + chr(10) + "    old-owner-pass" + chr(10),
                                              encoding="utf-8")
        old = hub_auth.Auth(box / hub_auth.DEFAULT_STORE_NAME, out=lambda *x: None)
        t.ok(old.login("old-owner-pass", "9.9.9.9")[0], "an old hub's owner is not locked out by the upgrade")
        t.ok(not (box / "hub_password.txt").exists(), "and its plain-text password file is deleted")
    finally:
        import shutil
        shutil.rmtree(box, ignore_errors=True)


def over_http(t):
    base, main = F.start_hub()
    auth = main.auth()
    auth.add_user("newbie", "admin123")
    code, cookie = _login(base, "newbie", "admin123")
    t.eq(code, 200, "over HTTP: the shipped password logs a new account in")
    # whoami is a GET: read it with the cookie
    def whoami(ck):
        req = urllib.request.Request(base + "/api/whoami")
        if ck:
            req.add_header("Cookie", ck)
        with urllib.request.urlopen(req, timeout=10) as r:
            return json.loads(r.read().decode())

    w = whoami(cookie)
    t.ok(w.get("mustChange") is True and w.get("hasRecovery") is False,
         "whoami says: still on the shipped password, no recovery code yet", str(w)[:150])

    # choosing your own password: no 'current password' box for the shipped one
    c, j, _ = _call(base, "/api/users/password", {"user": "newbie", "password": "Fresh-pass-1"}, cookie)
    t.ok(c == 200 and CODE_SHAPE.match(j.get("recoveryCode", "")),
         "choosing a password over HTTP answers with a recovery code", "%s %s" % (c, str(j)[:120]))
    first = j.get("recoveryCode", "")
    t.eq(_login(base, "newbie", "admin123")[0], 401, "the shipped password no longer logs that account in")
    code, cookie2 = _login(base, "newbie", "Fresh-pass-1")
    t.eq(code, 200, "the chosen password logs in")
    w = whoami(cookie2)
    t.ok(w.get("mustChange") is False and w.get("hasRecovery") is True,
         "whoami now says: own password and a recovery code on file", str(w)[:150])
    raw = main.AUTH_STORE.read_text(encoding="utf-8")
    t.ok(first not in raw and "Fresh-pass-1" not in raw, "neither the code nor the password is in the store file")
    # with a real password the old one IS asked for again
    c, j, _ = _call(base, "/api/users/password", {"user": "newbie", "password": "Sneaky-pass-9"}, cookie2)
    t.ok(c == 400, "changing it again without the current password is refused", str(j))

    # ---- a new code needs a login and the password ---------------------------
    c, j, _ = _call(base, "/api/recovery/code", {"password": "Fresh-pass-1"})
    t.eq(c, 401, "no session: a new recovery code is refused")
    c, j, _ = _call(base, "/api/recovery/code", {"password": "wrong-wrong-1"}, cookie2)
    t.ok(c == 400 and "recoveryCode" not in j, "a wrong password does not make a code")
    c, j, _ = _call(base, "/api/recovery/code", {"password": "Fresh-pass-1"}, cookie2)
    second = j.get("recoveryCode", "")
    t.ok(c == 200 and CODE_SHAPE.match(second) and second != first, "with the password a NEW code is made")

    # ---- forgot password over HTTP -----------------------------------------
    c, j, _ = _call(base, "/api/recovery/use", {"user": "newbie", "code": first, "password": "Never-used-1"})
    t.ok(c == 400 and not j.get("ok"), "the replaced (old) code no longer works", str(j))
    bad = _call(base, "/api/recovery/use", {"user": "nobody", "code": second, "password": "Never-used-1"})
    badcode = _call(base, "/api/recovery/use", {"user": "newbie", "code": "ZZZZ-ZZZZ-ZZZZ-ZZZZ",
                                                "password": "Never-used-1"})
    t.ok(bad[1].get("error") and bad[1].get("error") == badcode[1].get("error"),
         "an unknown name and a wrong code get the same words over HTTP", "%s | %s" % (bad[1], badcode[1]))
    for pw in ("", "short", "x" * 10000, "has spaces in it", "admin123"):
        c, j, _ = _call(base, "/api/recovery/use", {"user": "newbie", "code": second, "password": pw})
        t.ok(c == 400 and not j.get("ok"), "a bad new password is refused (%d characters)" % len(pw), str(j)[:80])
    c, j, _ = _call(base, "/api/recovery/use", {"user": "newbie", "code": second, "password": "Unicode-Пароль-🔒"})
    third = j.get("recoveryCode", "")
    t.ok(c == 200 and CODE_SHAPE.match(third), "the right code and a good unicode password: accepted", str(j)[:120])
    t.eq(whoami(cookie2).get("authed"), False, "the old session of that account was ended")
    t.eq(_login(base, "newbie", "Fresh-pass-1")[0], 401, "the password from before the recovery is gone")
    t.eq(_login(base, "newbie", "Unicode-Пароль-🔒")[0], 200, "the recovered password logs in")
    c, j, _ = _call(base, "/api/recovery/use", {"user": "newbie", "code": second, "password": "Again-pass-12"})
    t.ok(c == 400 and not j.get("ok"), "the used code does not work a second time", str(j))

    # ---- no network way to reset a password, even claiming to be the PC -----
    spoof = {"X-Forwarded-For": "127.0.0.1", "X-Real-IP": "127.0.0.1", "Forwarded": "for=127.0.0.1",
             "Host": "localhost"}
    for path in ("/api/reset", "/api/users/reset", "/api/recovery/reset", "/api/auth/reset",
                 "/api/hub/reset_password", "/api/reset_password", "/api/users/factory"):
        c, j, _ = _call(base, path, {"user": "newbie", "password": "Hacked-pass-1"}, headers=spoof)
        t.ok(c in (404, 405) or not j.get("ok"), "no reset at %s (with spoofed local headers)" % path,
             "%s %s" % (c, str(j)[:80]))
    t.eq(_login(base, "newbie", "Hacked-pass-1")[0], 401, "and nothing was reset")
    t.eq(_login(base, "newbie", "Unicode-Пароль-🔒")[0], 200, "the real password still works")

    # ---- spoofed addresses buy no extra tries (this must be LAST) ------------
    seen = []
    for i in range(7):
        c, j, _ = _call(base, "/api/recovery/use",
                        {"user": "newbie", "code": "YYYY-YYYY-YYYY-YYYY", "password": "Some-Pass-123"},
                        headers={"X-Forwarded-For": "10.1.%d.%d" % (i, i), "X-Real-IP": "10.2.%d.%d" % (i, i)})
        seen.append(c)
    # 127.0.0.1 already made wrong tries above (the throttle counts per socket
    # address), so the wall comes within the first five of these, not after five more.
    t.ok(seen.count(400) <= 4 and 429 in seen[:5] and seen[-1] == 429,
         "the source is locked (429) after its 5th wrong try however many addresses the headers claim",
         str(seen))
    c, j, _ = _call(base, "/api/recovery/use", {"user": "newbie", "code": third, "password": "Last-pass-123"})
    t.ok(c == 429 and (j.get("wait") or 0) > 0 and not j.get("ok"),
         "and while locked the right code is refused, with the wait in the answer", "%s %s" % (c, str(j)[:100]))


def run(t):
    unit(t)
    over_http(t)
