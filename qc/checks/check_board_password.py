"""The board does not hand out its own password, and insists on a real one.

Two faults, and the second is the one that lasts:

  1 the login card PRINTED it — "Default account manny / 12345678" — on a page
    anyone on the WiFi could open. Before the board had any auth at all that
    was the whole door; afterwards it was the key taped beside the lock.
  2 nothing ever made anyone change it, so every board in the room answered to
    the same password, forever.

Checked BY VALUE, not by a flag. A flag set when the firmware creates the first
account only knows about boards this firmware set up — and a board that has
been in service for a year already had its account, so it would keep the
shipped password and never be asked. The boards most likely to still have it
are exactly the ones a flag misses. That was caught before flashing, on the
real board, which had been running since before the change.

Verified on hardware 2026-08-19 (nong id 85): login answered mustChange:true,
a 7-character password was refused, changing it to 12345678 was refused, a real
change was accepted and the old password then failed to log in.
"""
import re

import qc as F

AREA = "auth"
TITLE = "the board keeps its password to itself, and demands a real one"
SLOW = False

SHIPPED = "admin123"


def run(t):
    page = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    store_h = (F.FIRMWARE / "src/core/UserStore.h").read_text(encoding="utf-8", errors="replace")
    store_c = (F.FIRMWARE / "src/core/UserStore.cpp").read_text(encoding="utf-8", errors="replace")
    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")

    # ---- the page does not print it -----------------------------------
    body = page[page.find("<body>"):]
    body = re.sub(r"<!--.*?-->", "", body, flags=re.S)      # comments may discuss it
    t.ok(SHIPPED not in body,
         "the module page does not print the password",
         "it was on the login card, on a page anyone on the WiFi can open")

    # ---- the board knows whether anyone has chosen one ----------------
    t.contains(store_h, "firstPassword", "the board can say if it is still on the shipped password")
    fn = store_c[store_c.find("bool UserStore::firstPassword"):]
    fn = fn[:fn.find("\n}") + 2] if "\n}" in fn else fn[:600]
    t.ok(fn, "and it is implemented")
    # BY VALUE. A flag would miss every board that predates this firmware.
    t.ok("users_" in fn and "shippedPassword" in fn,
         "by looking at the stored password, not a flag set at first boot",
         "a board already in service kept its account, so a flag would say it "
         "was set up and it would never be asked")

    # ---- a change has to be a real change -----------------------------
    setp = store_c[store_c.find("bool UserStore::setPass"):]
    setp = setp[:setp.find("\n}") + 2] if "\n}" in setp else setp[:600]
    t.contains(setp, "shippedPassword",
               "changing the password TO the shipped one is refused")
    t.ok(re.search(r"minPassLength|length\(\)\s*<\s*8", store_c + store_h),
         "and a new password has a minimum length",
         "forcing a change is theatre if the new one can be a single character")

    # ---- the page is told, and acts on it -----------------------------
    t.contains(portal, "mustChange",
               "the board tells the page it is still on the shipped password")
    t.contains(page, "mustChangeBox",
               "and the page has somewhere to say so")
    t.ok("mustChange" in page and "doFirstChange" in page,
         "with a way to fix it right there")
    # Setup must NOT open while the board is unsecured: that is the whole point.
    login_fn = page[page.find("async function doLogin"):]
    login_fn = login_fn[:login_fn.find("function doLogout")]
    # User 2026-09-17 changed the rule: the defaults are on EVERY board, so the
    # shipped password is a warning, not a lock. Re-added on each boot, a lock
    # on "any account" would have kept Setup closed forever.
    t.ok("mustChangeBox').style.display = mustChange ?" in login_fn
         and not re.search(r"if\s*\(\s*mustChange\s*\)\s*\{[^}]*return;", login_fn),
         "logging in on the default password opens Setup AND shows the warning",
         "a lock here never opens: the default accounts come back on every boot")
    login_api = portal[portal.find('"/api/login"'):]
    login_api = login_api[:login_api.find("server_.on(", 10)]
    t.ok("pass == UserStore::shippedPassword()" in login_api,
         "the warning is about the account that logged in",
         "firstPassword() is true on every board now (defaults re-added), so it "
         "would warn a user who already changed their own password")

    # ---- every board has both default logins (A26-43) -------------------
    beg = store_c[store_c.find("void UserStore::begin"):]
    beg = beg[:beg.find("\n}") + 2]
    t.ok('"super_admin"' in beg and '"admin"' in beg,
         "begin() knows both default accounts")
    t.ok("size() == 0" not in beg and "is<const char*>()" in beg,
         "and adds each one that is MISSING, not only on an empty store",
         "board #67 had only manny/12345678, so admin/admin123 never worked there")
    t.ok("users_.clear()" not in beg.replace("if (!users_.is<JsonObject>()) users_.clear();", ""),
         "an existing account is never wiped to make room",
         "never delete or rotate the user's accounts")
