"""New firmware over WiFi, without a cable — and without a way to brick a board.

The plan assumed this was blocked until the binaries shrank. It was not: the
partition table already in use (min_spiffs.csv) has TWO app slots, app0 and
app1, 1.875 MB each. An update is written to the slot that is NOT running and
only becomes the boot choice once it is complete and valid, so a failed update,
a dropped WiFi link or a PC that walks away half way leaves the board booting
exactly the firmware it already had.

That safety is the whole reason OTA is allowed to exist here, so it is what
this checks first: two slots, and every module type still fitting one with room
to spare. Then the board's side (it refuses while moving — a flash write stalls
the servo loop) and the hub's side (it sends the image and reports the board's
own words when it is refused).
"""
import json
import re
import time
from pathlib import Path

import fake_wifi
import qc as F

AREA = "firmware"
TITLE = "OTA: new firmware over WiFi, into the slot that is not running"
SLOW = False

SLOT = 0x1E0000          # 1,966,080 bytes — app0 and app1 in min_spiffs.csv
MARGIN = 0.85            # a build using more than 85% of a slot is too close


def _status(base):
    return json.loads(F.get(base + "/api/flash")[1])


def _wait_done(base, limit=30.0):
    end = time.time() + limit
    while time.time() < end:
        s = _status(base)
        if not s["running"]:
            return s
        time.sleep(0.05)
    return _status(base)



def _fn(text, name):
    """One function's source, brace matched, so an assertion cannot pass on
    a different function that happens to contain the same words."""
    i = text.find(name)
    if i < 0:
        return ""
    j = text.index("{", i)
    depth = 0
    while j < len(text):
        if text[j] == "{":
            depth += 1
        elif text[j] == "}":
            depth -= 1
            if depth == 0:
                return text[i:j + 1]
        j += 1
    return text[i:]


def run(t):
    # ---- 1. there really are two app slots ---------------------------
    ini = (F.FIRMWARE / "platformio.ini").read_text(encoding="utf-8", errors="replace")
    m = re.search(r"board_build\.partitions\s*=\s*(\S+)", ini)
    if not t.ok(m, "the build names a partition table"):
        return
    table = m.group(1)
    t.eq(table, "min_spiffs.csv", "it is the two-app-slot table")
    csv = (Path.home() / ".platformio" / "packages" /
           "framework-arduinoespressif32" / "tools" / "partitions" / table)
    if t.ok(csv.is_file(), "the partition table exists on this PC", str(csv)):
        text = csv.read_text(encoding="utf-8", errors="replace")
        t.contains(text, "ota_0", "there is an app slot to run from")
        t.contains(text, "ota_1", "and a SECOND one to update into")
        t.contains(text, "otadata", "plus the record of which one to boot")

    # ---- 2. and every module type fits one, with room --------------
    # This is the number the plan got wrong: the floor is the core, not the
    # module, so "it will be well under 1 MB" was never going to be true.
    for env in ("mice_nong", "mice_lift"):
        b = F.FIRMWARE / ".pio" / "build" / env / "firmware.bin"
        if not b.is_file():
            t.ok(True, "%s is not built here — skipped" % env)
            continue
        size = b.stat().st_size
        t.ok(size < SLOT * MARGIN,
             "%s fits an OTA slot with room (%.2f of %.2f MB)"
             % (env, size / 1048576.0, SLOT / 1048576.0),
             "an image that nearly fills the slot leaves no margin for growth")

    # ---- 3. the board's side ---------------------------------------
    web = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(web, '"/api/ota"', "the module accepts firmware over HTTP")
    ota = web[web.find('server_.on("/api/ota"'):]
    ota = ota[:ota.find("server_.onNotFound")]
    t.contains(ota, "Update.begin", "using the ESP32's own updater")
    t.contains(ota, "Update.end", "and finishing it properly")
    t.contains(ota, "requestReboot", "then rebooting into the new firmware")
    t.contains(ota, "Update.abort", "a bad write is aborted, not left half done")
    # Refusing while the robot is moving is not politeness: writing flash
    # stalls the servo loop, and a reboot mid-show is worse than waiting.
    t.contains(ota, "busy()", "it refuses while the module is moving")
    t.contains(ota, "running()", "and while a sequence is playing")
    t.contains(ota, "force", "with a way to override when you mean it")

    # the board can also SAY where an update would go, before you send one
    router = (F.FIRMWARE / "src/core/CommandRouter.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(router, "esp_ota_get_next_update_partition",
               "OTA reports which slot an update would use")
    import registry
    decl = {(c["name"], c["scope"]) for c in registry.commands()}
    t.ok(("OTA", "core") in decl, "the OTA command is declared like every other")
    cmds_md = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.contains(cmds_md, "/api/ota", "COMMANDS.md documents the endpoint")

    # ---- 4. the hub's side, end to end -----------------------------
    ip = fake_wifi.start()
    fake_wifi.MODULE.reset()
    base, main = F.start_hub()

    im = json.loads(F.get(base + "/api/flash/images")[1])
    ready = [i for i in im.get("images", []) if i["ready"]]
    if not ready:
        t.give_up("no firmware built on this PC — run pio run -e mice_nong")
    ty = ready[0]["type"]

    # a module that is MOVING must not be updated out from under itself
    fake_wifi.MODULE.busy = True
    F.post(base + "/api/ota?ip=%s&type=%s" % (ip, ty))
    s = _wait_done(base)
    t.ok(s["ok"] is False, "an OTA onto a moving robot fails")
    t.contains(s["error"].lower(), "moving",
               "and the hub repeats the board's own reason")

    # ...and the normal case really sends the firmware
    fake_wifi.MODULE.busy = False
    st = json.loads(F.post(base + "/api/ota?ip=%s&type=%s" % (ip, ty))[1])
    t.eq(st.get("how"), "wifi", "the job knows it is going over the air")
    s = _wait_done(base)
    t.ok(s["ok"] is True, "the update is accepted", s.get("error"))
    t.eq(s["percent"], 100, "and reaches 100%")
    sent = fake_wifi.MODULE.ota
    built = (F.FIRMWARE / ".pio" / "build" / ("mice_" + ty) / "firmware.bin").read_bytes()
    t.ok(len(sent) == len(built),
         "the module received the whole image (%d of %d bytes)"
         % (len(sent), len(built)))
    t.ok(sent[:4096] == built[:4096] and sent[-4096:] == built[-4096:],
         "byte for byte, start and end",
         "a truncated or re-encoded image is a brick over the air")

    # only the app image travels: the bootloader and partition table are the
    # parts that could brick a board, and OTA does not touch them
    t.ok(len(sent) < SLOT, "and it is only the app image, not the whole flash")

    # ---- 5. one board at a time ------------------------------------
    r = json.loads(F.post(base + "/api/ota?ip=%s&type=nope" % ip)[1])
    t.ok(r.get("ok") is False, "an unknown type is refused")
    t.contains(r.get("error", ""), "pio run -e mice_nope",
               "with the command that would build it")

    # ---- 6. the page offers it, and says what it does --------------
    hub = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8", errors="replace")
    t.contains(hub, "/api/ota", "the hub page can update a module over WiFi")
    # A2-2: one screen writes firmware, over a cable or over WiFi, so the OTA
    # path is fwWrite. Same properties, one implementation instead of two
    # that drifted apart.
    fn = _fn(hub, "async function fwWrite(")
    # Was: contains "confirm(". That matched the browser's own confirm box,
    # which named only an IP address. A1-4 replaced it with a panel that names
    # the board, the link and the PC — so assert THAT, not the old spelling.
    t.contains(fn, "confirmFlash(", "and asks first")
    t.contains(fn, "via:", "saying how the board is reached")
    t.contains(fn, "name:", "and which board it is, not just its address")
    t.contains(fn, "keeps the firmware it has now",
               "explaining that a failed update is not a brick")
    # Progress is announced from the row template, which is where the row is
    # described now — one shape, cloned per board, instead of a string built
    # inside the script.
    tpl = hub[hub.find('<template id=?tplFwTarget?>'.replace('?', chr(34))):]
    tpl = tpl[:tpl.find('</template>')]
    # A comment saying aria-live is not aria-live: the first version of this
    # assertion passed on the note explaining it, with the attribute removed.
    tpl = re.sub(r"<!--.*?-->", "", tpl, flags=re.S)
    t.contains(tpl, "aria-live", "progress is announced, not just painted")

    # WHICH firmware is sent is still asked, not assumed — it is the image row
    # whose button you press, and that image's type is what travels. This is
    # also how a board becomes a different module type without a cable.
    t.contains(fn, "encodeURIComponent(img.type)",
               "it asks which firmware to send")
    target = _fn(hub, "function fwTarget(")
    t.contains(target, "board.type !== img.type",
               "with the board's current type shown against the one offered")
    t.contains(target, "runs ", "in words, on the board it would replace")

    hub2 = hub[hub.find("async function applyTypeAfterFlash"):]
    hub2 = hub2[:hub2.find("\n// kept so anything")]
    t.contains(hub2, "SET TYPE", "a type change is completed on the board itself")
    t.contains(hub2, "REBOOT", "and it is rebooted into the new type")
    t.contains(fn, "'wifi:' + board.ip",
               "and the finished write is told which board it was")
    watch = _fn(hub, "function fwWatch(")
    t.contains(watch, "applyTypeAfterFlash",
               "which the update triggers once the firmware is on")
