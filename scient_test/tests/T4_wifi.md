# T4 — WiFi transport (tested on its own)

This file tests **the network path**, not the modules. Run it **once per
module** — once with the nong board, once with the lift board. Module type is a
control variable here, not a comparison.

Why separate from T3 (RS485) and T5 (USB): WiFi is the only transport that is
**wireless, routed and shared with other traffic**. Its independent variables —
distance, RSSI, obstacles, AP band, number of clients, mDNS — do not exist on a
wire, and its failure modes (5 GHz-only hotspot, roaming, DHCP, AP fallback)
have no equivalent there.

Source of truth: `code/firmware/src/core/WebPortal.cpp`,
`code/firmware/src/core/PeerDiscovery.cpp`,
`code/firmware/config/conf_network.h`, `code/firmware/COMMANDS.md` §1–2.

---

## What the firmware does on the network

| Behaviour | Value | Where |
|---|---|---|
| Band | **2.4 GHz only** (ESP32 has no 5 GHz radio) | hardware |
| STA connect timeout before fallback | **15 000 ms** (`WIFI_CONNECT_TIMEOUT_MS`) | `conf_network.h` |
| On failure | async scan + printed diagnosis, then **AP fallback** `MOD-…` / pass `12345678` | `startDiagnostic()`, `startAp()` |
| AP fallback in `on` mode | keeps retrying the real network every **60 s** | `WebPortal::loop()` |
| STA reconnect check | every **10 s** while online | `WebPortal::loop()` |
| WebSocket status push | every **500 ms** to all clients | `WebPortal::loop()` |
| Hostname re-apply check | every **2 s** (picks up `SET NAME` with no reboot) | `WebPortal::loop()` |
| mDNS | `http://<name>.local/`, service `_module._tcp` | `networkUp()`, `PeerDiscovery` |
| Peer scan | `MDNS.queryService` every **20 s** in its own task | `PeerDiscovery::taskLoop()` |
| Disconnect reasons logged | 201 = AP not found (or 5 GHz), 202/15 = auth failed | `WebPortal::begin()` |

HTTP surface: `/api/cmd?c=…`, `/api/status`, `/api/peers`, `/api/files`,
`/api/upload`, `/api/download`, `/api/delete`, `WS /ws`.

---

## Variables

### Independent variables

| # | Independent Variable | How to set it | Range used |
|---|---|---|---|
| 1 | **Distance from the AP** | move the module | 1 m, 5 m, 15 m, 30 m |
| 2 | **Obstacles / line of sight** | walls between module and AP | clear, 1 wall, 2 walls, metal frame |
| 3 | **Signal strength (RSSI)** | consequence of #1/#2, read from `INFO` | −40, −60, −75, −85 dBm |
| 4 | **WiFi mode** | `SET WIFI ON\|AP\|OFF` + reboot | on (STA + fallback), ap, off |
| 5 | **AP band / type** | the router or hotspot used | 2.4 GHz router, 2.4 GHz phone hotspot, **5 GHz-only** (must fail) |
| 6 | **Concurrent clients** | browsers / WebSocket connections open | 0, 1, 3, 6 |
| 7 | **Poll rate** | commands per second to `/api/cmd` | 1, 5, 10, 20 /s |
| 8 | **Addressing method** | how the host reaches the module | IP address, `<name>.local` (mDNS) |
| 9 | **Payload size** | file uploaded/downloaded over HTTP | 4 KB YAML, 200 KB, 3 MB MP3 |
| 10 | **Network load** | other traffic on the same AP | quiet, one device streaming video |
| 11 | **Module activity** | idle vs moving during the traffic | idle, sequence running |

### Dependent variables

| DV | Unit | How it is read |
|---|---|---|
| Round-trip latency | ms | `tools/bench.py wifi` — min / mean / p95 / max |
| Command success rate | % | same tool |
| RSSI | dBm | `INFO` → `wifi.rssi` |
| Time to ready after power-on | s | stopwatch from power to first successful `/api/status` |
| Time to AP fallback | s | power on with the AP off; time until the `MOD-…` SSID appears (expect ≈15 s + scan) |
| Late-join time | s | power on with no network, then switch the AP on; time until it joins (expect ≤60 s) |
| Reconnect time after AP drop | s | drop the AP mid-run, restore it, time to next successful command |
| mDNS resolve success | % | `ping <name>.local` / bench.py with the hostname, 20 attempts |
| Peers found | count | `/api/peers` vs modules actually powered |
| WS push interval | ms + jitter | timestamp arriving status frames; expect 500 ms |
| File transfer throughput | KB/s | upload/download of a known file, timed |
| File integrity | pass/fail | md5 compare after the round trip |
| Disconnect reason | code | serial log (`[wifi] disconnected, reason=…`) |

### Control variables

| CV | Fixed at |
|---|---|
| AP | one router, one SSID, one channel, fixed position — do not move it mid-series |
| Band | 2.4 GHz for everything except IV #5's deliberate 5 GHz run |
| Host PC | one laptop, one position (next to the AP), WiFi power-saving off |
| Command | `PING` for latency rows |
| Module state | idle, `HOME`d, except IV #11 |
| RS485 | disconnected, so bus traffic can't affect the timing |
| Module type under test | one per series — run the file for nong, then again for lift |
| Sample size | 50 commands per run, 3 runs per IV value |
| Firmware version + hostname | unchanged mid-series (`SET NAME` restarts the STA interface) |

---

## Tests

### WIFI-01 — distance and RSSI

CV: clear line of sight, 1 client, 10 cmd/s.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-01a | 1 m | `python ../tools/bench.py wifi --host <ip> --cmd PING -n 50`; record `wifi.rssi` from `INFO` | RSSI, success %, mean/p95 ms | RSSI ≈ −35…−45; 100 %; mean 5–20 ms | 100 %, p95 <100 ms |
| WIFI-01b | 5 m | same | same | RSSI ≈ −55; 100 % | 100 %, p95 <150 ms |
| WIFI-01c | 15 m | same | same | RSSI ≈ −70; occasional retry | ≥98 % |
| WIFI-01d | 30 m | same | same | RSSI ≈ −80…−85; loss appears | record the % |
| WIFI-01e | edge of range | walk out until success <90 % | distance, RSSI | **the usable range of the installation** | report both numbers |

Plot p95 latency and loss % against RSSI. The knee in that curve is the RSSI
below which the show cannot be driven over WiFi — a number worth putting on the
installation drawing.

### WIFI-02 — obstacles

CV: fixed 10 m distance, everything else as WIFI-01.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-02a | clear line of sight | bench.py ×50 | RSSI, success %, p95 | baseline | 100 % |
| WIFI-02b | 1 plasterboard wall | same | same | −5…−10 dB | ≥99 % |
| WIFI-02c | 2 walls | same | same | −15…−20 dB | ≥95 % |
| WIFI-02d | metal frame / inside the set | put the module where it will actually live | same | the real installed condition | record — this is the number that matters |

WIFI-02d is the most important row in the file: it measures the module **where
it will be installed**, not on the bench.

### WIFI-03 — WiFi mode and AP fallback

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-03a | `on`, AP present | `SET WIFI ON`, reboot | time to ready (s), serial log | joins, prints ip, mDNS up | ready <15 s |
| WIFI-03b | `on`, AP absent | turn the AP off, reboot the module | time until the `MOD-…` SSID appears | 15 s timeout + scan, then AP fallback | AP up <30 s |
| WIFI-03c | `on`, AP appears late | continue 03b, switch the AP on, wait | time to join (s) | retries every 60 s → joins, **fallback AP stays up** | joins ≤75 s |
| WIFI-03d | `ap` | `SET WIFI AP`, reboot | website reachable at 192.168.4.1? does it ever join the router? | own hotspot only, never joins | matches |
| WIFI-03e | `off` | `SET WIFI OFF`, reboot | is the radio off? time to ready on **USB**? | no WiFi at all; **fastest boot** — USB/RS485 respond ~1 s | no SSID; note the boot time |
| WIFI-03f | wrong password | `SET WIFI <ssid> wrongpass`, reboot | serial `reason=` code | **202 or 15** = auth failed | correct code logged |
| WIFI-03g | 5 GHz-only AP | point it at a 5 GHz-only hotspot | serial `reason=` code, scan output | **201** = AP not found, and the scan says "NOT visible on 2.4GHz" | correct diagnosis |

WIFI-03e is a fair comparison point between transports: it measures **boot-to-
controllable** with the radio off, which is the fastest the module can ever be.

### WIFI-04 — concurrent clients (WebSocket load)

CV: 5 m, clear, module idle. Every connected browser gets a full status JSON
every 500 ms.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-04a | 0 browsers | bench.py ×50 | p95 ms, success % | baseline | 100 % |
| WIFI-04b | 1 browser open | open the module website, repeat | p95 ms, WS interval + jitter | ≈500 ms pushes; latency barely moves | 100 %, jitter <100 ms |
| WIFI-04c | 3 browsers | three tabs/devices, repeat | same | three status pushes per 500 ms | ≥99 % |
| WIFI-04d | 6 browsers | repeat | same, plus dropped WS clients | the point where the async server saturates | record |
| WIFI-04e | 3 browsers + Nong Studio live mode | add the editor in `live` mode | p95 ms, pose lag | the realistic show-control load | record |

### WIFI-05 — command rate

CV: 5 m, 1 client.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-05a | 1 /s | bench.py `--rate 1 -n 50` | success %, p95 | 100 % | 100 % |
| WIFI-05b | 5 /s | `--rate 5` | same | 100 % | 100 % |
| WIFI-05c | 10 /s | `--rate 10` | same | 100 % | ≥99 % |
| WIFI-05d | 20 /s | `--rate 20` | same | each `/api/cmd` is a new HTTP connection — this is where it costs | record |
| WIFI-05e | WebSocket instead of HTTP | send the same 50 commands as WS text frames | p95 ms vs 05c | **lower** than HTTP — one open connection, no handshake per command | report the difference |

WIFI-05e answers a real design question with a measurement: for live posing,
use the WebSocket, not `/api/cmd`. Prove it here.

### WIFI-06 — addressing: IP vs mDNS

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-06a | raw IP | bench.py `--host 10.x.x.x` ×50 | success %, p95 | 100 % | 100 % |
| WIFI-06b | `<name>.local` | bench.py `--host nong.local` ×50 | success %, p95, first-resolve time | works; the first call pays the mDNS lookup | ≥99 % |
| WIFI-06c | `.local` from a phone | same from iOS/Android | resolve success | Apple resolves mDNS natively; Android is patchy | record per platform |
| WIFI-06d | after `SET NAME` | `SET NAME nong2`, wait, then `nong2.local` | time until the new name resolves | the hostname check runs every 2 s and restarts the STA interface | resolves <30 s |
| WIFI-06e | DHCP lease change | reboot the router, then reach the module | IP change, `.local` still working? | the IP may move — mDNS is why the name is used | `.local` still works |

### WIFI-07 — fleet discovery (`/api/peers`)

CV: all modules powered, same AP.

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-07a | 1 module | `GET /api/peers` | entries | 1 (itself, `self:true`) | exact |
| WIFI-07b | 2 modules | same, on each module | entries, time until complete | 2 within one scan cycle (20 s) | complete ≤40 s |
| WIFI-07c | 4 modules | same | entries | 4 | complete ≤40 s |
| WIFI-07d | one module rebooting | power-cycle one, poll `/api/peers` on another | time until it disappears / reappears | list refreshes on the 20 s scan | reappears ≤40 s |
| WIFI-07e | one module in AP mode | set one to `ap`, poll from a module on the router | is it listed? | **no** — it's on a different network. The expected, correct answer | confirm and document |

### WIFI-08 — file transfer over HTTP

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-08a | 4 KB YAML upload | `POST /api/upload?dir=/moves` | seconds, KB/s, integrity | fast; `MOVE <file>` then plays it | md5 match |
| WIFI-08b | 200 KB upload | same | KB/s | SD write speed starts to dominate | md5 match |
| WIFI-08c | 3 MB MP3 upload | same to `/music` | KB/s, any timeout? | the realistic worst case | md5 match, no reset |
| WIFI-08d | 3 MB download | `GET /api/download?path=/music/a.mp3` | KB/s, integrity | chunked response | md5 match |
| WIFI-08e | download aborted midway | start 08d, kill the browser tab | does the module stay healthy? | `onDisconnect` closes the file under the SD mutex | still answers `PING` |
| WIFI-08f | upload while moving | 08b while a sequence runs | KB/s, motion smoothness, drop-outs | SD and motion share the loop | record both effects |

### WIFI-09 — robustness

| ID | IV setting | Command / action | Measure (DV) | Expected | Pass if |
|---|---|---|---|---|---|
| WIFI-09a | AP dropped mid-command-stream | run bench.py `-n 500`, power-cycle the AP mid-run | commands lost, seconds to recover | reconnect check runs every 10 s | recovers ≤60 s |
| WIFI-09b | module power-cycled | reboot the module during a poll loop | seconds to recover | full boot + join | recovers ≤20 s |
| WIFI-09c | busy network | start a video stream on the same AP, repeat WIFI-01b | p95 ms, success % | latency rises; airtime is shared | record |
| WIFI-09d | module moving | run a sequence, poll at 10/s | p95 ms, success %, motion smoothness | web server runs in its own async task | motion unaffected |
| WIFI-09e | long soak | poll at 1/s for 60 min | success %, memory (`INFO`), any reboot | must be stable — this is the show-length test | no reboot, ≥99.5 % |

---

## Run this file twice

| Series | Device under test | Everything else |
|---|---|---|
| T4-NONG | the nong board | lift board off or on another AP |
| T4-LIFT | the lift board | nong board off or on another AP |

Record both in [`../results/wifi_results.csv`](../results/wifi_results.csv); the
`module` column separates them.
