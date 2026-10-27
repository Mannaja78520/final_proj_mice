"use strict";
const fs = require("fs"), vm = require("vm");
const read = path => fs.readFileSync(path, "utf8");
let failed = 0;
function ok(value, label) { console.log((value ? "PASS " : "FAIL ") + label); if (!value) failed++; }
async function test(label, fn) {
  try { await fn(); } catch (e) { ok(false, label + ": " + e.message); }
}

class Element {
  constructor(tag = "div") {
    this.tag = tag; this.children = []; this.className = ""; this.style = {};
    this.dataset = {}; this.hidden = false; this._value = ""; this._html = "";
    this.tBodies = [{innerHTML: "", rows: []}]; this.inputs = [];
    this.classList = {remove() {}, add() {}, toggle() {}};
  }
  get value() { return this.tag === "select" ? ((this.children.find(c => c.selected) || this.children[0] || {}).value || "") : this._value; }
  set value(v) { this._value = v; if (this.tag === "select") this.children.forEach(c => { c.selected = c.value === v; }); }
  get innerHTML() { return this._html; }
  set innerHTML(v) { this._html = v; this.children = []; }
  get textContent() { return this._html; }
  set textContent(v) { this._html = String(v); }
  appendChild(c) { this.children.push(c); return c; }
  append(...nodes) { this.children.push(...nodes); }
  replaceChildren(...nodes) { this._html = ""; this.children = [...nodes]; }
  getAttribute(k) { return Object.prototype.hasOwnProperty.call(this, k) ? String(this[k]) : null; }
  setAttribute(k, v) { this[k] = v; }
  removeAttribute(k) { delete this[k]; }
  querySelectorAll() { return this.inputs; }
}

function context() {
  const elements = new Map(), events = new Map(), timers = new Map(), storage = new Map();
  const el = id => { if (!elements.has(id)) elements.set(id, new Element()); return elements.get(id); };
  const listeners = (name, fn) => { if (!events.has(name)) events.set(name, []); events.get(name).push(fn); };
  let nextTimer = 0;
  const c = {console, URL, URLSearchParams, AbortController, setTimeout, clearTimeout,
    CustomEvent: class {}, innerWidth: 900, navigator: {},
    localStorage: {getItem: k => storage.get(k) || null, setItem: (k, v) => storage.set(k, v)},
    setInterval: fn => { timers.set(++nextTimer, fn); return nextTimer; }, clearInterval: id => timers.delete(id),
    addEventListener: listeners, dispatchEvent() {},
    document: {readyState: "loading", hidden: false, getElementById: el, createElement: t => new Element(t),
      querySelectorAll: () => [], addEventListener: listeners, dispatchEvent() {}, documentElement: new Element(), body: new Element()},
    location: {origin: "http://fixture.invalid", href: "http://fixture.invalid/", hash: ""},
    fetch: async () => { throw Error("Unexpected fixture request"); }};
  c.window = c; c.globalThis = c; c.el = el; c.timers = timers; c.storage = storage;
  c.fire = (name, event = {}) => (events.get(name) || []).forEach(fn => fn(event));
  vm.createContext(c);
  vm.runInContext(read("shared/web/mice-ui.js"), c);
  return c;
}

function voice(c) {
  const src = read("apps/voice/app.js");
  vm.runInContext(src.slice(0, src.indexOf("window.voiceApp = new VoiceApp")), c);
  return vm.runInContext("new VoiceApp()", c);
}
function tv(c) {
  const src = read("apps/tv/index.html");
  vm.runInContext(src.slice(src.indexOf("const JOINTS ="), src.indexOf("const app = new TVRemoteApp")), c);
  return vm.runInContext("new TVRemoteApp()", c);
}
function gacha(c) {
  vm.runInContext(read("apps/gacha/motion.js"), c);
  if (fs.existsSync("apps/gacha/presets.js")) vm.runInContext(read("apps/gacha/presets.js"), c);
  const src = read("apps/gacha/index.html"), start = src.lastIndexOf("<script>");
  vm.runInContext(src.slice(start + 8, src.indexOf("window.GachaApp =")), c);
  const app = vm.runInContext("new GachaApp()", c);
  c.gachaApp = app;
  // Execute the shipped global bindings, including the old stale aliases.
  const bindings = src.slice(src.indexOf("window.GachaApp =")).split("\n").filter(line =>
    /^(let S =|let ED =|const (drawMachines|removeMachine|edRead|edDraw|edRemove) =)/.test(line));
  vm.runInContext(bindings.join("\n"), c);
  return app;
}
const machine = (id, label = id) => ({id, label, module: id, item: "gift", near: [], live: {cfg: {}, stock: 1}});

(async () => {
  await test("Voice with actual shared App", () => {
    const c = context(), app = voice(c);
    app.say("Ready fixture"); app.say("Warning fixture", "warn");
    ok(c.el("stat").textContent === "Warning fixture", "Voice status works with the real inherited App getter");
    const first = app._status; app.say("Again");
    ok(app._status === first, "Voice reuses its existing status object");
  });
  await test("Voice bundle before its DOM", () => {
    const c = context(), lookup = c.document.getElementById;
    c.document.getElementById = () => null;
    const app = voice(c);
    c.document.getElementById = lookup;
    app.say("DOM ready");
    ok(c.el("stat").textContent === "DOM ready", "head-loaded Voice creates its status only after the DOM is available");
  });
  await test("Voice standalone fallback", () => {
    const c = context(); delete c.Mice.App; const app = voice(c);
    app.say("First"); const first = app._status; app.say("Second");
    ok(app._status === first && c.el("stat").textContent === "Second", "Voice status also works when the base App is absent");
  });
  await test("Loaded Gacha machine removal", () => {
    const c = context(), app = gacha(c);
    const second = machine("second"); second.live.cfg.slots = 8; second.at = 42;
    app.S = {machines: [machine("first"), second], items: {}}; c.S = app.S;
    app.readMachines = () => [{id: "first", label: "first"}, {id: "second", label: "unsaved edit"}];
    app.drawMachines();
    const click = [...c.el("mTable").tBodies[0].innerHTML.matchAll(/onclick="([^"]+)">remove<\/button>/g)][0][1];
    vm.runInContext(click, c);
    ok(app.S.machines.length === 1 && app.S.machines[0].id === "second", "machine Remove acts on the latest loaded state");
    ok(app.S.machines[0].label === "unsaved edit", "machine Remove preserves edits in the remaining rows");
    ok(app.S.machines[0].live.cfg.slots === 8 && app.S.machines[0].at === 42, "machine Remove retains live tuning and route timestamps");
    let command = ""; app.motion.run = (i, cmd) => { command = cmd; }; app.testAllSlots(0);
    ok(command === "GTEST 8", "remaining machine tests still use its actual pocket count");
  });
  await test("Loaded Sheet row removal", () => {
    const c = context(), app = gacha(c);
    app.ED = [["name"], ["remove me"], ["old value"]];
    c.el("edT").inputs = app.ED.map((r, i) => ({dataset: {r: i, c: 0}, value: i === 2 ? "unsaved edit" : r[0]}));
    app.edDraw();
    const click = [...c.el("edT").tBodies[0].innerHTML.matchAll(/onclick="([^"]+)">remove<\/button>/g)][1][1];
    vm.runInContext(click, c);
    ok(app.ED.length === 2 && app.ED[1][0] === "unsaved edit", "Sheet Remove uses loaded rows and retains unsaved edits");
  });
  async function preset(failure, boardFailure, refresh = true) {
    const c = context(), app = gacha(c), calls = [];
    app.readMachines = () => [machine("new-board")]; app.readItems = () => ({gift: {label: "Gift"}});
    app.readRows = () => []; app.load = async () => refresh; c.el("evName").value = "Fixture event";
    c.fetch = async (path, opts) => {
      const body = JSON.parse(opts.body); calls.push({path, body});
      const accepted = calls.length !== failure;
      const key = "name" in body ? "name" : "open";
      const sent = {[key]: {"new-board": boardFailure && body.open === true ? "ERR busy" : "OK"}};
      return {ok: accepted, status: accepted ? 200 : 403, json: async () => ({ok: accepted, error: accepted ? "" : "Denied fixture", sent})};
    };
    const result = await app.saveAllPreset();
    return {c, app, calls, result};
  }
  await test("Preset success ordering", async () => {
    const p = await preset(0, false);
    ok(p.result && p.result.ok, "preset reports success after acknowledged saves");
    ok(p.calls.length === 5 && p.calls[0].body.open === false && p.calls[4].body.open === true,
      "preset closes before configuration and opens only after configuration, rules and name");
    ok(p.calls[1].body.machines[0].id === "new-board" && p.calls[1].body.items.gift.label === "Gift", "preset saves the complete captured machine/item data");
  });
  for (let stage = 1; stage <= 5; stage++) await test("Preset refusal stage " + stage, async () => {
    const p = await preset(stage, false);
    ok(p.result && p.result.ok === false, "preset stage " + stage + " refusal cannot report ready");
    ok(p.calls.length === stage + (stage === 5 ? 1 : 0), "preset stage " + stage + " stops writes, except closing after an uncertain open");
    ok(!p.app.preset || !p.app.preset.busy, "preset refusal releases its owner");
  });
  await test("Preset board refusal", async () => {
    const p = await preset(0, true);
    ok(p.result && !p.result.ok && p.result.error.includes("ERR busy"), "HTTP 200 with a board refusal remains a failed start");
    ok(p.calls.at(-1).body.open === false, "partial or uncertain open is followed by a checked close");
  });
  await test("Preset refresh failure", async () => {
    const p = await preset(0, false, false);
    ok(p.result && p.result.ok && !p.result.refreshed, "successful saved/open state is distinguished from failed UI refresh");
  });
  await test("Preset simultaneous start", async () => {
    const c = context(), app = gacha(c); let release, requests = 0;
    app.readMachines = () => [machine("new-board")]; app.readItems = () => ({}); app.readRows = () => [];
    app.load = async () => true;
    c.fetch = async (path, opts) => {
      requests++;
      if (requests === 1) await new Promise(resolve => { release = resolve; });
      const body = JSON.parse(opts.body), key = "name" in body ? "name" : "open";
      return {ok: true, status: 200, json: async () => ({ok: true, sent: {[key]: {"new-board": "OK"}}})};
    };
    const first = app.saveAllPreset(), second = await app.saveAllPreset();
    ok(second && second.busy && requests === 1, "repeated start clicks cannot duplicate a pending preset operation");
    release(); await first;
    ok(requests === 5, "one preset owner completes exactly one save/start sequence");
  });
  await test("Preset missing acknowledgement", async () => {
    const c = context(), app = gacha(c); let opened = false;
    app.readMachines = () => [machine("new-board")]; app.readItems = () => ({}); app.readRows = () => [];
    c.fetch = async (path, opts) => {
      const body = JSON.parse(opts.body); if (body.open === true) opened = true;
      return {ok: true, status: 200, json: async () => ({ok: true, sent: {open: {}, name: {}}})};
    };
    const result = await app.saveAllPreset();
    ok(result && !result.ok && !opened, "missing new-board name acknowledgement prevents opening");
  });
  await test("TV hidden in-flight reply", async () => {
    const c = context(), app = tv(c); app.resetPollTimer(900);
    c.document.hidden = true; c.timers.clear(); app.pollTimer = null;
    app.updatePlayState({running: true, total_ms: 1000, at_ms: 100});
    app.updatePlayState({running: false});
    ok(c.timers.size === 0 && !app.pollTimer, "late playback replies cannot restart polling in a hidden tab");
    let calls = 0; c.fetch = async () => { calls++; throw Error("hidden request"); }; await app.poll();
    ok(calls === 0, "hidden TV poll does not request module or playback status");
    c.document.hidden = false; app.resetPollTimer(900);
    ok(c.timers.size === 1, "visible TV can resume exactly one polling timer");
  });
  await test("TV unavailable storage", () => {
    const c = context(); Object.defineProperty(c, "localStorage", {get() { throw Error("Storage denied"); }});
    const app = tv(c); let polls = 0; app.loadSequences = () => {}; app.poll = () => { polls++; };
    app.init(); ok(app.currentMode === "tech" && polls === 1, "TV initializes controls and polling when storage access is denied");
  });
  await test("Theme selectors stay synchronized", () => {
    const c = context(); c.storage.set("mice_theme", "first");
    c.document.styleSheets = [{cssRules: ["first", "second"].map(id => ({selectorText: ':root[data-theme="' + id + '"]',
      style: {getPropertyValue: key => key === "--theme-name" ? id : key === "--theme-note" ? id + " note" : ""}}))}];
    const src = read("shared/web/mice.js"); vm.runInContext(src.slice(0, src.indexOf("/* ONE ANSWER")), c);
    const left = new Element(), right = new Element();
    const a = c.miceTheme.picker(left), b = c.miceTheme.picker(right);
    c.miceTheme.set("second");
    ok(a.value === "second" && b.value === "second", "same-page theme selectors follow manager changes");
    ok(left.children[1].textContent === "second note", "theme explanatory note follows its selection");
    c.fire("storage", {key: "mice_theme", newValue: "first"});
    ok(a.value === "first" && b.value === "first", "cross-tab theme changes update both selectors");
    c.miceTheme.set("second"); c.fire("storage", {key: "mice_theme", newValue: null});
    ok(!c.document.documentElement["data-theme"] && a.value === "first", "removing a stored theme restores default and picker together");
  });
  await test("Tools registry order, fallback and single global help", () => {
    const c = context(), src = read("main_python/web/home/parts/tools.js");
    vm.runInContext(src.slice(0, src.indexOf("window.MiceToolsManager")), c);
    const manager = vm.runInContext("new MiceToolsManager()", c), box = new Element();
    const apps = [{id: "cctv-camera", name: "Camera", path: "/app/cctv-camera/", help: "camera"},
      {id: "new-addon", name: "New add-on", path: "/app/new-addon/"}];
    const rows = node => (node.className.split(" ").includes("tool-tile") ? [node] : []).concat(...node.children.map(rows));
    manager.render(box, apps);
    const rendered = rows(box), names = rendered.map(row => row.children.find(n => n.className === "nm").textContent);
    ok(rendered.length === apps.length && names.join("|") === apps.map(a => a.name).join("|"),
      "registry order is preserved and each tool appears exactly once");
    ok(names.includes("New add-on"), "unknown tools remain visible without a category catalog");
    rendered.forEach((row, i) => {
      const links = row.children.filter(n => n.tag === "a");
      ok(links.length === 1 && links[0].href === new URL(apps[i].path, c.location.href).href,
        "each tool has one native link to its registered destination");
      ok(links[0].target === "_blank" && links[0].rel.includes("noopener") && links[0].getAttribute("aria-label").includes(apps[i].name),
        "native new-tab links have a safe opener and accessible app label");
      ok(!links.some(n => n.href.includes("/help#")), "per-tool Help is absent even when a manifest declares it");
    });
    manager.render(box, apps);
    ok(rows(box).length === apps.length, "redrawing replaces rather than duplicates rows");
  });
  process.exitCode = failed ? 1 : 0;
})().catch(error => { console.error(error); process.exitCode = 1; });
