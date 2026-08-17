# Mice — what changed, 27 Jul → 10 Aug 2026

Two weeks. Short version: the project went from *one program that drove one
robot* to *a system that finds its own modules, flashes them, and keeps a show
running without a browser*.

Numbers, start → end:

| | 27 Jul | 10 Aug |
|---|---|---|
| QC assertions | ~250 | **1387** |
| firmware builds | 1 (everything in one) | **5** (nong, lift, cam, blank, all-in-one) |
| module types | 2 (lift, nong) | **4** (+ cam, + blank) |
| web patches | 0008 | **0048** |
| firmware patches | ~0001 | **0031** |

---

## The five big ones

**1. One firmware per module type.**
Every board used to carry the code *and the web page* for every other type — a
nong shipped the lift's controls. Now each board gets only its own. Flash went
from 74.9% to 65.5% (nong) / 62.5% (blank), and a lift's web page no longer
even *contains* the nong markup, so no bug can show the wrong controls.

**2. The hub flashes boards — over USB and over WiFi.**
Pick a type on the hub page and press Flash; the cable is handed to esptool and
handed back. Updating over WiFi (OTA) works too — the camera board was updated
twice with no cable attached. A failed update cannot brick a board: the old
firmware stays in the second slot.

**3. The hub became the show clock.**
The biggest day-to-day fix. A browser tab that is hidden has its animation loop
stopped and its timers slowed to about once a minute — that is browser policy,
not something code can opt out of. So playback moved into the hub, which is a
normal program nothing throttles. A rehearsal now survives switching apps,
minimising, or closing the browser entirely.

**4. Modules find each other, and only their own.**
Every module hosts its own hotspot all the time, so a board out of router range
can join a neighbour and be reached through it. A module on a weak link moves to
a stronger neighbour by itself. **Groups** keep that safe: a module's hotspot
password is derived from its group name, so two companies on the same site can
each let their own modules link up and neither can touch the other's.

**5. A camera module type.**
The ESP32-CAM now runs the same firmware family and serves real 320×240 frames.
It can never be a servo module — the camera uses almost every pin — but as its
own type it costs the other modules nothing.

---

## Things that were quietly broken and now are not

- **The USB lag.** The hub waited up to 80 ms before *every* command. On live
  sliders that was most of the delay. Now ~16 ms per command, ~48 commands/sec.
- **Nong Studio crashed the PC.** It leaked a material on every 3D rebuild —
  and it rebuilds on every rig edit. That is a graphics-memory leak, which is
  why the whole machine went down rather than just the tab.
- **The joint sliders never appeared** on the module website. One variable was
  used and never defined, which threw halfway through drawing the page and took
  everything below it with it.
- **Two clocks drove the robot at once.** The module kept playing its own
  sequence while Studio streamed poses, so the arm fought itself and Stop only
  stopped one of them.
- **The 3D view covered the settings panel**, and the splitter between them
  could not be dragged.
- **Suspending a keyframe** kept the old move's time, so the arm sat still for
  400 ms going nowhere.
- **Replies came back shifted by one** while the radio was busy — 49 of 60
  commands returned the *previous* command's answer.

---

## New things you can use

- **Move your setup to another PC** — export/import a file, or Share on one PC
  and Get on the other over the network. (Studio → Setup)
- **Groups** — tick which modules belong together. (Hub → Network)
- **Run on robot** — hands the show to the module; keeps going with the page
  closed.
- **Shrug calibration curve** — for the 4-bar linkage, so the preview matches
  the real shoulders. *Waiting on measurements.*
- **`WIFI` command** — see and change the radio live, no reboot.
- **`GROUP`, `PEERS`, `REACH`** — ask a module who it can see, and talk to
  another module through it.

---

## How it looks

`docs/shots/` — **`studio-old.png` (27 Jul) vs `studio-new.png` (10 Aug)** is
the clearest pair. Also `hub-new.png` and `help-new.png`.

`module-site-new.png` shows only the header and the new tab names: no board was
plugged in when it was taken, so every card is hidden (the page shows only what
the module reports it has). Retake it with a module connected.

There is no "old" hub or help shot — only Nong Studio's files are kept in the
patch system, so 27 Jul versions of those pages no longer exist anywhere.

**Nong Studio** went from two side tabs (*Movement / Setup*) to four grouped by
task (*Pose / Sequence / Robot / Setup*), and the 3D model now shows your real
tuned proportions instead of placeholder spheres.

**The hub** gained tabs (*Modules / Network / Tools*), plain-language headings,
a per-cable flash control, and it now says *when* it last checked rather than
silently showing old data.

---

## Still open

- **SHRUG measurements** — on hold, needs the robot.
- A **nong board with servos actually attached** has never been driven; the test
  board is lift hardware.
- **RS485** between two modules is not exercised.
- Two boards **drop off USB** at random — cable or power.
- Browser-driven QC checks **flake under load** when several run at once; they
  pass alone. Worth making them serial.
