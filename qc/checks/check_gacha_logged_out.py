"""The Prize machines page makes no login-only calls while logged out.

Found 2026-11-21 (newcomer sweep): it asked for keys, rules, log and stats at
once, so a visitor's console showed four 401 errors on every open. The page now
asks who you are first and fetches those only when logged in.
"""
import re

import qc as F

AREA = "hub"
TITLE = "Prize machines asks for its admin lists only after the login is confirmed"
SLOW = False


def run(t):
    src = (F.CODE / "apps/gacha/index.html").read_text(encoding="utf-8")
    load = re.search(r"\n  load\(\)?[^\n]*\{|async load\(", src)
    t.ok("loadAdmin" in src, "the admin lists load through loadAdmin()")
    body = src[src.index("async loadAdmin()"):][:400]
    t.ok("miceLogin.refresh()" in body and body.index("refresh()") < body.index("this.keysLoad()"),
         "loadAdmin asks who you are before keysLoad/loadRules/loadLog", body[:120])
    first = src[:src.index("async loadAdmin()")]
    t.ok(first.count("this.keysLoad()") == 0 and first.count("this.loadLog()") == 0,
         "nothing else calls the admin lists directly")
    t.ok('addEventListener("mice-login"' in src, "logging in loads them without a reload")
