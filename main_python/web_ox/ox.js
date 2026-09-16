/* ox.js — the /o/ workbench version's logic.
 *
 * Wording contract (batch-5, shared with the incumbent page):
 *   - notice() is the FAIL banner. Routine progress lives on the card's own
 *     state line (.xs); refusals ("log in first") ARE failures and banner.
 *   - every wire value is esc()'d before it touches innerHTML: a module name
 *     is user-settable and any board on the venue WiFi can answer a sweep.
 */
"use strict";

const $ = id => document.getElementById(id);
const esc = s => String(s == null ? "" : s)
  .replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;")
  .replace(/"/g, "&quot;");

/* ------------------------------------------------------------------ notice */
let noticeSaid = "";
function notice(text) {
  if (text === noticeSaid && !$("noticeWrap").hidden) return;
  noticeSaid = text;
  $("noticeText").textContent = text;
  $("noticeWrap").hidden = false;
}
function noticeClear() { $("noticeWrap").hidden = true; }

/* -------------------------------------------------------------------- auth */
let authed = false;

async function refreshAuth() {
  try {
    const j = await fetch("/api/whoami").then(r => r.json());
    authed = !!j.authed;
    $("loginCard").hidden = authed;
    $("znav").hidden = !authed;
    $("app").hidden = !authed;
    $("logoutBtn").hidden = !authed;
    const who = $("whoBadge");
    who.hidden = !(authed && j.user);
    if (j.user) who.textContent = esc(j.user);
    if (j.locked_for > 0) showLock(j.locked_for);
    if (authed) boot();
  } catch (e) { notice("The hub did not answer — is it still running?"); }
}

function showLock(secs) {
  const el = $("loginLock");
  el.hidden = false; $("loginErr").hidden = true;
  // The number comes from the hub; the page never counts its own guess.
  const tick = () => {
    if (secs <= 0) { el.hidden = true; return; }
    el.textContent = "Too many tries. Wait " + secs + "s before trying again.";
    secs--; setTimeout(tick, 1000);
  };
  tick();
}

async function doLogin(ev) {
  ev.preventDefault();
  $("loginBusy").hidden = false; $("loginBtn").disabled = true;
  $("loginErr").hidden = true;
  try {
    const r = await fetch("/api/login", { method: "POST", body: JSON.stringify({
      user: ($("loginUser").value || "").trim(), password: $("loginPass").value }) });
    const j = await r.json();
    if (j.ok) {
      $("loginPass").value = "";
      await refreshAuth();
      refreshMods(true);
    } else if (j.locked_for > 0) showLock(j.locked_for);
    else { $("loginErr").hidden = false;
           $("loginErr").textContent = "That did not work — " + (j.error || "try again"); }
  } catch (e) {
    $("loginErr").hidden = false;
    $("loginErr").textContent = "The hub did not answer.";
  } finally { $("loginBusy").hidden = true; $("loginBtn").disabled = false; }
}

/* ------------------------------------------------------------------ modules */
const PINS = "ox_pins";
function pins() { try { return JSON.parse(localStorage.getItem(PINS) || "[]"); }
                  catch (e) { return []; } }
function isPinned(id) { return pins().indexOf(id) >= 0; }
function togglePin(id) {
  const p = pins(), i = p.indexOf(id);
  if (i >= 0) p.splice(i, 1); else p.push(id);
  try { localStorage.setItem(PINS, JSON.stringify(p)); } catch (e) {}
}

let modBusy = false, modsHave = [];

/* One list from three answers: WiFi sweep, this PC's cables, other PCs'
   boards. Bare cables stay hidden until asked for — they are how you FLASH,
   not something to drive. */
async function refreshMods(force) {
  if (modBusy) return;
  modBusy = true;
  const out = new Map();
  const put = (k, v) => { const old = out.get(k); out.set(k, Object.assign({}, old, v)); };
  let failed = null;
  try {
    const w = await fetch("/api/scan" + (force ? "?force=1" : "")).then(r => r.json());
    (w.modules || []).forEach(m => {
      put("wifi:" + m.ip, Object.assign({ dev: "wifi:" + m.ip }, m));
    });
  } catch (e) { failed = "the network sweep got no answer"; }
  try {
    const all = await fetch("/api/allmods" + (force ? "?force=1" : "")).then(r => r.json());
    (all.modules || []).forEach(m => {
      const k = m.host
        ? "far:" + m.host + ":" + (m.dev || m.id)
        : (m.dev || "id:" + m.id);
      put(k, m.dev ? Object.assign({ dev: m.dev }, m) : m);
    });
    paintShared(all);
  } catch (e) { /* no answer about other PCs is not fatal here */ }
  try {
    const ports = await fetch("/api/ports").then(r => r.json());
    (ports.ports || []).forEach(p => {
      if (p.bt) return;
      put("usb:" + p.port, { port: p.port, bare: true, name: p.desc || p.port });
    });
  } catch (e) { /* no ports is not an error */ }
  modBusy = false;
  modsHave = [...out.values()];
  paintMods(failed);
}

function typeClass(t) { return String(t || "").replace(/[^a-z0-9-]/gi, ""); }

function paintMods(failed) {
  const grid = $("modGrid");
  const showBare = $("showPorts").checked;
  const list = modsHave
    .filter(m => !m.bare || showBare)
    .sort((a, b) => (isPinned(b.id) ? 1 : 0) - (isPinned(a.id) ? 1 : 0));
  grid.innerHTML = "";
  if (!list.length) {
    grid.innerHTML =
      '<div class="card xcard"><div class="xt"><span class="grow">The rig</span></div>' +
      '<p class="xs ' + (failed ? "state-err" : "state-empty") + '">' +
      (failed
        ? esc(failed) + ' — <button onclick="refreshMods(true)">Try again</button>'
        : "Nothing on the cables or the WiFi yet. Plug a board in, or power one " +
          "on — it appears here by itself. " +
          '<button onclick="refreshMods(true)">Look now</button>') +
      "</p></div>";
    return;
  }
  list.forEach(m => grid.appendChild(modCard(m)));
}

function modCard(m) {
  const d = document.createElement("div");
  d.className = "card xcard mod";
  const ty = typeClass(m.type);
  if (ty) d.classList.add("t-" + ty);
  if (m.stale) d.classList.add("stale", "late");

  const head = document.createElement("div");
  head.className = "xt";
  let pinHtml = "";
  if (m.id != null) pinHtml =
    '<button class="pin' + (isPinned(m.id) ? " on" : "") + '" aria-pressed="' +
    isPinned(m.id) + '" title="Pinned modules are listed first, on this computer only">' +
    (isPinned(m.id) ? "★" : "☆") + "</button>";
  head.innerHTML = pinHtml +
    '<span class="grow">' + esc(m.name || (m.bare ? "cable" : "#" + (m.id != null ? m.id : "?"))) + "</span>" +
    (m.type ? '<span class="badge"><b>' + esc(m.type) + "</b></span>" : "");
  d.appendChild(head);
  const pinBtn = head.querySelector(".pin");
  if (pinBtn) pinBtn.onclick = ev => { ev.stopPropagation(); togglePin(m.id); refreshMods(false); };

  const state = document.createElement("p");
  state.className = "xs";
  if (m.bare) state.className += " mini";
  if (m.stale) {
    state.className += " state-stale";
    state.textContent = "last answered " +
      (m.lastSeen != null ? m.lastSeen + "s ago" : "a while ago") +
      " — what it is doing right now is not known. Check its power.";
  } else if (m.bare) {
    state.textContent = "A cable with nothing answering on it yet.";
  } else if (m.host && m.hostDev !== false) {
    state.textContent = "Reachable through " + m.host + ".";
  } else {
    state.textContent = "Ready.";
  }
  d.appendChild(state);

  const tech = document.createElement("p");
  tech.className = "mini tech";
  tech.textContent = [m.ip ? "ip " + m.ip : "", m.port ? "port " + m.port : "",
                      m.id != null ? "id " + m.id : ""].filter(Boolean).join(" · ");
  d.appendChild(tech);

  const act = document.createElement("div");
  act.className = "xa";
  const dev = m.dev || (m.port ? "usb:" + m.port : "");
  if (!m.bare && dev) {
    const open = document.createElement("button");
    open.className = "primary";
    open.textContent = "Open module";
    open.onclick = () => window.open("/mod?dev=" + encodeURIComponent(dev) +
      "&name=" + encodeURIComponent(m.name || ""), "_blank");
    act.appendChild(open);
  }
  if (m.port || m.farPort || m.ip) {
    const flash = document.createElement("button");
    flash.textContent = "Put software on it";
    flash.onclick = () => { fwPickBoard(m); openSheet("flashSheet"); };
    act.appendChild(flash);
  }
  // RGB lives on lift boards only, as in the incumbent page.
  if (m.type === "lift" && (m.ip || m.port)) {
    const rgb = document.createElement("button");
    rgb.textContent = "💡 RGB";
    rgb.title = "Colours, effects and light shows for this board's strip";
    const target = m.ip ? "ip=" + encodeURIComponent(m.ip)
      : "port=" + encodeURIComponent(m.port);
    rgb.onclick = () => window.open("/o/rgb.html?" + target +
      "&name=" + encodeURIComponent(m.name || ""), "_blank");
    act.appendChild(rgb);
  }
  d.appendChild(act);
  return d;
}

function paintShared(all) {
  const card = $("sharedCard"), line = $("sharedLine"), box = $("sharedList");
  const mods = (all.modules || []).filter(m => m.host);
  card.hidden = !mods.length && !(all.errors || []).length;
  if (!mods.length && !(all.errors || []).length) return;
  const byHost = {};
  mods.forEach(m => {
    const h = m.host;
    (byHost[h] = byHost[h] || { ip: m.hostIp, mods: [] }).mods.push(m);
  });
  const hosts = Object.keys(byHost);
  line.textContent = hosts.length
    ? hosts.length + (hosts.length === 1 ? " PC is" : " PCs are") +
      " sharing boards over the network."
    : "No other PC answered.";
  box.innerHTML = "";
  hosts.forEach(h => {
    const row = document.createElement("p");
    row.className = "mini";
    row.innerHTML = "🖥 <b>" + esc(h) + "</b>: " +
      byHost[h].mods.map(m => esc(m.name || ("#" + m.id))).join(", ") +
      ' <span class="tech">' + esc(byHost[h].ip || "") + "</span>";
    box.appendChild(row);
  });
}

/* ------------------------------------------------------------------ sheets */
function openSheet(id) {
  closeSheets();
  $(id).hidden = false;
}
function closeSheets() {
  ["flashSheet", "pairSheet", "settingsSheet"].forEach(i => { $(i).hidden = true; });
  fwReset();
}
// click outside the panel closes the sheet
["flashSheet", "pairSheet", "settingsSheet"].forEach(id => {
  document.addEventListener("DOMContentLoaded", () => {
    $(id).addEventListener("click", ev => { if (ev.target === $(id)) closeSheets(); });
  });
});

/* ---------------------------------------------------------- flash wizard */
let fwImgs = [], fwImg = null, fwBoardList = [], fwBoard = null;

function fwReset() {
  fwImg = null; fwBoard = null;
  ["fw1", "fw2", "fw3"].forEach((s, i) => { $(s).hidden = i !== 0; });
  $("fwBar").hidden = true; $("fwErr").hidden = true; $("fwSay").textContent = "";
}

async function fwLoad() {
  if ($("fwImgs").children.length) return;         // already listed
  try {
    const r = await fetch("/api/flash/images").then(x => x.json());
    fwImgs = r.images || [];
  } catch (e) {
    $("fwImgLine").className = "xs state-err";
    $("fwImgLine").textContent = "This PC did not say what it has built.";
    notice("Could not list firmware images — is this the PC with the toolchain?");
    return;
  }
  $("fwImgLine").textContent = "";
  if (!fwImgs.length) {
    $("fwImgLine").className = "xs state-empty";
    $("fwImgLine").textContent =
      "Nothing is built yet. Build a firmware image first (pio run), then come back.";
    return;
  }
  fwImgs.forEach(img => {
    const l = document.createElement("label");
    l.className = "fwpick";
    l.innerHTML = '<input type="radio" name="fwimg" value="' + esc(img.type) + '">' +
      "<span><b>" + esc(img.type) + "</b> <span class='mini'>" +
      esc(img.desc || "") + "</span></span>";
    l.querySelector("input").onchange = () => { fwImg = img; $("fwNext1").disabled = false; };
    $("fwImgs").appendChild(l);
  });
}

function fwToBoards() { if (fwImg) { $("fw1").hidden = true; $("fw2").hidden = false; fwBoards(); } }
function fwBack1() { $("fw2").hidden = true; $("fw1").hidden = false; }
function fwBack2() { $("fw3").hidden = true; $("fw2").hidden = false; }

/* Every board the write could reach: WiFi answers, cables, boards on other
   PCs' cables. Built fresh each time the step opens. */
async function fwBoards() {
  const box = $("fwBoardsBox"), line = $("fwBoardLine");
  box.innerHTML = ""; fwBoardList = []; $("fwNext2").disabled = true;
  line.className = "xs state-load"; line.textContent = "listing every board it can reach…";
  const out = new Map();
  try {
    const w = await fetch("/api/scan").then(r => r.json());
    (w.modules || []).forEach(m =>
      out.set("wifi:" + m.ip, Object.assign({ ip: m.ip }, m)));
  } catch (e) { /* fall through */ }
  try {
    const ports = await fetch("/api/ports").then(r => r.json());
    (ports.ports || []).forEach(p => {
      if (!p.bt) out.set("usb:" + p.port,
        { port: p.port, name: p.desc || p.port, silent: true });
    });
  } catch (e) { /* fall through */ }
  try {
    const all = await fetch("/api/allmods").then(r => r.json());
    const me = await fetch("/api/mine").then(r => r.json());
    (all.modules || []).forEach(m => {
      if (!m.host || m.host === me.host) return;
      const port = (String(m.dev || "").split("usb:")[1] || "").split(":")[0];
      if (port) out.set("far:" + m.host + port,
        Object.assign({}, m, { farPort: port, host: m.host, hostIp: m.hostIp }));
    });
  } catch (e) { /* fall through */ }
  fwBoardList = [...out.values()];
  if (!fwBoardList.length) {
    line.className = "xs state-empty";
    line.textContent = "No board is reachable right now — plug one in or power one up, then press Back and Next again.";
    return;
  }
  line.textContent = "";
  fwBoardList.forEach(b => {
    const l = document.createElement("label");
    l.className = "fwpick";
    const where = b.ip ? "over WiFi" : b.host ? "on " + b.host + "'s cable"
      : "on cable " + b.port;
    l.innerHTML = '<input type="radio" name="fwboard">' +
      "<span><b>" + esc(b.name || ("#" + (b.id != null ? b.id : "?"))) + "</b> " +
      (b.type ? "runs <b>" + esc(b.type) + "</b> now · " : "") +
      "<span class='mini'>" + esc(where) + "</span></span>";
    l.querySelector("input").onchange = () => { fwBoard = b; $("fwNext2").disabled = false; };
    box.appendChild(l);
  });
}

function fwToConfirm() {
  if (!fwBoard || !fwImg) return;
  $("fw2").hidden = true; $("fw3").hidden = false;
  const far = !!fwBoard.host;
  const via = far ? ("the cable on " + fwBoard.host + " (" + fwBoard.farPort + "), from that PC")
    : fwBoard.ip ? ("WiFi at " + fwBoard.ip)
    : ("the cable on " + fwBoard.port);
  const cost = fwBoard.ip
    ? "Written to the board's spare slot — if it does not finish, the module keeps the firmware it has."
    : "About a minute. The cable cannot be used for anything else until it finishes. The board keeps its id, name, WiFi and pins." +
      (fwBoard.bus ? " Over the RS485 bus it takes several minutes." : "");
  $("fwConfirm").innerHTML =
    "<p><b>" + esc(fwImg.type) + "</b> → <b>" +
    esc(fwBoard.name || ("#" + (fwBoard.id != null ? fwBoard.id : "?"))) + "</b>" +
    (fwBoard.id != null ? " · #" + esc(String(fwBoard.id)) : "") +
    (fwBoard.type ? " · runs " + esc(fwBoard.type) + " now" : "") + "</p>" +
    "<p class='mini'>via " + esc(via) + "</p><p class='mini'>" + esc(cost) + "</p>";
}

async function fwWrite() {
  if (!fwBoard || !fwImg) return;
  const far = !!fwBoard.host;
  const overCable = !!(fwBoard.port && !fwBoard.silent) && !fwBoard.ip;
  const overBus = !!fwBoard.bus;
  $("fwGo").disabled = true; $("fwBar").hidden = false;
  $("fwSay").textContent = "starting…"; $("fwErr").hidden = true;
  let r;
  try {
    if (far) {
      // The image travels; esptool runs on the PC holding the cable.
      r = await fetch("/api/flash/send", { method: "POST", body: JSON.stringify({
        to: fwBoard.hostIp, port: fwBoard.farPort, type: fwImg.type }) })
        .then(x => x.json());
    } else {
      const url = overCable
        ? "/api/flash?port=" + encodeURIComponent(fwBoard.port) +
          "&type=" + encodeURIComponent(fwImg.type)
        : overBus
          ? "/api/flash/bus?dev=" + encodeURIComponent(fwBoard.dev) +
            "&type=" + encodeURIComponent(fwImg.type)
          : "/api/ota?ip=" + encodeURIComponent(fwBoard.ip) +
            "&type=" + encodeURIComponent(fwImg.type);
      r = await fetch(url, { method: "POST" }).then(x => x.json());
    }
  } catch (e) { r = { ok: false, error: "the hub did not answer" }; }
  if (r && r.ok === false) {
    $("fwSay").textContent = "";
    $("fwErr").hidden = false;
    $("fwErr").textContent = r.error || "refused";
    $("fwGo").disabled = false; $("fwBar").hidden = true;
    notice("Writing " + fwImg.type + " was refused: " + (r.error || "unknown reason"));
    return;
  }
  fwWatch({
    dev: overCable ? "usb:" + fwBoard.port
       : far ? "" : overBus ? fwBoard.dev : ("wifi:" + fwBoard.ip),
    type: fwImg.type },
    far ? "/api/flash/at?ip=" + encodeURIComponent(fwBoard.hostIp) : "/api/flash");
}

/* Follow the write. A bar that stops moving says so instead of sitting there. */
function fwWatch(want, from) {
  let quiet = 0, last = -1;
  const tick = setInterval(async () => {
    let s;
    try { s = await fetch(from || "/api/flash").then(x => x.json()); }
    catch (e) { return; }
    const pct = Math.round(s.percent || 0);
    $("fwBar").querySelector("i").style.width = pct + "%";
    const how = s.how === "bus" ? " over RS485" : s.how === "wifi" ? " over WiFi"
              : s.how === "usb" ? " over the cable" : "";
    $("fwSay").textContent = (s.stage || pct + "%") + how;
    quiet = pct === last ? quiet + 1 : 0;
    last = pct;
    if (quiet > 8) {
      $("fwSay").textContent = "No progress for a while — the hub will say when it gives up. Watch the board's own light.";
    }
    if (s.done || /done|ok|success/i.test(s.stage || "")) {
      clearInterval(tick);
      $("fwSay").textContent = "✓ Written. The board restarts into " + want.type + ".";
      $("fwGo").disabled = false;
    }
    if (/error|fail|refus/i.test((s.stage || "") + (s.error || ""))) {
      clearInterval(tick);
      $("fwSay").textContent = "";
      $("fwErr").hidden = false;
      $("fwErr").textContent = s.error || s.stage || "it stopped part way";
      $("fwGo").disabled = false;
    }
  }, 1500);
}

function fwPickBoard(m) {
  // Arriving from a module card: preselect nothing but remember which board
  // the designer meant — step 1 still asks what to install.
  fwReset();
  fwWanted = m;
}

let fwWanted = null;
const _fwToBoards = fwToBoards;
fwToBoards = function () {
  _fwToBoards();
  if (fwWanted) {
    const wanted = fwWanted; fwWanted = null;
    const pick = [...$("fwBoardsBox").querySelectorAll(".fwpick")]
      .find(l => l.textContent.indexOf(wanted.name || "") >= 0 ||
                 (wanted.id != null && l.textContent.indexOf("#" + wanted.id) >= 0));
    if (pick) { pick.querySelector("input").checked = true;
                fwBoard = wanted; $("fwNext2").disabled = false; }
  }
};

/* ------------------------------------------------------------------ pairing */
let pairTimer = null;

async function openPair() {
  openSheet("pairSheet");
  try {
    const r = await fetch("/api/pair/status").then(x => x.json());
    const may = r.ok !== false && !r.need_login;
    $("pairYes").hidden = !may; $("pairNo").hidden = may;
    if (!may) return;
    if (r.showing) pairCountdown(r.code, r.seconds);
  } catch (e) { notice("Pairing status: the hub did not answer."); }
}

async function pairStart() {
  try {
    const r = await fetch("/api/pair/start", { method: "POST" }).then(x => x.json());
    if (!r.ok) return pairFail(r.error || "the hub refused");
    pairCountdown(r.code, r.seconds);
  } catch (e) { pairFail("the hub did not answer"); }
}

function pairCountdown(code, secs) {
  $("pairCode").textContent = code;
  clearTimeout(pairTimer);
  const tick = () => {
    if (secs <= 0) { $("pairCode").textContent = ""; $("pairLeft").textContent = ""; return; }
    $("pairLeft").textContent = "Good for " + Math.floor(secs / 60) + "m " +
      ("0" + (secs % 60)).slice(-2) + "s";
    secs--; pairTimer = setTimeout(tick, 1000);
  };
  tick();
}

async function pairStop() {
  try { await fetch("/api/pair/stop", { method: "POST" }); } catch (e) {}
  $("pairCode").textContent = ""; $("pairLeft").textContent = "";
}

function pairFace(id) {
  ["pairEnter", "pairClash"].forEach(f => {});   // faces live in one sheet now
  $("pairClash").hidden = id !== "pairClash";
  if (id === "pairEnter") { $("pairErr").hidden = true; $("pairDone").hidden = true; }
}

function pairFail(why) {
  $("pairErr").hidden = false;
  $("pairErr").textContent = why;
}

async function pairLink(replace) {
  const addr = $("pairAddr").value.trim(), code = $("pairInput").value.trim();
  try {
    const r = await fetch("/api/pair/link", { method: "POST",
      body: JSON.stringify({ ip: addr, code: code, replace: !!replace }) })
      .then(x => x.json());
    if (r.ok === false) return pairFail(r.error || "refused");
    if ((r.clashed || []).length) {
      $("pairClashWhy").textContent =
        "This PC already has an account called " + r.clashed.join(", ") +
        ". Replacing means that name logs in with the password set on " +
        (r.from || "that PC") + ". Keeping it leaves the two names different.";
      pairFace("pairClash");
      return;
    }
    const took = (r.added || []).concat(r.replaced || []);
    $("pairDone").hidden = false;
    $("pairDone").textContent = took.length
      ? "Paired with " + (r.from || "that PC") + " — " + took.join(", ") +
        " can log in here with the same password."
      : "Already paired with " + (r.from || "that PC") + " — nothing to copy.";
  } catch (e) { pairFail("the hub did not answer"); }
}

/* ------------------------------------------------------------------ reports */
async function loadReports(force) {
  const line = $("repLine"), box = $("repList");
  if (!box.children.length || force) {
    line.className = "xs state-load"; line.textContent = "reading the complaints…";
  }
  let rows;
  try {
    rows = (await fetch("/api/reports").then(r => r.json())).reports || [];
  } catch (e) {
    line.className = "xs state-err";
    line.textContent = "The hub did not answer.";
    notice("Complaints could not be read.");
    return;
  }
  if (!rows.length) {
    line.className = "xs state-empty";
    line.textContent = "Nothing reported so far.";
    box.innerHTML = "";
    return;
  }
  line.textContent = rows.length + " report" + (rows.length === 1 ? "" : "s") + ".";
  box.innerHTML = "";
  rows.slice(0, 8).forEach(rp => {
    const d = document.createElement("div");
    d.className = "rep";
    const en = rp.text_en && rp.text_en !== rp.text
      ? "<br><span class='mini'>en: " + esc(rp.text_en) + "</span>" : "";
    d.innerHTML = "<span class='when'>" + esc(rp.time || "") + " · " +
      esc(rp.status || "open") + "</span><br>" + esc(rp.text || "") + en + "<br>";
    const sel = document.createElement("select");
    sel.setAttribute("aria-label", "Set status");
    [["open", "still open"], ["fixed", "fixed"], ["not-a-problem", "not a problem"]]
      .forEach(([v, w]) => {
        const o = document.createElement("option");
        o.value = v; o.textContent = w; if (v === (rp.status || "open")) o.selected = true;
        sel.appendChild(o);
      });
    sel.onchange = async () => {
      try {
        await fetch("/api/reports", { method: "POST",
          body: JSON.stringify({ id: rp.id, status: sel.value }) });
        loadReports(true);
      } catch (e) { notice("Could not save that status."); }
    };
    d.appendChild(sel);
    box.appendChild(d);
  });
}

function reportOpen() { $("repModal").hidden = false; $("repText").focus(); }
function reportClose() { $("repModal").hidden = true; $("repBusy").classList.remove("show"); }

async function reportSend() {
  const text = $("repText").value.trim();
  if (!text) { $("repText").focus(); return; }
  $("repBusy").classList.add("show");
  let diag = "";
  if ($("repIncDiag").checked) { try { diag = await fetch("/api/diag").then(r => r.text()); } catch (e) {} }
  try {
    const r = await fetch("/api/report", { method: "POST",
      body: JSON.stringify({ text: text, page: location.pathname, diag: diag }) })
      .then(r => r.json());
    if (!r.ok) throw new Error(r.error || "refused");
    $("repText").value = "";
    reportClose();
    loadReports(true);
  } catch (e) {
    notice("The report did not send: " + (e.message || e) + " — your words are still in the box.");
  } finally { $("repBusy").classList.remove("show"); }
}

/* ------------------------------------------------------- tools, diag, update */
async function loadApps() {
  let apps = [], broken = null;
  try {
    const r = await fetch("/api/apps").then(r => r.json());
    apps = r.apps || [];
    if (r.ok === false) broken = r.error;
  } catch (e) { broken = "the hub did not answer"; }
  if (broken) {
    $("appsLine").className = "xs state-err";
    $("appsLine").textContent = "The app list could not be read.";
    notice("App registry problem: " + broken);
    return;
  }
  if (!apps.length) {
    $("appsLine").className = "xs state-empty";
    $("appsLine").textContent = "No extra tools are installed on this PC.";
    return;
  }
  $("appsLine").textContent = "";
  apps.forEach(a => {
    // The registry's field is path (the URL to open), not url — reading url
    // silently produced href="#" rows that looked fine and opened nothing.
    const b = document.createElement("a");
    b.href = a.path || "#"; b.textContent =
      (a.icon ? a.icon + " " : "") + (a.name || "tool");
    b.target = "_blank"; b.rel = "noopener";
    if (a.help) {
      b.title = "opens " + (a.name || "this tool") + "; its help is section " + a.help;
    }
    $("appsList").appendChild(b);
  });
}

async function copyDiag(btn) {
  btn.disabled = true;
  try {
    const text = await fetch("/api/diag").then(r => r.text());
    $("diagTech").textContent = String(text).slice(0, 400);
    try { await navigator.clipboard.writeText(text); $("diagLine").textContent = "Copied."; }
    catch (e) { $("diagLine").textContent = "Clipboard refused — the detail is shown beside the button."; }
  } catch (e) {
    $("diagLine").className = "xs state-err";
    $("diagLine").textContent = "The hub did not answer.";
  } finally { btn.disabled = false; }
}

async function checkUpdate() {
  let s;
  try { s = await fetch("/api/selfupdate").then(r => r.json()); }
  catch (e) { $("updLine").textContent = "Could not ask about updates."; return; }
  if (!s.can) { $("updLine").textContent = s.why || "Nothing to update."; return; }
  $("updLine").textContent = s.message || "An update is available.";
  $("updBtn").hidden = false;
}

async function selfUpdate(btn) {
  btn.disabled = true;
  $("updLine").textContent = "Downloading…";
  try {
    const r = await fetch("/api/selfupdate", { method: "POST" }).then(x => x.json());
    $("updLine").textContent = r.message || (r.ok ? "Done." : "It did not work.");
  } catch (e) { $("updLine").textContent = "The hub did not answer."; }
  finally { btn.disabled = false; }
}

/* ------------------------------------------------------------------ users */
async function loadUsers() {
  let users = [];
  try { users = (await fetch("/api/users").then(r => r.json())).users || []; }
  catch (e) { $("usersLine").textContent = "The account list could not be read."; return; }
  $("usersLine").textContent = users.length ? "" : "No accounts listed.";
  const box = $("usersList");
  box.innerHTML = "";
  users.forEach(u => {
    const row = document.createElement("p");
    row.className = "mini";
    row.innerHTML = esc(typeof u === "string" ? u : (u.user || u.name || "?"));
    const rm = document.createElement("button");
    rm.className = "icon danger"; rm.textContent = "✕";
    rm.title = "Remove this account";
    rm.onclick = async () => {
      try {
        await fetch("/api/users/remove", { method: "POST",
          body: JSON.stringify({ user: typeof u === "string" ? u : (u.user || u.name) }) });
        loadUsers();
      } catch (e) { notice("Could not remove the account."); }
    };
    row.appendChild(rm);
    box.appendChild(row);
  });
}

/* ------------------------------------------------------------------- misc */
async function stopEverything() {
  const btn = $("stopAllBtn"), said = $("stopSaid");
  btn.disabled = true; btn.textContent = "STOPPING…";
  try {
    const r = await fetch("/api/stopall", { method: "POST" }).then(x => x.json());
    const bad = r.failed || [];
    // The result speaks beside the button, in the colour of what happened;
    // the red banner stays failures-only. Partial reach IS a warning: the
    // boards it names keep moving until somebody uses the power switch.
    said.className = "banner " + (bad.length ? "warn" : "ok");
    said.textContent = bad.length
      ? "Stopped some, but could NOT reach: " + bad.join(", ") +
        " — use the power switch for those."
      : "Everything stopped" + ((r.stopped || []).length
        ? "" : " (nothing was moving)") + ".";
    said.hidden = false;
  } catch (e) {
    said.className = "banner err";
    said.textContent = "The stop did not reach the hub. Use the power switch.";
    said.hidden = false;
    notice("Stop command: the hub did not answer.");
  }
  finally { btn.disabled = false; btn.textContent = "STOP EVERYTHING"; }
}

/* ------------------------------------------------------------------- boot */
function boot() {
  refreshMods(false);
  loadApps();
  loadReports(false);
  copyDiagPrep();
  checkUpdate();
  loadUsers();
}

function copyDiagPrep() { /* diag is fetched on demand only */ }

document.addEventListener("DOMContentLoaded", () => {
  if (window.miceTheme) miceTheme.picker($("themePick"));
  if (window.miceAdv) $("advOn").checked = miceAdv.on();
  $("advOn").addEventListener("change", e => miceAdv.set(e.target.checked));
  $("loginForm").addEventListener("submit", doLogin);
  $("logoutBtn").onclick = async () => {
    try { await fetch("/api/logout", { method: "POST" }); } catch (e) {}
    location.reload();
  };
  $("showPorts").addEventListener("change", () => paintMods(null));
  $("userForm").addEventListener("submit", async ev => {
    ev.preventDefault();
    try {
      await fetch("/api/users/add", { method: "POST", body: JSON.stringify({
        user: $("userName").value.trim(), password: $("userPass").value }) });
      $("userName").value = ""; $("userPass").value = "";
      loadUsers();
    } catch (e) { notice("Could not add that account."); }
  });
  $("fwGo").onclick = fwWrite;
  refreshAuth();
  // Tonight stays live by itself: a light poll beats making somebody press
  // Look again to learn that a board came up.
  setInterval(() => { if (authed && !modBusy) refreshMods(false); }, 8000);
});
