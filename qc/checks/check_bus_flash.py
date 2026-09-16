"""New firmware over the bus, because RS485 has no reset line and no web server.

Asked for on 2026-08-20: *make it can flash through all this 3 method too if i
need to shieft to stm 32 it cannot use wifi it can use only rs485*, and then
straight after: *why wifi can but rs485 can't i don't know*.

The answer is that neither existing way is transport-agnostic:

  * **esptool** reaches the ESP32's ROM bootloader by pulling EN and IO0 with
    DTR and RTS. RS485 is two differential wires and has neither, so no amount
    of hub-side work gets there;
  * **`POST /api/ota`** posts the image to the board's own web server, which a
    board with no radio does not have.

Both are ways of getting an image IN. The third way is the board writing its own
spare app slot from ordinary command lines - `FWBEGIN` / `FWDATA` / `FWEND` -
which is text like every other command, so a cable, the bus and WiFi all carry
it unchanged.

What this check holds, and why each one is here rather than merely tidy:

  * **the update commands are NOT the file commands.** `FBEGIN`/`FDATA`/`FEND`
    already existed and write an SD file. Reusing those names would have made
    one command that either stores a sequence or overwrites the firmware
    depending on hidden state, which is how a robot eventually gets flashed with
    a YAML file;
  * **a chunk out of order is refused, never written.** A bus drops a line now
    and then. Writing the next chunk into the gap produces a board that boots
    into rubbish and no message anywhere saying why;
  * **the md5 is checked before the reboot,** while the firmware that works is
    still running;
  * **the chunk fits an RS485 frame.** `RS485Bus::loop` throws away any line
    over 250 characters, so a chunk plus `#<id> FWDATA <seq> ` has to fit under
    it - and base64 costs a third on top of the raw bytes;
  * **a failed send aborts,** so the board is left on the firmware it had.
"""
import base64
import json
import re

import qc as F

AREA = "firmware"
TITLE = "firmware can be sent over RS485, not only USB and WiFi"

# RS485Bus::loop discards anything longer than this.
LINE_CAP = 250


def run(t):
    fw = F.FIRMWARE
    hub = (F.HUB / "main.py").read_text(encoding="utf-8")
    up = (fw / "src" / "core" / "BusUpdate.cpp").read_text(encoding="utf-8")
    router = (fw / "src" / "core" / "CommandRouter.cpp").read_text(encoding="utf-8")

    # ---- the names do not collide with the SD file transfer -----------
    cmds = json.loads(re.sub(r"^\s*//.*$", "", (fw / "config" / "commands.json")
                             .read_text(encoding="utf-8"), flags=re.M))["commands"]
    names = {c["name"] for c in cmds}
    for n in ("FWBEGIN", "FWDATA", "FWEND", "FWABORT", "FWSTAT"):
        t.ok(n in names, "%s is declared in the registry, so HELP knows it" % n)
    for n in ("FBEGIN", "FDATA", "FEND"):
        t.ok(n in names,
             "%s still means the SD file transfer it always meant" % n,
             "if the firmware update had taken these names, one command would "
             "either store a sequence or overwrite the firmware depending on "
             "state - and sooner or later a robot gets flashed with a YAML file")
    # and the router really keeps them apart
    t.ok('cmd == "FWDATA"' in router and 'cmd == "FDATA"' in router,
         "and the router handles the two separately")

    # ---- a chunk really fits an RS485 line ----------------------------
    m = re.search(r"MAX_CHUNK = (\d+)", up)
    raw = int(m.group(1)) if m else 0
    if t.ok(m, "the firmware states its chunk size"):
        # The worst case a real line has to carry: a three-digit bus id and a
        # five-digit sequence number, with base64 expansion on the payload.
        b64 = len(base64.b64encode(b"x" * raw))
        line = len("#255 FWDATA 12345 150 ") + b64
        t.ok(line <= LINE_CAP,
             # phrased so it reads correctly WHEN IT FAILS too: the sabotage run
             # printed "a 298 character line, inside the 250 cap", which is the
             # sort of message that makes somebody doubt the check, not the code
             "a %d byte chunk makes a %d character line, against a %d cap"
             % (raw, line, LINE_CAP),
             "RS485Bus::loop throws away a longer line as garbage, so an "
             "update over the bus would fail on the very first chunk")
    # BOTH readers cap a line, not just the bus one. main.cpp got the same
    # guard so a host sending bytes with no terminator cannot eat the heap, and
    # a chunk has to fit under whichever is smaller — an update over a plain
    # cable goes through the USB reader, not RS485Bus.
    bus = (fw / "src" / "core" / "RS485Bus.cpp").read_text(encoding="utf-8")
    usb = (fw / "src" / "main.cpp").read_text(encoding="utf-8")
    for where, src, var in (("RS485Bus", bus, "buf_"),
                            ("the USB reader in main.cpp", usb, "serialBuf")):
        m = re.search(re.escape(var) + r"\.length\(\) > (\d+)", src)
        t.ok(m and int(m.group(1)) >= LINE_CAP,
             "%s still allows %d characters, which is what that sum assumed"
             % (where, LINE_CAP),
             "if either reader's limit is lowered, the chunk size has to come "
             "down with it or every update over that channel breaks at once")

    # the hub sends chunks of exactly that size
    m2 = re.search(r"BUS_CHUNK = (\d+)", hub)
    if t.ok(m2, "the hub states the chunk size it sends"):
        t.ok(int(m2.group(1)) <= raw,
             "and never sends more than the board accepts (%s vs %s)"
             % (m2.group(1), raw),
             "the board answers ERR chunk too big and the update stops dead")

    # ---- out of order is REFUSED, not written ------------------------
    data = up[up.find("String BusUpdate::data"):]
    data = data[:data.find("\nString BusUpdate::end")]
    i_check = data.find("seq != next_")
    i_write = data.find("Update.write")
    t.ok(0 < i_check < i_write,
         "a chunk that is not the expected one is refused BEFORE it is written",
         "a bus loses a line now and then; writing the next chunk into the gap "
         "makes a board that boots into rubbish, with nothing saying why")
    t.contains(data, "expected",
               "and the refusal says which chunk it wants")

    # ---- a TRUNCATED line is caught, which base64 cannot do alone ----
    # This is not a theoretical hardening. Measured 2026-08-20 flashing a real
    # 1.29 MB image over a cable: one chunk in nine thousand arrived 64
    # characters short. 136 characters is a legal base64 length, so it decoded
    # cleanly into 102 bytes instead of 150 and NOTHING complained until FWEND
    # counted the whole image 48 bytes light - four minutes of transfer thrown
    # away, with no way to tell which chunk had done it.
    i_len = data.find("got != want")
    t.ok(0 < i_len < i_write,
         "a chunk that decoded to the wrong LENGTH is refused before it is "
         "written",
         "a truncated line is still valid base64 when what survives is a "
         "multiple of four, so decoding alone cannot tell a short chunk from a "
         "whole one - only the declared length can")
    t.contains(data, "send it again",
               "and the refusal asks for a repeat")
    i_next = data.find("next_++")
    t.ok(0 < i_len < i_next,
         "and it does NOT advance the sequence, so the repeat is accepted",
         "advancing past a chunk that was never written is how a hole gets "
         "into the image; leaving the counter alone is what makes a damaged "
         "line cost one round trip instead of the whole update")
    t.ok("FWDATA %d %d %s" in hub,
         "the hub really puts the length on the wire")
    t.ok(re.search(r'OK \\d\+ \(\\d\+\)', hub) or 'r"OK \\d+ (\\d+)"' in hub,
         "and it checks the running total the board reports back",
         "the board has counted the bytes it holds and says so in every reply; "
         "ignoring that is what let 48 missing bytes go unnoticed for four "
         "minutes")

    # ---- the image is checked before the board reboots ---------------
    end = up[up.find("String BusUpdate::end"):]
    end = end[:end.find("\nString BusUpdate::abort")]
    t.contains(end, "written_ != total_",
               "a short image is caught")
    t.contains(end, "Update.end(true)",
               "and the md5 is verified")
    fwend = router[router.find('cmd == "FWEND"'):]
    fwend = fwend[:fwend.find("\n    if (cmd ==", 1)]
    # Comments out, or a comment mentioning requestReboot passes for the call.
    # That is not hypothetical: the comment above this very line does mention
    # it, and the first version of this assertion read the comment instead.
    fwend = re.sub(r"//.*", "", fwend)
    i_ok = fwend.find('startsWith("OK")')
    i_boot = fwend.find("requestReboot(")
    t.ok(0 < i_ok < i_boot,
         "and the reboot happens ONLY when the image checked out",
         "rebooting into an image that failed its md5 is the one outcome this "
         "whole path exists to avoid - the board is still running working "
         "firmware right up to that line")
    t.contains(up, "setMD5",
               "the md5 the hub sent is what gets checked")
    t.ok("hashlib.md5" in hub, "and the hub really sends the image's own md5")

    # ---- and the md5 is NOT optional --------------------------------
    # Found by a model review 2026-08-20 and confirmed in the code: this read
    # `if (md5_.length() == 32 && ...)`, so FWBEGIN with no md5 started an
    # update with NO integrity check and said nothing about it. Everything else
    # here guards a different failure - the per-chunk length catches a
    # TRUNCATED line, the byte total catches a SHORT image - and neither
    # catches a CORRUPTED one. A flipped bit in a chunk that still decoded to
    # the declared length passed every guard, and FWEND answered OK and
    # rebooted the board into it. The hub always sent an md5, which is exactly
    # why it could sit there unnoticed: the only caller did the right thing.
    beg = up[up.find("String BusUpdate::begin"):]
    beg = beg[:beg.find("\nString BusUpdate::data")]
    t.ok("md5_.length() != 32" in beg,
         "an update with no md5 is REFUSED, not started",
         "without one, Update.end(true) checks that the write finished and "
         "nothing about what was written - so a damaged image boots")
    i_ref = beg.find("md5_.length() != 32")
    i_run = beg.find("running_ = true")
    t.ok(0 < i_ref < i_run,
         "and refused before the update is marked as running")
    t.contains(router, 'if (argc < 3) return "ERR usage: FWBEGIN <bytes> <md5hex>"',
               "the command itself requires it too")

    # ---- a failed send leaves the board on what it had ---------------
    run_bus = hub[hub.find("    def _run_bus"):]
    run_bus = run_bus[:run_bus.find("\n    def start(")]
    t.contains(run_bus, "FWABORT",
               "a send that dies tells the board to abandon the update")
    t.ok("keeps the firmware it already" in run_bus,
         "and says so, rather than leaving somebody guessing",
         "after a failed flash the first question is always whether the board "
         "still works; the answer should not require a reboot to find out")
    for attempt in ("range(4)", "expected"):
        t.contains(run_bus, attempt,
                   "a chunk that did not land is retried, not skipped")

    # ---- it goes through dev_cmd, so every transport is covered -------
    t.contains(run_bus, "dev_cmd(dev,",
               "the sender talks through dev_cmd")

    # ---- the two commands that do WORK get time to do it -------------
    # Every ordinary command answers in milliseconds, so dev_cmd waits 2 s.
    # These two are not questions: FWBEGIN erases most of two megabytes of
    # flash to reserve the slot, and FWEND hashes the whole image before it
    # will boot into it. Timing either out reports a FAILED update for one that
    # was working, which is the worst wrong answer available here — somebody
    # then reflashes a board that was already fine.
    for cmd, floor in (("FWBEGIN", 10), ("FWEND", 30)):
        # The call may be wrapped across lines, so look inside the call itself
        # rather than to the end of one line — the first version of this used
        # [^\n]* and failed on the wrapped one while the code was correct.
        call = run_bus[run_bus.find('dev_cmd(dev, "%s' % cmd):][:220]
        m3 = re.search(r"wait=(\d+)", call)
        if t.ok(m3, "%s asks for longer than the default" % cmd):
            t.ok(int(m3.group(1)) >= floor,
                 "%s waits at least %ds (got %ss)" % (cmd, floor, m3.group(1)),
                 "this is flash erase and an md5 over 1.3 MB, not a question")
    t.ok("/api/flash/bus" in hub, "and there is a route to start it")
    # dev_cmd is the one call that already speaks all of them - that is the
    # entire reason this path works over RS485 without any RS485 code in it.
    dc = hub[hub.find("def dev_cmd(dev, c"):]
    dc = dc[:dc.find("\ndef ", 1)]
    t.contains(dc, "usb_cmd",
               "which reaches a cable and the bus behind it")
    t.contains(dc, "robot_get",
               "and WiFi, so one sender covers all three")

    # ---- documented, because the next person will ask the same thing --
    md = (fw / "COMMANDS.md").read_text(encoding="utf-8")
    for n in ("FWBEGIN", "FWDATA", "FWEND", "FWABORT", "FWSTAT"):
        t.contains(md, "`%s" % n, "COMMANDS.md documents %s" % n)
    t.ok("DTR" in md and "IO0" in md,
         "and it says WHY esptool cannot do this over RS485",
         "the user asked exactly this - *why wifi can but rs485 can't i don't "
         "know* - and the answer belongs where the commands are, not in a "
         "chat message that scrolls away")
