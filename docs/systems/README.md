# Systems

Find the file you are changing below, read that ONE page, and stay in it.
`python tools/systems.py which <path>` answers the same question.

Generated from `docs/systems.json` by `tools/systems.py build`.

| system | what it is |
|---|---|
| [hub-resources](hub-resources.md) | Machine-local configurable CPU/GPU/RAM policy, bounded capability discovery, next-load Voice budgets and independent client display choices. |
| [hub](hub.md) | The hub program: HTTP server, the device routes (dev, modules, USB proxy, pairing, robot proxy), startup. Split into hub-* systems (A26-76, A26-93). |
| [hub-usb](hub-usb.md) | The hub's USB serial manager (one owner of every cable) and the port probe that finds which module is on which cable. |
| [hub-flash](hub-flash.md) | Flashing a board: esptool over the cable, OTA over WiFi, chunks over the command channel, and images sent from another PC. |
| [hub-show](hub-show.md) | The hub as the show clock: the show player, live audio to a speaker, the rig's one speaking queue and its speakers, saved shows by name, stop-all. |
| [hub-apps](hub-apps.md) | The hub's routes for the app launcher, page access, partner programs and the voice helper. |
| [hub-support](hub-support.md) | Self-update, the diagnostics text and problem reports. |
| [hub-studio](hub-studio.md) | The hub's routes for Nong Studio's files, shared settings and the list of other hubs. |
| [hub-auth](hub-auth.md) | Hub logins, sessions, which pages need a login, pairing two hubs. |
| [hub-modules](hub-modules.md) | The one module list: every board once, with every route to it, and the fastest route chosen. |
| [hub-net](hub-net.md) | Finding boards and other hubs on the network, mDNS names, QR codes, choosing the fastest route. |
| [hub-media](hub-media.md) | Camera relay, camera board pinouts, and audio streaming to boards. |
| [hub-shows](hub-shows.md) | Saved shows: sequences played in series by name. |
| [hub-web](hub-web.md) | The pages the hub serves: Home/Modules, help, login, and their patch snapshots. |
| [shared-web](shared-web.md) | One stylesheet and theme set for every page (mice.css, themes), and the page parts every hub page is built from (mice-ui.js; guide docs/web_style.md). |
| [studio](studio.md) | Nong Studio: pose editor, timeline, 3D monitor. |
| [nong-sim](nong-sim.md) | Optional MuJoCo world: any number of Nongs play Studio sequences with servo lag, gravity and the board's clock (tools/nong_sim, user 2026-10-27). Nothing else needs it. |
| [app-voice](app-voice.md) | Voice helper: speech in, answers, speech out. |
| [app-gacha](app-gacha.md) | Prize machines (gachapon): several gacha boards, kinds, hand-over when one is empty, rules per event and person (local or Google Sheet), webhooks, the prize log; and which Voice answers give a prize plus the Voice question log (A47-2, A47-3); wins in the friend's games (/play/<id>/ + apps/all-jao/link.js) and app keys for other PCs (A47-6, A47-7). |
| [app-faces](app-faces.md) | Face recognition app. |
| [app-camera](app-camera.md) | Camera viewer app. |
| [app-small](app-small.md) | Small apps: help, All-Jao, Photobooth, TV Remote. |
| [fw-core](fw-core.md) | Firmware shared by every board: identity, commands, RS485, WiFi/web portal, SD, OTA, PERF?. |
| [fw-web](fw-web.md) | The board's own website (WebUI.h). |
| [fw-nong](fw-nong.md) | The nong (humanoid) module: servos, joints, poses. |
| [fw-dummy](fw-dummy.md) | The dummy module: a hand-posed copy of the nong, a pot on every joint, answers POSE?. |
| [fw-gacha](fw-gacha.md) | The prize dispenser module (gachapon): one motor, one hall sensor at the loading place, magnets under the pockets; counts, turns, refuses when closed or empty (A47-1); no encoder (user 2026-10-22). |
| [fw-lift](fw-lift.md) | The lift module: motor, limit switches (encoder optional, off by default: the built lift has none), RGB, speaker. |
| [fw-cam](fw-cam.md) | The camera module (ESP32-CAM). |
| [fw-registry](fw-registry.md) | Registries: commands, modules, servos, amps, cameras, pins - and the generators that turn them into firmware tables. |
| [qc](qc.md) | The QC suite, its gate and the promotion tool. |
| [build](build.md) | Web asset and Studio builds. |
| [agents](agents.md) | Plan, handoff and multi-AI tooling: plan.py, bridge, review panel, AI entry files. |
| [bench](bench.md) | Scripts for real boards on the bench. |
| [docs](docs.md) | Plan, references, thesis sources, architecture notes, panel reports. |
| [misc](misc.md) | One-off scripts and experiments kept for reference, and any loose file at the top of the tree. Move a file out of here when it becomes part of a system. |
