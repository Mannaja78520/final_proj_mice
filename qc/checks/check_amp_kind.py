"""Which amplifier is wired is DATA, and the analog one must name its pin.

The nong got a speaker in A7-9, and A24-16 found the firmware had been built
for the wrong amp all along. Two bugs, both silent, both pinned here:

* `AudioPlayer::begin` always built `AudioOutputI2S` — digital I2S. The user's
  amp is a TPA3118: an ANALOG class-D amp with a line input. Fed raw I2S bits
  it plays loud noise, not sound. So the amp kind is now one entry in
  `config/amps.json`, stored per board in NVS and picked by name on the
  Hardware-pins page. Nothing about it is compiled in.
* The analog path uses `AudioOutputI2SNoDAC`, which still runs the ESP32's I2S
  peripheral and so still claims pins. Its library defaults are BCLK 26 /
  LRC 25 / DOUT 22 — on a full nong those are servos 4, 3 and 6. Without an
  explicit `SetPinout` a PLAY would put a 44 kHz audio wave on three servo
  signal lines.

And one the panel caught before it reached a board, 2026-08-27: the obvious way
to say *leave this pin alone* is `SetPinout(-1, ...)`, and it does not work.
`AudioOutputI2S` keeps its pin numbers in **uint8_t** (`AudioOutputI2S.h:73-76`),
so -1 arrives as 255 — not `I2S_PIN_NO_CHANGE`. Its `mclkPin` therefore keeps
its default of 0, and on IDF 4.4 that routes a master clock onto GPIO0, which
on a nong carries LRC. `AudioPlayer::applyPins` sets the pins once more through
the driver itself, after the library installed it, with a real -1 for MCLK.
Any `SetPinout(-1` in this file is that bug coming back.

The rest is the usual registry bargain: the json, the generated table, the
command and the picker are one fact in four places, so this check fails if any
of them drifts.

A24-41, 2026-09-08: the lift's speaker is a CHAIN of two boards - I2S into a
PCM5102A DAC, its line out into a TPA3118 amp, then the 12V speaker. So an amp
also says where each wire goes (`to`), and the lift defaults to the entry that
names both boards. The board builds AMP VALID's JSON by joining strings, so the
generated table is COMPILED and RUN here (g++ with a String stand-in) and its
answer parsed: a stray quote or a dropped field would otherwise empty the
Amplifier picker with nothing on screen to say why.
"""
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import qc as F

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402  (JSONC loader — amps.json carries comments)

AREA = "firmware"
TITLE = "the amplifier kind is data, and the analog path names its pin"

MODES = ("i2s", "analog", "dac", "none")


def run(t):
    fw = F.FIRMWARE
    amps = registry.load(fw / "config" / "amps.json", {}).get("amps", {})
    t.ok(len(amps) >= 2, "config/amps.json lists the amps", "found %d" % len(amps))

    for key, a in amps.items():
        for field in ("label", "mode", "pins", "mono", "wiring", "to"):
            t.ok(field in a, "amp %s has %s" % (key, field))
        # one destination per wired pin: with a DAC and an amp in hand, this is
        # what says which board a wire belongs on
        to = a.get("to") if isinstance(a.get("to"), dict) else {}
        t.eq(sorted(to), sorted(a.get("pins", [])),
             "amp %s says where each of its wires goes" % key)
        t.ok(all(v.strip() for v in to.values()),
             "amp %s has no empty destination" % key, to)
        t.ok(a.get("mode") in MODES, "amp %s has a real mode" % key, repr(a.get("mode")))
        # An analog amp carries the audio on ONE wire. Any other pin list here
        # means the generator's own guard was edited away.
        if a.get("mode") == "analog":
            t.eq(a.get("pins"), ["i2s_dout"], "analog amp %s wires DOUT only" % key)

    # the user's parts, 2026-08-27: MAX98357A on the nong, TPA3118 on the lift
    for want in ("tpa3118", "max98357a"):
        t.ok(want in amps, "%s is one of the amps" % want)

    # ---- the generated table carries every entry, so the chip needs no json
    tbl = F.generated("core/AmpTable.h").read_text(encoding="utf-8", errors="replace")
    for key, a in amps.items():
        t.contains(tbl, '"%s"' % key, "AmpTable.h carries %s" % key)
        t.contains(tbl, a["wiring"][:40], "AmpTable.h carries %s's wiring line" % key)
    t.contains(tbl, "inline String ampJson", "one amp can be answered as JSON (AMP?)")
    _board_answer(t, amps)

    # ---- each type must default to an amp it can actually drive
    for kind, hdr_name in (("NONG", "esp32_hardware_nong_module.h"),
                           ("LIFT", "esp32_hardware_lift_module.h")):
        hdr = (fw / "config" / hdr_name).read_text(encoding="utf-8", errors="replace")
        m = re.search(r'%s_AUDIO_AMP_DEFAULT\s+"([^"]+)"' % kind, hdr)
        if not t.ok(m is not None, "the %s header names a default amp" % kind.lower()):
            continue
        got = m.group(1)
        t.ok(got in amps, "the %s default amp %s exists in amps.json" % (kind.lower(), got))
        # GPIO25/26 are nong servos 3 and 4, so the built-in DAC is not a
        # default any full nong could boot with.
        t.ok(amps.get(got, {}).get("mode") != "dac",
             "%s does not default to the built-in DAC" % kind.lower(),
             "25/26 drive servos on a full nong")
        if kind == "LIFT":
            # user 2026-09-08: ESP32 I2S -> PCM5102A -> TPA3118 -> 12V speaker.
            # The chip only sees the DAC, so the default is i2s AND names both.
            chain = amps.get(got, {})
            t.eq(chain.get("mode"), "i2s",
                 "the lift default drives its DAC over I2S (%s)" % got)
            for word in ("PCM5102A", "TPA3118", "12V"):
                t.contains(chain.get("wiring", ""), word,
                           "the lift default's wiring names %s" % word)

    # ---- the analog path names its pins (the servo-pin bug above)
    player = (fw / "src/core/AudioPlayer.cpp").read_text(encoding="utf-8", errors="replace")
    t.eq(player.count("SetPinout(hw.pins.i2sBclk, hw.pins.i2sLrc, hw.pins.i2sDout)"), 2,
         "both the analog and the i2s amp name the board's own audio pins")
    t.ok("SetPinout(-1" not in player,
         "no pin is set to -1 through the library",
         "its pin fields are uint8_t, so -1 becomes 255, not I2S_PIN_NO_CHANGE")
    t.contains(player, "p.mck_io_num   = I2S_PIN_NO_CHANGE",
               "applyPins keeps the master clock off GPIO0")
    t.contains(player, "applyPins();",
               "the pins are re-applied after the decoder installs the driver")
    t.contains(player, 'argv[0].endsWith("?")',
               "AMP? answers what is set instead of ERR usage")

    # ---- both types that wire a speaker can be asked and told
    for name in ("nong", "lift"):
        src = (fw / ("src/modules/%s/%sModule.cpp" % (name, name.capitalize()))
               ).read_text(encoding="utf-8", errors="replace")
        t.contains(src, "audio_.ampCmd", "%s routes AMP to the shared parser" % name)
        t.contains(src, 'AMP?', "%s answers AMP? too" % name)

    decl = registry.commands()
    for scope in ("nong", "lift"):
        t.ok(any(c["name"] == "AMP" and c["scope"] == scope for c in decl),
             "AMP is declared for %s" % scope)

    t.contains((fw / "COMMANDS.md").read_text(encoding="utf-8", errors="replace"),
               "AMP VALID", "COMMANDS.md documents the amp commands")

    # ---- the picker: a designer chooses the amp by NAME, never by editing code
    page = F.generated("web/ModuleUI.h")
    if t.ok(page.is_file(), "the module page was generated"):
        s = page.read_text(encoding="utf-8", errors="replace")
        t.contains(s, "id='ampSel'", "the Amplifier picker is on the pins page")
        t.contains(s, "AMP VALID", "the picker fills itself from the board's own list")
        t.contains(s, "ampPinKeys", "only the GPIO boxes that amp uses are shown")
        t.contains(s, "wiring", "the wiring sentence is printed under the picker")
        t.contains(s, "cmd('AMP '+ampPick)", "Save & reboot stores the chosen amp")
        t.contains(s, "(grp==='audio')?ampWireTo(k)",
                   "each speaker pin box says where its wire goes")


# A String with just what AmpTable.h uses, so the generated table can run here.
STUB = r"""
#pragma once
#include <cctype>
#include <string>
class String {
public:
    std::string v;
    String() {}
    String(const char* s) : v(s) {}
    String& operator+=(const char* s) { v += s; return *this; }
    String& operator+=(char c) { v += c; return *this; }
    String& operator+=(const String& o) { v += o.v; return *this; }
    String operator+(const char* s) const { String r(*this); r.v += s; return r; }
    bool equalsIgnoreCase(const char* s) const {
        std::string o(s);
        if (o.size() != v.size()) return false;
        for (size_t i = 0; i < v.size(); i++)
            if (std::tolower((unsigned char)v[i]) != std::tolower((unsigned char)o[i]))
                return false;
        return true;
    }
    const char* c_str() const { return v.c_str(); }
};
"""

MAIN = r"""
#include <cstdio>
#include "core/AmpTable.h"
int main() { std::printf("%s\n", ampListJson().c_str()); return 0; }
"""


def _board_answer(t, amps):
    """Run the generated table and read AMP VALID exactly as the page will."""
    cxx = shutil.which("g++") or shutil.which("clang++")
    if not cxx:
        print("      \033[33mNOTE: no host C++ compiler, so AMP VALID's JSON was "
              "not run here\033[0m")
        return
    with tempfile.TemporaryDirectory() as tmp:
        (Path(tmp) / "Arduino.h").write_text(STUB, encoding="utf-8")
        (Path(tmp) / "main.cpp").write_text(MAIN, encoding="utf-8")
        exe = str(Path(tmp) / "amps")
        r = subprocess.run([cxx, "-std=c++17", "-I", tmp, "-I", str(F.generated()),
                            str(Path(tmp) / "main.cpp"), "-o", exe],
                           capture_output=True, text=True, timeout=120)
        if not t.ok(r.returncode == 0, "the generated amp table compiles",
                    (r.stderr or r.stdout)[-300:]):
            return
        out = subprocess.run([exe], capture_output=True, text=True, timeout=30).stdout
    try:
        board = json.loads(out)
    except ValueError as e:
        t.ok(False, "AMP VALID is valid JSON, so the Amplifier picker can read it",
             "%s: %s" % (e, out[:200]))
        return
    t.ok(True, "AMP VALID is valid JSON, so the Amplifier picker can read it")
    t.eq([b.get("id") for b in board], list(amps), "AMP VALID lists every amp, in order")
    for b in board:
        a = amps.get(b.get("id"), {})
        want = {"id": b.get("id"), "label": a.get("label"), "mode": a.get("mode"),
                "pins": ",".join(a.get("pins", [])), "mono": a.get("mono"),
                "wiring": a.get("wiring"), "to": a.get("to")}
        t.eq(b, want, "the board answers %s exactly as amps.json says" % b.get("id"))
