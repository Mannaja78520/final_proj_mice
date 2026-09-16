"""The speaker is shared hardware, not a lift privilege (A7-9).

AudioPlayer used to live in modules/lift/ with PLAY/VOL scoped to lift, so a
nong board answered `ERR unknown cmd` — while the user had asked for a speaker
on the nong. Now the player is ONE core file behind __has_include, and every
type that wires an amp gets it by adding the lib to its env. This check pins
each half of that bargain so neither can quietly rot back:

* exactly one copy of the player exists,
* both module types handle PLAY/VOL through it,
* commands.json declares both scopes and COMMANDS.md no longer calls PLAY
  unknown on a nong,
* the generated module page carries the Speaker card for every type and gates
  it by capability, with pin groups that understand multi-type groups,
* platformio.ini gives the decoder lib to every env that declares the command.
"""
import sys

import qc as F

sys.path.insert(0, str(F.CODE / "tools"))
import registry  # noqa: E402  (JSONC loader — commands.json carries comments)

AREA = "firmware"
TITLE = "one speaker player, wired to every type that declares it"


def run(t):
    fw = F.FIRMWARE
    players = list((fw / "src").rglob("AudioPlayer.*"))
    t.eq(len(players), 2, "exactly one AudioPlayer.h + .cpp")
    if len(players) == 2:
        t.ok(all("core" in p.parts for p in players),
             "the player lives in core, not inside one module")

    for name in ("nong", "lift"):
        src = (fw / ("src/modules/%s/%sModule.cpp" % (name, name))
               ).read_text(encoding="utf-8", errors="replace")
        for verb in ("PLAY", "VOL"):
            t.contains(src, 'cmd == "%s"' % verb, "%s handles %s" % (name, verb))
        t.contains(src, "audio_.playCmd", "%s uses the shared parser" % name)

    decl = registry.commands()
    for scope in ("nong", "lift"):
        for verb in ("PLAY", "VOL"):
            t.ok(any(c["name"] == verb and c["scope"] == scope for c in decl),
                 "%s declared for %s" % (verb, scope))

    cmds_md = (fw / "COMMANDS.md").read_text(encoding="utf-8", errors="replace")
    t.ok("`RGB`/`PLAY`/`VOL` answer `ERR unknown cmd`" not in cmds_md,
         "COMMANDS.md does not call PLAY unknown on nong any more")

    # what the BOARD actually gets: gen_tables.py output, same as the build runs
    page = F.generated("web/ModuleUI.h")
    if t.ok(page.is_file(), "the module page was generated"):
        s = page.read_text(encoding="utf-8", errors="replace")
        t.contains(s, 'id="audCard"', "the Speaker card is on the page")
        t.contains(s, "pinGroupTypes", "pin groups understand multi-type groups")
        t.contains(s, "audio:['lift','nong']",
                   "the audio pin group belongs to lift AND nong")
        # ORDER, not only presence. The Speaker card used to be the first
        # thing on Move it, above the arm - the user asked for the robot
        # first and the music under it (2026-09-07).
        for other in ('id="nongCard"', 'id="liftCard"'):
            if other in s:
                t.ok(s.index('id="audCard"') > s.index(other),
                     "the Speaker card sits below %s, not above it"
                     % other.split('"')[1],
                     "Move it opens on the robot's own controls")

    pio = (fw / "platformio.ini").read_text(encoding="utf-8").split("[env:")
    for env in ("mice_nong]", "mice_lift]"):
        body = next((e for e in pio if e.startswith(env)), "")
        t.contains(body, "ESP8266Audio",
                   "%s carries the decoder lib" % env.rstrip("]"))
