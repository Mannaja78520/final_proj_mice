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

SHIPPED = "12345678"


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
    t.ok(re.search(r"mustChange\s*\)\s*\{", login_fn),
         "and logging in does not open Setup while the password is unchanged",
         "a board nobody has secured is the same as a board with no login")
