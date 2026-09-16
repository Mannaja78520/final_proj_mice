"""Guards that exist AND are armed, and claims that cannot race.

Nine findings on 2026-08-21, from two reviewers reading different halves of the
tree. Three of them were the same shape, and it is the shape worth naming: **a
guard that is present but not armed.** It reads correctly, it passes review,
and it protects nothing.

  * `/api/ota` checked the login in its COMPLETION handler. AsyncWebServer runs
    the body handler first, so `Update.end(true)` had already switched the boot
    partition when the 401 was sent - anyone on the venue WiFi could flash a
    board and get a refusal afterwards;
  * the same upload used `UPDATE_SIZE_UNKNOWN` with no `setMD5`, so
    `end(true)` verified nothing at all and a truncated upload answered
    *OK updated, rebooting*. The bus path had required an md5 since that
    morning; the transport most likely to drop a connection had not;
  * `if (want && got != want)` switched itself off when the declared length was
    0 - and `toInt()` returns 0 for any non-number, so `FWDATA 7 x <b64>` wrote
    a short chunk in silence.

The other shape was **check-then-act across a lock**: four flash paths and the
show player tested "am I busy" outside the lock and claimed after it, so two
requests in that window both won. Two clocks on one robot is the exact fault
`check_takeover` exists to prevent, and it could never see this one.

And the brownout guard said *two in a row* while counting *two ever*, because
nothing cleared the count after a boot that worked.
"""
import re

import qc as F

AREA = "firmware"
TITLE = "every guard is armed, and no claim can be won twice"


def run(t):
    fw = F.FIRMWARE / "src" / "core"
    portal = (fw / "WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    bus = (fw / "BusUpdate.cpp").read_text(encoding="utf-8", errors="replace")
    guard = (fw / "BrownoutGuard.cpp").read_text(encoding="utf-8", errors="replace")
    main = (F.HUB / "main.py").read_text(encoding="utf-8")
    auth = (F.HUB / "hub_auth.py").read_text(encoding="utf-8")

    # ---- the OTA login is checked where the WRITING happens ----------
    body = portal[portal.find('server_.on("/api/ota", HTTP_POST'):]
    body = body[:body.find("\n    server_.on(", 10)]
    i_body = body.find("uint8_t* data, size_t len, bool final")
    i_auth = body.find("allowed(req)", i_body)
    i_write = body.find("Update.write", i_body)
    t.ok(0 < i_auth < i_write,
         "the OTA body handler checks the login BEFORE it writes",
         "AsyncWebServer runs this handler as the bytes arrive and the "
         "completion handler afterwards - a check only up there ran after "
         "Update.end had switched the boot partition, so the 401 was true and "
         "far too late")

    # ---- and the image is verified ----------------------------------
    t.contains(body, "setMD5",
               "the WiFi upload registers an md5")
    t.ok("UPDATE_SIZE_UNKNOWN" not in body or "md5.length() != 32" in body,
         "and refuses an upload that brings none",
         "with an unknown size and no md5, Update.end(true) checks nothing: a "
         "truncated upload answers OK and boots whatever arrived")
    t.contains(main, "/api/ota?md5=",
               "and the hub sends one, so its own path still works")

    # ---- the chunk-length guard cannot switch itself off -------------
    data = bus[bus.find("String BusUpdate::data"):]
    data = data[:data.find("\nString BusUpdate::end")]
    t.ok("want == 0" in data,
         "a chunk with no declared length is refused",
         "toInt() returns 0 for any token that is not a number, so `want && "
         "...` disarmed the whole check on FWDATA 7 x <b64>")
    t.contains(data, "want > MAX_CHUNK",
               "and one claiming more than a chunk can hold")
    t.ok("if (want && got != want)" not in data,
         "the guard is not conditional on its own argument")

    # ---- "in a row" really means in a row ---------------------------
    t.contains(guard, "void BrownoutGuard::markBooted()",
               "a boot that reached the command loop clears the count")
    mb = guard[guard.find("void BrownoutGuard::markBooted()"):]
    t.contains(mb, "if (tripped_) return;",
               "except when the radio was left off, which proves nothing",
               )
    main_cpp = (F.FIRMWARE / "src" / "main.cpp").read_text(encoding="utf-8",
                                                           errors="replace")
    i_mark = main_cpp.find("brownout.markBooted()")
    i_portal = main_cpp.find("portal.begin(")
    t.ok(0 < i_portal < i_mark,
         "and it is called AFTER the radio started",
         "clearing before the thing that browns the board out would clear it "
         "every time and count nothing")

    # ---- one claim, under one lock ----------------------------------
    # Signature grew target/args/stage when launching moved INSIDE the lock
    # (A22-1) - anchor on the fixed prefix, not the whole parameter list.
    claim = main[main.find("    def _claim(self, port, module_type, how,"):]
    claim = claim[:claim.find("\n    def ", 1)]
    t.contains(claim, "with self.lock:", "the flash job is claimed under a lock")
    i_run = claim.find("self.running()")
    i_set = claim.find("self.port, self.type")
    t.ok(0 < i_run < i_set,
         "checking and claiming happen inside the SAME lock",
         "tested outside it, two POSTs in that window both pass and both spawn "
         "a writer on one shared job - each overwriting the other's progress, "
         "with neither caller told")
    t.eq(main.count("self._claim("), 4,
         "and every start path goes through it")
    t.ok(main.count("if self.running():") <= 1,
         "with no unlocked check left over",
         "one is the claim's own; a second is a path that can still race")

    # ---- the show player cannot be started twice --------------------
    st = main[main.find("    def start(self, dev, steps"):]
    st = st[:st.find("\n    def ", 1)]
    t.contains(st, "with self._starting:",
               "stopping and starting a show is one atomic step")
    i_stop = st.find("self.stop()")
    i_lock = st.find("with self._starting:")
    t.ok(0 < i_lock < i_stop,
         "with the stop INSIDE it",
         "two POSTs for one robot could each find nothing to stop and each "
         "spawn a clock: two threads sending POSE to the same arm")
    t.contains(main, "self._starting = threading.Lock()",
               "on a lock of its own")
    t.ok("with self.lock:" in st.split("with self._starting:")[1][:400],
         "and the state is still written under the ordinary lock",
         "holding the running thread's lock across a join would deadlock, "
         "which is why these are two locks and not one")

    # ---- the identity cache is read once ----------------------------
    t.ok("_usb_ident.get(port)" in main,
         "the identity cache is read in ONE lookup",
         "`if port in _usb_ident` then `_usb_ident[port]` can KeyError when "
         "another thread pops the key between the two - which happens exactly "
         "when the port is busy, the only case that path is for")
    t.ok("if light and port in _usb_ident:" not in main,
         "and the test-then-read version is gone")

    # ---- the lockout counts every try -------------------------------
    t.contains(auth, "self._count_lock",
               "failed logins are counted under a lock")
    fails = auth[auth.find("if not self._matches("):]
    fails = fails[:fails.find("self._fails[who] = (n, until)") + 40]
    i_lk = fails.find("with self._count_lock:")
    i_rd = fails.find("self._fails.get(who")
    t.ok(0 <= i_lk < i_rd,
         "with the read inside the lock, not only the write",
         "a read-modify-write from two threads loses a try, so a five-try "
         "lockout quietly takes more than five")
