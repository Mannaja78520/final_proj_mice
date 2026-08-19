# The user-facing surfaces

Five of them: `hub.html` (964 ln), `help.html` (1198),
`rgb.html` (309), `firmware/src/web/WebUI.h` (1109), and Nong Studio
(`index.html` 351 + `app.js` 4200+ + `style.css` 245).

## Where a user lands

`main.py:1961` auto-opens `http://127.0.0.1:8642/` → the hub. But
`hub.html:957` restores the last tab from `localStorage`, so a returning user
may land on Network or Tools with no cue that this is remembered state.

## Navigation, as it really is

```
HUB (/)                          3 tabs: Modules · Network · Tools
├── Modules   "found over WiFi" card + "plugged in by cable" card
│              (the two module lists are NOT adjacent in source, so the
│               cable list is easy to miss below the fold)
├── Network   group linking
└── Tools     exactly 2 apps: Nong Studio, Features & help

MODULE SITE (/mod?dev=…)         3 tabs, 13 cards, no link back to the hub
├── Move it        lift / nong / cam cards by build + capability
├── Shows & files  sequences · SD files · console
└── Setup & wiring login · peers · hardware pins · settings

STUDIO (/studio/)                4 side tabs + an always-visible timeline
├── Pose · Sequence · Robot · Setup

HELP (/help)                     1 page, 10 sections, 106 cards, 88 KB
                                 grouped BY CODE LOCATION, not by task
```

## Opening a module — the good path is genuinely good

| path | clicks | must know |
|---|---|---|
| hub → **⚙ Open module** (WiFi or cable) | **1** | nothing |
| hub → Studio + monitor | 1 | nothing |
| Tools → Studio → connect manually | 5 | maybe an IP |
| Studio over USB manually | 4 | **the COM port** |
| phone → hub | manual typing | **IP and port 8642** |

**But a cable row can open over WiFi.** `hub.html:450` prefers `wifi:` whenever
the board has an IP — so a row under the heading "Modules plugged in by cable",
described as "plugged in directly", opens over WiFi. Unplug the cable and it
still works; unplug WiFi and it does not.

~~**A module in AP mode is a dead end** presented as instructions
(`hub.html:467`): it points at "the USB page", which is `module.html` — a page
nothing links to and which redirects away.~~ **Fixed (A0-5):** `module.html` is
deleted and the message now says to plug the board in, where the cable list
below really does pick it up.

## Tools and Help

Tools is 1 click (tab 3). Help is 2 clicks, inside Tools, and it is
**the only entry point** — a grep for "help" across all five other surfaces
yields one unrelated substring (`WebUI.h:1011`, "re-flashing won't help").

Help is one 88 KB page grouped explicitly "by where each feature runs"
(`help.html:138`) — i.e. by code location — with the developer QC section in the
same list as user content. There is no "getting started", no "first time", no
"connect from a phone".

The Tools tab's own tip says *"use the Studio + monitor button on a nong module
above"* — but `showTab('tools')` has just hidden every module element, so there
is nothing above.

## Phone connection — the largest single gap

The address exists **only** as a console `print` (`main.py:1956-1958`). It is on
no web page. `MiceHub.exe` is the shipped artifact; close the console and the
address is gone.

* **No QR** — no match for `qr` in any Python or web file.
* **No mDNS for the hub** — no zeroconf import; `/api/scan` is a 254-address TCP
  sweep.
* **mDNS exists for boards only**, board-to-board (`PeerDiscovery.cpp:22-25`).
  The only user-visible trace is a placeholder string: `"module IP or
  name.local"` — and nothing tells you the name.
* Help documents it in two lines that **omit the port**.
* Every other occurrence of "phone" in the UI source is inside a CSS or JS
  comment.

## The five states — where they are missing

`rgb.html` is the reference: it has all five, with a CSS class per state and
reserved height so nothing jumps.

| surface | missing |
|---|---|
| `WebUI.h` `#peerList` | **error is dead code** — `const g` declared in `try{}`, used in `catch{}` → `ReferenceError`; stuck on `scanning...` forever, retried every 15 s |
| `WebUI.h` `#fileTbl` | **error is dead code** — catch targets `$('fileRows')`, element is `id="fileTbl"`; also no empty and no loading, so "no card", "busy" and "empty folder" all render as one blank table |
| `WebUI.h` `loadList()` | `catch(e){}` — zero states |
| `WebUI.h` header badges | no error, no stale; a lost socket only greys a dot |
| `hub.html` `#tools` | **error renders as empty** — `/api/apps` returns HTTP 200 with `{"ok":false,"apps":[]}` and the page checks `apps.length` first, so a broken registry says "No tools yet… drop one in" about folders that exist, **and Help disappears** |
| `hub.html` `#netlist` | no stale; if one of two probes fails it says "No modules found" |
| Studio `#seqList` `#projList` `#meshAssign` | **no try/catch at all**, fired unguarded at boot — a hub hiccup leaves the dropdowns at their placeholders, which reads as "your saved work is gone" |
| Studio `#robotStat` | no "connecting…" during a multi-second USB handshake |

## Where network complexity leaks onto main screens

14 leaks on the hub's default tab, including **`pio run -e mice_nong` — a
PlatformIO shell command — printed under every COM port** (`hub.html:770,796`)
and repeated in an `alert()`. Also raw IPs in every row, the `/24` subnet, the
literal `192.168.4.1`, COM port names, and `CH340 or CP210x`.

2 in the module site's permanent header: the raw IP **and signal strength in
dBm** (`WebUI.h:456`).

1 in an `<h1>`: `rgb.html:157` falls back to `💡 RGB — 192.168.1.47` or
`💡 RGB — COM7 #3` when no name is passed.

8+ in Studio's connect card, including three protocol names in one select and a
live badge reading `USB COM7→RS485 #3 (shared) ✓ + WiFi 192.168.1.5`.

Correctly hidden: the pin legend, the console placeholders, the peer chips, the
settings card — all behind login or in Setup.

## Identity in the UI — one board, five labels

```
hub, WiFi card     nong-1  [nong]  #3 · SD · 10.0.0.5
hub, cable card    nong-1  [nong]  #3 · COM7 · 10.0.0.5
hub, Network tab   nong-1          nong · 10.0.0.5   group: mice-show
module site        nong-1  ID 3  type nong  wifi 10.0.0.5 (-52dBm)
Studio             [USB COM7 (shared) ✓] nong-1 (id 3, type nong), SD ok
rgb.html, no name  💡 RGB — 10.0.0.5
```

A stable `id` exists in the data and is never the identity in the UI. The routing
key is the **transport**. The Modules tab does not dedupe at all, so a board on
WiFi *and* cable appears twice, and the two rows can produce the same URL.

## Flashing in the UI

Two entry points, mixed into module management: a flash box appended to **every**
cable slot, and `⚡ update over WiFi` appended into the module row itself — so
one row reads `[⚙ Open module] [direct] [Studio + monitor] [⚡ update over WiFi]
[💡 RGB]`, with the **destructive control styled quieter than the safe one**
(`hub.html` never defines `.danger`; since A0-4 it comes from `mice.css`, so
every page has it).

The choice offered is a module type plus a **file size in MB** — no version, no
date, no "what this will change". The confirms themselves are good. Cable flash
has a progress bar; OTA has status text only.

The failure message asks the user to send `SET TYPE <x>` — and `hub.html` has no
console to send it from.

## Duplicated UI

* ~~**Six copies of the design tokens** (`hub.html:8`, `module.html:19`,
  `rgb.html:12`, `WebUI.h:38`, `style.css:1`, `help.html:5`), each commented as
  "the SHARED design system". Nothing is actually shared.~~ **Fixed (A0-4):**
  one `shared/web/mice.css`, linked at `/mice.css` by every page and compiled
  into the board's flash by `firmware/tools/gen_tables.py`. `check_design_system`
  fails if a page declares tokens again.
* ~~**The "shared floor" block copy-pasted 4×**, and `module.html`/`rgb.html` use a
  weaker variant.~~ **Fixed (A0-4):** stated once in `mice.css` — focus ring,
  reduced motion and `pointer:coarse` targets.
* **Three tab systems, all called `showTab`**, with different class names, data
  attributes — and **different active styles**: the hub's is an outline tab while
  the module site's and Studio's are filled. The hub looks like a different
  product.
* **Four status-text classes**: `.mini`, `.statline`, `.hint`, `.now`. Still four
  names (element ids and QC drivers use them), but **one rule** in `mice.css`
  since A0-4, so they can no longer look different from each other.
* ~~**Six whole cards duplicated** between `module.html` and `WebUI.h`, with the
  same element ids, including `saveSettings()` **with its bug-fix comment** — and
  they have already diverged.~~ **Fixed (A0-5):** `module.html` is deleted;
  `WebUI.h` is the only module page.
* ~~**`module.html` has 8 joints where everything else has 10** — no WAIST, no
  SHRUG.~~ **Fixed (A0-5):** deleted. That was the reason it had to go rather
  than be maintained.
* Forward kinematics implemented twice in JS, and the module page's copy cannot
  see a tuned rig, so its XYZ readout disagrees with Studio's on any customised
  robot.
* `esc()` exists only in `hub.html`.

## Confusion points worth fixing first

1. **Studio writes its connection status into a hidden tab.** `app.js:3977` runs
   `showTab("pose")` at boot; `#robotStat` lives in the Robot tab. Every connect
   error renders into `display:none` while Play and Run-on-robot stay visible.
2. **The module site has no way back to the hub** — the page users spend the most
   time in.
3. ~~**`module.html` opened without `?port=`** is a fully functional-looking dead
   page that retries silently forever.~~ **Fixed (A0-5):** the URL is now a
   redirect — with a port it goes to that module, without one it goes to the
   hub.
4. **Studio has two Play buttons that mean different things**, distinguished only
   by a 12 px muted hint that can reflow onto a different line.
5. **The auto-check advice contradicts the shared-port design** — the hub says
   turn it off while using Studio over USB; the code says a port in use is never
   re-probed; Studio says both can be open at once. Three surfaces, three
   answers.
6. **The login card prints the default password** (`WebUI.h:135-137`) on a page
   reachable by anyone on the WiFi with no gate.
