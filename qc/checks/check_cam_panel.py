"""The camera's settings on its own page, and a way in that is not the module.

Two things asked for on 2026-08-21:

*make the esp32 cam can setting all everything* — the firmware grew 24
settings, and the board's own website still showed four. Then, plainly:
*make firmware update the web too. not only in hub*.

*how to go to camera view while not go to the module do you have tool?* —
watching a camera meant opening that board's entire website and finding the
Camera card on it.

WHAT MUST STAY TRUE
-------------------
1. The panel is built from what the BOARD answers to `CAM LIST`, never from a
   list written into the page. That is the whole promise of the registry: a
   control added to config/cam_controls.json appears with no code touched. So
   the check reads the page and refuses to find control names in it.
2. `CAM LIST` has to carry enough for a page to draw itself — the group, the
   label, whether this sensor HAS the control, and what it depends on. Without
   those the page would have to know them, which puts the list back in code.
3. The camera app is one entry in a registry, like every other app here.
4. A camera reachable only on a cable cannot be watched at all: /api/dev/cam.jpg
   refuses USB and RS485 as surely as cam.stream does, because a JPEG does not
   fit on a one-line command channel. The page must not offer a button that
   the transport will refuse.
"""
import json
import re
import sys

import qc as F

AREA = "ui"
TITLE = "the camera's settings draw themselves, and a camera can be watched on its own"
SLOW = False

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402

UI = F.FIRMWARE / "src" / "web" / "WebUI.h"
CAM = F.FIRMWARE / "src" / "modules" / "cam" / "CamModule.cpp"
APP = F.CODE / "apps" / "camera" / "index.html"


def run(t):
    ui = UI.read_text(encoding="utf-8", errors="replace")
    cam = CAM.read_text(encoding="utf-8", errors="replace")

    # ---- the panel exists, on the BOARD's page ------------------------
    t.contains(ui, "camGroups", "the module's own page has a settings panel")
    t.contains(ui, "CAM LIST", "and fills it from what the board reports")
    t.contains(ui, "CAM AUTO", "with one control to put everything back")

    # ---- and it does NOT know the settings ---------------------------
    # The four that used to be hardcoded are the ones to look for: if the page
    # still names controls, adding the next one means editing this file, and
    # the registry has bought nothing.
    controls = json.loads(re.sub(r"^\s*//.*$", "",
                                 (F.FIRMWARE / "config" / "cam_controls.json")
                                 .read_text(encoding="utf-8"), flags=re.M))["controls"]
    named = [n for n in ("brightness", "contrast", "saturation", "wb_mode",
                         "aec_value", "agc_gain", "special_effect", "gainceiling")
             if ("'" + n + "'") in ui or ('"' + n + '"') in ui]
    t.ok(not named,
         "the page names no individual setting",
         "found %r written into the page — a new control would then need a "
         "code change, which is the thing the registry exists to prevent"
         % (named,))

    # ---- CAM LIST carries what a page needs to draw itself ------------
    for field in ("group=", "label=", "missing=", "needs="):
        t.contains(cam, field,
                   "CAM LIST reports %s so the page does not have to know it"
                   % field.rstrip("="))
    # every control really has a group, or it lands in the wrong place
    for name, c in sorted(controls.items()):
        t.ok(c.get("group") in ("basic", "exposure", "colour", "advanced"),
             "%s says which group it belongs to" % name,
             "got %r" % (c.get("group"),))
    # ...and a dependency names a control that exists
    for name, c in sorted(controls.items()):
        if not c.get("needs"):
            continue
        other = c["needs"].split("=")[0]
        t.ok(other in controls,
             "%s depends on %s, which exists" % (name, other),
             "a dependency on a control that is not there disables the row "
             "for a reason nobody can act on")

    # ---- the way in that is not the module page ----------------------
    apps = {a["id"]: a for a in registry.apps()}
    if not t.ok("camera" in apps, "the camera app is registered",
                "apps found: %r" % (sorted(apps),)):
        return
    t.eq(apps["camera"]["path"], "/app/camera/", "and the hub serves it")
    t.ok(APP.is_file(), "its page is there", str(APP))
    page = APP.read_text(encoding="utf-8", errors="replace")
    t.contains(page, "cam.stream", "it shows the live view")
    t.contains(page, "/api/mine", "built from the cameras the hub can reach")
    t.contains(page, "/mice.css", "and it uses the one design system")

    # ---- and it does not offer what a cable cannot do -----------------
    t.contains(page, "shot.disabled = !live",
               "a cable-only camera cannot be asked for a picture",
               )
    t.ok("A picture can be taken" not in page,
         "and the page does not claim otherwise",
         "cam.jpg refuses USB and RS485 too, not just the live view")
