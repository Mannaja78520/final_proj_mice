/* mice-ui.js - the parts every hub page is built from.
 *
 * Asked 2026-10-14: *each web page in main goes its own way, hard to read and
 * hard to use - make it simple, the same everywhere, and OOP so a later change
 * is easy and costs fewer tokens*. Measured that day: five app pages, four
 * ways back to the hub, three status lines, and three copies of "is the
 * outside program running" that each probed 127.0.0.1 from the BROWSER - so a
 * phone (the hub shows a QR for it) always heard "not running".
 *
 * A page now ASSEMBLES these instead of writing them again:
 *   Mice.Api      every call to the hub: timeout, JSON, words a person reads
 *   Mice.Status   one status line, five states, the technical part hidden
 *   Mice.TopBar   the same head on every page (auto-mounted, see below)
 *   Mice.Partner  an outside program: is it up, start it, open it
 *   Mice.Tabs     one section on screen at a time, picked from a side list
 *
 * Served by the hub only (not compiled into a board's flash: the board site
 * has no room - mice_nong is near its OTA slot). How to build a page with
 * these: docs/web_style.md. Plain script, no build step, no framework.
 */
(function () {
  "use strict";

  // The machine this page was opened on is not always the hub's PC. A link
  // the hub wrote as 127.0.0.1 means "the hub's PC", which from a phone is
  // the hub's own address (what the page was loaded from).
  const LOOPBACK = ["localhost", "127.0.0.1", "[::1]"];
  function here(url) {
    try {
      const u = new URL(url, location.href);
      if (LOOPBACK.includes(u.hostname) && !LOOPBACK.includes(location.hostname))
        u.hostname = location.hostname;
      return u.href;
    } catch (e) { return url; }
  }

  /* ---------------------------------------------------------------- Api */
  // Never throws. Every answer is {ok, data, status, says, tech}: `says` is
  // for the person, `tech` for the technical switch. A page that forgot a
  // catch used to leave a status line on "checking..." forever.
  class Api {
    static async call(path, opts) {
      opts = opts || {};
      const ctl = new AbortController();
      const timer = setTimeout(() => ctl.abort(), opts.timeout || 8000);
      const init = {method: opts.method || "GET", cache: "no-store", signal: ctl.signal};
      if (opts.body !== undefined) {
        init.headers = {"Content-Type": "application/json"};
        init.body = JSON.stringify(opts.body);
      }
      try {
        const r = await fetch(path, init);
        let data = {};
        try { data = opts.text ? {reply: await r.text()} : await r.json(); } catch (e) { /* not JSON: keep {} */ }
        const ok = r.ok && data.ok !== false;
        return {ok, data, status: r.status,
                needLogin: r.status === 401 || !!data.need_login,
                says: ok ? "" : (data.error || "the hub said no (" + r.status + ")"),
                tech: data.detail || (r.ok ? "" : "HTTP " + r.status + " " + path)};
      } catch (e) {
        return {ok: false, data: {}, status: 0, needLogin: false,
                says: "cannot reach the hub - is it still running?",
                tech: String(e.name === "AbortError" ? "timed out: " + path : e.message || e)};
      } finally {
        clearTimeout(timer);
      }
    }
    static get(path, opts) { return Api.call(path, opts); }
    static post(path, body, opts) {
      return Api.call(path, Object.assign({method: "POST", body: body}, opts));
    }
  }

  /* ------------------------------------------------------------- Status */
  // The five states every list and line has (loading, empty, error, stale,
  // ready), as the classes mice.css already styles. The technical detail is
  // a .tech span, so it shows only behind "Show technical details".
  const KIND = {loading: "state-load", empty: "state-empty", error: "state-err",
                stale: "state-stale", ready: "state-ok", warn: "state-warn"};
  class Status {
    constructor(el) {
      this.el = typeof el === "string" ? document.getElementById(el) : el;
      this.base = this.el.className.replace(/\bstate-\w+/g, "").trim();
      this.el.setAttribute("role", "status");
      this.el.setAttribute("aria-live", "polite");
    }
    show(kind, says, tech) {
      this.el.className = (this.base + " " + (KIND[kind] || "")).trim();
      this.el.textContent = says || "";
      if (tech) {
        const t = document.createElement("span");
        t.className = "tech mini";
        t.textContent = " " + tech;
        this.el.appendChild(t);
      }
      return this;
    }
    loading(says, tech) { return this.show("loading", says || "checking…", tech); }
    empty(says, tech) { return this.show("empty", says, tech); }
    error(says, tech) { return this.show("error", says, tech); }
    stale(says, tech) { return this.show("stale", says, tech); }
    warn(says, tech) { return this.show("warn", says, tech); }
    ready(says, tech) { return this.show("ready", says, tech); }
    // An Api answer, worded: the error words, or `good` when it went through.
    from(ans, good) {
      return ans.ok ? this.ready(good, ans.tech) : this.error(ans.says, ans.tech);
    }
  }

  /* ------------------------------------------------------------- TopBar */
  // One head on every page: the way back to the hub always first, then what
  // the page wrote inside <header class="topbar"> (title, status, its own
  // buttons), then the technical switch always last. The page writes only
  // what is its own; the frame around it is this.
  class TopBar {
    constructor(el) {
      this.el = el;
      if (el.dataset.mounted) return;
      el.dataset.mounted = "1";
      if (el.dataset.home !== "none") {
        const home = document.createElement("a");
        home.className = "topbar-home";
        home.href = el.dataset.home || "/";
        home.textContent = "← Hub";
        home.title = "back to the hub's Home page";
        el.insertBefore(home, el.firstChild);
      }
      // One switch per page: a page that already carries its own keeps it.
      if (!document.getElementById("advOn")) {
        const lab = document.createElement("label");
        lab.className = "topbar-adv mini";
        lab.innerHTML = '<input type="checkbox" id="advOn"> Show technical details';
        el.appendChild(lab);
        const box = lab.firstChild;
        box.checked = !!(window.miceAdv && window.miceAdv.on());
        box.onchange = () => window.miceAdv && window.miceAdv.set(box.checked);
      }
    }
    static mountAll() {
      document.querySelectorAll("header.topbar").forEach(el => new TopBar(el));
    }
  }

  /* ------------------------------------------------------------ Partner */
  // An outside program from config/partners.json (Reconize, Photobooth,
  // All-Jao). The hub checks it and starts it - the browser never probes
  // 127.0.0.1 itself, which is the PHONE's own machine when the page was
  // opened from the hub's QR. One class, so the next program is an entry in
  // partners.json and a page that says `new Mice.Partner("its-id", ...)`.
  class Partner {
    // opts: {status: Status, name, startPath, startWait}
    constructor(id, opts) {
      this.id = id;
      this.opts = opts || {};
      this.status = this.opts.status;
      this.links = null;
      this.starting = null;
    }
    get name() { return this.opts.name || (this.links && this.links.name) || this.id; }

    async load() {
      const a = await Api.get("/api/partners");
      if (!a.ok) { this.status.error("the list of outside apps could not be read.", a.says); return null; }
      this.links = (a.data.partners || {})[this.id] || null;
      if (!this.links)
        this.status.error("This app is not set up yet.",
                          "config/partners.json has no entry called " + this.id);
      return this.links;
    }
    url(which) { return this.links && this.links[which] ? here(this.links[which]) : ""; }

    // Asks the HUB whether it answers. {up, says}
    async check() {
      this.status.loading();
      const a = await Api.get("/api/partners/health?id=" + encodeURIComponent(this.id));
      if (!a.ok) { this.status.error(a.says, a.tech); return false; }
      if (a.data.up) this.status.ready(this.name + " is running.", a.data.checked);
      else this.status.warn(this.name + " is not running. Press Open and it starts by itself.",
                            a.data.checked);
      return !!a.data.up;
    }

    // Starts it through the hub when silent, waits until it answers.
    // Resolves to where it answered; rejects with [words, detail].
    ensure() {
      if (!this.starting) this.starting = this._start().finally(() => { this.starting = null; });
      return this.starting;
    }
    async _start() {
      const until = Date.now() + (this.opts.startWait || 120000);
      const path = this.opts.startPath || "/api/partners/start?id=" + encodeURIComponent(this.id);
      for (;;) {
        const a = await Api.post(path);
        const got = a.data || {};
        const log = [].concat(got.log || []).join(" ");
        if (a.needLogin)
          throw [this.name + " can only be started from the PC that runs Mice, or after signing in on the hub page."];
        if (!a.ok) throw [a.says || this.name + " could not be started.", log || a.tech];
        if (got.ready || got.already_running) return this._where(got);
        // A starter that only launches (no `ready` in its answer): ask the
        // hub until it answers, and never press start twice.
        if (!("ready" in got)) {
          while (Date.now() < until) {
            this.status.loading("Starting " + this.name + "…", got.message || "");
            await new Promise(res => setTimeout(res, 1000));
            if (await this._answers()) return this._where(got);
          }
          throw [this.name + " is taking too long to start.", got.message || ""];
        }
        this.status.loading("Starting " + this.name + "… this can take about twenty seconds", log);
        if (Date.now() > until) throw [this.name + " is taking too long to start.", log];
        await new Promise(res => setTimeout(res, 2000));
      }
    }
    _where(got) { return here(got.open || (this.links && this.links.open) || ""); }
    async _answers() {
      const a = await Api.get("/api/partners/health?id=" + encodeURIComponent(this.id));
      return a.ok && !!a.data.up;
    }

    // The tab is opened NOW, inside the click: a tab opened after a wait is
    // blocked as a pop-up. `which` is a key in its partners.json entry.
    async open(which, btn) {
      if (!this.links) return this.status.error("The address has not loaded yet - try again in a moment.");
      if (btn) btn.disabled = true;
      const tab = window.open("about:blank", "_blank");
      try {
        const where = await this.ensure();
        const target = which && which !== "open" ? this.url(which) : where;
        if (tab && !tab.closed) tab.location.href = target; else window.open(target, "_blank");
        this.status.ready(this.name + " is running.", target);
        return target;
      } catch (err) {
        if (tab && !tab.closed) tab.close();
        const [words, detail] = Array.isArray(err) ? err : [this.name + " could not be started.", String(err)];
        this.status.error(words + " Press the button to try again.", detail);
        return "";
      } finally {
        if (btn) btn.disabled = false;
      }
    }
  }

  /* --------------------------------------------------------------- Tabs */
  // One section on screen at a time, picked from a list down the side (a
  // wrapping row on a phone): the friend's Reconize app's layout, asked
  // 2026-10-23 ("ทำ tab ... ให้ใช้งานง่ายแบบตัวของ facereg") so a setting is
  // a click away instead of a long scroll. Markup:
  //   <div class="tabbed"><nav id="tabs"></nav><div> cards with data-tab="id" </div></div>
  //   new Mice.Tabs("tabs", [{id, label, icon?, load?}], {onShow?, hash?, attr?})
  // The open tab is kept in the address (#id) so a reload or a shared link
  // lands on it; `load` runs each time its tab opens (fresh data, no polling).
  class Tabs {
    constructor(nav, tabs, opts = {}) {
      this.nav = typeof nav === "string" ? document.getElementById(nav) : nav;
      this.tabs = tabs;
      this.opts = opts;
      this.attr = opts.attr || "tab";
      this.nav.classList.add("tabs");
      this.nav.setAttribute("role", "tablist");
      this.nav.innerHTML = "";
      tabs.forEach(t => {
        const b = document.createElement("button");
        b.type = "button";
        b.className = "tab" + (t.tech ? " tech" : "");
        b.setAttribute("role", "tab");
        b.dataset.t = t.id;
        b.textContent = (t.icon ? t.icon + " " : "") + t.label;
        b.onclick = () => this.show(t.id);
        this.nav.appendChild(b);
      });
      if (opts.hash !== false)
        window.addEventListener("hashchange", () => this.show(location.hash.slice(1), true));
      this.show(opts.hash !== false ? location.hash.slice(1) : opts.start);
    }
    has(id) { return this.tabs.some(t => t.id === id); }
    show(id, fromHash) {
      if (!this.has(id)) {
        if (fromHash) return;               // a hash that is not ours (an in-page link)
        id = this.opts.start && this.has(this.opts.start) ? this.opts.start : this.tabs[0].id;
      }
      this.current = id;
      document.querySelectorAll("[data-" + this.attr + "]").forEach(c => {
        c.hidden = c.dataset[this.attr] !== id;
      });
      this.nav.querySelectorAll(".tab").forEach(b => {
        const on = b.dataset.t === id;
        b.classList.toggle("on", on);
        b.setAttribute("aria-selected", on);
      });
      if (this.opts.hash !== false && location.hash !== "#" + id)
        history.replaceState(null, "", "#" + id);
      const t = this.tabs.find(x => x.id === id);
      if (t.load) t.load();
      if (this.opts.onShow) this.opts.onShow(id);
    }
  }

    /* ---------------------------------------------------------------- App */
  // Base class for all Mice applications providing unified DOM access,
  // lifecycle management, status reporting, and event handling.
  class App {
    constructor(name, opts = {}) {
      this.name = name || "app";
      this.opts = opts;
      this.$ = id => document.getElementById(id);
      this._status = opts.statusId ? new Status(opts.statusId) : null;
      this._events = new Map();
    }
    get status() { return this._status; }
    esc(s) {
      return String(s == null ? "" : s).replace(/[&<>"]/g, c => ({"&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;"}[c]));
    }
    on(event, handler) {
      if (!this._events.has(event)) this._events.set(event, new Set());
      this._events.get(event).add(handler);
      return () => this.off(event, handler);
    }
    off(event, handler) {
      if (this._events.has(event)) this._events.get(event).delete(handler);
    }
    emit(event, data) {
      if (this._events.has(event)) {
        this._events.get(event).forEach(fn => {
          try { fn(data); } catch(e) { console.error(`[${this.name}] Event ${event} error:`, e); }
        });
      }
    }
    init() {}
  }

  window.Mice = {Api, Status, TopBar, Partner, Tabs, App, here};
  if (window.miceTheme) window.Mice.theme = window.miceTheme;
  if (window.MiceThemeManager) window.Mice.ThemeManager = window.MiceThemeManager;

  if (document.readyState === "loading")
    document.addEventListener("DOMContentLoaded", TopBar.mountAll);
  else TopBar.mountAll();
})();
