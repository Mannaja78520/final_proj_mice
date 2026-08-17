# QC — re-check everything after any change

```
python qc/run_qc.py            everything (~1 min, drives a real browser)
python qc/run_qc.py --quick    no browser (~3 s) — use while iterating
python qc/run_qc.py connection only checks matching a word
python qc/run_qc.py --list     what is covered today
python qc/run_qc.py -v         show every passing assertion, not just failures
```

Exit code 0 = green, 1 = something regressed. No pip installs: stdlib plus the
Edge that is already on the machine.

**Run `--quick` after every edit, and the full suite before saying something
works.** Every assertion in here is a bug that actually shipped once.

## What it covers

| area | file | guards |
|---|---|---|
| `connection` | `check_connection.py` | one USB cable shared by the module site + Studio, one handle not one per client, replug recovery, busy-cable message, RS485 framing, command latency budget |
| `contracts` | `check_contracts.py` | firmware ↔ Studio agreement: joint count, joint ORDER, move-time floor, every command Studio sends exists, COMMANDS.md not stale, the per-joint-array trap |
| `hub` | `check_hub_api.py` | the pages a user opens, the dev API on every transport, the log-line vs JSON parsing rule |
| `studio` | `check_studio_boot.py` | opens on the Neutral pose, old saved rigs migrate, no NaN/invisible robot |
| `studio` | `check_studio_live.py` | a fast drag leaves the arm where the numbers say |
| `studio` | `check_studio_playback.py` | Play sends over any link, keyframe 0, hold between moves, Pause really stops, resume asks for the remainder |
| `docs` | `check_docs.py` | the offline help page describes every command, module type, servo preset and QC area — docs rot is a failure, not a note |
| `responsive` | `check_responsive.py` | every web app measured in a real browser at 360–1920px; fails if anything scrolls sideways |
| `firmware` | `check_firmware_build.py` | the real PlatformIO build compiles and still fits, plus native tests that RUN the gear/travel maths and move-time floor on the PC |
| `registries` | `check_registries.py` | adding an app, servo, command or capability costs one file — it adds a throwaway app every run to prove it |
| `transports` | `check_transports.py` | the same command, SD transfer and pin-config round trip on USB/UART, RS485, direct Web Serial and WiFi |
| `persistence` | `check_persistence.py` | every save path returns exactly what went in; bad names refused |
| `sendrig` | `check_sendrig.py` | sending the rig stays one command per joint, values intact |
| `view` | `check_view.py` | the standard views really are orthographic |
| `sequences` · `edge cases` · `calibration` | | suspend/chain/speed, the awkward states, tuning surviving a power cycle |

## Adding a check — this is the point

**Every time we add something to the project, add its check here.** Nothing is
registered by hand: `run_qc.py` finds every `checks/check_*.py` by itself, so a
new area of the system is one new file. The suite is meant to grow with the
project rather than freeze at whatever we happened to think of first.

```python
"""One line on what part of the system this guards."""
import qc as F

AREA  = "connection"        # connection | contracts | hub | studio | firmware | ...
TITLE = "what it proves"
SLOW  = False               # True if it drives a browser (skipped by --quick)

def run(t):
    base, main = F.start_hub()          # hub + a fake nong on COM99
    s, b = F.cmd(base, "INFO")          # talk to it the way Studio does
    t.contains(b, '"type"', "the module answers INFO")
```

`t` collects results instead of raising, so one run reports **every** problem,
not just the first. Assertions: `t.ok(cond, label, detail)`, `t.eq`,
`t.contains`, `t.under(value, limit, label, unit)`, and `t.give_up(why)` when a
precondition is missing (a missing browser, not a failure).

New `AREA` names need no registration — invent one when a new part of the
system appears.

### The rule that makes a check worth writing

**Break the fix and watch the check fail.** A check that passes both before and
after guards nothing. This is not optional — the live-drag check passed against
the very bug it was written for until the driver was corrected to reproduce the
real user action (dragging without a final commit event).

### A check must never touch the user's data

`check_persistence` writes through `/api/rigdefault`, which **overwrites**
`rig_default.json` — the file holding the real robot's measured geometry. The
first version of that check left a three-field dummy in its place and destroyed
the tuning; only `promote.py` refusing to promote a red suite kept it out of the
working tree.

Any check that writes to a real path must back the file up first and restore it
in a `finally`, then assert it came back. Test data and user data live in the
same folders here.

### Moved files must be deleted in the real tree too

`promote.py` copies but never deletes, so a file you MOVED in staging still
exists at its old path in the real tree and comes back on the next `--init`.
That silently re-broke the native firmware build once. Promotion now lists them
loudly with the `del` commands to run.

### Browser checks

`lib/browser.py` carries the hard-won details — read its docstring before
touching it. Short version: Edge must be launched through `Start-Process`;
never reuse a profile directory; `--virtual-time-budget` breaks anything that
measures time; `--dump-dom` never finishes while a page keeps fetching; and
`alert()` blocks headless forever.

Report results through `qcMark("...")` (it goes down the module wire and the
fake records it) rather than the DOM, unless the page truly goes idle.

### Assert on the wire, not on the UI

The UI is always right about itself — `pose` holds the value you set, the
slider shows it — while the **arm** sits somewhere else. `fake_serial.wire`,
`.poses()` and `.qc_marks` record what the module was actually told, with
timestamps. Assert on those.

## The fake module

`lib/fake_serial.py` is a stand-in `serial` module: one **exclusive** COM99, so
a second open fails exactly like Windows. That exclusivity is the whole point —
it is what proves the hub shares one handle instead of each client opening its
own. It can also play dead (`fake_serial.dead[0] = True`) to reproduce a
replugged board, and records every command with the time it arrived.
