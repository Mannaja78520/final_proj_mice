"""The radio can be seen and changed without rebooting the module.

Two bugs, both found on real hardware with two ESP32s on the bench:

1. **A half-eaten log line came back as a command reply.** The hub cleared the
   input buffer before every command. If the firmware was midway through
   printing `[wifi] disconnected, reason=201 (AP not found: ... 5GHz-only ...)`
   the head was thrown away and the tail — `Hz-only network ...)` — survived
   with no `[tag]` on it, so the log filter did not recognise it and it was
   returned as the reply. `SET WIFI "manny" qwertyui` literally answered
   "Hz-only network - ESP32 is 2.4GHz only)". Any command could be hit; only
   the timing decided which.

2. **WiFi needed a reboot to apply.** `SET WIFI <ssid>` answered "(reboot to
   apply)" and there was no `WIFI` command at all. At a show that means the
   only way to fix a typo'd network name is to power-cycle a module, which
   leaves the arm wherever it stopped.

Both are asserted here — the first against a fake port that deliberately
splits a log line, the second against the firmware source and the registry.
"""
import re
import time

import fake_serial
import qc as F
import registry

AREA = "wifi"
TITLE = "WiFi is visible and changeable live, and a log line is never a reply"
SLOW = False


def run(t):
    fake_serial.reset()
    base, main = F.start_hub()

    # ---- 1. the partial log line ---------------------------------------
    # Push a log line into the port with NO trailing newline, exactly as a
    # board does when it is still printing when the next command arrives.
    F.cmd(base, "PING")            # make the hub open the port first
    ser = F.hub_serial(main, fake_serial.PORT)
    if not t.ok(ser, "the hub has the port open"):
        return
    half = b"[wifi] disconnected, reason=201 (AP not found: wrong SSID, or 5G"
    ser._rx += half                      # noqa: SLF001 - that is the point
    s, b = F.cmd(base, "PING")
    t.eq(s, 200, "the command still answers")
    t.ok(b.startswith("PONG"),
         "a command interrupted mid-log-line still gets its OWN reply",
         "got the orphan tail of a log line instead: %r" % b)
    t.ok("Hz-only" not in b and "GHz" not in b,
         "and no scrap of the log line leaks into it", b)

    # the next command must be clean too — the drain must not have eaten it
    s, b = F.cmd(base, "PING")
    t.ok(b.startswith("PONG"), "the command after that is clean as well", b)

    # a WHOLE log line was always filtered; prove that still holds
    ser._rx += b"[wifi] connecting to \"manny\"\n"    # noqa: SLF001
    s, b = F.cmd(base, "PING")
    t.ok(b.startswith("PONG"), "a complete log line is still skipped", b)

    # THE HARD ONE. The orphan tail arrives a moment AFTER the buffer is
    # cleared, so draining cannot see it — there is nothing in flight to wait
    # for yet. On the bench this shifted every reply by one: PING answered
    # "son=8", the tail of "[wifi] disconnected, reason=8". 49 of 60 commands
    # were wrong while the radio was reconnecting.
    import threading

    def late_orphan():
        time.sleep(0.02)
        with ser._rxlock:                       # noqa: SLF001
            ser._rx += b"son=8\n"
    for _ in range(6):
        threading.Thread(target=late_orphan, daemon=True).start()
        s, b = F.cmd(base, "PING")
        if not t.ok(b.startswith("PONG"),
                    "a log-line tail arriving mid-command is not mistaken for the reply",
                    "the reply came back as %r" % b):
            break
    else:
        t.ok(True, "six commands in a row survive a stream of log-line tails")

    # ---- 2. no reboot to change the radio ------------------------------
    hub = (F.CODE / "main_python/main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(hub, "_drain_to_line_boundary",
               "the hub drains to a line boundary instead of cutting blind")
    t.ok(not re.search(r"^\s+ser\.reset_input_buffer\(\)", hub, re.M) or
         hub.count("ser.reset_input_buffer()") == 1,
         "and reset_input_buffer is only used inside that helper",
         "a call site still clears the buffer without waiting for a newline")

    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(
        encoding="utf-8", errors="replace")
    m = re.search(r'if \(cmd == "WIFI"\)(.{0,400})', router, re.S)
    if t.ok(m, "the firmware has a WIFI command"):
        t.contains(m.group(1), "wifiCommand", "which asks the radio directly")

    m = re.search(r'if \(what == "WIFI"\)(.*?)\n        \}', router, re.S)
    if t.ok(m, "SET WIFI is still there"):
        body = m.group(1)
        t.contains(body, "applyCreds",
                   "and now joins the network immediately")
        t.contains(body, "OK joining", "and says so")
        # "reboot to apply" may still exist — but ONLY as the fallback for a
        # board so early in boot that there is no radio object yet. Every one
        # of them must sit behind a WebPortal::instance() test.
        stray = [i for i in range(len(body))
                 if body.startswith("reboot to apply", i)
                 and body.rfind("WebPortal::instance()", 0, i) < 0]
        t.ok(not stray,
             "so the happy path never tells the user to reboot",
             "a 'reboot to apply' reply is reachable with the radio running")

    portal = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    for verb in ("ON", "OFF", "AP", "RETRY", "SCAN", "CLEAR"):
        t.contains(portal, '"%s"' % verb, "WIFI %s is handled" % verb)
    # There must be a way BACK to the network compiled into the firmware.
    # Without it a board could only be moved from one named network to
    # another, and a module pointed at a bench hotspot could never rejoin the
    # real show network without a reflash.
    m = re.search(r'if \(a == "CLEAR"\)(.{0,300})', portal, re.S)
    if t.ok(m, "WIFI CLEAR exists"):
        t.contains(m.group(1), 'setWifi("", "")',
                   "and forgets the credentials stored on the board")
        t.contains(m.group(1), "applyMode",
                   "then rejoins immediately, without a reboot")
    t.contains(portal, "id_->wifiSsid().length() ? id_->wifiSsid() : String(WIFI_SSID)",
               "credentials set on the board win over the compiled-in default")
    t.contains(portal, "scanNetworks(true)",
               "SCAN is asynchronous — a blocking scan would stall a moving joint")
    # a comment may SAY delay(); only real code counts
    code = re.sub(r"//[^\n]*", "", portal)
    t.ok("delay(" not in code and "scanNetworks(false)" not in code,
         "and nothing in the radio path blocks the loop",
         "a delay() or a blocking scan here stops the servo interpolation mid-move")

    # The website must be started AFTER the radio. AsyncWebServer::begin binds
    # a TCP socket and lwip has no mailbox until an interface exists — getting
    # this backwards panics the chip in a boot loop with
    # "assert failed: tcpip_api_call ... (Invalid mbox)". Found by flashing it,
    # so it is asserted here and never has to be found that way again.
    m = re.search(r"void WebPortal::applyMode\(.*?\n\}", portal, re.S)
    if t.ok(m, "applyMode brings the radio up"):
        body = m.group(0)
        for radio in ("WiFi.mode(WIFI_AP)", "WiFi.mode(WIFI_AP_STA)"):
            i = body.find(radio)
            if i < 0:
                continue
            j = body.find("ensureServer()", i)
            t.ok(j > i,
                 "the radio is up before the website starts (%s)" % radio,
                 "server_.begin() before an interface exists = boot loop")

    # ---- 2b. the OTHER half of the same bug, on the board ---------------
    # Serial.println() is print(text) then a separate print("\n"), so a WiFi
    # event on another task can land BETWEEN them and glue its log line onto
    # the reply. Seen on the bench:
    #   OK joining "lift-test" now (WIFI for progress)[wifi] disconnected, reason=8
    # A reply must go out as one write.
    mainc = (F.FIRMWARE / "src/main.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(mainc, "emitLine", "the board writes a reply in one call")
    code = re.sub(r"//[^\n]*", "", mainc)
    t.ok("Serial.println(router.handle" not in code.replace(" ", "") and
         "Serial.println(serialBuf" not in code.replace(" ", ""),
         "and never with println, which another task can cut in half",
         "a reply still goes out as two writes")
    m = re.search(r"static void emitLine\(.*?\n\}", mainc, re.S)
    if t.ok(m, "emitLine exists"):
        body = m.group(0)
        t.ok("println" not in body and body.count("Serial.print") == 1,
             "as ONE Serial.print, so the newline cannot be separated from it",
             "emitLine emits in more than one call: %r" % body)
        t.ok(body.count(chr(92) + "n") == 2,
             "with the newline built into the same string",
             "the reply text and its line ending are not one string")

    # ---- 3. it is a real registered command, not a hidden one -----------
    cmds = {c["name"]: c for c in registry.commands()}
    if t.ok("WIFI" in cmds, "WIFI is declared in config/commands.json"):
        t.contains(cmds["WIFI"]["args"], "RETRY", "with its arguments documented")
    docs = (F.CODE / "firmware/COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(docs, "`WIFI RETRY`", "and COMMANDS.md describes it")

    # ---- 4. the module shares its WiFi while connected ------------------
    # A module that joins the network used to drop its AP, so a board out of
    # router range had nothing to connect to.
    t.contains(portal, "WIFI_AP_STA",
               "a connected module keeps its own AP up (AP_STA), so it can share")
    m = re.search(r"case W_CONNECTING:(.*?)break;", portal, re.S)
    if t.ok(m, "the connect transition exists"):
        t.ok("WiFi.mode(WIFI_STA)" not in m.group(1),
             "and joining the network does NOT tear the shared AP down",
             "switching to STA-only on connect kills the AP other modules use")
