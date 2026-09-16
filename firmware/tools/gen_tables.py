#!/usr/bin/env python3
"""Turn the config/*.json registries and the master web page into C++ headers
at BUILD time — carrying only what THIS build's module type needs.

Run automatically by PlatformIO (`extra_scripts` in platformio.ini) before the
firmware compiles, and safe to run by hand:

    python firmware/tools/gen_tables.py                 every type
    python firmware/tools/gen_tables.py --types nong    the humanoid only
    python firmware/tools/gen_tables.py --out some/dir  write somewhere else

Why generate instead of parsing on the chip: the ESP32 should not spend flash,
RAM or milliseconds reading JSON that never changes at runtime. The data stays
in one human-editable file; the firmware gets a plain `static const` array with
zero runtime cost. Adding a servo is still one edit.

WHAT IS PER TYPE, AND WHY IT IS GENERATED
-----------------------------------------
A board runs one module type. It used to carry every type anyway — a nong
carried the lift's commands and the lift's web cards, hidden at runtime by a
JavaScript capability check. Hidden is not absent: when that check once broke
(`isNong` was used and never defined) the wrong cards were one bug away from
being on screen, and the flash was spent either way.

So the env's `-D MICE_TYPE_*` flag (see platformio.ini) decides three things
here, from ONE source each:

    config/commands.json  -> core/CommandHelp.h       this type's commands
    config/servos.json    -> modules/nong/ServoPresets.h
    config/amps.json      -> core/AmpTable.h          the speaker amps
    src/web/WebUI.h       -> web/ModuleUI.h           this type's page
    ../shared/web/mice.css-> web/MiceCss.h            the shared design system

`src/web/WebUI.h` stays the one master page and is not compiled itself. It
marks per-type regions with lines of their own:

    <!--#type nong-->        (or  //#type nong  inside <script>)
      ...only in a build that carries nong...
    <!--#end-->              (or  //#end)

The marker lines never reach the output, so the same file is also served
whole by the hub (main_python) for a module reached over USB, where the type
is not known until the board answers.

WHERE THE OUTPUT GOES
---------------------
Under PlatformIO: `$BUILD_DIR/generated/`, added to the include path here.
Per env, so two envs can never overwrite each other's tables — the reason
these headers are no longer written into `src/`.
Standalone: `firmware/generated/`, which is what QC reads.
"""
import argparse
import json
import re
import sys
from pathlib import Path

# PlatformIO runs extra_scripts through SCons, which does NOT define __file__.
# It does run them with the project directory as the working directory, so fall
# back to that; standalone `python firmware/tools/gen_tables.py` uses __file__.
try:
    HERE = Path(__file__).resolve().parent
except NameError:
    HERE = Path.cwd().resolve() / "tools"
FIRMWARE = HERE.parent
CODE = FIRMWARE.parent
sys.path.insert(0, str(CODE / "tools"))
from registry import strip_jsonc  # noqa: E402

SERVOS_JSON = FIRMWARE / "config" / "servos.json"
AMPS_JSON = FIRMWARE / "config" / "amps.json"
RGB_PINS_JSON = FIRMWARE / "config" / "rgb_pins.json"
MODULES_JSON = FIRMWARE / "config" / "modules.json"
CAM_BOARDS_JSON = FIRMWARE / "config" / "cam_boards.json"
CAM_CONTROLS_JSON = FIRMWARE / "config" / "cam_controls.json"
WEBUI_MASTER = FIRMWARE / "src" / "web" / "WebUI.h"
# The ONE design system, shared with the hub, the help page, the RGB page and
# Nong Studio. The board has no filesystem to read it from, so it is compiled
# into flash here and served at /mice.css — the same URL the hub serves when
# the same page is opened over USB.
MICE_CSS = CODE / "shared" / "web" / "mice.css"
# The palette, joined with the above into one served stylesheet.
THEMES_CSS = CODE / "shared" / "web" / "themes.css"
# The one shared script (theme handling), compiled in the same way.
MICE_JS = CODE / "shared" / "web" / "mice.js"
DEFAULT_OUT = FIRMWARE / "generated"


def c_str(s):
    return '"%s"' % s.replace("\\", "\\\\").replace('"', '\\"')


def ident_ok(name):
    return bool(re.match(r"^[a-z][a-z0-9_]*$", name))


def load_modules():
    """The module types, from the one file that declares them."""
    data = json.loads(strip_jsonc(MODULES_JSON.read_text(encoding="utf-8")))
    mods = data.get("modules", {})
    if not mods:
        raise SystemExit("no modules in %s" % MODULES_JSON)
    for key, m in mods.items():
        if not ident_ok(key):
            raise SystemExit("module type %r must be lower-case letters/digits/_" % key)
        for field in ("label", "blurb", "class", "header", "board"):
            if field not in m:
                raise SystemExit("module %r is missing %r" % (key, field))
    return mods


# Every module type that can be built in. "core" is not a type: it is what
# every build carries, and "blank" is the fallback inside the firmware rather
# than a module anyone builds.
ALL_TYPES = tuple(load_modules())

BANNER = ("// GENERATED by firmware/tools/gen_tables.py from %s\n"
          "// Do NOT edit this file — edit the source and rebuild.\n")


def write_if_changed(path, text, what):
    """Write only on a real change — an untouched header keeps its timestamp,
    so PlatformIO does not rebuild half the firmware on every run."""
    if path.exists() and path.read_text(encoding="utf-8") == text:
        print("gen_tables: %s already current (%s)" % (path.name, what))
        return False
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8", newline="\n")
    print("gen_tables: wrote %s (%s)" % (path.name, what))
    return True


def gen_servos(out, types):
    # The servo table is nong hardware, but it costs nothing in a build without
    # nong: nothing includes the header, so nothing lands in flash. Writing it
    # always keeps every generated tree complete and inspectable.
    data = json.loads(strip_jsonc(SERVOS_JSON.read_text(encoding="utf-8")))
    servos = data.get("servos", {})
    if not servos:
        raise SystemExit("no servos in %s" % SERVOS_JSON)

    rows = []
    for key, s in servos.items():
        if not ident_ok(key):
            raise SystemExit("servo id %r must be lower-case letters/digits/_" % key)
        for field in ("label", "min", "max", "dps", "range", "hz"):
            if field not in s:
                raise SystemExit("servo %r is missing %r" % (key, field))
        if s["max"] <= s["min"]:
            raise SystemExit("servo %r: max must exceed min" % key)
        rows.append("    { %-14s %-22s %5d, %5d, %6.1ff, %6.1ff, %4d }," % (
            c_str(key) + ",", c_str(s["label"]) + ",",
            s["min"], s["max"], float(s["dps"]), float(s["range"]), s["hz"]))

    text = BANNER % SERVOS_JSON.name + """
#pragma once
#include <Arduino.h>

// One servo, exactly as config/servos.json describes it. `range` is the
// SERVO's own travel — not the joint's limits, which are per robot (LIMIT).
struct ServoPreset {
    const char* id;
    const char* label;
    int   pulseMin;
    int   pulseMax;
    float maxDps;
    float travelDeg;
    int   frameHz;
};

static const ServoPreset SERVO_PRESETS[] = {
%s
};
static const int SERVO_PRESET_COUNT =
    sizeof(SERVO_PRESETS) / sizeof(SERVO_PRESETS[0]);

// Look one up by the name the SERVO command takes; nullptr when unknown.
inline const ServoPreset* findServoPreset(const String& id) {
    for (int i = 0; i < SERVO_PRESET_COUNT; i++)
        if (id.equalsIgnoreCase(SERVO_PRESETS[i].id)) return &SERVO_PRESETS[i];
    return nullptr;
}

// "mg90s pdi1181mg tiankong35 ..." — for the command's own help text, so it
// can never list something the table does not have.
inline String servoPresetNames() {
    String s;
    for (int i = 0; i < SERVO_PRESET_COUNT; i++) {
        if (i) s += ' ';
        s += SERVO_PRESETS[i].id;
    }
    return s;
}
""" % "\n".join(rows)

    write_if_changed(out_path(out, "modules/nong/ServoPresets.h"), text,
                     "%d servos" % len(rows))
    return len(rows)


COMMANDS_JSON = FIRMWARE / "config" / "commands.json"


AMP_MODES = ("i2s", "analog", "dac", "none")
AUDIO_PIN_KEYS = ("i2s_bclk", "i2s_lrc", "i2s_dout")


# GPIOs that exist on an ESP32 and can drive an output. 34-39 are input-only
# and 6-11 belong to the flash chip, so a strip on any of them is a wire that
# never blinks - refused here rather than compiled.
RGB_BAD_PINS = set(range(6, 12)) | set(range(34, 40))


def gen_rgb_pins(out, types):
    """config/rgb_pins.json -> modules/lift/RgbPins.h

    FastLED fixes the data pin at COMPILE time (it is a template parameter), so
    the strip's pin was the one pin on the board a person could not choose from
    the website - and nothing on that page said why. This writes a switch with
    one instantiation per allowed pin, so the page can offer them and the
    choice lands in NVS like every other pin. Each entry costs a few hundred
    bytes of flash: that is why the list is short and lives in a file somebody
    can edit without touching code.
    """
    if "lift" not in types:
        return 0                     # only a lift build carries a strip
    data = json.loads(strip_jsonc(RGB_PINS_JSON.read_text(encoding="utf-8")))
    pins = [int(p["gpio"]) for p in data.get("pins", [])]
    if not pins:
        raise SystemExit("no pins in %s" % RGB_PINS_JSON)
    for g in pins:
        if g in RGB_BAD_PINS or not 0 <= g <= 39:
            raise SystemExit("rgb pin %d cannot drive a strip (input-only, "
                             "flash, or not a GPIO on this chip)" % g)
    if len(set(pins)) != len(pins):
        raise SystemExit("the same rgb pin is listed twice in %s" % RGB_PINS_JSON)
    default = int(data.get("default", pins[0]))
    if default not in pins:
        raise SystemExit("the default rgb pin %d is not in the list" % default)

    cases = "\n".join(
        "    case %d: FastLED.addLeds<WS2812B, %d, GRB>(leds, n); return true;"
        % (g, g) for g in pins)
    body = """
#pragma once
#include <FastLED.h>

// Which pin a strip may be wired to. One case per pin because FastLED takes it
// as a template parameter; the board picks at boot from what NVS holds.
#define RGB_PIN_DEFAULT {default}

inline bool rgbAddLeds(int gpio, CRGB* leds, int n) {{
    switch (gpio) {{
{cases}
    }}
    return false;              // not a pin this build was given
}}

static const int RGB_PINS[] = {{ {list} }};
static const int RGB_PIN_COUNT = {count};
""".format(default=default, cases=cases,
           list=", ".join(str(g) for g in pins), count=len(pins))

    write_if_changed(out_path(out, "modules/lift/RgbPins.h"),
                     BANNER % RGB_PINS_JSON.name + body,
                     "%d rgb data pins" % len(pins))
    return len(pins)


def gen_amps(out, types):
    """config/amps.json -> core/AmpTable.h

    The amp is a per-board WIRING fact, so the firmware carries the whole list
    and the board's website picks one by name. A mode this generator does not
    know is refused here rather than compiled: an unknown mode would fall back
    to digital I2S, which is exactly the silent wrong-amp bug this replaces.
    """
    data = json.loads(strip_jsonc(AMPS_JSON.read_text(encoding="utf-8")))
    amps = data.get("amps", {})
    if not amps:
        raise SystemExit("no amps in %s" % AMPS_JSON)

    rows = []
    for key, a in amps.items():
        if not ident_ok(key):
            raise SystemExit("amp id %r must be lower-case letters/digits/_" % key)
        for field in ("label", "mode", "pins", "mono", "wiring"):
            if field not in a:
                raise SystemExit("amp %r is missing %r" % (key, field))
        if a["mode"] not in AMP_MODES:
            raise SystemExit("amp %r: mode %r is not one of %s"
                             % (key, a["mode"], ", ".join(AMP_MODES)))
        for p in a["pins"]:
            if p not in AUDIO_PIN_KEYS:
                raise SystemExit("amp %r wires %r, which is not an audio pin (%s)"
                                 % (key, p, ", ".join(AUDIO_PIN_KEYS)))
        # An i2s amp that names no pin would be driven with nothing wired.
        if a["mode"] == "i2s" and len(a["pins"]) != 3:
            raise SystemExit("amp %r is i2s, so it must wire all three pins" % key)
        if a["mode"] == "analog" and a["pins"] != ["i2s_dout"]:
            raise SystemExit("amp %r is analog: it carries audio on i2s_dout "
                             "alone" % key)
        rows.append("    { %-14s %-42s %-10s %-6s %5s, %s }," % (
            c_str(key) + ",", c_str(a["label"]) + ",",
            c_str(a["mode"]) + ",",
            c_str(",".join(a["pins"])) + ",",
            "true" if a["mono"] else "false",
            c_str(a["wiring"])))

    text = BANNER % AMPS_JSON.name + """
#pragma once
#include <Arduino.h>

// One amplifier, exactly as config/amps.json describes it. `mode` is how the
// ESP32 must drive it — an analog amp (TPA3110, PAM8403) takes a line signal,
// so writing digital I2S at it plays noise, not sound.
struct AmpKind {
    const char* id;
    const char* label;
    const char* mode;     // i2s | analog | dac | none
    const char* pins;     // comma separated audio pin keys actually wired
    bool        mono;
    const char* wiring;   // the plain sentence the website prints
};

static const AmpKind AMP_KINDS[] = {
%s
};
static const int AMP_KIND_COUNT = sizeof(AMP_KINDS) / sizeof(AMP_KINDS[0]);

// Look one up by the name the AMP command takes; nullptr when unknown.
inline const AmpKind* findAmp(const String& id) {
    for (int i = 0; i < AMP_KIND_COUNT; i++)
        if (id.equalsIgnoreCase(AMP_KINDS[i].id)) return &AMP_KINDS[i];
    return nullptr;
}

// "tpa3110 max98357a ..." — for the command's own help, so it can never
// offer something the table does not have.
inline String ampNames() {
    String s;
    for (int i = 0; i < AMP_KIND_COUNT; i++) {
        if (i) s += ' ';
        s += AMP_KINDS[i].id;
    }
    return s;
}

// One amp as JSON. AMP? answers with this, so the page prints the wiring
// sentence for the amp the BOARD has, never one it guessed from the id.
inline String ampJson(const AmpKind& a) {
    String s = "{\\"id\\":\\"";
    s += a.id;
    s += "\\",\\"label\\":\\""; s += a.label;
    s += "\\",\\"mode\\":\\"";  s += a.mode;
    s += "\\",\\"pins\\":\\"";  s += a.pins;
    s += "\\",\\"mono\\":";     s += a.mono ? "true" : "false";
    s += ",\\"wiring\\":\\"";   s += a.wiring;
    return s + "\\"}";
}

// The whole list as JSON, for the Amplifier dropdown on the board's page.
inline String ampListJson() {
    String s = "[";
    for (int i = 0; i < AMP_KIND_COUNT; i++) {
        if (i) s += ',';
        s += ampJson(AMP_KINDS[i]);
    }
    return s + "]";
}
""" % "\n".join(rows)

    write_if_changed(out_path(out, "core/AmpTable.h"), text,
                     "%d amps" % len(rows))


def gen_commands(out, types):
    data = json.loads(strip_jsonc(COMMANDS_JSON.read_text(encoding="utf-8")))
    cmds = data.get("commands", [])
    if not cmds:
        raise SystemExit("no commands in %s" % COMMANDS_JSON)

    seen = set()
    rows = []
    for c in cmds:
        for field in ("name", "scope", "help"):
            if field not in c:
                raise SystemExit("command %r is missing %r" % (c.get("name", "?"), field))
        if c["scope"] not in ("core",) + ALL_TYPES:
            raise SystemExit("command %s: scope must be core/%s"
                             % (c["name"], "/".join(ALL_TYPES)))
        key = (c["name"], c["scope"])
        if key in seen:
            raise SystemExit("command %s declared twice for %s" % key)
        seen.add(key)
        # A command for a type this build does not carry has no handler here:
        # listing it in HELP would advertise something that answers
        # "unknown cmd".
        if c["scope"] != "core" and c["scope"] not in types:
            continue
        rows.append("    { %-10s %-8s %-38s %-64s %-6s %-6s %s }," % (
            c_str(c["name"]) + ",", c_str(c["scope"]) + ",",
            c_str(c.get("args", "")) + ",", c_str(c["help"]) + ",",
            ("true," if c.get("query") else "false,"),
            ("true," if c.get("motion") else "false,"),
            "true" if c.get("safety") else "false"))

    text = BANNER % COMMANDS_JSON.name + """
#pragma once
#include <Arduino.h>

// One command, as config/commands.json declares it. The handlers live where
// they always did; this is the table HELP prints and QC checks against, so a
// command cannot quietly exist without being documented.
struct CommandDoc {
    const char* name;
    const char* scope;      // core | lift | nong
    const char* args;
    const char* help;
    bool        query;      // reports only, changes nothing
    bool        motion;     // starts or stops physical movement
    // Must work with NO login. `motion` cannot say this: it is true for both
    // starting a move and stopping one, and refusing a STOP is the dangerous
    // answer — someone watching an arm about to hit a person cannot be asked
    // for a password first. Declared in commands.json, so making another
    // command always-allowed is one entry there and no change here.
    bool        safety;
};

static const CommandDoc COMMAND_DOCS[] = {
%s
};
static const int COMMAND_DOC_COUNT =
    sizeof(COMMAND_DOCS) / sizeof(COMMAND_DOCS[0]);

// Everything this board understands: core plus its own module type.
// ONE LINE, always.
//
// Every channel here is line-based: one command in, one reply line out. A
// multi-line reply poisons the NEXT command — its remaining lines are still
// arriving when that reply is read, so the caller gets a fragment of the
// previous answer. It happened for real on the bench: HELP printed 54 lines
// and the CAL after it came back as "-line status JSON".
//
// So bare HELP lists the NAMES, and HELP <name> explains exactly one.
inline String commandHelp(const String& type, const String& one = "") {
    String out;
    if (one.length()) {
        for (int i = 0; i < COMMAND_DOC_COUNT; i++) {
            const CommandDoc& d = COMMAND_DOCS[i];
            if (!one.equalsIgnoreCase(d.name)) continue;
            if (strcmp(d.scope, "core") && !type.equalsIgnoreCase(d.scope)) continue;
            out = String(d.name);
            if (strlen(d.args)) { out += ' '; out += d.args; }
            out += " - "; out += d.help;
            return out;
        }
        return String("no such command here: ") + one;
    }
    for (int i = 0; i < COMMAND_DOC_COUNT; i++) {
        const CommandDoc& d = COMMAND_DOCS[i];
        if (strcmp(d.scope, "core") && !type.equalsIgnoreCase(d.scope)) continue;
        if (out.length()) out += ' ';
        out += d.name;
    }
    return out + "  (HELP <name> for one)";
}

// Does this command move the robot?
//
// Used by CommandRouter to decide whether an arriving command has to stop a
// sequence the board is playing on its own. ONE table decides it, the same one
// HELP reads, so a new moving command cannot be added and forgotten: mark it
// `"motion": true` in config/commands.json and every path agrees.
inline bool commandIsMotion(const String& cmd) {
    for (int i = 0; i < COMMAND_DOC_COUNT; i++)
        if (COMMAND_DOCS[i].motion && cmd.equalsIgnoreCase(COMMAND_DOCS[i].name))
            return true;
    return false;
}
""" % "\n".join(rows)

    write_if_changed(out_path(out, "core/CommandHelp.h"), text,
                     "%d commands" % len(rows))
    return len(rows)


def gen_camcontrols(out, types):
    """config/cam_controls.json -> modules/cam/CamControls.h

    The table a person sees and the switch that applies it, from one file, so
    a control cannot be offered on a page the firmware has no way to apply.

    EVERY SETTER IS NULL-CHECKED. `sensor_t` is a struct of function pointers
    filled in per sensor, and a part that does not implement a control leaves
    its pointer null - calling it does not return an error, it panics the board
    with LoadProhibited. Four setters were already being called unchecked here;
    exposing two dozen from data would have made that a certainty.
    """
    data = json.loads(strip_jsonc(CAM_CONTROLS_JSON.read_text(encoding="utf-8")))
    controls = data.get("controls", {})
    if not controls:
        raise SystemExit("no controls in %s" % CAM_CONTROLS_JSON)

    rows, applies, reads = [], [], []
    for key, c in controls.items():
        if not re.match(r"^[a-z][a-z0-9_]*$", key):
            raise SystemExit("camera control %r must be lower-case letters, "
                             "digits and underscores" % key)
        for field in ("setter", "kind", "lo", "hi", "def", "label"):
            if field not in c:
                raise SystemExit("camera control %r is missing %r" % (key, field))
        if c["kind"] not in ("range", "toggle", "choice"):
            raise SystemExit("camera control %r: kind must be range, toggle "
                             "or choice" % key)
        lo, hi, dflt = int(c["lo"]), int(c["hi"]), int(c["def"])
        if not lo <= dflt <= hi:
            raise SystemExit("camera control %r: default %d is outside %d..%d"
                             % (key, dflt, lo, hi))
        choices = c.get("choices") or []
        if c["kind"] == "choice" and len(choices) != hi - lo + 1:
            raise SystemExit("camera control %r: %d choices for the range "
                             "%d..%d" % (key, len(choices), lo, hi))
        rows.append("    { %-18s %-26s %-10s %5d, %5d, %5d, %-34s %-12s %s }," % (
            c_str(key) + ",", c_str(c["label"]) + ",", c_str(c["kind"]) + ",",
            lo, hi, dflt, c_str(" ".join(choices)) + ",",
            c_str(c.get("group", "advanced")) + ",", c_str(c.get("needs", ""))))
        # Almost every setter takes an int; set_gainceiling takes an enum, and
        # a bare int there is a compile error. The cast is declared with the
        # control rather than special-cased here.
        cast = "(%s)" % c["cast"] if c.get("cast") else ""
        applies.append(
            '    if (name.equalsIgnoreCase("%s")) {\n'
            '        if (!s->set_%s) return false;\n'
            '        return s->set_%s(s, %sv) == 0;\n'
            '    }' % (key, c["setter"], c["setter"], cast))
        reads.append('    if (name.equalsIgnoreCase("%s")) return s->status.%s;'
                     % (key, c.get("status", c["setter"])))

    text = BANNER % CAM_CONTROLS_JSON.name + """
#pragma once
#include <Arduino.h>
#include <esp_camera.h>

// One camera setting, exactly as config/cam_controls.json declares it.
struct CamControl {
    const char* name;
    const char* label;
    const char* kind;       // range | toggle | choice
    int         lo;
    int         hi;
    int         def;        // where the driver starts, and what AUTO restores
    const char* choices;    // space separated, for kind == choice
    // WHERE IT BELONGS ON THE PAGE, and what it depends on - both declared
    // with the control, so adding one lands it in the right group with the
    // right note and no page code decides anything.
    const char* group;      // basic | exposure | colour | advanced
    const char* needs;      // e.g. "aec=0": only applies while that is so
};

static const CamControl CAM_CONTROLS[] = {
%s
};
static const int CAM_CONTROL_COUNT =
    sizeof(CAM_CONTROLS) / sizeof(CAM_CONTROLS[0]);

inline const CamControl* findCamControl(const String& name) {
    for (int i = 0; i < CAM_CONTROL_COUNT; i++)
        if (name.equalsIgnoreCase(CAM_CONTROLS[i].name)) return &CAM_CONTROLS[i];
    return nullptr;
}

// -> true when the sensor took it. False means this part does not implement
// that control, which is an answer, not a crash: an unimplemented setter is a
// NULL POINTER in sensor_t and calling it panics the board.
inline bool applyCamControl(sensor_t* s, const String& name, int v) {
    if (!s) return false;
%s
    return false;
}

inline int readCamControl(sensor_t* s, const String& name) {
    if (!s) return 0;
%s
    return 0;
}
""" % ("\n".join(rows), "\n".join(applies), "\n".join(reads))

    write_if_changed(out_path(out, "modules/cam/CamControls.h"), text,
                     "%d camera controls" % len(rows))
    return len(rows)


def gen_seqsteps(out, types):
    """The YAML step keys a saved sequence may use -> core/SeqSteps.h.

    SequencePlayer used to carry these as an if-else chain, so adding a step
    meant editing C++ that already knew about both module types by name. They
    are declared on the command they call instead, and this writes the table
    the player walks.

    ONE KEY CAN COME FROM TWO ENTRIES. `home`, `stop` and `speed` exist for
    both lift and nong, and a build that carries both (mice_module_firmware)
    sees the entry twice. Identical declarations collapse to one row; a real
    disagreement is refused here rather than silently picking whichever came
    first in the file.
    """
    data = json.loads(strip_jsonc(COMMANDS_JSON.read_text(encoding="utf-8")))
    by_key = {}
    for c in data.get("commands", []):
        if c["scope"] != "core" and c["scope"] not in types:
            continue                    # not in this binary, so not a step here
        for st in c.get("steps", []):
            if "key" not in st:
                raise SystemExit("command %s: a step needs a key" % c["name"])
            key = st["key"]
            if not ident_ok(key.replace("-", "_")):
                raise SystemExit("step key %r is not a plain name" % key)
            cmd = c["name"] + ((" " + st["sub"]) if st.get("sub") else "")
            row = (cmd, bool(st.get("wait")))
            if key in by_key and by_key[key] != row:
                raise SystemExit(
                    "step %r means two different things: %r and %r"
                    % (key, by_key[key], row))
            by_key[key] = row

    rows = ["    { %-10s %-18s %s }," % (c_str(k) + ",", c_str(cmd) + ",",
                                         "true" if wait else "false")
            for k, (cmd, wait) in sorted(by_key.items())]

    text = BANNER % COMMANDS_JSON.name + """
#pragma once
#include <Arduino.h>

// One YAML step key, as config/commands.json declares it.
//
// `wait` cannot be derived from `motion`: STOP and RELAX are both motion and
// both must NOT wait, or a sequence stops dead on them — STOP has nothing to
// finish, and RELAX unpowers the servos so `busy` never clears.
struct SeqStepDoc {
    const char* key;        // what the step is called in the file
    const char* cmd;        // the command line it becomes, without the value
    bool        wait;       // let the move finish before the next step
};

static const SeqStepDoc SEQ_STEPS[] = {
%s
};
static const int SEQ_STEP_COUNT = sizeof(SEQ_STEPS) / sizeof(SEQ_STEPS[0]);

inline const SeqStepDoc* findSeqStep(const String& key) {
    for (int i = 0; i < SEQ_STEP_COUNT; i++)
        if (key.equalsIgnoreCase(SEQ_STEPS[i].key)) return &SEQ_STEPS[i];
    return nullptr;
}
""" % "\n".join(rows)

    write_if_changed(out_path(out, "core/SeqSteps.h"), text,
                     "%d sequence steps" % len(rows))
    return len(rows)


# ---------------------------------------------------------------- the page
# One master page, `src/web/WebUI.h`, marks the parts that belong to one
# module type. This strips the parts this build does not carry, so a lift
# binary does not contain the joint sliders at all — not even hidden.
#
# Marker lines, each alone on its line (leading spaces are fine):
#     <!--#type nong-->   ...   <!--#end-->      in HTML
#     //#type nong        ...   //#end           inside <script>
# Two spellings because one has to be a comment in HTML and the other in
# JavaScript: the master is ALSO served whole by the hub, where a stray
# marker would either show up on the page or break the script.
_TYPE_OPEN = re.compile(r'^\s*(?:<!--\s*|//\s*)#type\s+([a-z0-9 ]+?)\s*(?:-->)?\s*$')
_TYPE_END = re.compile(r'^\s*(?:<!--\s*|//\s*)#end\s*(?:-->)?\s*$')


def split_page(src, types):
    """The master page with every other type's regions removed."""
    kept, keeping, open_at = [], None, 0
    for n, line in enumerate(src.splitlines(), 1):
        m = _TYPE_OPEN.match(line)
        if m:
            if keeping is not None:
                raise SystemExit("WebUI.h:%d: #type inside #type (opened at %d)"
                                 % (n, open_at))
            want = m.group(1).split()
            for t in want:
                if t not in ALL_TYPES:
                    raise SystemExit("WebUI.h:%d: unknown module type %r" % (n, t))
            keeping = any(t in types for t in want)
            open_at = n
            continue
        if _TYPE_END.match(line):
            if keeping is None:
                raise SystemExit("WebUI.h:%d: #end without #type" % n)
            keeping = None
            continue
        if keeping is None or keeping:
            kept.append(line)
    if keeping is not None:
        raise SystemExit("WebUI.h:%d: #type was never closed with #end" % open_at)
    return "\n".join(kept) + "\n"


def gen_webui(out, types):
    src = WEBUI_MASTER.read_text(encoding="utf-8")
    page = split_page(src, types)
    text = BANNER % WEBUI_MASTER.name + page
    # what the board will actually serve, which is the number worth watching
    body = re.search(r'R"rawliteral\((.*)\)rawliteral"', page, re.S)
    size = len(body.group(1).encode("utf-8")) if body else len(page)
    write_if_changed(out_path(out, "web/ModuleUI.h"), text,
                     "%.1f KB page for %s" % (size / 1024.0,
                                              "+".join(types) or "core only"))
    return size


def gen_micecss(out):
    """The shared stylesheet, as a PROGMEM string the board can serve.

    Not a copy anyone edits: it is regenerated from shared/web/mice.css on
    every build, so the module website cannot drift away from the hub the way
    six hand-kept copies of the same tokens already did once.
    """
    # The palette lives in themes.css and the components in mice.css (split on
    # 2026-08-19 so a colour can be changed in one small file). The board still
    # serves ONE stylesheet, so they are joined here in that order - a theme
    # has to be defined before the rules that use it.
    css = ""
    for f in (THEMES_CSS, MICE_CSS):
        if f.is_file():
            css += ("/* ---- %s ---- */" + chr(10) + "%s" + chr(10)) % (
                f.name, f.read_text(encoding="utf-8"))
    if ")rawliteral" in css:            # would close the C++ raw string early
        raise SystemExit("the stylesheet contains )rawliteral, which cannot be embedded")
    text = (BANNER % ("../" + MICE_CSS.name)
            + '#pragma once\n#include <Arduino.h>\n\n'
              'static const char MICE_CSS[] PROGMEM = R"rawliteral('
            + css + ')rawliteral";\n')
    write_if_changed(out_path(out, "web/MiceCss.h"), text,
                     "%.1f KB stylesheet" % (len(css.encode("utf-8")) / 1024.0))

    # ...and the shared script beside it. Same reasoning, same one source: a
    # board reached over WiFi has to behave like the same product as a board
    # reached through the hub.
    js = MICE_JS.read_text(encoding="utf-8") if MICE_JS.is_file() else ""
    if ")rawliteral" in js:
        raise SystemExit("mice.js contains )rawliteral, which cannot be embedded")
    jtext = (BANNER % ("../" + MICE_JS.name)
             + '#pragma once' + chr(10) + '#include <Arduino.h>' + chr(10) + chr(10)
             + 'static const char MICE_JS[] PROGMEM = R"rawliteral('
             + js + ')rawliteral";' + chr(10))
    write_if_changed(out_path(out, "web/MiceJs.h"), jtext,
                     "%.1f KB shared script" % (len(js.encode("utf-8")) / 1024.0))


# ------------------------------------------------- the module types in C++
# Generated, not hand-kept, so "adding a module type is one file" is true of
# the FIRMWARE too and not only of the tools around it. Two headers:
#
#   core/BuildTypes.h     what this build carries (MICE_HAS_<TYPE>)
#   modules/ModuleTable.h the includes and the factory, both guarded
def gen_buildtypes(out, types):
    mods = load_modules()
    names = [t.upper() for t in mods]
    guard = " && ".join("!defined(MICE_TYPE_%s)" % n for n in names + ["BLANK"])
    lines = [BANNER % MODULES_JSON.name, """
#pragma once

// Which module types THIS binary carries.
//
// A board runs one module type, so it should not have to carry the others.
// platformio.ini defines exactly one `MICE_TYPE_*` per env (see the header of
// that file); everything that is per-type — the module classes, their pin
// entries, their web cards, their commands — is behind the macros below.
//
// No flag at all means "carry everything", which is the legacy
// `mice_module_firmware` build. That default is deliberate: a new env, or a
// hand-run compile that forgets the flag, gets the OLD behaviour (too much
// code) rather than a board with no module at all.
"""]
    lines.append("#if " + guard)
    for n in names:
        lines.append("#define MICE_TYPE_%s" % n)
    lines.append("#endif\n")
    for n in names:
        lines.append("#ifdef MICE_TYPE_%s\n#define MICE_HAS_%s 1\n#else\n"
                     "#define MICE_HAS_%s 0\n#endif\n" % (n, n, n))
    write_if_changed(out_path(out, "core/BuildTypes.h"), "\n".join(lines),
                     "%d module types" % len(names))


def gen_module_table(out, types):
    mods = load_modules()
    inc, mk, known = [], [], []
    for key, m in mods.items():
        up = key.upper()
        inc.append('#if MICE_HAS_%s\n#include "%s"\n#endif' % (up, m["header"]))
        mk.append('#if MICE_HAS_%s\n    if (type == "%s") return new %s(sd);\n#endif'
                  % (up, key, m["class"]))
        known.append('#if MICE_HAS_%s\n    "%s",\n#endif' % (up, key))
    text = BANNER % MODULES_JSON.name + """
#pragma once
#include <Arduino.h>
#include "core/BuildTypes.h"
#include "modules/Module.h"

class SDStore;

%s

// Every type THIS binary can boot, ending with the blank fallback — which is
// what an unknown stored type falls back to, so a board is never unreachable.
static const char* const MODULE_TYPES[] = {
%s
    "blank",
};
static const int MODULE_TYPE_COUNT =
    sizeof(MODULE_TYPES) / sizeof(MODULE_TYPES[0]);

// nullptr when this build does not carry that type; ModuleFactory turns that
// into the blank module.
inline Module* makeModule(const String& type, SDStore* sd) {
%s
    (void)sd;
    return nullptr;
}
""" % ("\n".join(inc), "\n".join(known), "\n".join(mk))
    write_if_changed(out_path(out, "modules/ModuleTable.h"), text,
                     "%d module types" % len(mods))


# ---------------------------------------------------------------- plumbing
def out_path(out, rel):
    return Path(out) / rel


def types_from_defines(names):
    """Which module types a build carries, from its -D MICE_TYPE_* flags.

    No flag at all means every type — see src/core/BuildTypes.h, which makes
    the same choice for the C++ side. The two must agree.
    """
    names = set(names)
    if not any(n.startswith("MICE_TYPE_") for n in names):
        return list(ALL_TYPES)
    return [t for t in ALL_TYPES if ("MICE_TYPE_%s" % t.upper()) in names]


def defines_of(env):
    """Every -D this env compiles with, as plain names.

    Both sources are read on purpose. In a `pre:` script CPPDEFINES is still
    EMPTY — PlatformIO has not turned build_flags into it yet — and reading only
    that silently produced an all-types page for every env: each binary still
    carried the other module's cards while the build looked correct. The flags
    themselves are already there, in BUILD_FLAGS, as the text the compiler gets.
    """
    names = set()
    for d in env.get("CPPDEFINES") or []:
        name = d[0] if isinstance(d, (list, tuple)) else d
        names.add(str(name).split("=")[0].strip())
    text = " ".join(str(f) for f in (env.get("BUILD_FLAGS") or []))
    names.update(re.findall(r"-D\s*([A-Za-z_]\w*)", text))
    return names


# Field order in the generated table. It is written down ONCE, here, because
# both the C++ struct and every row are emitted from it - a hand-kept struct and
# a hand-kept row list are two places to get the same order wrong, and the
# symptom of getting it wrong is a camera that initialises and returns noise.
CAM_PIN_ORDER = ("pwdn", "reset", "xclk", "siod", "sioc",
                 "y9", "y8", "y7", "y6", "y5", "y4", "y3", "y2",
                 "vsync", "href", "pclk")


def gen_cam_boards(out, types):
    """config/cam_boards.json -> modules/cam/CamBoards.h

    The camera driver tries these in order until a sensor answers, so the list
    is data the hub needs too: it draws the pin diagram for whichever board a
    module reports, from this same file. Two copies of a pin map would be two
    chances for the picture to lie about the wiring.
    """
    data = json.loads(strip_jsonc(CAM_BOARDS_JSON.read_text(encoding="utf-8")))
    boards = data.get("boards", {})
    if not boards:
        raise SystemExit("no boards in %s" % CAM_BOARDS_JSON)

    rows = []
    for key, b in boards.items():
        if not re.match(r"^[a-z][a-z0-9-]*$", key):
            raise SystemExit("camera board %r must be lower-case letters, "
                             "digits and dashes" % key)
        pins = b.get("pins") or {}
        missing = [k for k in CAM_PIN_ORDER if k not in pins]
        if missing:
            raise SystemExit("camera board %r is missing pins: %s"
                             % (key, ", ".join(missing)))
        for k in CAM_PIN_ORDER:
            v = pins[k]
            if not isinstance(v, int) or v < -1 or v > 48:
                raise SystemExit("camera board %r: %s is %r, which is not a "
                                 "GPIO (-1 means not wired)" % (key, k, v))
        # The flash LED and the status LED are part of the board too. They
        # were compiled in until 2026-08-20, which meant a board with no flood
        # LED had GPIO 4 driven anyway - on an ESP-EYE that pin is a camera
        # data line. -1 means this board has none, and the firmware then drives
        # nothing rather than guessing.
        ex = b.get("extra") or {}
        nums = ", ".join("%3d" % pins[k] for k in CAM_PIN_ORDER)
        rows.append("    { %-18s %s, %3d, %3d }," % (
            c_str(key) + ",", nums,
            int(ex.get("flash", -1)), int(ex.get("led", -1))))
        if b.get("note"):
            rows.insert(len(rows) - 1, "    // %s" % b["note"])

    text = BANNER % CAM_BOARDS_JSON.name + """
#pragma once
#include <Arduino.h>

// One camera board's wiring, exactly as config/cam_boards.json describes it.
// -1 means the board does not wire that signal at all.
struct CamPins {
    const char* name;
    int8_t pwdn, reset, xclk, siod, sioc;
    int8_t y9, y8, y7, y6, y5, y4, y3, y2;
    int8_t vsync, href, pclk;
    int8_t flash, led;      // -1: this board has none
};

// Tried in this order until a sensor answers on the SCCB bus, so the commonest
// board is first: every wrong guess costs one failed init.
static const CamPins CAM_BOARDS[] = {
""" + chr(10).join(rows) + """
};
static const int CAM_BOARD_COUNT = sizeof(CAM_BOARDS) / sizeof(CAM_BOARDS[0]);
"""
    write_if_changed(out / "modules" / "cam" / "CamBoards.h", text,
                     "%d camera boards" % len(boards))


def generate(out, types):
    print("gen_tables: %s -> %s" % ("+".join(types) or "core only", out))
    gen_buildtypes(out, types)
    gen_module_table(out, types)
    gen_servos(out, types)
    gen_amps(out, types)
    gen_rgb_pins(out, types)
    gen_commands(out, types)
    gen_seqsteps(out, types)
    gen_cam_boards(out, types)
    gen_camcontrols(out, types)
    gen_webui(out, types)
    gen_micecss(out)


def main(argv=None):
    ap = argparse.ArgumentParser(description="generate the firmware's tables and page")
    ap.add_argument("--types", default=",".join(ALL_TYPES),
                    help="module types this build carries (comma separated, "
                         "or 'none' for a core-only build)")
    ap.add_argument("--out", default=str(DEFAULT_OUT), help="output folder")
    a = ap.parse_args(argv)
    types = [] if a.types.strip().lower() in ("", "none") else [
        t.strip() for t in a.types.split(",") if t.strip()]
    for t in types:
        if t not in ALL_TYPES:
            raise SystemExit("unknown module type %r (have: %s)"
                             % (t, ", ".join(ALL_TYPES)))
    generate(Path(a.out), types)


# PlatformIO imports this as a pre-build script; it also runs standalone.
# Only the Import is guarded: a NameError raised by the generation itself is a
# real bug and must not be mistaken for "not running under PlatformIO".
_env = None
try:
    Import("env")  # noqa: F821  (injected by SCons when PlatformIO runs it)
    _env = env     # noqa: F821
except NameError:
    pass

if _env is not None:
    _out = Path(_env.subst("$BUILD_DIR")) / "generated"
    generate(_out, types_from_defines(defines_of(_env)))
    # The generated folder is where core/CommandHelp.h, web/ModuleUI.h and
    # modules/nong/ServoPresets.h now live, so it has to be on the include
    # path. It is added AFTER src, but nothing shadows it: those three files
    # exist nowhere else in the tree.
    _env.Append(CPPPATH=[str(_out)])
    # ArduinoJson's own sources, so YAMLDuino's __has_include(<ArduinoJson.h>)
    # guard enables its JsonDocument bindings while the library itself is
    # compiled. This used to be a fixed -I in platformio.ini naming ONE env's
    # libdeps folder, which silently stopped being right the moment a second
    # env existed.
    _env.Append(CPPPATH=[_env.subst("$PROJECT_LIBDEPS_DIR/$PIOENV/ArduinoJson/src")])
elif __name__ == "__main__":
    main()
