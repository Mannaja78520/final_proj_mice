# Speed and reconnect sweep (2026-11-21)

Asked 2026-11-21: "test every speed and every reconnect", including many boards (30..255 on RS485),
WiFi backup networks and far boards with others in between. Everything below ran in a 4-core cloud
container: hub, voice and faces were real processes on localhost, boards were QEMU or models.
**Nothing here was measured on a real board or a real radio.** Raw files (private):
`/mnt/project-files/experiments/2026-11-21_speed_reconnect/`; scripts: `tools/bench/`.

## 1. Services, 200 clients at once (tools/bench/chaos_services.py)

Cause: `ThreadingHTTPServer` listens with a queue of 5; a burst waits for a SYN retry (1 s, 3 s, 7 s).
Fix: `request_queue_size = 256` in hub, voice, faces.

| path (200 clients) | p95 before | p95 after | errors before / after |
|---|---|---|---|
| / | 1430 ms | 162 ms | 0 / 0 |
| /studio/ | 2062 ms | 239 ms | 0 / 0 |
| /app/voice/ | 6018 ms | 936 ms | 56 / 0 |
| /api/version | 2047 ms | 75 ms | 2 / 0 |
| /api/modules | 2054 ms | 161 ms | 13 / 0 |
| /api/ports | 5926 ms | 3546 ms | 29 / 0 (still slow: serial probing) |

One client: p50 0.6 to 2.2 ms on every path. Voice at 50 clients: p95 1020 ms to 89 ms.
Hub p99 while voice is killed and restarted every 4 s: 1021 ms to 16 ms (1200 requests, no errors).

## 2. Kill and restart (kill -9 three times each)

- Voice: down seen at once, hub answers 503 in 16 ms, the hub starts it again by itself in 0.23 s.
- Faces: hub answers 503 in 2 ms; it does not restart by itself (by design, it holds a login: Start button); starts in 0.12 s.

## 3. Hub list with many boards (tools/bench/hub_many_boards.js, stubbed boards, 390 and 1440 px)

5/30/100/255 boards render, no sideways scroll. The order was text order (id 100 before 20, "lift 10" before
"lift 2"), no grouping. Now kind, then name with numbers as numbers, then id; a heading per kind when 8 or more
boards and more than one kind; the filter hides empty headings. A phone row is about 180 px, so 255 boards is a long scroll.

## 4. RS485 census, 5..255 boards (tools/bench/bus_census_model.py)

Model of one wire at 115200 baud, overlap loses both lines. Old rule `(id % 24) * 10 ms`: boards with ids 24 apart
share a slot. Lost answers per sweep, old rule: 30 boards 12 (contiguous ids) or 21 (random ids), 60 boards 55-60,
100 or more: nearly all. New rule `id * 6 ms` (BusSlot.h): 0 lost at every size; id 255 answers at 1530 ms,
inside the hub's 1.6 s listening floor. QEMU check: ids 9 and 33 (same old slot) answer 0.2 s apart in id order.

## 5. WiFi

- The board kept ONE home network. Now `SET WIFI2` / `SET WIFI3` add backups; a failed join walks them in order, then falls
  back to the hotspot and retries the whole list (every 20 s with backups, 60 s without). Native test + QC; QEMU has no radio.
- Relay model (tools/bench/wifi_topology_model.py, the firmware's own `WifiLink.h` compiled and called): a module only
  joins a hotspot whose name sorts after its own. A line of 10 boards leaving the router with names rising outward strands 9;
  random layouts of 100 or 255 boards strand 71 and 234 (noise 3 dB; chains of up to 6 hops form on paper but cannot route:
  every hotspot is 192.168.4.1/24). Not fixed: needs a rule choosing a host that is itself online. Proposal: host announces
  "online to router" in its hotspot name or beacon; join only such hosts, strongest first.

## 6. On the PC (Windows 11, real hub, real friend app, real Ollama; measured before #154 reached the PC)

- Hub, one client p50: 11-18 ms per page (cloud 1-2 ms). 200 clients: p95 about 2010 ms and 25-114 failed requests per page
  (Windows connection retry: same cause as the cloud; re-measure after #154 reaches the PC).
- Voice kill x3: hub answers 503 about 1 s, revives it itself in 5.4 s (first kill 10.1 s). Faces kill x3: hub revived it once (11 s), twice not within 25 s.
- Friend app Face_Regonize, read-only, 1/10/50 clients p95: /api/health 39/17/219 ms, /openapi.json 42/92/169 ms, page 5173 13/15/34 ms, no errors.
  /api/history needs a login (not measured). It was not running at the start (nothing keeps it up).
- Friend backend killed: our faces service saw the live feed drop in under 4 s, the hub page showed only live=false (no message),
  friend back in 8 s, our feed live again at 27 s (19 s of reconnect backoff). Fixed: backoff cap 30 s to 5 s.
- Ollama: normal 0.3-0.8 s. Killed: next question 9.3 s (hub restarts it) then 0.3 s. Blocked from starting: first turn 45 s
  (40 s wait, then Qwen 0.5B), recovery to Typhoon about 60 s (cooldown) plus 6.9 s model load. Changed: start wait 40 s to 15 s.
- Cloud provider with a bad key (Groq): first turn 11 s (includes Qwen cold load), later turns 2 s.
- Not run: replug check (no USB/RS485 adapter on the PC), cloud provider with the network blocked.

## Not covered here

Friend apps (8000/5173; not in the cloud), Ollama down/up and cloud think failover timing (PC), real WiFi radio, real
RS485 timing with 30+ boards, real OTA. Hub census asks INFO of only the first 6 boards per bus (hub_probe.py): boards 7+
show no chip/group.
