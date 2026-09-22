# Systems

Find the file you are changing below, read that ONE page, and stay in it.
`python tools/systems.py which <path>` answers the same question.

Generated from `docs/systems.json` by `tools/systems.py build`.

| system | what it is |
|---|---|
| [hub](hub.md) | The hub program: HTTP server, the device routes (dev, modules, USB proxy, pairing, robot proxy), startup. Split into hub-* systems (A26-76, A26-93). |
| [hub-usb](hub-usb.md) | The hub's USB serial manager (one owner of every cable) and the port probe that finds which module is on which cable. |
| [hub-flash](hub-flash.md) | Flashing a board: esptool over the cable, OTA over WiFi, chunks over the command channel, and images sent from another PC. |
| [hub-show](hub-show.md) | The hub as the show clock: the show player, live audio to a speaker, saved shows by name, stop-all. |
| [hub-apps](hub-apps.md) | The hub's routes for the app launcher, page access, partner programs and the voice helper. |
| [hub-support](hub-support.md) | Self-update, the diagnostics text and problem reports. |
| [hub-studio](hub-studio.md) | The hub's routes for Nong Studio's files, shared settings and the list of other hubs. |
| [hub-auth](hub-auth.md) | Hub logins, sessions, which pages need a login, pairing two hubs. |
| [hub-net](hub-net.md) | Finding boards and other hubs on the network, mDNS names, QR codes, choosing the fastest route. |
| [hub-media](hub-media.md) | Camera relay and audio streaming to boards. |
| [hub-shows](hub-shows.md) | Saved shows: sequences played in series by name. |
| [hub-web](hub-web.md) | The pages the hub serves: Home/Modules, help, login, and their patch snapshots. |
| [shared-web](shared-web.md) | One stylesheet and theme set for every page (mice.css, themes). |
| [studio](studio.md) | Nong Studio: pose editor, timeline, 3D monitor. |
| [app-voice](app-voice.md) | Voice helper: speech in, answers, speech out. |
| [app-faces](app-faces.md) | Face recognition app. |
| [app-camera](app-camera.md) | Camera viewer app. |
| [app-small](app-small.md) | Small apps: help, All-Jao. |
| [fw-core](fw-core.md) | Firmware shared by every board: identity, commands, RS485, WiFi/web portal, SD, OTA, PERF?. |
| [fw-web](fw-web.md) | The board's own website (WebUI.h). |
| [fw-nong](fw-nong.md) | The nong (humanoid) module: servos, joints, poses. |
| [fw-lift](fw-lift.md) | The lift module: motor, encoder, limits, RGB, speaker. |
| [fw-cam](fw-cam.md) | The camera module (ESP32-CAM). |
| [fw-registry](fw-registry.md) | Registries: commands, modules, servos, amps, cameras, pins - and the generators that turn them into firmware tables. |
| [qc](qc.md) | The QC suite, its gate and the promotion tool. |
| [build](build.md) | Web asset and Studio builds. |
| [agents](agents.md) | Plan, handoff and multi-AI tooling: plan.py, bridge, review panel, AI entry files. |
| [bench](bench.md) | Scripts for real boards on the bench. |
| [docs](docs.md) | Plan, references, thesis sources, architecture notes, panel reports. |
| [misc](misc.md) | One-off scripts and experiments kept for reference, and any loose file at the top of the tree. Move a file out of here when it becomes part of a system. |
