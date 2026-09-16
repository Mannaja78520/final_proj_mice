// --- robot link ---
// Transports, one command language (see firmware COMMANDS.md):
//   wifi   — HTTP through the local python proxy (/api/robot/*)
//   usb    — the cable, THROUGH THE HUB (/api/usb/cmd?port=..&id=..). This is
//            the default: a COM port can only be opened by one program, and
//            the hub is that one owner. It shares the port between all of its
//            pages, so the module website (/mod?dev=usb:COMx) and Nong Studio
//            can drive the SAME cable at the same time — no more
//            "serial port already in use" when both are open. It also works
//            from a phone/laptop on the LAN, where Web Serial does not exist.
//   serial — optional DIRECT Web Serial from this browser. Lowest latency and
//            works with no hub, but it OWNS the port exclusively: while it is
//            connected nothing else (module website, hub probe) can use that
//            cable. Chrome/Edge on the host PC only.
// With an empty "bus id" the cable goes straight into the nong module's USB.
// With a bus id set, every command is framed "#<id> ..." and replies
// "@<id> ..." — the RS485 wire protocol, so the same mode covers BOTH a
// USB-RS485 dongle on the bus AND reaching the nong through any other
// module's USB port (modules bridge '#' lines onto the bus).
// Every text command AND SD file transfer works on all transports (see the
// sdUpload/sdDownload/sdDelete helpers below).
function robotIp() { return $("robotIp").value.trim(); }
function transport() { return $("connSel").value; }
function busId() { const v = $("busId").value.trim(); return v ? parseInt(v, 10) : 0; }

let serialPort = null;    // direct Web Serial handle (exclusive mode)
let serialWaiters = [];   // [{filter(line)->string|null, res, rej}]
let hubPort = "";         // COM port driven through the hub (shared mode)

function connModeChanged() {
  const t = transport(), usb = t === "usb", direct = t === "serial";
  $("robotIp").style.display = (usb || direct) ? "none" : "";
  $("busId").style.display = (usb || direct) ? "" : "none";
  $("usbPort").style.display = usb ? "" : "none";
  $("usbRescan").style.display = usb ? "" : "none";
  $("connBtn").textContent = direct && !serialPort ? "Connect USB" : "Connect";
  if (usb) { if (!$("usbPort").dataset.loaded) loadPorts(); }
  else if (direct && !("serial" in navigator)) {
    $("robotStat").textContent = "This browser cannot open a USB port by itself. "
      + "Pick “+ USB (shared)” instead — the hub opens the cable and shares it — "
      + "or connect over WiFi. (Web Serial works in Chrome and Edge.)";
    notice($("robotStat").textContent);
  }
}

// ------- shared USB: the hub owns the port, we send commands through it
// The hub serialises every command per port, so this page and the module
// website can hold the same cable at once.
async function loadPorts(keepSel) {
  const sel = $("usbPort"), want = keepSel || sel.value;
  sel.innerHTML = "<option value=''>looking for USB ports…</option>";
  try {
    const r = await fetch("/api/ports").then(r => r.json());
    const ps = (r.ports || []).filter(p => !p.bt);
    sel.innerHTML = "<option value=''>pick the USB port…</option>";
    ps.forEach(p => {
      const o = document.createElement("option");
      o.value = p.port;
      o.textContent = p.port + (p.who ? " — " + p.who : (p.desc ? " — " + p.desc : "")) +
        (p.inuse ? " · in use (shared)" : "");
      sel.appendChild(o);
    });
    if (!ps.length) sel.innerHTML = "<option value=''>no USB port found — cable plugged in?</option>";
    sel.dataset.loaded = "1";
    if (want && ps.some(p => p.port === want)) sel.value = want;
    else if (ps.length === 1) sel.value = ps[0].port;
  } catch (e) {
    sel.innerHTML = "<option value=''>the port list needs the hub (python main.py)</option>";
  }
}
function usbPortChanged() {   // picking another port drops the old link
  if (hubPort && hubPort !== $("usbPort").value) hubPort = "";
  $("robotStat").textContent = linkBadge();
}
async function hubUsbCmd(c) {
  // With a peer, the command has to go to the module behind the plugged-in
  // one's hotspot, and only the unified endpoint understands that: the hub
  // turns dev=usb:COM7@far-nong into REACH far-nong <command> down the cable.
  // Without a peer this stays on the endpoint it always used, so nothing about
  // the ordinary cable path changes.
  // /api/usb/cmd only ever means a port on THIS PC. A peer or another hub
  // needs the unified endpoint, which understands the whole dev string.
  const url = (window.HUB_PEER || window.HUB_VIA)
    ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/usb/cmd?port=${encodeURIComponent(hubPort)}` +
      `&id=${busId()}&c=${encodeURIComponent(c)}`;
  const r = await fetch(url);
  const t = await r.text();
  if (!r.ok) {
    let msg = t;
    try { msg = JSON.parse(t).error || t; } catch (e) { /* plain text error */ }
    throw new Error(msg);
  }
  return t.trim();
}

async function serialConnect() {
  if (!("serial" in navigator))
    throw new Error("no Web Serial here — USB works only in Chrome/Edge on the " +
      "host PC at http://127.0.0.1:8642 (not from the LAN address or other devices); " +
      "use WiFi mode instead");
  serialPort = await navigator.serial.requestPort();
  await serialPort.open({ baudRate: 115200 });
  // release the ESP32 strap lines: asserted DTR/RTS can hold the board in
  // reset/bootloader through the USB-UART chip
  try { await serialPort.setSignals({ dataTerminalReady: false, requestToSend: false }); }
  catch (e) { /* some adapters don't support it */ }
  serialReadLoop();
  await new Promise(r => setTimeout(r, 400)); // let boot/log noise pass
}
async function serialReadLoop() {
  try {
    const decoder = new TextDecoderStream();
    serialPort.readable.pipeTo(decoder.writable).catch(() => {});
    const reader = decoder.readable.getReader();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += value;
      let i;
      while ((i = buf.indexOf("\n")) >= 0) {
        const line = buf.slice(0, i).trim();
        buf = buf.slice(i + 1);
        // Skip blank lines and firmware LOG lines only. A log line is a bracket
        // TAG — "[wifi] …", "[sd] …", "[  1234][I]…". A JSON ARRAY reply
        // (PIN VALID → "[{…}]", FILES → "[\"…\"]") also starts with "[" and must
        // NOT be skipped (that made pin config say "unsupported" over USB).
        if (!line || /^\[[\w ]*\]/.test(line)) continue;
        const w = serialWaiters[0];
        if (!w) continue;                            // unsolicited bus chatter
        const out = w.filter(line);
        if (out !== null) { serialWaiters.shift(); w.res(out); }
        // out === null: not the reply we wait for (e.g. "-> sent, ..." bridge
        // note, or another module's traffic on the bus) — keep waiting
      }
    }
  } catch (e) { /* port closed / unplugged */ }
  serialPort = null;
  $("robotStat").textContent = "USB disconnected";
  notice($("robotStat").textContent);
}
function serialCmd(c) {
  return new Promise((res, rej) => {
    if (!serialPort || !serialPort.writable) return rej(new Error("USB not connected"));
    const id = busId();
    // direct USB: any reply line. bus mode: only "@<id> ..." from our module
    const filter = id
      ? (line) => (line.startsWith("@" + id + " ") ? line.slice(String(id).length + 2) : null)
      : (line) => line;
    const w = { filter, res, rej };
    serialWaiters.push(w);
    setTimeout(() => {
      const k = serialWaiters.indexOf(w);
      if (k >= 0) { serialWaiters.splice(k, 1); rej(new Error("timeout (bus id right?)")); }
    }, 2500);
    const framed = id ? "#" + id + " " + c : c;      // RS485 frame when addressed
    const writer = serialPort.writable.getWriter();
    writer.write(new TextEncoder().encode(framed + "\n")).finally(() => writer.releaseLock());
  });
}

// Transports are NOT exclusive: WiFi and USB/RS485 can be connected at the
// same time. Commands take the cable when it is open (lowest latency, works
// without any network) and WiFi otherwise; bulk SD file transfer prefers
// WiFi and falls back to the cable.
function usbDirect() { return !!(serialPort && serialPort.writable); }
function haveUsb() { return usbDirect() || !!hubPort; }
function haveWifi() { return !!robotIp(); }
// one call for "send this over the cable", whichever USB mode is connected
function cableCmd(c) { return usbDirect() ? serialCmd(c) : hubUsbCmd(c); }
async function httpCmd(c) {
  // Same over WiFi: wifi:<ip>@peer reaches a module on that board's hotspot.
  const url = (window.HUB_PEER || window.HUB_VIA)
    ? `/api/dev/cmd?dev=${encodeURIComponent(moduleDev())}` +
      `&c=${encodeURIComponent(c)}`
    : `/api/robot/cmd?ip=${encodeURIComponent(robotIp())}&c=${encodeURIComponent(c)}`;
  return fetch(url).then(r => r.text());
}
async function rawCmd(c) { // reply text or throws
  if (haveUsb()) return cableCmd(c);
  if (haveWifi()) return httpCmd(c);
  throw new Error("connect first — 🔍 Find modules (WiFi) or pick a USB port");
}

// ------- open the module's own website for the board we are talking to
// The hub serves that site for any transport as /mod?dev=..., so the config
// (pins, users, WiFi, servo type, SD files) is one click away from here and
// points at the SAME board the commands go to — hence the same precedence as
// rawCmd: cable first, WiFi otherwise.
function moduleDev() {
  // The peer rides along. Without it this link opened the website of the
  // board on the CABLE while every command went to the module behind that
  // board's hotspot — two different robots, one screen, no warning.
  const at = window.HUB_PEER ? "@" + window.HUB_PEER : "";
  // The hub prefix goes back on FIRST: hub:<ip>/usb:COM7 is that port on the
  // other PC. Without it the same string names a local port and drives
  // whatever is plugged in here.
  const via = window.HUB_VIA || "";
  if (hubPort) return via + "usb:" + hubPort + (busId() ? ":" + busId() : "") + at;
  if (haveWifi()) return via + "wifi:" + robotIp() + at;
  return "";     // direct Web Serial: see openModule()
}

// Forget the peer the moment the person aims at something else by hand.
// HUB_PEER comes from the ?dev= the page was opened with; it describes THAT
// module, and keeping it after the cable or the address changes sends
// commands to a board nobody chose.
// A PERSON changing the target drops the peer. Deliberately on the events and
// not inside usbPortChanged/connModeChanged: those are also called during boot
// — the ?dev= handler calls connModeChanged() to set the connection up — so
// doing it there threw the peer away the moment the page opened with one.
// Setting a value from code fires no change event; choosing one by hand does.
window.addEventListener("DOMContentLoaded", function () {
  const port = document.getElementById("usbPort");
  const mode = document.getElementById("connSel");
  if (port) port.addEventListener("change", () => clearPeer("you picked another cable"));
  if (mode) mode.addEventListener("change", () => clearPeer("you changed the connection"));
});

function clearPeer(why) {
  if (!window.HUB_PEER) return;
  window.HUB_PEER = "";
  if (typeof log === "function") log("(no longer aiming at a peer module: " + why + ")");
}
function openModule() {
  if (!currentUser) {
    showTab("robot");
    $("loginStat").textContent = "Log in to configure the module.";
    return;
  }
  const dev = moduleDev();
  if (dev) {
    // The hub shares the cable, so the module site and this editor can both
    // stay open on one USB port.
    window.open("/mod?dev=" + encodeURIComponent(dev), "_blank");
    return;
  }
  if (usbDirect()) {
    $("robotStat").textContent = "direct Web Serial owns this cable, so the module " +
      "site cannot share it — switch the link to “+ USB (shared)” and connect again, " +
      "then this button works with both open at once.";
    notice($("robotStat").textContent);
    return;
  }
  $("robotStat").textContent = "connect first — pick a USB port or find a module on WiFi";
  notice($("robotStat").textContent);
}
async function robotCmd(c) {
  if (!currentUser) return "";
  try {
    const t = await rawCmd(c);
    $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + t.slice(0, 120);
    return t;
  } catch (e) {
    $("robotStat").textContent = "" + (e.message || e);
    return "";
  }
}
async function getStatus() { // full status JSON on whichever link is up
  if (haveUsb()) {
    try { return JSON.parse(await cableCmd("INFO")); }
    catch (e) { return JSON.parse(await cableCmd("INFO")); } // boot noise: retry once
  }
  if (haveWifi())
    return fetch("/api/robot/status?ip=" + encodeURIComponent(robotIp())).then(r => r.json());
  throw new Error("not connected");
}
function linkBadge() { // shown in robotStat so you see every open channel
  const parts = [], bus = busId() ? "→RS485 #" + busId() : "";
  if (usbDirect()) parts.push("USB direct" + bus + " ✓");
  else if (hubPort) parts.push("USB " + hubPort + bus + " (shared) ✓");
  if (haveWifi()) parts.push("WiFi " + robotIp());
  if (parts.length) return parts.join(" + ");
  // NOT CONNECTED IS NOT AN ANSWER. It says what the operator already knows and
  // nothing about what to do, and the same two words were used by three
  // different screens for three different situations. window.miceLink is the
  // one list, shared with the hub page and the board's own website - see
  // shared/web/mice.js. It is optional here only because Studio can be opened
  // from a file with no hub serving that script.
  if (window.miceLink) {
    const s = window.miceLink.read({ cable: false, wifi: false, viaHub: false,
                                     everHeard: false });
    return s.says + (s.next ? "  " + s.next : "");
  }
  return "not connected";
}

// ------- auto-discovery: the hub server scans the WiFi — just click one
async function scanModules() {
  const sel = $("foundSel");
  sel.innerHTML = "<option value=''>scanning the WiFi… (a few seconds)</option>";
  try {
    const r = await fetch("/api/scan?force=1").then(r => r.json());
    sel.innerHTML = "<option value=''>found: pick one…</option>";
    (r.modules || []).forEach(m => {
      const o = document.createElement("option");
      o.value = m.ip;
      o.textContent = `${m.name} (${m.type}) — ${m.ip}`;
      sel.appendChild(o);
    });
    if (!(r.modules || []).length)
      sel.innerHTML = "<option value=''>no modules found — same WiFi? rescan</option>";
  } catch (e) {
    sel.innerHTML = "<option value=''>scan needs the hub server (python main.py)</option>";
  }
}
function pickFound(ip) {
  if (!ip) return;
  $("connSel").value = "wifi";
  connModeChanged();
  $("robotIp").value = ip;
  connectRobot();
}
async function connectRobot() {
  if (!currentUser) {
    showTab("robot"); // This will actually show the login card since they aren't logged in
    $("loginStat").textContent = "Log in to connect to the robot.";
    if (!pendingConnect) {
      pendingConnect = {};
      pendingConnect.promise = new Promise((resolve, reject) => {
        pendingConnect.resolve = resolve; pendingConnect.reject = reject;
      });
    }
    return pendingConnect.promise;
  }
  const t = transport(), had = hubPort;
  try {
    if (t === "usb") {
      if (!$("usbPort").dataset.loaded) await loadPorts();
      hubPort = $("usbPort").value;
      if (!hubPort) throw new Error("pick the USB port the module is plugged into " +
        "(⟳ to rescan)");
    } else if (t === "serial" && !usbDirect()) {
      await serialConnect();
    }
    const s = await getStatus();
    // If the module is playing a sequence on its OWN clock, say so here. It is
    // the moment the question "why is the robot moving by itself?" gets asked —
    // it happens after a hand-off, or when the board was left running from an
    // earlier session, and the answer used to be invisible.
    const own = (s.seq && s.seq.running)
      ? ` — the module is PLAYING ${s.seq.file || "a sequence"} on its own; ` +
        "Play or Stop here takes over" : "";
    $("robotStat").textContent =
      `[${linkBadge()}] ${s.name} (id ${s.id}, type ${s.type})` +
      (s.type !== "nong" ? " — WARNING: type is not nong" : "") +
      (s.sd ? ", SD ok" : ", no SD card") + own;
    refreshSd();
  } catch (e) {
    if (t === "usb" && !had) hubPort = "";   // never show a link that isn't there
    $("robotStat").textContent = "Could not reach the robot. Check it is powered "
      + "and on the same network or cable, then try again. " + (e.message || e);
    notice($("robotStat").textContent);
  }
}
function sendPose(quiet) {
  const c = "POSE " + pose.map(fmtA).join(" "); // no T: firmware uses its speed setting
  if (quiet) { sendPoseLive(); return; }
  robotCmd(c);
}

// Live sending: ONE command in flight at a time, newest pose wins.
//
// Fire-and-forget sends are NOT ordered. Dragging a slider fast put several
// fetches in the air at once, and whichever the module happened to serve last
// won — so the arm could settle on an older pose while the number on screen
// showed the value you released at. A plain time throttle made it worse: if
// the final update landed inside the throttle window it was dropped outright
// and the last position was never sent at all.
//
// Holding exactly one request open fixes both: replies come back in order, and
// `livePending` always holds the NEWEST pose, so the loop cannot exit without
// having sent the value the user finished on. It also self-tunes — a fast link
// sends more often, a slow one less, with no magic interval to keep in step
// with the transport.
// Two kinds of live traffic share the ONE channel, which is what keeps them in
// order relative to each other:
//   liveQueue   — commands that must all be sent, in order (playback segments,
//                 the keyframe-0 send, STOP). Sending these as separate
//                 fetches raced: Play could deliver segment 1 BEFORE the
//                 keyframe-0 pose and start the arm from the wrong place.
//   livePending — the newest pose from a drag. Superseded, never queued.
let liveBusy = false, livePending = null, liveQueue = [];
// How long a dragged pose should take, in ms — and why it is not left to the
// board to decide.
//
// A drag used to send `POSE …` with no T, so the module fell back to its SPEED
// setting: at 120°/s a 20° slider move takes 166 ms, the next update arrives
// before that finishes, and the arm is permanently easing towards where your
// hand WAS. It reads as lag, and no amount of sending faster fixes it, because
// each command asks for a slow move.
//
// So a live pose asks for the time it actually has: the measured round trip to
// this module, which self-tunes to the link (~25 ms on USB, ~100 ms over WiFi).
// The firmware floors T per joint at what the servos can really do, so asking
// for less than is possible is safe — it is a request, not a promise.
let liveRtt = 120;                      // ms, smoothed
const LIVE_T_MIN = 80, LIVE_T_MAX = 300;
function liveT() {
  return Math.max(LIVE_T_MIN, Math.min(LIVE_T_MAX, Math.round(liveRtt * 1.3)));
}
function liveSend(c) { if (!currentUser) return; liveQueue.push(c); livePump(); }
function sendPoseLive() { if (!currentUser) return; livePending = pose.slice(); livePump(); }
function liveAbort() { liveQueue = []; livePending = null; }
function livePump() {
  if (liveBusy) return;
  liveBusy = true;
  (async () => {
    try {
      for (;;) {
        let c = null;
        if (liveQueue.length) {
          c = liveQueue.shift();                 // ordered work comes first
        } else if (livePending) {
          // ...with the time it has, not the module's default easing speed
          c = "POSE " + livePending.map(fmtA).join(" ") + " T " + liveT();
          livePending = null;                    // only ever the newest pose
        }
        if (!c) break;
        try {
          const t0 = performance.now();
          const r = await rawCmd(c);
          // Measure the link from the traffic itself — no probing, and it
          // follows a link that changes (USB pulled, WiFi gone slow).
          liveRtt += ((performance.now() - t0) - liveRtt) * 0.25;
          $("robotStat").textContent = "> " + c.slice(0, 60) + "  →  " + r.slice(0, 80);
        } catch (e) {
          $("robotStat").textContent = "" + (e.message || e);
        }
      }
    } finally { liveBusy = false; }
  })();
}

// ------- SD file access on ANY transport
// wifi: the module's HTTP file API through the python proxy.
// usb/rs485: the firmware's FBEGIN/FDATA/FEND/FREAD/FDEL text commands
// (base64 chunks small enough for one RS485 frame) — so the SD card can be
// managed over every channel, not only WiFi.
async function sdUploadSerial(fname, text) {
  const bytes = new TextEncoder().encode(text);
  // direct USB can take bigger chunks; 120 bytes only when framed for the
  // RS485 bus (its frames are limited to ~250 chars)
  const CH = busId() ? 120 : 180;
  let r = await cableCmd("FBEGIN " + fname);
  if (!r.startsWith("OK")) throw new Error(r);
  for (let o = 0; o < bytes.length; o += CH) {
    const chunk = bytes.subarray(o, Math.min(o + CH, bytes.length));
    r = await cableCmd("FDATA " + btoa(String.fromCharCode(...chunk)));
    if (!r.startsWith("OK")) throw new Error(r);
    $("sdStat").textContent = `uploading ${fname}: ${Math.min(o + CH, bytes.length)}/${bytes.length} bytes`;
  }
  r = await cableCmd("FEND");
  if (!r.startsWith("OK")) throw new Error(r);
}
async function sdUpload(fname, text) {
  if (haveWifi()) { // fastest for whole files; fall back to the cable
    try {
      const r = await fetch("/api/robot/upload", {
        method: "POST", body: JSON.stringify({ ip: robotIp(), name: fname, yaml: text }),
      }).then(r => r.json());
      if (!r.ok) throw new Error(JSON.stringify(r));
      return;
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (haveUsb()) return sdUploadSerial(fname, text);
  throw new Error("connect first (WiFi or USB)");
}
async function sdDownloadSerial(fname) {
  const parts = [];
  for (let off = 0; ; ) {
    const r = await cableCmd(`FREAD ${fname} ${off} 120`);
    if (r === "EOF") break;
    if (r.startsWith("ERR")) throw new Error(r);
    const bin = atob(r);
    parts.push(bin);
    off += bin.length;
    $("sdStat").textContent = `reading ${fname}: ${off} bytes`;
  }
  const all = parts.join("");
  return new TextDecoder().decode(Uint8Array.from(all, c => c.charCodeAt(0)));
}
async function sdDownload(fname) {
  if (haveWifi()) {
    try {
      return await fetch(`/api/robot/download?ip=${encodeURIComponent(robotIp())}` +
                         `&path=${encodeURIComponent("/moves/" + fname)}`).then(r => r.text());
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (haveUsb()) return sdDownloadSerial(fname);
  throw new Error("connect first (WiFi or USB)");
}
async function sdDelete(fname) {
  if (haveWifi()) {
    try {
      // READ the reply. fetch does not throw on 404 or 502, and the firmware
      // answers 200 with the body "ERR delete failed" — so this branch used to
      // report success for a file that is still sitting on the card, and the
      // caller then removed it from the list. The cable branch below has always
      // checked; only this one did not.
      const res = await fetch(`/api/robot/delete?ip=${encodeURIComponent(robotIp())}` +
                  `&path=${encodeURIComponent("/moves/" + fname)}`);
      const body = (await res.text()).trim();
      if (!res.ok || body.startsWith("ERR")) {
        throw new Error(body || ("the robot answered " + res.status));
      }
      return;
    } catch (e) { if (!haveUsb()) throw e; }
  }
  if (!haveUsb()) throw new Error("connect first (WiFi or USB)");
  const r = await cableCmd("FDEL " + fname);
  if (!r.startsWith("OK")) throw new Error(r);
}

// ------- SD card manager: list /moves, run/edit/delete a sequence
async function refreshSd() {
  const box = $("sdList");
  // A loading state, so the panel is never a blank hole while a cable round
  // trip runs — over USB with a peer this can take several seconds.
  box.textContent = "Reading the robot's card…";
  try {
    let files;
    if (haveWifi()) {
      files = await fetch(`/api/robot/files?ip=${encodeURIComponent(robotIp())}&dir=/moves`)
        .then(r => r.json());
    } else if (haveUsb()) {
      files = JSON.parse(await cableCmd("FILES /moves"));
    } else {
      // An empty state says what goes here and names the ONE action that fills
      // it, rather than a bare instruction with no subject.
      box.textContent = "Not connected to a robot yet, so there is no card to "
        + "read. Press 🔍 Find modules, or pick a USB cable above.";
      return;
    }
    box.innerHTML = "";
    if (!files.length) {
      box.textContent = "This robot's card has no sequences on it yet. Build a "
        + "timeline, then press “Send to robot” to put one there.";
    }
    // the "then run…" chain box offers the files that are really on the card
    const dl = $("seqNextList");
    if (dl) {
      dl.innerHTML = "";
      files.forEach(f => {
        const o = document.createElement("option");
        o.value = f.n;
        dl.appendChild(o);
      });
    }
    files.forEach(f => {
      const row = document.createElement("div"); row.className = "row";
      const name = document.createElement("span");
      name.style.flex = "1"; name.textContent = f.n + "  (" + (f.s / 1024).toFixed(1) + " kB)";
      const run = document.createElement("button");
      run.textContent = "▶ Run"; run.className = "primary";
      run.onclick = () => robotCmd("MOVE " + f.n);
      const play = document.createElement("button");
      play.textContent = "▶ Preview";
      play.title = "load this sequence into the timeline and play it here, in Studio";
      play.onclick = () => playSdSeq(f.n);
      const edit = document.createElement("button");
      edit.textContent = "✎ Edit";
      edit.title = "load this sequence from the SD card into the timeline";
      edit.onclick = () => editSdSeq(f.n);
      const del = document.createElement("button");
      del.textContent = "✕"; del.title = "delete from SD";
      del.onclick = async () => {
        if (!confirm("Delete " + f.n + " from the robot SD card?")) return;
        try { await sdDelete(f.n); } catch (e) { $("sdStat").textContent = "" + e; }
        refreshSd();
      };
      row.append(name, run, play, edit, del);
      box.appendChild(row);
    });
    $("sdStat").textContent = "";
  } catch (e) {
    // An error says what to DO next, and offers the control that does it.
    box.textContent = "";
    const msg = document.createElement("span");
    msg.textContent = "Could not read the robot's card. It may have gone off the "
      + "network, or it has no card fitted. ";
    const why = document.createElement("span");
    why.className = "hint";                 // the raw reason, demoted
    why.textContent = e.message || String(e);
    const again = document.createElement("button");
    again.textContent = "Try again";
    again.onclick = () => refreshSd();
    box.append(msg, why, document.createTextNode(" "), again);
  }
}
async function uploadYaml() {
  if (nothingToWrite("sdStat")) return;
  if (!crashGate("UPLOAD it")) return;
  const { name, yaml } = buildYaml();
  try {
    await sdUpload(name + ".yaml", yaml);
    $("sdStat").textContent =
      `uploaded ${name}.yaml to /moves — press its ▶ Run button (or pick it on the module website)`;
    refreshSd();
  } catch (e) { $("sdStat").textContent = "upload failed: " + (e.message || e); notice($("sdStat").textContent); }
}
// Stop any sequence the MODULE is playing on its own.
//
// Safe to call when nothing is running: the firmware answers "OK move stopped"
// either way, and it costs one command. Calling it too often is harmless;
// calling it too seldom leaves two things driving the servos at once.
//
// Since the firmware learned to preempt (any MOTION command from outside stops
// the module's own sequence), this is no longer the only thing standing between
// you and two clocks on one robot — a stray slider drag is now safe too. It
// stays because saying so EXPLICITLY is what makes the arm start the show from
// keyframe 0 instead of from wherever the interrupted sequence left it, and
// because a board on older firmware still needs it.
function stopRobotSequence() {
  handedOff = false;
  if (!haveUsb() && !haveWifi()) return;
  try { robotCmd("MOVE STOP"); } catch (e) {}
}

// ---- keeping a show running when you leave the page --------------------
//
// The browser clock CANNOT be made reliable in the background. A hidden tab
// has requestAnimationFrame stopped and its timers throttled to roughly once a
// minute, and no amount of silent-audio trickery changes that on every browser
// and every platform. Symptoms seen: the sequence ran at the wrong speed, or
// simply stopped and sat still until the page was looked at again.
//
// So the fix is not to fight the browser — it is to stop being the clock. When
// a show is playing and the page goes away, hand the whole sequence to the
// MODULE and let it play on its own 50 Hz timer. That path already exists
// (Run on robot), it survives closing the browser entirely, and the module
// interpolates with the same formulas this preview uses, so the motion is
// identical rather than merely similar.
let handedOff = false;

async function handOffToRobot() {
  if (handedOff || !playing) return;
  if (!haveUsb() && !haveWifi()) return;     // nothing to hand off TO
  // Hand off only what was ALREADY driving the arm. Two ways this used to move
  // a robot nobody asked to move:
  //   previewOnly — the crash gate said this movement collides and the user
  //     pressed Cancel. `playing` stays true so the preview still draws, so
  //     hiding the tab uploaded and ran the very movement that was refused.
  //   live unchecked — `haveWifi()` is only "an IP is typed in the box", not
  //     "connected". Previewing a show with the live box OFF and then switching
  //     window started the arm.
  // In both cases the preview is a drawing, and a drawing must never become
  // motion just because the tab lost focus.
  if (previewOnly) return;
  if (!liveLinked()) return;
  // Nothing to rescue when the HUB is the clock: it is a native process and
  // this page going away does not touch it. Handing the show to the module as
  // well would put two clocks on one robot — the thing all of this prevents.
  if (hubDriven()) return;
  handedOff = true;
  try {
    // Hand over from where the show HAS GOT TO, not from the top. Hiding the
    // tab half way through used to send the arm back to keyframe 0 first —
    // the same sweep as Run, but nobody pressed anything to cause it.
    const part = playT > 0 && keyIndexAtMs(playT) > 0;
    const { name, yaml } = buildYaml(playT);
    const file = (part ? name + ".part" : name) + ".yaml";
    await sdUpload(file, yaml);              // falls back to module memory with no SD
    await robotCmd("MOVE " + file);
    // stop being the clock: the module owns the show now
    playing = false;
    keepAwake(false);
    $("playBtn").textContent = "▶ Play";
    const st = $("sdStat");
    if (st) st.textContent = "the module is running this sequence on its own — "
      + "it keeps going with this page closed. Press Stop to end it.";
  } catch (e) {
    handedOff = false;                       // it did not take: keep previewing
  }
}

document.addEventListener("visibilitychange", function () {
  if (document.hidden) { handOffToRobot(); return; }
  handedOff = false;                         // back on the page: allow it again
  // While the hub was the clock the ROBOT kept moving and this preview did
  // not (a hidden tab stops rAF and throttles timers). So do not resume where
  // the picture stopped — ask the hub where the show actually is and jump the
  // play head there, or the preview stays permanently behind the arm.
  if (!hubDriven() || !playing) return;
  fetch("/api/play").then(r => r.json()).then(s => {
    if (!s.running) { playing = false; $("playBtn").textContent = "▶ Play"; keepAwake(false); return; }
    playT = Math.min(s.at_ms || 0, totalMs());
    lastPlayMs = 0;                          // fresh clock, no catch-up burst
    pose = poseAt(playT).map((v, i) => clampJ(i, v));
    applyPose(); renderSliders();
  }).catch(() => {});
});

// Send the sequence, THEN play it. This used to send only `MOVE <name>.yaml`,
// so the module ran whatever copy of that name was already on its SD card while
// the crash check had just approved the timeline on screen. Edit a pose to fix
// a collision, press Run, and the robot performed the old crashing version —
// the safety check and the motion were looking at different data. Uploading
// first is what makes the check mean anything.
async function robotRun() {
  if (nothingToWrite("sdStat")) return;     // a file with no moves does nothing
  if (!crashGate("RUN it on the robot")) return;
  // Run from where the clock is parked. Clicking a keyframe parks it there, so
  // Run continues the show from the pose on screen instead of sweeping back to
  // the first one — which is what the robot's arm would have to travel through.
  // A partial run is written under its own name: <name>.yaml stays the whole
  // show, so running part of it never overwrites the saved sequence.
  const resumeMs = playT;
  const part = resumeMs > 0 && keyIndexAtMs(resumeMs) > 0;
  const { name, yaml } = buildYaml(resumeMs);
  const file = (part ? name + ".part" : name) + ".yaml";
  const st = $("sdStat");
  if (st) st.textContent = "sending " + file + " to the robot…";
  try {
    await sdUpload(file, yaml);
  } catch (e) {
    if (st) st.textContent = "could not send the sequence, so nothing was run — "
      + (e && e.message ? e.message : e);
    return;
  }
  await robotCmd("MOVE " + file);
  if (st) st.textContent = part
    ? "the robot is running from the move you picked, to the end — it does not "
      + "go back to the start. The whole show is still saved as " + name + ".yaml."
    : "the robot is running " + file + " on its own.";
}

// ---- zero-position calibration (password-gated; default manny/12345678) ----
function zeroCred() { try { return JSON.parse(localStorage.getItem("nongZeroCred")) || null; } catch (e) { return null; } }
function zeroCredOr() { return zeroCred() || { user: "manny", pass: "12345678" }; }
function zeroUnlock() {
  const c = zeroCredOr();
  if ($("zUser").value === c.user && $("zPass").value === c.pass) {
    $("zeroLocked").style.display = "none";
    $("zeroPanel").style.display = "";
    $("zPass").value = "";
  } else {
    // Say what to do, and never imply the reader is at fault. Which of the two
    // is wrong is deliberately not revealed.
    $("zStat").textContent = "That user name and password do not match. "
      + "Check them and try again.";
  }
}
function zeroLock() { $("zeroPanel").style.display = "none"; $("zeroLocked").style.display = ""; }
function zeroChangeCred() {
  const u = $("zNewUser").value.trim(), p = $("zNewPass").value;
  if (!u || !p) { $("zStat2").textContent = "enter a new user and password"; return; }
  localStorage.setItem("nongZeroCred", JSON.stringify({ user: u, pass: p }));
  $("zNewUser").value = ""; $("zNewPass").value = "";
  $("zStat2").textContent = "login changed (this browser)";
}
async function robotZeroSet() {
  if (!haveUsb() && !haveWifi()) { $("zStat2").textContent = "connect to the robot first"; notice($("zStat2").textContent); return; }
  const r = await robotCmd("SETZERO");
  $("zStat2").textContent = r.startsWith("OK")
    ? "zero set — this pose is now the robot's home. Your start angles are unchanged."
    : ("failed: " + r);
  if (!r.startsWith("OK")) notice($("zStat2").textContent);
}

// ------- monitor mode: the 3D model follows the REAL robot
// (poll status; module.joints drives the rig, seq shows what's playing)
let monTimer = null;
function liveChanged() {
  if ($("liveChk").checked) { $("monChk").checked = false; monitorChanged(); }
}
function monitorChanged() {
  if ($("monChk").checked) {
    $("liveChk").checked = false;
    // Same trap as livePause: a show started while Live was ticked belongs to
    // the HUB's clock, and switching this page to watching must end it.
    hubStop();
    playing = false; $("playBtn").textContent = "▶ Play";
    monTimer = setInterval(monitorTick, 350);
    $("robotStat").textContent = "monitoring…";
  } else {
    clearInterval(monTimer); monTimer = null;
  }
}
async function monitorTick() {
  try {
    const s = await getStatus();
    const m = s.module || {};
    // 10 joints now (8 arm + WAIST + SHRUG); an old 8-joint board leaves the
    // two body joints at their current value.
    if (Array.isArray(m.joints) && m.joints.length >= ARMJ) {
      pose = pose.map((cur, i) => (m.joints[i] !== undefined ? clampJ(i, m.joints[i]) : cur));
      applyPose(); renderSliders();
    }
    const seq = s.seq || {};
    $("robotStat").textContent =
      `MONITOR ${s.name}: ` +
      (seq.running ? `playing ${seq.file}` : "no sequence running") +
      (m.moving ? ` | moving (${m.move_left || 0} ms left)` : " | idle") +
      (m.attached === false ? " | relaxed" : "");
  } catch (e) {
    $("robotStat").textContent = "monitor: no reply (" + (e.message || e) + ")";
    notice($("robotStat").textContent);
  }
}
