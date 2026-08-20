"""A camera is just another module type — and that claim is what this checks.

The plan said the camera would be "just another type, costing the others
nothing" once the build was split. That is only true if adding a type really is
one declaration: if it needs a hand-edit in six places, the sixth is the one
that gets forgotten and a module type ends up half-registered.

So this checks the CHAIN, from the one file outwards: every type in
config/modules.json has a class, a build env, a generated factory entry, a
place in the hub's flash list — and none of it is a hand-kept second list.

Then the camera's own facts: it cannot be a servo board (the camera and the SD
card take every usable pin), its pins are therefore fixed rather than
configurable, and a picture is HTTP because a JPEG cannot travel on a
one-line channel.
"""
import json
import re

import qc as F

AREA = "firmware"
TITLE = "a module type is one declaration, and the camera is one of them"
SLOW = False


def run(t):
    import registry
    mods = registry.modules()
    t.ok(len(mods) >= 3, "the module registry declares the types (%s)"
         % ", ".join(mods))
    t.ok("cam" in mods, "the camera is one of them")

    ini = (F.FIRMWARE / "platformio.ini").read_text(encoding="utf-8", errors="replace")
    cmds = registry.commands()
    scopes = {c["scope"] for c in cmds}

    # ---- every declared type is wired all the way through -----------
    for ty, m in mods.items():
        hdr = F.FIRMWARE / "src" / m["header"]
        t.ok(hdr.is_file(), "%s: its class header exists (%s)" % (ty, m["header"]))
        if hdr.is_file():
            t.contains(hdr.read_text(encoding="utf-8", errors="replace"),
                       "class %s" % m["class"], "%s: declares %s" % (ty, m["class"]))
        t.contains(ini, "[env:mice_%s]" % ty, "%s: has its own build env" % ty)
        t.contains(ini, "-D MICE_TYPE_%s" % ty.upper(),
                   "%s: that env asks for its own code only" % ty)

    # ---- the C++ side is GENERATED from it, not kept by hand --------
    bt = F.generated("core/BuildTypes.h").read_text(encoding="utf-8", errors="replace")
    tab = F.generated("modules/ModuleTable.h").read_text(encoding="utf-8", errors="replace")
    t.contains(bt, "GENERATED", "BuildTypes.h is generated")
    t.contains(tab, "GENERATED", "and so is the module factory table")
    for ty, m in mods.items():
        t.contains(bt, "MICE_HAS_%s" % ty.upper(), "%s: has a build guard" % ty)
        t.contains(tab, 'new %s(sd)' % m["class"], "%s: the factory can make it" % ty)
        t.contains(tab, '"%s"' % ty, "%s: it is a known type" % ty)
    # A real board found this one: the generator wrote `#endif    "blank",` on
    # ONE line, so "blank" was part of the directive line and the compiler threw
    # it away. The board then refused `SET TYPE blank` — with a table that
    # looked perfectly correct in the source.
    for n, line in enumerate(tab.splitlines(), 1):
        st = line.strip()
        if st.startswith("#endif") or st.startswith("#else"):
            t.eq(st.split("//")[0].strip(), st.split()[0],
                 "ModuleTable.h:%d: nothing follows %s" % (n, st.split()[0]))
    t.contains(tab, '"blank"',
               "blank is in the table — a board must always be able to park")
    fac = (F.FIRMWARE / "src/modules/ModuleFactory.cpp").read_text(
        encoding="utf-8", errors="replace")
    for ty, m in mods.items():
        t.ok(m["class"] not in fac,
             "%s is NOT hand-listed in ModuleFactory.cpp" % m["class"],
             "a second list is the one that goes stale")
    t.ok(not (F.FIRMWARE / "src/core/BuildTypes.h").exists(),
         "no hand-written BuildTypes.h is left to disagree with the generated one")

    # ---- and the hub offers it without being told separately -------
    base, main = F.start_hub()
    info = json.loads(F.get(base + "/api/flash/images")[1])
    offered = {i["type"] for i in info.get("images", [])}
    for ty in mods:
        t.ok(ty in offered, "the hub offers to flash a %s" % ty,
             "the hub keeps its own list of types instead of reading the registry")

    # ---- the camera's own facts ------------------------------------
    t.ok("cam" in scopes, "the camera's commands are declared with scope cam")
    cam_cmds = {c["name"] for c in cmds if c["scope"] == "cam"}
    t.ok({"SNAP", "CAM"} <= cam_cmds, "SNAP and CAM exist (%s)" % sorted(cam_cmds))
    for c in cmds:
        if c["scope"] == "cam":
            t.ok(not c.get("motion"), "%s does not claim to move anything" % c["name"],
                 "a camera has no moving parts — marking it motion would stop shows")

    src = (F.FIRMWARE / "src/modules/cam/CamModule.cpp").read_text(
        encoding="utf-8", errors="replace")
    t.contains(src, "esp_camera_init", "the module starts the real sensor")
    t.contains(src, "psramFound", "and adapts to whether the board has PSRAM")
    # not returning a frame buffer stalls the camera after a few shots
    t.contains(src, "esp_camera_fb_return", "every frame buffer is given back")
    t.contains(src, '"camera"', "it declares the camera capability")

    # ---- a frame is borrowed, and given back exactly once ------------
    # The driver reclaims and REFILLS its buffer the moment it is returned. The
    # first pictures off the board were a 200 with 353 bytes of a 13,000-byte
    # frame, because the response was still queued when the frame went back.
    code = re.sub(r"//.*", "", src)
    for call in ("malloc(", "memcpy("):
        t.ok(call not in code, "CamModule does not %s a frame" % call.rstrip("("),
             "the module lends its frame; only the HTTP route makes a copy")
    t.contains(src, "inflight_",
               "exactly one frame is on loan, so give() is safe to call twice")
    web = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(
        encoding="utf-8", errors="replace")
    cam_route = web[web.find('server_.on("/api/cam.jpg"'):]
    cam_route = cam_route[:cam_route.find("#endif")]
    t.contains(cam_route, "memcpy(copy",
               "the HTTP route copies the frame before sending it")
    t.contains(cam_route, "free(copy)", "and frees the copy when the send ends")
    give = cam_route.find("cam->give(fb)")
    send = cam_route.find("req->send(res)")
    t.ok(0 <= give < send,
         "the frame goes back to the driver BEFORE the response is queued")
    t.contains(src, "psramSick_",
               "a board whose PSRAM never reached the heap says so at boot")

    # ---- PSRAM stays OFF on the camera build ------------------------
    # Measured, not assumed: with BOARD_HAS_PSRAM set, ANY large HTTP response
    # kills that board — GET / (the module page) died the same way the picture
    # did, while the identical core serves that page fine on a board without
    # PSRAM. Turning it back on costs the website.
    cam_env = ini[ini.find("[env:mice_cam]"):]
    nxt = cam_env.find("[env:", 1)
    cam_env = cam_env[:nxt] if nxt > 0 else cam_env
    t.contains(cam_env, "-UBOARD_HAS_PSRAM", "the camera build disables PSRAM")
    t.ok("PSRAM IS DELIBERATELY OFF" in cam_env,
         "and says why, so nobody re-enables it by tidying",
         "a bare flag gets removed by the next person who reads the board docs")
    t.contains(src, "FRAMESIZE_QVGA",
               "the module still works without PSRAM (smaller frames)")

    # ---- and the SD card may not be mounted on camera pins ----------
    # The shared SPI defaults (5, 18, 19, 23) ARE the camera's data lines. A
    # failed mount still leaves the bus holding them.
    sd = (F.FIRMWARE / "src/core/SDStore.cpp").read_text(encoding="utf-8", errors="replace")
    beg = sd[sd.find("bool SDStore::begin"):]
    beg = beg[:beg.find("\n}")]
    beg = re.sub(r"//.*", "", beg)      # the comment above it NAMES SPI.begin
    spi = beg.find("SPI.begin")
    guard = beg.find("< 0")
    t.ok(0 <= guard < spi,
         "SDStore refuses a disabled pin BEFORE it claims the SPI bus",
         "SPI.begin() on -1, or on another peripheral's pins, still takes them")
    campins = (F.FIRMWARE / "config/esp32_hardware_cam_module.h").read_text(
        encoding="utf-8", errors="replace")
    t.contains(campins, "#define SD_CS_PIN   -1",
               "and a cam board declares it has no SPI card")

    # ---- picture quality, measured not guessed -----------------------
    # Every frame arrived with single-pixel coloured lines scattered through
    # it — whole scanlines corrupted, which looks like sensor noise and is not.
    # Measured, corrupted rows per frame: 20 MHz clock vs 10 MHz, and then by
    # frame size (qqvga 0.8, qvga 26.4, vga 12.8, svga 1.6).
    t.contains(campins, "#define CAM_XCLK_HZ 10000000",
               "the sensor clock is 10 MHz, not the usual 20")
    t.ok("corrupted" in campins or "coloured lines" in campins,
         "with the reason, so it is not 'optimised' back to 20 MHz")
    for fn, why in (("set_bpc", "black-pixel correction"),
                    ("set_wpc", "white-pixel correction"),
                    ("set_lenc", "lens shading correction")):
        t.contains(src, fn + "(s, 1)", "the sensor's %s is enabled" % why)
    # The start size is per SENSOR now. SVGA was measured on an OV2640 and was
    # applied to every board; a real ESP32-CAM here turned out to be an OV5640,
    # a five megapixel part, and running it at SVGA while the frame buffer was
    # allocated for the init size failed every capture after a clean init.
    t.contains(src, "startSize(s->id.PID",
               "the start size is chosen by which sensor this actually is")
    start = src[src.find("static framesize_t startSize("):]
    start = start[:start.find(chr(10) + "}") + 2]
    t.contains(start, "FRAMESIZE_SVGA",
               "an OV2640 still starts where it measured cleanest")
    t.contains(start, "return initSize",
               "and a sensor nobody has measured keeps the size its buffer "
               "was allocated for")
    t.contains(src, "sensorName(", "the board says which sensor it found")
    # ...and it really TRIES them. Naming the table is not the same as looping
    # over it: the first version of this assertion passed against a loop that
    # had been disabled.
    loop = src[src.find("esp_camera_init(&c);"):]
    loop = loop[:loop.find("if (err != ESP_OK) {")]
    t.contains(loop, "b < CAM_BOARD_COUNT",
               "and it tries every pin layout it knows until one answers")
    t.contains(loop, "esp_camera_deinit",
               "letting the driver go between attempts, or the next one fails "
               "for the wrong reason")
    # The table moved OUT of the C++ on 2026-08-20, into
    # firmware/config/cam_boards.json, so that adding a board is one entry in
    # data and the hub can draw that board's pin diagram from the same file.
    # This assertion followed it rather than being deleted: the property it
    # guards - one table, not a branch per board - is exactly the same, and it
    # is the reason a camera nobody has seen before can still be wired up.
    t.contains(src, 'include "modules/cam/CamBoards.h"',
               "the layouts come from the generated table")
    # ---- it says WHICH board, even when the compiled-in pins worked --
    # Found by the five-model panel on 2026-08-20. esp_camera_init is tried
    # first with the compiled-in pins, so on an AI-Thinker - the commonest
    # board - it succeeds and the loop never runs. board_ then kept its default
    # and the hub showed the pin diagram marked as a GUESS, about the one board
    # the firmware is certain of.
    first = src[src.find("esp_err_t err = esp_camera_init(&c);"):]
    first = first[:first.find("for (int b = 0; err != ESP_OK")]
    t.contains(first, "board_ = m.name",
               "a board found on the compiled-in pins is still named")
    t.contains(first, "CAM_XCLK_PIN",
               "by matching those pins against the table, not by assuming")

    # ---- LEDs belong to the board, not to the build ------------------
    # BOTH paths must adopt them: the compiled-in attempt and the loop. The
    # first version of this asserted the word appeared anywhere in the file,
    # which stayed true when the compiled-in path stopped calling it.
    t.contains(first, "adoptLeds(board_)",
               "the compiled-in path takes that board's LED pins")
    loop_ok = src[src.find("for (int b = 0; err != ESP_OK"):]
    loop_ok = loop_ok[:loop_ok.find("if (err != ESP_OK) {")]
    t.contains(loop_ok, "adoptLeds(board_)",
               "and so does a board found by trying the table")
    t.contains(src, "if (flashPin_ >= 0)",
               "and a board with no flood LED drives nothing",
               )
    t.ok("digitalWrite(CAM_FLASH_PIN, flash_" not in src,
         "the compiled-in flash pin is never driven blindly",
         "GPIO 4 is the flood LED on an AI-Thinker and XCLK on an ESP-EYE: "
         "driving it because the build said so breaks the camera")

    # ---- and the SCCB probe asks every bus, not just ours ------------
    probe = src[src.find("String CamModule::probeSensor"):]
    probe = probe[:probe.find("String CamModule::probeBus")]
    t.contains(probe, "CAM_BOARDS[b].siod",
               "the sensor probe tries every SCCB pin pair the table knows",
               )
    t.contains(probe, "on any pin pair",
               "and says so when nothing answers anywhere")

    t.ok("CAM_BOARDS[] = {" not in src,
         "and are not ALSO written out in the C++",
         "two copies of a pin map is two chances for the diagram and the "
         "wiring to disagree, and the diagram is what someone wires to")
    # ...but NOT as the init size: the frame buffer is allocated for that, and
    # SVGA in internal RAM fails outright with `camera init failed 0x105`.
    init = src[src.find("camera_config_t c = {}"):src.find("esp_camera_init")]
    t.contains(init, "psram ? FRAMESIZE_SVGA : FRAMESIZE_QVGA",
               "the INIT size still fits a board with no PSRAM")

    # a live viewer that dies must not lock the camera out for good
    t.contains(web, "camStreamAt_",
               "a stalled live viewer releases the camera on its own")

    # The pins are FIXED, not configurable: they are etched onto the board, so
    # a pin picker for them could only ever break a working camera.
    pins = (F.FIRMWARE / "config/esp32_hardware_cam_module.h").read_text(
        encoding="utf-8", errors="replace")
    t.contains(pins, "CAM_SIOD_PIN", "the camera pins are compile-time constants")
    hw = (F.FIRMWARE / "src/core/HwConfig.cpp").read_text(encoding="utf-8", errors="replace")
    t.ok("cam" not in re.findall(r'"(\w+)"\}?,\s*(?:true|false)\}', hw),
         "and they are not offered on the pin page")
    t.ok("CAM_" not in hw, "HwConfig does not touch the camera pins")

    # A picture is HTTP: it cannot travel as a one-line reply on RS485/serial.
    web = (F.FIRMWARE / "src/core/WebPortal.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(web, "/api/cam.jpg", "a frame is served over HTTP")
    # a lift would otherwise carry a route it can never answer
    t.contains(web, "MICE_HAS_CAM", "and only on a camera build")
    # ...and EVERY camera route must be inside a guard, not just the first one.
    # The stream route was added after the #endif: the camera build compiled,
    # and nong, lift and the all-types build all broke.
    depth, unguarded = 0, []
    for line in web.splitlines():
        st = line.strip()
        if st.startswith("#if"):
            depth += 1
        elif st.startswith("#endif"):
            depth = max(0, depth - 1)
        elif "CamModule" in st and depth == 0 and not st.startswith("//"):
            unguarded.append(st[:60])
    t.eq(unguarded, [], "every mention of CamModule is behind a build guard")
    ui = (F.FIRMWARE / "src/web/WebUI.h").read_text(encoding="utf-8", errors="replace")
    t.contains(ui, "<!--#type cam-->", "the camera card is marked for cam builds only")
    t.contains(ui, "showCard('camCard',has('camera'))",
               "and shown by capability like every other card")

    # ---- the picture must follow the page's transport ---------------
    # The hub serves this same page for a module it reaches over WiFi or a
    # cable, and re-addresses /api/* by patching window.fetch. An <img src>
    # never goes through fetch: it asked the HUB for /api/cam.jpg, got a 404,
    # and the card blamed the ribbon cable on a camera that worked perfectly.
    shot = ui[ui.find("function camShot"):]
    shot = shot[:shot.find("\nfunction ")]
    t.contains(shot, "fetch(", "the page FETCHES the frame")
    t.ok(".src='/api/cam.jpg" not in shot.replace('"', "'"),
         "and never points an <img> straight at the endpoint",
         "an <img src> bypasses the hub's transport shim")
    t.contains(shot, "r.text()",
               "a refusal is shown in the module's own words, not guessed at")
    hub = (F.HUB / "main.py").read_text(encoding="utf-8", errors="replace")
    t.contains(hub, 'what == "cam.jpg"',
               "the hub can fetch a frame for a module it is serving")
    dev_cam = hub[hub.find('what == "cam.jpg"'):]
    dev_cam = dev_cam[:dev_cam.find('if what == "download"')]
    t.contains(dev_cam, "501",
               "and refuses over a cable rather than pretending")
    t.contains(dev_cam, "open this module over WiFi",
               "saying what to do instead")
    cmds_md = (F.FIRMWARE / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    for name in ("SNAP", "/api/cam.jpg"):
        t.contains(cmds_md, name, "COMMANDS.md documents %s" % name)
