"""The light strip's pin is chosen on the page, not compiled into the code.

Every pin on a board is set from its own website and kept in NVS - except the
WS2812 data pin, which was `RGB_LED_PIN 13`, fixed when the firmware was
built. FastLED is the reason: it takes the pin as a TEMPLATE parameter

    FastLED.addLeds<WS2812B, RGB_LED_PIN, GRB>(...)

so it cannot simply be a variable. The page therefore offered every pin but
that one, and said nothing about why - which is exactly the fault the standing
rule names: a value somebody can only change by editing code (panel finding,
2026-09-08; the user chose the picker over a note).

So the firmware carries a SWITCH with one instantiation per allowed pin,
generated from config/rgb_pins.json, and the page offers those. What this
holds:

  * the list is DATA - adding a pin is one line, no code;
  * a pin that cannot drive an output is refused by the generator rather than
    compiled into a strip that never blinks (34-39 are input-only, 6-11 are
    the flash chip);
  * the default really is in the list, or a board boots pointing at a case
    that does not exist;
  * the strip asks for the CHOSEN pin and falls back to the default rather
    than attaching to nothing;
  * and the pin picture marks the pin in use, not a hardcoded 13.
"""
import json
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

AREA = "firmware"
TITLE = "the light strip's pin is picked on the page, not compiled in"


def run(t):
    fw = F.FIRMWARE
    sys.path.insert(0, str(F.CODE / "tools"))
    import registry                                        # noqa: E402

    src = (fw / "config/rgb_pins.json")
    t.ok(src.is_file(), "the allowed pins live in a data file")
    data = json.loads(registry.strip_jsonc(src.read_text(encoding="utf-8")))
    pins = [int(p["gpio"]) for p in data["pins"]]
    t.ok(len(pins) >= 2, "with more than one to choose from", pins)
    t.ok(int(data["default"]) in pins,
         "and the default is one of them",
         "a default outside the switch boots a board onto a case that is not "
         "there, and the strip is dark with nothing to see")
    bad = [g for g in pins if 6 <= g <= 11 or g >= 34]
    t.eq(bad, [], "no pin on the list is input-only or owned by the flash chip")

    # ---- the generated switch ------------------------------------------
    gen = fw / "generated/modules/lift/RgbPins.h"
    t.ok(gen.is_file(), "the switch is generated for the lift build")
    text = gen.read_text(encoding="utf-8", errors="replace")
    for g in pins:
        t.contains(text, "case %d: FastLED.addLeds<WS2812B, %d, GRB>" % (g, g),
                   "pin %d has its own instantiation" % g)
    t.contains(text, "#define RGB_PIN_DEFAULT %d" % int(data["default"]),
               "and the default travels with it")

    # ---- a bad pin is refused, not compiled -----------------------------
    # Run the generator against a file with GPIO 35 (input-only) in it: it must
    # stop, because a strip wired there is a wire that never blinks.
    box = Path(tempfile.mkdtemp(prefix="qc_rgbpin_"))
    try:
        bad_json = json.dumps({"default": 13,
                               "pins": [{"gpio": 13}, {"gpio": 35}]})
        (box / "rgb_pins.json").write_text(bad_json, encoding="utf-8")
        r = subprocess.run(
            [sys.executable, "-c",
             "import sys;sys.path.insert(0,r'%s');"
             "import gen_tables as g;"
             "g.RGB_PINS_JSON=__import__('pathlib').Path(r'%s');"
             "g.gen_rgb_pins(r'%s', ('lift',))"
             % (fw / "tools", box / "rgb_pins.json", box)],
            capture_output=True, text=True, cwd=str(fw))
        t.ok(r.returncode != 0,
             "an input-only pin stops the build instead of shipping",
             (r.stdout + r.stderr)[-200:])
        t.contains((r.stdout + r.stderr).lower(), "input-only",
                   "and says which kind of pin it refused")
    finally:
        import shutil
        shutil.rmtree(box, ignore_errors=True)

    # ---- the firmware and the page use it -------------------------------
    strip = (fw / "src/modules/lift/RgbStrip.cpp").read_text(encoding="utf-8",
                                                             errors="replace")
    t.contains(strip, "rgbAddLeds(hw.pins.rgbData",
               "the strip attaches to the pin the board was told to use")
    t.contains(strip, "rgbAddLeds(RGB_PIN_DEFAULT",
               "and falls back to the default rather than to nothing")
    cfg = (fw / "src/core/HwConfig.cpp").read_text(encoding="utf-8", errors="replace")
    t.contains(cfg, '{"rgb_data"', "rgb_data is a settable pin like the others")
    t.contains(cfg, 'if (g == hw.pins.rgbData) cls = "rgb"',
               "and the pin picture marks the one in use, not a fixed 13")
    page = (fw / "generated/web/ModuleUI.h").read_text(encoding="utf-8",
                                                       errors="replace")
    t.contains(page, "rgb:'lift'",
               "the page shows the strip's pin under the lift")
    t.contains(page, "rgb:'Light strip'", "with a name a person would use")
