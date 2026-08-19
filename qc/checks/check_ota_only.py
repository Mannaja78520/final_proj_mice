"""A PC with only the app image can still update a board over WiFi.

This is the situation of every machine that was HANDED the firmware instead of
building it — the second laptop at a venue, or anything installed from the app
branch. It has `firmware.bin` and nothing else, because that is the only file
an over-the-air update sends.

Until 2026-08-19 such a PC was told it had nothing:

  * `flash_image` reported `ready` only when all four flash parts were present
    — the bootloader and the partition table included, neither of which an OTA
    can use, because a running board cannot rewrite them;
  * so `start_ota` refused, and the Firmware screen hid the image entirely and
    printed the `pio run` command instead.

Both are wrong in the same way: they asked for what a CABLE write needs in
order to do something else. The distinction is now explicit — `ready` means a
cable write is possible, `ota_ready` means an update over WiFi is — and this
check holds both, because collapsing them again would look like a tidy-up.
"""
import json
import shutil
import tempfile
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "an app image alone is enough to update over WiFi"


def run(t):
    import sys
    sys.path.insert(0, str(F.HUB))
    import main  # noqa: PLC0415 - the module under test

    real = main.flash_image("nong")
    if not t.ok(real.get("ready"), "this PC has a full nong image to work from",
                "build it: pio run -e mice_nong"):
        return

    # A build folder holding ONLY the app image - what a PC that was given the
    # firmware has. Built as a copy so the real one is never touched.
    tmp = Path(tempfile.mkdtemp(prefix="qc_otaonly_"))
    try:
        d = tmp / ".pio" / "build" / "mice_nong"
        d.mkdir(parents=True)
        src = [q for _off, q in real["parts"] if q.endswith("firmware.bin")][0]
        shutil.copy(src, d / "firmware.bin")

        was = main.FIRMWARE_DIR
        main.FIRMWARE_DIR = tmp
        try:
            im = main.flash_image("nong")
        finally:
            main.FIRMWARE_DIR = was

        t.ok(not im["ready"],
             "a cable write is correctly refused - the bootloader is missing",
             "esptool writes every part, so this one really cannot be done")
        t.ok(im["ota_ready"],
             "but an update over WiFi is offered",
             "OTA sends the app image and nothing else; refusing here told a "
             "PC that had exactly the right file that it had nothing")
        t.contains(str(im["missing"]), "bootloader",
                   "and it still says which parts are absent")

    finally:
        shutil.rmtree(tmp, ignore_errors=True)

    # ---- the two are kept apart on purpose --------------------------
    src_py = (F.HUB / "main.py").read_text(encoding="utf-8")
    i = src_py.find("def start_ota")
    body = src_py[i:i + 1400]
    code = "".join(l for l in body.splitlines(True) if not l.strip().startswith("#"))
    t.ok('im["ready"]' not in code,
         "start_ota does not ask whether a CABLE write would be possible",
         "it used to demand all four parts in order to send one of them, so a "
         "PC holding exactly the right file was refused")
    t.contains(code, "firmware.bin",
               "it asks for the one file an over-the-air update carries")

    j = src_py.find("def send_firmware")
    t.contains(src_py[j:j + 900], "ready",
               "while remote flash still needs the FULL set",
               )

    # ...and the screen offers what each PC can really do.
    page = (F.HUB / "web" / "hub.html").read_text(encoding="utf-8")
    t.contains(page, "i.ready || i.ota_ready",
               "the Firmware screen lists an image it can write ANY way")
    t.contains(page, "!img.ready && !img.ota_ready",
               "and only calls one unavailable when it can do neither")
    k = page.find("cable write needs the full image")
    t.ok(k > 0,
         "and says so on the button rather than hiding the board",
         "a disabled control has to explain itself or it reads as broken")
