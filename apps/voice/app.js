"use strict";
class VoiceApp {
  constructor() {
    this.$ = id => document.getElementById(id);
    this.rec = null;
    this.ch = null;
    this.convActive = false;
    this.faqs = null;
    this.cfg = null;
    this.convAnalyser = null;
    this.convSession = 0;
    this.convAbort = null;
    this.convHistory = [];
    this.mvTimer = null;
    this.mvBtn = null;
    this.editAt = -1;
    this.seqs = [];
    this.robots = [];
    this.pollTimer = null;
    this.initialized = false;
    this.askLang = "";                    // "" = any language; else the one held to
    this.sheet = [];                      // the answers sheet: [{item, dirty}]
    this.voicesByLang = {};               // every voice per language, from the helper
    this.moveEnabled = true;
    this.globalRobot = "";
    this.currentPerson = "";
    this._faceInterval = null;
    this.CAM_KEY = "mice_voice_camera";   // this browser's own camera choice
    this.camStream = null;
    this.camLoop = null;
    this.camDefaultLabel = "";            // what the face app already saved
    this.camSeconds = 5;                  // config/voice.json face.autoSeconds
    this.camStations = [];                // cameras the face app already watches
    this.camStation = "";                 // the one being read, if any
    this.lookRefused = null;              // {why, detail}: the face app would keep a frame
  }


  // The head's one status line (Mice.Status, mice-ui.js); plain text where the
  // shared parts are not loaded (a check runs this class in node).
  say(msg, kind = "ready", tech = ""){
    const M = globalThis.Mice;
    if (M && M.Status) {
      this.status = this.status || new M.Status("stat");
      return (this.status[kind] || this.status.ready).call(this.status, msg, tech);
    }
    this.$("stat").textContent = msg;
  }

  // Any language, or the one every question is held to (the Language box).
  get autoDetect(){ return !this.askLang; }

  // One look at a time: a slow answer must not pile up behind the timer.
  async pollFace(){
    if (this.facePolling || !this.facesOn()) return;
    this.facePolling = true;
    try {
      // With a station picked, ask who THAT camera sees - the face app is
      // already watching it, so Voice reads the result instead of opening
      // a second camera on the same lens.
      const q = this.camStation ? "?camera=" + encodeURIComponent(this.camStation) : "";
      const r = await fetch("/api/voice/face" + q).then(res => res.json()).catch(() => null);
      if (r && r.ok) {
        if (r.off) return this.showFaces(false);  // switched off elsewhere
        this.updateFace(r.person || "");
        if (r.watcher === false) this.startWatcher();
      }
    } catch(e) {
    } finally {
      this.facePolling = false;
    }
  }

  // Use faces (user 2026-10-15: *let me choose to use faces or not*). Off:
  // no camera, no name, no watcher, nothing waited on - the helper answers
  // the plain way. Saved at once as face.on, alone (the helper merges it).
  facesOn(){
    const box = this.$("faceOn");
    return !box || box.checked !== false;
  }

  showFaces(on){
    const box = this.$("faceOn");
    if (box) box.checked = on;
    const tools = this.$("faceTools");
    if (tools) tools.hidden = !on;
    if (on) return;
    if (this.camLoop) { clearInterval(this.camLoop); this.camLoop = null; }
    ["autoFace", "camShow"].forEach(id => { const b = this.$(id); if (b) b.checked = false; });
    this.stopImg();
    this.closeCam();
    this.updateFace("");
  }

  async toggleFaces(){
    const on = this.facesOn();
    this.showFaces(on);
    if (this.cfg) (this.cfg.face = this.cfg.face || {}).on = on;
    let r = null;
    try {
      r = await fetch("/api/voice/config", {method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({config: {face: {on}}})});
    } catch (e) { r = null; }
    if (r && r.ok) {
      this.say(on ? "Faces on: people it knows are greeted by name."
                  : "Faces off: no camera and no names — answers come at once.");
      if (on) { this.loadCamera(); this.pollFace(); }
      return;
    }
    this.say(r && r.status === 401 ? "Turning faces on or off needs a login — log in at the top."
                                   : "That did not save — try again.", "warn");
  }

  // Why Voice was slow (user 2026-10-15 *voice checks who it is very slowly,
  // the app does it fast*): with our face watcher not running, each look
  // read the face app's history - 2.5 s a call - instead of its live feed.
  // So the page starts the watcher itself (only ours, never the face app),
  // once per page, and names then arrive as fast as the face app sees them.
  async startWatcher(){
    if (this.watcherAsked) return;
    this.watcherAsked = true;
    let r = null;
    try {
      r = await fetch("/api/faces/start?only=watcher", {method: "POST", cache: "no-store"})
            .then(res => res.json());
    } catch (e) { r = null; }
    if (r && r.ok) return this.say("Names now come straight from the face app's live camera.");
    this.say("Names may show slowly: the face watcher could not be started.", "warn",
             (r && (r.watcherError || r.error || r.detail)) || "no answer");
  }

  updateFace(person){
    this.currentPerson = (person || "").trim();
    const badge = this.$("faceBadge");
    const nameEl = this.$("faceName");
    if (!badge || !nameEl) return;
    badge.classList.toggle("on", !!this.currentPerson);
    nameEl.textContent = this.currentPerson || "nobody I know";
    badge.title = this.currentPerson ? "The face app sees " + this.currentPerson
                                     : "Nobody the face app knows was seen lately";
  }

  // ---- the camera on THIS device -----------------------------------------
  // One frame at a time, sent to /api/voice/identify, which passes it on only
  // to a face app that promises to keep none of it (user 2026-09-18: *do not
  // save the picture of it because it took my rom*); otherwise nothing is sent
  // and the page stops looking. The camera is let go in every exit - a page
  // that leaves the light on looks like it is recording.
  //
  // Which camera is NOT a new setting: the face app already stores an
  // app-wide default as the device LABEL, and this page asks the helper for
  // it (/api/voice/camera). A choice made here is this browser's own
  // override, kept in localStorage, which is how their kiosk does it too.
  // Nothing picked yet: the PC camera the hub shares (config/faces.json
  // "pc:"), so this page never takes the webcam from the face app.
  camPicked(){
    let v = "";
    try { v = localStorage.getItem(this.CAM_KEY) || ""; } catch(e) {}
    if (v) return v;
    const pc = (this.camStations || []).find(s => String(s.dev || "").startsWith("pc:"));
    return pc ? "station:" + pc.id : "";
  }

  async fillCameras(){
    const sel = this.$("camPick");
    // globalThis, not a bare navigator: this class is also loaded outside a
    // browser by a check, where a bare navigator throws on sight.
    const media = globalThis.navigator && globalThis.navigator.mediaDevices;
    if (!sel) return;
    // The picker is ALWAYS there (user 2026-10-15). A phone on plain http
    // has no camera of its own to offer, but the face app's cameras still are.
    let cams = [];
    try {
      if (media && media.enumerateDevices)
        cams = (await media.enumerateDevices()).filter(d => d.kind === "videoinput");
    } catch (e) { cams = []; }
    const want = this.camPicked();
    sel.innerHTML = "";
    const add = (value, text, into) => {
      const o = document.createElement("option");
      o.value = value;
      o.textContent = text;
      if (value === want) o.selected = true;
      (into || sel).appendChild(o);
      return o;
    };
    add("", this.camDefaultLabel
        ? "From the face app: " + this.camDefaultLabel : "Let the computer choose");
    // The cameras the face app is ALREADY watching. Picking one of these
    // opens nothing here: Voice reads what that camera sees, so one camera
    // serves both apps (user 2026-09-18).
    if (this.camStations.length) {
      const g = document.createElement("optgroup");
      g.label = "Cameras the face app watches";
      this.camStations.forEach(s => add("station:" + s.id,
                                        s.name + (s.online ? "" : " (offline)"), g));
      sel.appendChild(g);
    }
    if (cams.length) {
      const g = document.createElement("optgroup");
      g.label = "This device";
      // Labels stay blank until the camera has been allowed once.
      cams.forEach((d, i) => add(d.deviceId, d.label || ("Camera " + (i + 1)), g));
      sel.appendChild(g);
    } else if (!media || !media.getUserMedia) {
      const o = add("", "(this browser can use a camera only on the PC itself)");
      o.disabled = true;
    }
  }

  pickCamera(){
    const sel = this.$("camPick");
    const value = sel ? sel.value : "";
    try { localStorage.setItem(this.CAM_KEY, value); } catch(e) {}
    this.camStation = value.startsWith("station:") ? value.slice(8) : "";
    const auto = this.$("autoFace");
    if (this.camStation) {
      // Nothing to switch on: that camera is already being watched, and the
      // answer arrives through the face badge on its own.
      this.closeCam();
      if (auto) { auto.checked = false; auto.disabled = true; }
      const s = this.camStations.find(x => x.id === this.camStation);
      this.say("Reading " + ((s && s.name) || this.camStation) +
               " — the face app is watching it, so no camera is opened here.");
      this.pollFace();
      if (this.viewOn()) this.showView();
      return;
    }
    if (auto) auto.disabled = false;
    this.stopImg();
    const was = !!this.camStream;              // swap the camera under a watch
    if (was) this.closeCam();
    if (was && auto && auto.checked) this.openCam().catch(() => {});
    else if (this.viewOn()) this.showView();
  }

  // The live picture (A42-2, user 2026-10-15 *voice does not show the
  // camera*). This device: its own camera, shown here and sent nowhere. A
  // rig camera: the hub's live view of that board, the stream the watcher
  // reads. A face-app station has no address we can show: the line says
  // where its picture is. Hidden tab = nothing streams.
  viewOn(){
    const box = this.$("camShow");
    return !!(box && box.checked);
  }

  async toggleView(){
    const on = this.viewOn();
    try { localStorage.setItem(this.CAM_KEY + "_show", on ? "1" : ""); } catch(e) {}
    return on ? this.showView() : this.hideView();
  }

  async showView(){
    if (!this.viewOn() || document.hidden) return;
    const vid = this.$("camVid"), img = this.$("camImg"), box = this.$("camBox");
    if (this.camStation) {
      const s = this.camStations.find(x => x.id === this.camStation) || {};
      if (vid) vid.hidden = true;
      if (box) box.hidden = false;
      if (!s.dev) {
        this.stopImg();
        return this.sayCam("This camera belongs to the face app, so its picture shows there — use Open Reconize.");
      }
      this.sayCam("");
      if (!img) return;
      // The PC's own webcam fails for one reason in practice: another app
      // or browser tab holds it (PC, 2026-10-15). A board: the WiFi.
      const pc = String(s.dev).startsWith("pc:"), station = this.camStation;
      img.onerror = () => {
        this.sayCam(pc
          ? "this PC's camera is in use by another app — close the other app or tab using it, and the picture starts by itself"
          : "the picture from this camera did not arrive — is its board on the WiFi?", s.dev);
        // Try again while it is still wanted; the hub spaces its own tries.
        if (pc) setTimeout(() => {
          if (this.viewOn() && this.camStation === station && !document.hidden) this.showView();
        }, 10000);
      };
      img.hidden = false;
      img.src = "/api/dev/cam.stream?dev=" + encodeURIComponent(s.dev);
      return;
    }
    this.stopImg();
    try {
      await this.openCam();
      if (vid) vid.hidden = false;             // already open for Check by itself
      this.sayCam("");
    } catch (e) {
      if (box) box.hidden = false;
      if (vid) vid.hidden = true;              // an empty frame reads as "broken"
      this.sayCam("the camera could not be shown: " + (e.message || e));
    }
  }

  // Off: the board's stream ends (no src = the hub lets the board go) and
  // this device's camera too, unless Check by itself still needs it.
  hideView(){
    this.stopImg();
    if (this.autoFaceOn() && this.camStream) {   // still looking, just not shown
      const vid = this.$("camVid");
      if (vid) vid.hidden = true;
      return;
    }
    this.closeCam();
  }

  stopImg(){
    const img = this.$("camImg");
    if (!img) return;
    img.onerror = null;
    if (typeof img.removeAttribute === "function") img.removeAttribute("src");
    img.hidden = true;
  }

  // Opens the chosen camera, or the one the face app names, or any camera.
  async openCam(){
    if (this.camStream) return this.camStream;
    if (this.camStation)                       // that camera belongs to the face app
      throw new Error("this camera is watched by the face app — its answers arrive on their own");
    const media = globalThis.navigator && globalThis.navigator.mediaDevices;
    if (!media || !media.getUserMedia)
      throw new Error("this browser only allows a camera over https, or on the PC itself");
    let want = this.camPicked();
    if (!want && this.camDefaultLabel) {
      const cams = (await navigator.mediaDevices.enumerateDevices())
                     .filter(d => d.kind === "videoinput");
      const hit = cams.find(d => d.label === this.camDefaultLabel);
      if (hit) want = hit.deviceId;
    }
    // exact: a chosen camera that is unplugged must fail out loud, not open
    // a different one and answer with the wrong room's faces.
    const video = want ? {deviceId: {exact: want}} : {width: 640, height: 480};
    this.camStream = await navigator.mediaDevices.getUserMedia({video});
    const vid = this.$("camVid");
    // The picture shows only with Show the camera ticked (user 2026-10-15:
    // *unticked, why does it still show?*). Check by itself still reads it
    // hidden; the box stays for the line under it.
    this.$("camBox").hidden = false;
    vid.hidden = !this.viewOn();
    vid.srcObject = this.camStream;
    await vid.play();
    await this.fillCameras();                  // labels exist now permission does
    return this.camStream;
  }

  closeCam(){
    if (this.camStream) this.camStream.getTracks().forEach(t => t.stop());
    this.camStream = null;
    const vid = this.$("camVid");
    if (vid) vid.srcObject = null;
    if (this.$("camBox")) this.$("camBox").hidden = true;
  }

  // Grabs one frame and asks who it is. Returns the answer, and never throws.
  async lookOnce(){
    const vid = this.$("camVid");
    const line = this.$("camSay");
    if (!vid || !vid.videoWidth) return {ok: false, error: "the camera is not ready yet"};
    const c = document.createElement("canvas");
    c.width = vid.videoWidth;
    c.height = vid.videoHeight;
    c.getContext("2d").drawImage(vid, 0, 0, c.width, c.height);
    const blob = await new Promise(res => c.toBlob(res, "image/jpeg", 0.9));
    let r;
    try {
      r = await fetch("/api/voice/identify", {method: "POST", body: blob}).then(res => res.json());
    } catch (e) {
      r = {ok: false, error: "the voice helper stopped answering"};
    }
    if (r.wouldKeep) this.refuseLooks(r.error, r.detail);
    if (r.ok && r.person) {
      this.updateFace(r.person);
      if (line) this.sayCam("");
    } else {
      // The badge must agree with the look that just happened: it used to
      // keep showing the last name while this line said the frame was empty.
      this.updateFace("");
      this.sayCam(r.error || "nobody I know is in front of the camera",
                  r.detail, r.canStart);
    }
    return r;
  }

  // The face app would store every frame, so no frame is taken at all: the
  // looping stops and the camera is let go until the page is opened again.
  refuseLooks(why, detail){
    this.lookRefused = {why: why || "the face app would keep the picture", detail: detail || ""};
    if (this.camLoop) { clearInterval(this.camLoop); this.camLoop = null; }
    const auto = this.$("autoFace");
    if (auto) auto.checked = false;
    // A picture only SHOWN here goes nowhere, so a view asked for stays.
    if (!this.viewOn()) this.closeCam();
  }

  // The one line under the camera. Plain words on the surface; the address or
  // the WinError behind the technical switch, which is the rule every page
  // here follows. A face app that is merely SILENT gets a button, because
  // starting it is the fix and nobody should have to find a folder for it.
  sayCam(text, detail, canStart){
    const line = this.$("camSay");
    if (!line) return;
    line.textContent = text || "";
    if (detail) {
      const t = document.createElement("span");
      t.className = "tech";
      t.textContent = " (" + detail + ")";
      line.appendChild(t);
    }
    if (!canStart) return;
    const b = document.createElement("button");
    b.className = "secondary mini";
    b.id = "btnStartFace";
    b.style.cssText = "margin-left:8px;padding:2px 8px;font-size:12px";
    b.textContent = "Start the face app";
    b.onclick = () => this.startFaceApp();
    line.appendChild(b);
  }

  // Starts the face app in the background and looks again when it answers.
  // No tab is opened: the person asked who they are, not to be sent to
  // another app (openReconize is the button for that).
  async startFaceApp(){
    const b = this.$("btnStartFace");
    if (b) b.disabled = true;
    const until = Date.now() + 120000;         // a cold face model is slow
    try {
      while (true) {
        const got = await fetch("/api/partners/start?id=reconize",
                                {method: "POST", cache: "no-store"}).then(r => r.json());
        if (got.need_login) throw new Error("the face app starts only on this PC, or after signing in");
        if (!got.ok) throw new Error(got.error || "the face app could not be started");
        if (got.ready) break;
        this.sayCam("Starting the face app… about fifteen seconds");
        if (Date.now() > until) throw new Error("the face app is taking too long to start");
        await new Promise(res => setTimeout(res, 2000));
      }
      this.sayCam("Looking…");
      const r = await this.lookOnce();
      if (r.ok && r.person) this.say("Hello " + r.person);
    } catch (e) {
      this.sayCam(e.message || String(e));
    }
  }

  // The button: look once, say hello, put the camera away again.
  async whoAmI(){
    const btn = this.$("btnWhoAmI");
    const line = this.$("camSay");
    if (btn) btn.disabled = true;
    try {
      if (this.camStation) {                  // that camera is already watched
        await this.pollFace();
        this.say(this.currentPerson
                 ? "Hello " + this.currentPerson
                 : "that camera has not seen anyone it knows in the last two minutes");
        return;
      }
      if (this.lookRefused) {                 // it would only be kept - do not open
        // Ask what the face app's OWN camera sees instead: that answer is
        // live with the watcher up, and sends no picture (A42-4).
        await this.pollFace();
        if (this.currentPerson) return this.say("Hello " + this.currentPerson);
        this.say(this.lookRefused.why, "warn", this.lookRefused.detail);
        return this.sayCam(this.lookRefused.why, this.lookRefused.detail);
      }
      const fresh = !this.camStream;
      await this.openCam();
      if (line) line.textContent = "Look at the camera…";
      // A frame grabbed the instant a camera opens is dark, and a dark frame
      // holds no face. Only a camera that was just opened needs this wait.
      if (fresh) await new Promise(res => setTimeout(res, 1000));
      if (line) line.textContent = "Looking…";
      const r = await this.lookOnce();
      if (r.ok && r.person) this.say("Hello " + r.person);
    } catch (e) {
      if (line) line.textContent = "the camera could not be used: " + (e.message || e);
    } finally {
      if (!this.autoFaceOn() && !this.viewOn()) this.closeCam();
      if (btn) btn.disabled = false;
    }
  }

  autoFaceOn(){
    const box = this.$("autoFace");
    return !!(box && box.checked);
  }

  // Keeps looking by itself, every `seconds` from config/voice.json. It stops
  // while the tab is hidden: a camera running behind another window is both a
  // surprise and a flat battery.
  async toggleAutoFace(){
    const on = this.autoFaceOn();
    try { localStorage.setItem(this.CAM_KEY + "_auto", on ? "1" : ""); } catch(e) {}
    if (this.camLoop) { clearInterval(this.camLoop); this.camLoop = null; }
    if (!on) return this.viewOn() ? this.showView() : this.closeCam();
    if (this.lookRefused) {
      this.$("autoFace").checked = false;
      return this.sayCam(this.lookRefused.why, this.lookRefused.detail);
    }
    try {
      await this.openCam();
    } catch (e) {
      const line = this.$("camSay");
      if (line) line.textContent = "the camera could not be used: " + (e.message || e);
      this.$("autoFace").checked = false;
      return;
    }
    await new Promise(res => setTimeout(res, 1000));
    await this.lookOnce();
    const every = Math.max(2, Number(this.camSeconds || 5)) * 1000;
    this.camLoop = setInterval(() => {
      if (document.hidden || !this.camStream) return;
      this.lookOnce();
    }, every);
  }

  // What the helper says about the camera: the face app's default, and how
  // often to look. Both are data - neither is written into this page.
  async loadCamera(){
    try {
      const r = await fetch("/api/voice/camera").then(res => res.json());
      if (!r || !r.ok) return;
      if (r.on === false) return this.showFaces(false);   // no camera restored
      this.camDefaultLabel = r.label || "";
      this.camSeconds = r.seconds || 5;
      this.camStations = r.stations || [];
      if (r.look && r.look.ok === false) this.refuseLooks(r.look.why, r.look.detail);
      const picked = this.camPicked();
      this.camStation = picked.startsWith("station:") ? picked.slice(8) : "";
      const box = this.$("autoFace");
      if (this.camStation && box) box.disabled = true;
      let want = "";
      try { want = localStorage.getItem(this.CAM_KEY + "_auto") || ""; } catch(e) {}
      if (box && want && !box.checked) { box.checked = true; this.toggleAutoFace(); }
      let show = "";
      try { show = localStorage.getItem(this.CAM_KEY + "_show") || ""; } catch(e) {}
      const view = this.$("camShow");
      if (view && show && !view.checked) { view.checked = true; this.showView(); }
      this.fillCameras();
    } catch (e) {}
  }

  // Starts Reconize if silent, then opens its camera page so a face reaches
  // the badge above. Addresses come from config/partners.json, never this file.
  // The tab opens inside the click: one opened after the wait is a blocked pop-up.
  async openReconize(){
    const btn = this.$("btnOpenReconize");
    const tab = window.open("about:blank", "_blank");
    if (btn) btn.disabled = true;
    try {
      const all = await fetch("/api/partners", {cache: "no-store"}).then(r => r.json());
      const links = (all.partners || {}).reconize;
      if (!links) throw new Error("config/partners.json has no reconize entry");
      let got = null;
      const until = Date.now() + 120000;          // a cold face model is slow
      while (true) {
        got = await fetch("/api/partners/start?id=reconize", {method: "POST", cache: "no-store"}).then(r => r.json());
        if (got.need_login) throw new Error("Reconize starts only from this PC, or after signing in on the hub");
        if (!got.ok) throw new Error(got.error || "Reconize could not be started");
        if (got.ready) break;
        this.say("Starting face recognition… about fifteen seconds");
        if (Date.now() > until) throw new Error("Reconize is taking too long to start");
        await new Promise(res => setTimeout(res, 2000));
      }
      const url = new URL((got.open || links.open) + (links.camera || ""));
      // From a phone, "localhost" is the phone itself: use the hub's host.
      if (["localhost", "127.0.0.1"].includes(url.hostname) && !["localhost", "127.0.0.1", "[::1]"].includes(location.hostname))
        url.hostname = location.hostname;
      if (tab && !tab.closed) tab.location.href = url.href;
      else window.open(url.href, "_blank");
      this.say("Face recognition is open. Turn on the camera there and look at it.");
      this.pollFace();
    } catch (e) {
      if (tab && !tab.closed) tab.close();
      this.say("Could not open face recognition: " + (e.message || e));
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  detectLang(text){
    for (const ch of text || "") {
      const cp = ch.codePointAt(0);
      if (cp >= 0x0E00 && cp <= 0x0E7F) return "th";
      if ((cp >= 0x3040 && cp <= 0x309F) || (cp >= 0x30A0 && cp <= 0x30FF)) return "ja";
      if (cp >= 0x4E00 && cp <= 0x9FFF) return "zh";
    }
    for (const ch of text || "") {
      if ((ch >= "a" && ch <= "z") || (ch >= "A" && ch <= "Z")) return "en";
    }
    return "th";
  }

  async load(){
  this.$("retry").hidden = true;
  this.$("down").hidden = true;
  this.$("ready").hidden = true;
  this.say("checking the voice helper…", "loading");
  let r;
  try {
    r = await fetch("/api/voice/health").then(r => r.json());
  } catch(e) { return this.down("The hub did not answer."); }
  if (!r.ok) return this.down(this.human(r.error));
  this.$("down").hidden = true;
  this.$("ready").hidden = false;
  this.$("settings").hidden = false;        // settings exist only while helper runs
  if (this.cfg === null) this.loadStores();
  this.fillCameras();
  const p = r.parts || {};
  this.updateParts(p);
  this.showVoice(r.voice);

  // If LLM is configured but not yet loaded, auto-trigger background preload
  if (p.llm && p.llm.includes("first needed") && p.llm !== "off in config/voice.json") {
    fetch("/api/voice/preload", {method: "POST"}).catch(() => {});
    p.llm = "loading in background…";
    this.updateParts(p);
  }

  // Poll status while loading
  if ((p.llm && p.llm.includes("loading")) || (p.stt && p.stt.includes("loading"))) {
    this.startHealthPolling();
  } else {
    this.stopHealthPolling();
  }

  // Conversation mode needs STT; show it when speech-in is loaded or loading.
  const sttOk = p.stt && p.stt !== "off in config/voice.json"
                && !p.stt.startsWith("could not");
  this.$("convStart").hidden = !sttOk;
  this.say("ready — ask a question");
}

  // The line that says the PC's flat voice is speaking instead of the
  // natural one, and why. Hidden while the natural voice speaks.
  showVoice(v){
  const line = this.$("voiceWarn");
  if (!line) return;
  if (!v || v.natural !== false) { line.hidden = true; return; }
  line.hidden = false;
  line.textContent = "⚠ Speaking with this PC's backup voice, which sounds flat: "
                   + (v.why || "the natural voice did not answer") + ".";
  if (v.tech) {
    const t = document.createElement("span");
    t.className = "tech";
    t.textContent = " (" + v.tech + ")";
    line.appendChild(t);
  }
}

  async checkVoice(){
  try {
    const r = await fetch("/api/voice/health").then(res => res.json());
    this.showVoice(r && r.voice);
  } catch (e) {}
}

  updateParts(p){
  window._parts = p;
  const partsEl = this.$("parts");
  if (partsEl) {
    // Plain words on the surface; the helper's own lines behind the switch.
    const word = s => !s ? "?" : /^off/.test(s) ? "off" : /loading/.test(s) ? "loading…"
                     : /could not|no voice/.test(s) ? "has a problem"
                     : /loaded|speaking/.test(s) ? "ready" : "waits for the first question";
    partsEl.textContent = (p.faq || "?") + " · listening " + word(p.stt)
                        + " · speaking " + word(p.tts) + " · AI " + word(p.llm);
    const t = document.createElement("span");
    t.className = "tech";
    t.textContent = " (listening: " + (p.stt || "?") + "; speaking: " + (p.tts || "?")
                  + "; AI: " + (p.llm || "?") + ")";
    partsEl.appendChild(t);
  }
  const btnLoad = this.$("btnLoadModel");
  const btnUnload = this.$("btnUnloadModel");
  const isLoaded = p.llm === "loaded";
  const isLoading = (p.llm && p.llm.includes("loading")) || (p.stt && p.stt.includes("loading"));
  if (btnLoad && btnUnload) {
    btnLoad.style.display = "";
    btnUnload.style.display = "";
    if (isLoading) {
      btnLoad.disabled = true;
      btnLoad.textContent = "Loading…";
      btnUnload.disabled = true;
      btnUnload.textContent = "Unload the AI";
    } else if (isLoaded) {
      btnLoad.disabled = true;
      btnLoad.textContent = "AI loaded";
      btnUnload.disabled = false;
      btnUnload.textContent = "Unload the AI";
    } else {
      btnLoad.disabled = false;
      btnLoad.textContent = "Load the AI";
      btnUnload.disabled = true;
      btnUnload.textContent = "Unload the AI";
    }
  }
}

  async startVoiceService(){
    const btn = this.$("btnStartVoice");
    const stat = this.$("downStat");
    if (btn) btn.disabled = true;
    if (stat) stat.textContent = "starting helper…";
    try {
      const r = await fetch("/api/voice/start", {method: "POST"}).then(res => res.json());
      if (r && r.ok) {
        if (stat) stat.textContent = "helper started, connecting…";
        for (let i = 0; i < 10; i++) {
          await new Promise(res => setTimeout(res, 1000));
          try {
            const h = await fetch("/api/voice/health").then(res => res.json());
            if (h && h.ok) {
              this.load();
              return;
            }
          } catch(e) {}
        }
      } else {
        if (stat) stat.textContent = (r && r.error) ? r.error : "could not start helper";
      }
    } catch(e) {
      if (stat) stat.textContent = "could not reach hub to start helper";
    } finally {
      if (btn) btn.disabled = false;
    }
  }

  startHealthPolling(){
  if (this.pollTimer) return;
  this.pollTimer = setInterval(async () => {
    try {
      const r = await fetch("/api/voice/health").then(res => res.json());
      if (r && r.ok && r.parts) {
        this.updateParts(r.parts);
        const stillLoading = (r.parts.llm && r.parts.llm.includes("loading")) ||
                             (r.parts.stt && r.parts.stt.includes("loading"));
        if (!stillLoading) {
          this.stopHealthPolling();
        }
      }
    } catch(e) {
      this.stopHealthPolling();
    }
  }, 1500);
}

  stopHealthPolling(){
  if (this.pollTimer) {
    clearInterval(this.pollTimer);
    this.pollTimer = null;
  }
}

  async loadModel(){
  const btnLoad = this.$("btnLoadModel");
  if (btnLoad) {
    btnLoad.disabled = true;
    btnLoad.textContent = "Loading…";
  }
  try {
    await fetch("/api/voice/preload", {method: "POST"}).then(r => r.json());
  } catch(e) {}
  this.startHealthPolling();
  const r = await fetch("/api/voice/health").then(res => res.json()).catch(() => null);
  if (r && r.parts) this.updateParts(r.parts);
}

  async unloadModel(){
  this.stopHealthPolling();
  const btnUnload = this.$("btnUnloadModel");
  if (btnUnload) {
    btnUnload.disabled = true;
    btnUnload.textContent = "Unloading…";
  }
  try {
    await fetch("/api/voice/unload", {method: "POST"}).then(r => r.json());
  } catch(e) {}
  const r = await fetch("/api/voice/health").then(res => res.json()).catch(() => null);
  if (r && r.parts) this.updateParts(r.parts);
}

  down(why){
  this.say("the voice helper is off", "warn");
  this.$("down").hidden = false;
  this.$("retry").hidden = false;
  if (!this.$("down").querySelector(".why")) {
    const w = document.createElement("p");
    w.className = "why mini";
    this.$("down").prepend(w);
  }
  this.$("down").querySelector(".why").textContent = why || "";
}

// The helper's errors arrive in plain words already — show them as they are,
// only falling back when something answered without one.
  human(err){
  if (!err) return "";
  if (/not running|helper/.test(err)) return "";   // the down-card says it better
  return err;
}

  addMessageToLog(role, text, meta = {}){
  const logDiv = this.$("convLog");
  if (!logDiv) return null;
  const bubble = document.createElement("div");
  if (role === "user") {
    bubble.className = "bubble-user";
    const lbl = document.createElement("div");
    lbl.className = "role";
    const speaker = (meta.person || this.currentPerson || "").trim();
    lbl.textContent = speaker ? `${speaker} asked:` : "Person asked:";
    const body = document.createElement("div");
    body.className = "text";
    body.textContent = text;
    bubble.appendChild(lbl);
    bubble.appendChild(body);
  } else {
    bubble.className = "bubble-ai";
    const hdr = document.createElement("div");
    hdr.className = "hdr";
    const lbl = document.createElement("span");
    lbl.className = "role";
    lbl.textContent = "Rig / Mice:";
    hdr.appendChild(lbl);
    if (meta.source || meta.flag) {
      const badge = document.createElement("span");
      badge.className = "badge";
      const srcText = meta.source === "faq"
        ? "from saved answers · instant"
        : (meta.source === "error" ? "error" : "from local model");
      badge.textContent = (meta.flag ? meta.flag + " · " : "") + srcText;
      hdr.appendChild(badge);
    }
    const body = document.createElement("div");
    body.className = "text";
    body.textContent = text;
    bubble.appendChild(hdr);
    bubble.appendChild(body);
  }
  logDiv.appendChild(bubble);
  return bubble;
}

  scrollConv(target){
  const logDiv = this.$("convLog");
  if (!logDiv) return;
  if (target && typeof target.scrollIntoView === "function") {
    try {
      target.scrollIntoView({behavior: "smooth", block: "nearest"});
      return;
    } catch(e) {}
  }
  if (typeof logDiv.scrollHeight === "number") {
    logDiv.scrollTop = logDiv.scrollHeight;
  }
}

  async talk(){
  if(this.rec && this.rec.state==="recording") return this.rec.stop();
  try {
    const s = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    });
    this.rec = new MediaRecorder(s);
    this.ch = [];
    this.rec.ondataavailable = e => this.ch.push(e.data);
    this.rec.onstop = async () => {
      this.$("talk").textContent = "🎙 Press to talk";
      this.$("wait").textContent = "sending…";
      s.getTracks().forEach(t => t.stop());
      try {
        const langParam = this.autoDetect ? "auto" : this.askLang;
        const r = await fetch("/api/voice/transcribe?lang=" + encodeURIComponent(langParam), {
          method: "POST",
          body: new Blob(this.ch)
        }).then(r => r.json());
        if(r.ok) { 
          this.$("q").value = r.text; 
          this.$("wait").textContent = "";
          this.ask(r.language);
        }
        else this.$("wait").textContent = r.error || "That did not work.";
      } catch(e) { this.$("wait").textContent = "The voice helper stopped answering."; }
    };
    this.rec.start();
    this.$("talk").textContent = "■ Stop recording";
    this.$("wait").textContent = "listening…";
  } catch(e) { this.$("wait").textContent = "No microphone."; }
}

// ---- Conversation mode (A26-11) ----------------------------------------
// listen -> transcribe -> ask -> speak -> listen again, until the visitor
// stops it. Reuses the same endpoints as push-to-talk; the service itself
// never sees "conversation" - it stays stateless.



// Silence detection: reads time-domain samples from the analyser, centers
// them (silence is ~128, not 0), and returns true when rms is below 1%.
  convRms(){
  if (!this.convAnalyser) return false;
  const buf = new Uint8Array(this.convAnalyser.frequencyBinCount);
  this.convAnalyser.getByteTimeDomainData(buf);
  let sum = 0;
  for (let i = 0; i < buf.length; i++) {
    const c = (buf[i] / 128.0) - 1.0;   // center to [-1, 1]
    sum += c * c;
  }
  const rms = Math.sqrt(sum / buf.length);
  return rms < 0.01;
}

// Records for up to durationMs, or until sustained silence after speech
// begins. Cleanup of stream + AudioContext is local so Stop mid-recording
// never throws.
  async convRecord(stream, ctx, analyser, durationMs){
  const rec = new MediaRecorder(stream);
  const chunks = [];
  const mySession = this.convSession;
  rec.ondataavailable = e => chunks.push(e.data);
  let resolve;
  const p = new Promise(r => { resolve = r; });
  rec.onstop = () => resolve(new Blob(chunks));
  rec.start();

  let sawSpeech = false;
  let silenceMs = 0;
  const tick = () => {
    if (!this.convActive || this.convSession !== mySession) {
      if (rec.state === "recording") rec.stop();
      return;
    }
    if (this.convActive && rec.state === "recording") {
      if (this.convRms()) {
        if (sawSpeech) silenceMs += 200;
        if (silenceMs >= 1000 || silenceMs >= durationMs) {
          rec.stop(); return;
        }
      } else {
        sawSpeech = true;
        silenceMs = 0;
      }
      setTimeout(tick, 200);
    }
  };
  setTimeout(() => {
    if (rec.state === "recording") rec.stop();
  }, durationMs);
  tick();
  return p;
}

  async convListenOnce(){
  let stream, ctx, analyser, source;
  const mySession = this.convSession;
  try {
    stream = await navigator.mediaDevices.getUserMedia({
      audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true }
    });
    if (this.convSession !== mySession || !this.convActive) {
      stream.getTracks().forEach(t => t.stop()); return null;
    }
    ctx = new (window.AudioContext || window.webkitAudioContext)();
    analyser = ctx.createAnalyser();
    analyser.fftSize = 512;
    source = ctx.createMediaStreamSource(stream);
    source.connect(analyser);
    this.convAnalyser = analyser;     // silence detection reads from here

    const blob = await this.convRecord(stream, ctx, analyser, 8000);
    if (this.convSession !== mySession || !this.convActive) return null;
    return blob;
  } finally {
    // Always clean up mic + audio graph, even if Stop was hit mid-await
    this.convAnalyser = null;
    if (stream) stream.getTracks().forEach(t => t.stop());
    if (source) source.disconnect();
    if (ctx) ctx.close();
  }
}

  async startConv(){
  if (this.convActive) return;
  const mySession = this.convSession;
  this.convActive = true;
  this.convSession++;                       // fresh session: invalidates stale loops
  if (this.convSession !== mySession + 1) return this.convActive = false;
  if (this.convAbort) this.convAbort.abort();
  this.convAbort = new AbortController();
  const signal = this.convAbort.signal;
  this.$("convStart").hidden = true;
  this.$("convStop").hidden = false;
  this.$("talk").hidden = true;
  this.say("conversation on — speak");
  this.convHistory = [];

  while (this.convActive) {
    await this.rigQuiet(signal);
    if (!this.convActive || this.convSession !== mySession + 1) break;
    const heardFrom = Date.now();
    const blob = await this.convListenOnce();
    if (!blob || !this.convActive || this.convSession !== mySession + 1) break;
    if (await this.rigSpokeWithin(Date.now() - heardFrom + 500)) {
      this.say("the robot was talking - listening again");
      continue;
    }

    // 1. Transcribe
    this.$("wait").textContent = "listening…";
    let r;
    try {
      const langParam = this.autoDetect ? "auto" : this.askLang;
      r = await fetch("/api/voice/transcribe?lang=" + encodeURIComponent(langParam), {
              method:"POST", body:blob, signal}).then(r=>r.json());
    } catch(e) {
      if (e.name === "AbortError") break;
      this.say("The voice helper stopped answering.");
      this.stopConv(); break;
    }
    if (!this.convActive || this.convSession !== mySession + 1) break; // Stop during transcription

    if (!r.ok) {
      if (r.error) this.say(r.error);
      continue;
    }
    const text = r.text;
    if (!text) { this.say("no words heard — try again"); continue; }
    const detectedLang = (r.language && ["th", "en", "ja", "zh"].includes(r.language))
      ? r.language
      : this.detectLang(text);

    // 2. Show the question
    this.$("q").value = text;
    
    this.$("answerCard").hidden = false;
    let uBubble = this.addMessageToLog("user", text);
    this.scrollConv(uBubble);

    // 3. Ask
    this.$("wait").textContent = "thinking…";
    let a;
    try {
      const payload = {text: text, history: this.convHistory};
      if (this.currentPerson) {
        payload.person = this.currentPerson;
      }
      if (!this.autoDetect) {
        payload.autoDetect = false;
        payload.lang = this.askLang;
      } else if (detectedLang) {
        payload.lang = detectedLang;
      }
      a = await fetch("/api/voice/ask", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify(payload),
        signal,
      }).then(r => r.json());
    } catch(e) {
      if (e.name === "AbortError") break;
      this.say("The voice helper stopped answering.");
      this.stopConv(); break;
    }
    if (!this.convActive || this.convSession !== mySession + 1) break; // Stop during answer

    if (!a.ok) {
      if (a.error) this.say(a.error);
      continue;
    }

    if (a.person) {
      this.updateFace(a.person);
    }

    // 4. Show answer
    this.$("answerCard").hidden = false;
    this.$("answer").textContent = a.answer;
    const langFlags = {th: "TH", en: "EN", ja: "JA", zh: "ZH"};
    const flag = langFlags[a.lang || ""] || "";
    this.$("source").textContent = (a.source === "faq"
      ? "from the saved answers · instant"
      : "from the local model") + (flag ? " · " + flag : "");

    // 5. Speak and move concurrently (do not wait for speech to finish before moving)
    const tasks = [];
    const aHasMove = (a.move && a.module) || (Array.isArray(a.moves) && a.moves.length);
    if (aHasMove && (!this.$("moveOn") || this.$("moveOn").checked)) {
      const aBot = a.module || (a.moves && a.moves[0] && a.moves[0].module);
      if (aBot) {
        this.findRobot(aBot).then(bot => {
          if (bot && bot.dev) {
            fetch("/api/stream/voice", {
              method: "POST",
              headers: {"Content-Type": "application/json"},
              body: JSON.stringify({text: a.answer, dev: bot.dev})
            }).catch(e => console.log(e));
          }
        }).catch(() => {});
      }
      tasks.push(this.doMove(a));
    }
    if (this.$("sound").checked) {
      const convSpeakLang = this.autoDetect ? (a.lang || detectedLang) : this.askLang;
      tasks.push(this.speakAndWait(a.answer, convSpeakLang, signal));
    }
    if (tasks.length) await Promise.all(tasks);
    if (!this.convActive || this.convSession !== mySession + 1) break;

    if (this.$("sound").checked) {
      // Cooldown: let the speaker finish and the room quiet down before
      // listening again. This prevents the assistant's own voice from being
      // captured as a new question. Abortable on Stop.
      await new Promise(r => {
        if (!this.convActive || this.convSession !== mySession + 1) return r();
        const t = setTimeout(r, 800);
        if (signal) signal.addEventListener("abort", () => { clearTimeout(t); r(); }, {once: true});
      });
      if (!this.convActive || this.convSession !== mySession + 1) break;
    }

    // 6. Track history for context (keep last 16 messages)
    this.convHistory.push({role:"user", content:text});
    this.convHistory.push({role:"assistant", content:a.answer});
    if (this.convHistory.length > 16) this.convHistory = this.convHistory.slice(-16);

    // Update conversation log UI
    this.addMessageToLog("assistant", a.answer, {source: a.source, flag: flag});
    this.scrollConv(uBubble);

    if (this.convActive) this.say("conversation — keep talking");
  }

  // Session ended: restore UI (only if this session is still current)
  if (this.convSession !== mySession + 1) return;
  const p = window._parts || {};
  const sttOk = p.stt && p.stt !== "off in config/voice.json"
                && !p.stt.startsWith("could not");
  this.$("convStart").hidden = !sttOk;
  this.$("convStop").hidden = true;
  this.$("talk").hidden = false;
}

  stopConv(){
  this.convActive = false;
  this.convSession++;                       // invalidate any in-flight loop
  if (this.convAbort) { this.convAbort.abort(); this.convAbort = null; }
  const p = window._parts || {};
  const sttOk = p.stt && p.stt !== "off in config/voice.json"
                && !p.stt.startsWith("could not");
  this.$("convStart").hidden = !sttOk;
  this.$("convStop").hidden = true;
  this.$("talk").hidden = false;
  this.say("conversation off");
}

  async ask(explicitLang = ""){
  const text = this.$("q").value.trim();
  if (!text) { this.$("q").focus(); return; }
  const detectedLang = explicitLang || this.detectLang(text);
  this.$("answerCard").hidden = false;
  const uBubble = this.addMessageToLog("user", text);
  this.scrollConv(uBubble);
  this.$("q").value = "";

  const isLlmLoaded = window._parts && window._parts.llm === "loaded";
  const isLlmLoading = window._parts && window._parts.llm && window._parts.llm.includes("loading");
  this.$("wait").textContent = isLlmLoading
    ? "waiting for model to finish loading…"
    : (isLlmLoaded ? "thinking…" : "thinking — loading model…");
  try {
    const payload = {text: text, history: this.convHistory};
    if (this.currentPerson) {
      payload.person = this.currentPerson;
    }
    if (!this.autoDetect) {
      payload.autoDetect = false;
      payload.lang = this.askLang;
    } else if (explicitLang) {
      payload.lang = explicitLang;
    }
    const r = await fetch("/api/voice/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
    }).then(r => r.json());
    if (!r.ok) {
      this.$("answerCard").hidden = false;
      const errMsg = r.error || "That did not work — try again.";
      this.$("answer").textContent = errMsg;
      this.$("source").textContent = "";
      this.addMessageToLog("assistant", errMsg, {source: "error"});
      this.scrollConv(uBubble);
    } else {
      if (r.person) {
        this.updateFace(r.person);
      }
      this.$("answerCard").hidden = false;
      this.$("answer").textContent = r.answer;
      const langFlags = {th: "TH", en: "EN", ja: "JA", zh: "ZH"};
      const flag = langFlags[r.lang || ""] || "";
      this.$("source").textContent = (r.source === "faq"
        ? "from the saved answers · instant"
        : "from the local model") + (flag ? " · " + flag : "");

      // Update conversation history
      this.convHistory.push({role:"user", content:text});
      this.convHistory.push({role:"assistant", content:r.answer});
      if (this.convHistory.length > 16) this.convHistory = this.convHistory.slice(-16);

      this.addMessageToLog("assistant", r.answer, {source: r.source, flag: flag});
      this.scrollConv(uBubble);

      // Speak and move concurrently (do not wait for speech to finish before moving)
      const tasks = [];
      const hasMove = (r.move && r.module) || (Array.isArray(r.moves) && r.moves.length);
      if (hasMove && (!this.$("moveOn") || this.$("moveOn").checked)) {
        const primaryBot = r.module || (r.moves && r.moves[0] && r.moves[0].module);
        if (primaryBot) {
          this.findRobot(primaryBot).then(bot => {
            if (bot && bot.dev) {
              fetch("/api/stream/voice", {
                method: "POST",
                headers: {"Content-Type": "application/json"},
                body: JSON.stringify({text: r.answer, dev: bot.dev})
              }).catch(e => console.log(e));
            }
          }).catch(() => {});
        }
        tasks.push(this.doMove(r));
      }
      if (this.$("sound").checked) {
        const speakLang = this.autoDetect ? (r.lang || explicitLang || detectedLang) : this.askLang;
        tasks.push(this.speak(r.answer, speakLang));
      }
      if (tasks.length) await Promise.all(tasks);
    }
  } catch(e) {
    this.$("answerCard").hidden = false;
    const errMsg = "The voice helper stopped answering. Is it still running?";
    this.$("answer").textContent = errMsg;
    this.$("source").textContent = "";
    this.addMessageToLog("assistant", errMsg, {source: "error"});
    this.scrollConv(uBubble);
  }
  this.$("wait").textContent = "";
}

// The rig speaks the answer out loud (A20-9). The helper returns sound
// bytes; the checkbox remembers itself, because a visitor who muted it once
// should not have to again.
// THE HELPER PICKS THE VOICE (A42-1): the page used to send the language's
// own voice with every answer, which skipped the scenario's voice, the
// one-voice-for-everything and the voice for a two-language line. Only Try
// sends `try_` = {voice, speed, pitch}: a choice heard before it is saved.
  async speak(text, lang, try_ = null){
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(Object.assign({text: text, lang: lang || ""}, try_ || {})),
    });
    if (!r.ok) { this.$("wait").textContent = (await r.json()).error; this.$("speakingNow").hidden = true; return; }
    // MP3 = the natural voice spoke; a WAV = the PC's flat stand-in, and
    // the helper says why (A42-2).
    const kind = (r.headers && r.headers.get && r.headers.get("Content-Type")) || "";
    if (kind.includes("mpeg")) this.showVoice({natural: true});
    else if (kind.includes("wav")) this.checkVoice();
    const url = URL.createObjectURL(await r.blob());
    const player = new Audio(url);
    player.onended = () => { URL.revokeObjectURL(url); this.$("wait").textContent = ""; this.$("speakingNow").hidden = true; };
    try {
      await player.play();
    } catch(e) {
      // The browser allows sound only shortly after a click, and a long
      // model answer can outlive it. Offer the click instead of muting.
      this.$("wait").textContent = "";
      const again = document.createElement("button");
      again.textContent = "▶ Play the answer";
      again.onclick = () => { again.remove(); player.play()
                                .catch(() => { this.$("wait").textContent =
                                  "The sound could not play."; this.$("speakingNow").hidden = true; }); };
      player.onended = () => { again.remove(); this.$("wait").textContent = ""; this.$("speakingNow").hidden = true; };
      this.$("wait").appendChild(again);
    }
  } catch(e) {
    this.$("wait").textContent = "The sound could not play.";
    this.$("speakingNow").hidden = true;
  }
}

// What the rig's ONE speaking queue is doing (hub_speak.py, A4-4): a greeting
// or this page's own answer through a robot plays there, not in this browser,
// so the page cannot hear it end. null = unknown (not logged in, older hub).
  async rigSpeech(){
  try {
    const r = await fetch("/api/speak", {cache: "no-store"});
    return r.ok ? await r.json() : null;
  } catch (e) { return null; }
}

// Before listening again: wait while the rig is talking, or the microphone
// takes the rig's own words as the next question. Gives up after maxMs.
  async rigQuiet(signal, maxMs = 30000){
  const until = Date.now() + maxMs;
  while (Date.now() < until && !(signal && signal.aborted)) {
    const st = await this.rigSpeech();
    if (!st || !st.speaking) return;
    this.$("wait").textContent = "waiting for the robot to finish…";
    await new Promise(r => setTimeout(r, 300));
  }
}

// After a recording: did the rig talk while it ran? Then it holds the rig's
// voice, not the visitor's, and is thrown away.
  async rigSpokeWithin(ms){
  const st = await this.rigSpeech();
  return !!st && (st.speaking || (st.quietFor !== null && st.quietFor * 1000 < ms));
}

// Like this.speak(), but resolves only when playback finishes (onended).
// Used in the conversation loop so we don't listen again until the
// answer has fully played - prevents the assistant's voice being
// captured as a new question.
  async speakAndWait(text, langOrSignal, maybeSignal, maybeVoice){
  let lang = "";
  let signal = null;
  let voice = maybeVoice || "";
  if (langOrSignal && typeof langOrSignal === "object" && "aborted" in langOrSignal) {
    signal = langOrSignal;
  } else {
    lang = langOrSignal || "";
    signal = maybeSignal || null;
  }
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(voice ? {text: text, lang: lang || "", voice: voice}
                                 : {text: text, lang: lang || ""}),
      signal,
    });
    if (signal && signal.aborted) { this.$("speakingNow").hidden = true; return; }
    if (!r.ok) { this.$("wait").textContent = (await r.json()).error; this.$("speakingNow").hidden = true; return; }
    const blob = await r.blob();
    if (signal && signal.aborted) { this.$("speakingNow").hidden = true; return; }
    const url = URL.createObjectURL(blob);
    const player = new Audio(url);
    await new Promise((resolve, reject) => {
      const on_abort = () => {
        player.pause(); player.onended = null; player.onerror = null;
        URL.revokeObjectURL(url); this.$("speakingNow").hidden = true; reject(new Error("aborted"));
      };
      if (signal) signal.addEventListener("abort", on_abort, {once: true});
      player.onended = () => { if (signal) signal.removeEventListener("abort", on_abort); URL.revokeObjectURL(url); this.$("speakingNow").hidden = true; resolve(); };
      player.onerror = () => { if (signal) signal.removeEventListener("abort", on_abort); URL.revokeObjectURL(url); this.$("speakingNow").hidden = true; reject(); };
      player.play().catch(() => {
        if (signal) signal.removeEventListener("abort", on_abort);
        URL.revokeObjectURL(url); this.$("speakingNow").hidden = true; reject(new Error("play rejected"));
      });
    });
    this.$("wait").textContent = "";
  } catch(e) {
    this.$("wait").textContent = "";
    this.$("speakingNow").hidden = true;
  }
}

// An answer may name a saved sequence and a module (one line in
// qa_data.json). THIS page drives the show clock, because this page is
// what holds the login - the voice helper never touches it. The move
// starts by itself; Stop sits beside it until the show ends.

// One move on screen at a time: a fresh answer must retire the previous
// Stop and its polling, or intervals stack and two buttons fight.
  mvClear(){
  if (this.mvTimer) { clearInterval(this.mvTimer); this.mvTimer = null; }
  if (this.mvBtn) { this.mvBtn.remove(); this.mvBtn = null; }
}
// A saved answer names its robot by NAME ("Nong"), not by which PC or cable
// it hangs off - so the robot can be moved between PCs without editing
// qa_data.json. This page asks the hub for every robot it can see, right
// now, and matches names case-insensitively.
  async findRobot(name){
  const all = await fetch("/api/modules/all").then(x => x.json()).catch(() => null);
  const mods = (all && all.modules) || [];
  const want = String(name).trim().toLowerCase();
  const bot = mods.find(m => String(m.name || "").trim().toLowerCase() === want) || null;
  // A module row lists every way in (routes); a LIVE one must carry the
  // show - a stale-only row is as good as absent, so the visitor hears
  // "not found" instead of a dead end.
  if (bot) {
    const live = (bot.routes || []).find(rt => !rt.stale) || null;
    bot.dev = live && live.dev;
  }
  return bot;
}

  async doMove(r){
  if (this.$("moveOn") && !this.$("moveOn").checked) return;
  this.mvClear();

  // Determine which robot(s) and move(s) to execute
  const rawMoves = (Array.isArray(r.moves) && r.moves.length > 0)
    ? r.moves.filter(m => m && m.move)
    : ((r.move) ? [{module: r.module, move: r.move}] : []);

  if (!rawMoves.length && !(r.move && r.module)) return;

  const globalRob = this.$("globalRobot") ? this.$("globalRobot").value : "";
  let targetMoves = [];

  if (globalRob === "__all__") {
    // All robots override: run all available robots
    const robotsToRun = (this.robots && this.robots.length > 0) ? this.robots : (r.module ? [r.module] : []);
    targetMoves = robotsToRun.map(botName => {
      const match = rawMoves.find(m => m.module === botName);
      return {module: botName, move: match ? match.move : (r.move || (rawMoves[0] && rawMoves[0].move))};
    }).filter(m => m.move);
  } else if (globalRob) {
    // Single robot override
    const match = rawMoves.find(m => m.module === globalRob);
    const chosenMove = match ? match.move : (r.move || (rawMoves[0] && rawMoves[0].move));
    if (chosenMove) {
      targetMoves = [{module: globalRob, move: chosenMove}];
    }
  } else {
    // Per-answer
    targetMoves = rawMoves;
  }

  if (!targetMoves.length) return;

  let stopped = false;
  this.mvBtn = document.createElement("button");
  this.mvBtn.textContent = "■ Stop the move";
  this.mvBtn.onclick = () => {
    stopped = true;
    this.mvClear();
    fetch("/api/play/stop", {method: "POST"}).catch(() => {});
  };
  this.$("wait").textContent = "";
  this.$("wait").appendChild(this.mvBtn);

  for (let idx = 0; idx < targetMoves.length; idx++) {
    if (stopped) break;
    const item = targetMoves[idx];
    const modName = item.module || r.module;
    const moveName = item.move || r.move;
    if (!moveName) continue;

    const labelPrefix = targetMoves.length > 1 ? `[${idx + 1}/${targetMoves.length}] ` : "";
    this.$("wait").textContent = labelPrefix + "looking for " + modName + "…";
    this.$("wait").appendChild(this.mvBtn);

    try {
      const bot = await this.findRobot(modName);
      if (stopped) break;
      if (!bot || !bot.dev) {
        const all = await fetch("/api/modules/all").then(x => x.json()).catch(() => null);
        const here = (((all && all.modules) || [])
                      .map(m => m.name).filter(Boolean).join(", ")) || "none";
        this.$("wait").textContent = labelPrefix + "No robot named " + modName
                              + " answered just now. Here now: " + here + ".";
        this.$("wait").appendChild(this.mvBtn);
        await new Promise(res => setTimeout(res, 1500));
        continue;
      }

      const st = await fetch("/api/play").then(x => x.json()).catch(() => null);
      if (st && st.running && st.dev === bot.dev) {
        this.$("wait").textContent = labelPrefix + bot.name + " is already moving - ask again once it stops.";
        this.$("wait").appendChild(this.mvBtn);
        await new Promise(res => setTimeout(res, 1500));
        continue;
      }

      this.$("wait").textContent = labelPrefix + "getting the moves…";
      this.$("wait").appendChild(this.mvBtn);
      const s = await fetch("/api/seqsteps?name=" + encodeURIComponent(moveName))
                  .then(x => x.json());
      if (stopped) break;
      if (!s.ok) {
        this.$("wait").textContent = labelPrefix + (s.error || "cannot read that move.");
        this.$("wait").appendChild(this.mvBtn);
        await new Promise(res => setTimeout(res, 1500));
        continue;
      }

      const p = await fetch("/api/play", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({dev: bot.dev, steps: s.steps,
                              loop: s.loop, name: moveName}),
      }).then(x => x.json());
      if (stopped) break;
      if (p.error) {
        this.$("wait").textContent = labelPrefix + p.error;
        this.$("wait").appendChild(this.mvBtn);
        await new Promise(res => setTimeout(res, 1500));
        continue;
      }

      await new Promise(res => {
        const checkInterval = setInterval(async () => {
          if (stopped) {
            clearInterval(checkInterval);
            res();
            return;
          }
          const playSt = await fetch("/api/play").then(x => x.json()).catch(() => null);
          if (!playSt || !playSt.running) {
            clearInterval(checkInterval);
            res();
          }
        }, 500);
      });
    } catch(e) {
      this.$("wait").textContent = labelPrefix + "The robot did not take that move — log in first?";
      this.$("wait").appendChild(this.mvBtn);
      await new Promise(res => setTimeout(res, 1500));
    }
  }
  this.mvClear();
}

// ---- Settings (A20-12; tabs and the answers sheet A42-1). The stores live
// on the brain PC; this page reads them through the hub and saves through the
// same gated doors as everything else that can change the rig. The helper
// picks edits up with no restart.

static MODEL_WORDS = [["base", "Fast"], ["small", "Balanced"],
                     ["medium", "Most accurate"]];

// The languages an answer is written in: [language, the key it is saved
// under]. The store's own shape - service.py reads qa_data.json the same way.
static ANSWER_KEYS = [["th", "answer"], ["en", "answer_en"],
                      ["ja", "answer_ja"], ["zh", "answer_zh"]];

// Which language column a way of asking belongs in, by its letters - the
// helper's own detect_lang (service.py), so the page and the matcher agree.
// The store keeps ONE `questions` list (every reader matches against all of
// it); the sheet only splits it per language (A42-2, user 2026-10-15).
static askLang(text){
  let kana = false, han = false, latin = false;
  for (const ch of String(text || "")) {
    const cp = ch.codePointAt(0);
    if (cp >= 0x0E00 && cp <= 0x0E7F) return "th";
    if (cp >= 0x3040 && cp <= 0x30FF) kana = true;
    else if (cp >= 0x4E00 && cp <= 0x9FFF) han = true;
    else if (/[A-Za-z]/.test(ch)) latin = true;
  }
  return kana ? "ja" : han ? "zh" : latin ? "en" : "th";
}

// A language in its own words ("th" -> "ไทย"), from the browser, so a fifth
// language needs no table of names here.
static langName(code){
  try { return new Intl.DisplayNames([code], {type: "language"}).of(code) || code; }
  catch (e) { return code; }
}

  // Every language the store speaks: its voice map first, then the answers'.
  langs(){
  const out = Object.keys(((this.cfg || {}).tts || {}).voices || {});
  VoiceApp.ANSWER_KEYS.forEach(([l]) => { if (!out.includes(l)) out.push(l); });
  return out;
}

  showTab(name){
  const all = sel => (document.querySelectorAll ? [...document.querySelectorAll(sel)] : []);
  all("#setTabs .tab").forEach(b => b.classList.toggle("on", b.dataset.tab === name));
  all("[data-pane]").forEach(p => { p.hidden = p.dataset.pane !== name; });
  try { localStorage.setItem("voice_tab", name); } catch(e) {}
}

  async loadStores(){
  const [c, f, ls] = await Promise.all([
    fetch("/api/voice/config").then(x => x.json()).catch(() => null),
    fetch("/api/voice/faq").then(x => x.json()).catch(() => null),
    fetch("/api/list?kind=sequences").then(x => x.json()).catch(() => null),
  ]);
  if (!c || !c.ok) return;                 // the down-card already explains
  this.cfg = c.config;
  this.faqs = (f && f.ok && Array.isArray(f.faqs)) ? f.faqs : [];
  this.seqs = (ls && ls.files) || [];
  this.fillAnswers(); this.fillVoice(); this.fillWords(); this.fillScenario(); this.fillThai(); this.fillFaces(); this.fillAdvanced();
  this.fillAskLangs();
  // Finding every robot on every PC took 10 s the first time (measured
  // 2026-10-15) and EVERY settings box stayed empty until it came back - the
  // page looked broken. The boxes fill now; the robot lists catch up.
  this.loadRobots();
}

  async loadRobots(){
  const ms = await fetch("/api/modules/all").then(x => x.json()).catch(() => null);
  this.robots = (((ms || {}).modules) || []).map(m => m.name).filter(Boolean);
  const grSel = this.$("globalRobot");
  if (grSel) {
    const cur = this.globalRobot || grSel.value || "";
    grSel.textContent = "";
    const opt = (v, t) => {
      const o = document.createElement("option");
      o.value = v; o.textContent = t;
      grSel.appendChild(o);
    };
    opt("", "the answer's own");
    opt("__all__", "all robots");
    this.robots.forEach(name => opt(name, name));
    if (cur && cur !== "__all__" && !this.robots.includes(cur)) opt(cur, "(missing) " + cur);
    grSel.value = cur;
  }
  // The sheet's robot boxes, in place: redrawing would drop a cell being typed in.
  this.sheet.forEach(row => (row.mvs || []).forEach(m =>
    this.fillPick(m.r, "(no robot)", this.robots, m.r.value)));
}

  // Every save writes the whole store, so each tab's Save keeps the others.
  async postConfig(statId){
  this.$(statId).textContent = "saving…";
  this.collectWords(); this.collectVoice(); this.collectScenario(); this.collectThai(); this.collectFaces(); this.collectAdvanced();
  let r;
  try {
    r = await fetch("/api/voice/config", {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({config: this.cfg})});
  } catch(e) {
    this.$(statId).textContent = "The voice helper is not answering."; return false;
  }
  if (r.status === 401) {
    this.$(statId).textContent = miceLogin.required(
      "Saving needs a login — log in at the top of this page, then press Save again.");
    return false;
  }
  if (!r.ok) {
    this.$(statId).textContent = ((await r.json().catch(() => ({}))).error)
                          || "That did not save — try again.";
    return false;
  }
  this.$(statId).textContent = "Saved.";
  this.fillAskLangs();
  const h = await fetch("/api/voice/health").then(x => x.json()).catch(() => null);
  if (h && h.parts) this.updateParts(h.parts);
  return true;
}

  // Saves the answers. Its word goes beside the Save button; the edits on
  // screen are kept whatever happens, so nothing typed is lost to a refusal.
  async postFaqs(faqs = this.faqs){
  const stat = this.$("ansStat");
  let r;
  try {
    r = await fetch("/api/voice/faq", {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({faqs})});
  } catch(e) {
    stat.textContent = "The voice helper is not answering — nothing was saved."; return false;
  }
  if (r.status === 401) {
    stat.textContent = miceLogin.required(
      "Saving needs a login — log in at the top of this page, then press Save again.");
    return false;
  }
  if (!r.ok) {
    stat.textContent = ((await r.json().catch(() => ({}))).error)
                       || "That did not save — try again.";
    return false;
  }
  return true;
}

// ---- Answers: a sheet (A42-1) ------------------------------------------
// User 2026-10-15: *like Excel would be easier; pressing Edit scrolled to
// the bottom and I could not tell where to change it*. Every cell is a box
// typed into where it stands; changed rows are marked; ONE Save sends them
// all. Undo puts back what is saved.
  fillAnswers(){
  this.removedRows = 0;
  this.sheet = (this.faqs || []).map(item => ({item: JSON.parse(JSON.stringify(item)), dirty: false}));
  this.drawSheet();
}

  drawSheet(){
  const head = this.$("ansHead"), body = this.$("ansRows");
  head.textContent = "";
  const th = t => { const e = document.createElement("th"); e.textContent = t; head.appendChild(e); };
  ["#"].forEach(th);
  VoiceApp.ANSWER_KEYS.forEach(([l]) => th(VoiceApp.langName(l)));
  ["Robot move", ""].forEach(th);
  body.textContent = "";
  this.sheet.forEach((row, i) => body.appendChild(this.sheetRow(row, i)));
  this.$("ansEmpty").hidden = this.sheet.length > 0;
  this.findAnswers();
  this.markDirty();
}

  // One answer as one row of boxes.
  sheetRow(row, i){
  const tr = document.createElement("tr");
  row.tr = tr;
  const td = () => { const c = document.createElement("td"); tr.appendChild(c); return c; };
  const changed = () => { row.dirty = true; tr.classList.remove("bad"); this.markDirty(); };
  const button = (text, title, fn) => {
    const b = document.createElement("button");
    b.type = "button"; b.textContent = text; b.title = title; b.onclick = fn;
    return b;
  };
  td().textContent = String(i + 1);

  // Each language is one column: how people ask it on top, what the rig
  // says under it. The asks are ONE list in the store, joined back here.
  row.asks = {};
  row.says = {};
  const joinAsks = () => {
    row.item.questions = VoiceApp.ANSWER_KEYS
      .flatMap(([l]) => row.asks[l].value.split("\n"))
      .map(s => s.trim()).filter(Boolean);
    changed();
  };
  VoiceApp.ANSWER_KEYS.forEach(([lang, key]) => {
    const c = td();
    const ask = this.cell(this.asksIn(row.item.questions, lang).join("\n"),
                          "people ask… (one per line)", joinAsks);
    ask.classList.add("ask");
    row.asks[lang] = ask;
    c.appendChild(ask);
    const box = this.cell(row.item[key], "it says…",
                          v => { row.item[key] = v.trim(); changed(); });
    row.says[lang] = box;
    const bar = document.createElement("div");
    bar.className = "cellbar";
    bar.appendChild(button("▶", "Hear it", () => this.hear(box.value.trim(), lang)));
    c.appendChild(box);
    c.appendChild(bar);
  });

  // Moves: a robot and one of its saved sequences, as many pairs as wanted.
  const mc = td();
  mc.className = "moves";
  row.mvs = [];
  const list = document.createElement("div");
  const syncMoves = () => {
    row.item.moves = row.mvs.filter(m => !m.gone)
                     .map(m => ({module: m.r.value, move: m.s.value}))
                     .filter(m => m.module || m.move);
    changed();
  };
  const addMove = (m) => {
    const d = document.createElement("div");
    d.className = "mv";
    const r = document.createElement("select");
    this.fillPick(r, "(no robot)", this.robots, m.module || "");
    const s = document.createElement("select");
    this.fillPick(s, "(no move)", this.seqs, m.move || "");
    const one = {r, s, gone: false};
    r.onchange = s.onchange = syncMoves;
    d.appendChild(r); d.appendChild(s);
    d.appendChild(button("✕", "Take this move off", () => { one.gone = true; d.remove(); syncMoves(); }));
    list.appendChild(d);
    row.mvs.push(one);
  };
  this.answerMoves(row.item).forEach(addMove);
  mc.appendChild(list);
  mc.appendChild(button("＋ move", "Add a robot move", () => addMove({})));

  const ac = td();
  const acts = document.createElement("div");
  acts.className = "acts";
  acts.appendChild(button("🌐 Translate", "Fill the empty languages, and add the ways of asking in each language",
                          () => this.translateRow(row, true)));
  acts.appendChild(button("✕ Delete", "Delete this answer (Undo changes brings it back until you save)",
                          () => this.deleteRow(row)));
  ac.appendChild(acts);
  return tr;
}

  // A cell: a box that grows with what is typed, like a spreadsheet row.
  asksIn(questions, lang){
  return (questions || []).filter(q => VoiceApp.askLang(q) === lang);
}

  // The box to type in first: the first language with a way of asking, else
  // the first language.
  firstAsk(row){
  if (!row || !row.asks) return null;
  const ls = VoiceApp.ANSWER_KEYS.map(([l]) => l);
  return row.asks[ls.find(l => row.asks[l].value.trim()) || ls[0]];
}

  cell(value, hint, onInput){
  const ta = document.createElement("textarea");
  ta.rows = 1;
  ta.value = value || "";
  ta.placeholder = hint || "";
  ta.addEventListener("input", () => { this.grow(ta); onInput(ta.value); });
  setTimeout(() => this.grow(ta), 0);
  return ta;
}

  grow(ta){
  if (!ta.style || typeof ta.scrollHeight !== "number") return;
  ta.style.height = "auto";
  ta.style.height = ta.scrollHeight + "px";
}

  fillPick(select, none_, items, chosen){
  select.textContent = "";
  const o = document.createElement("option");
  o.value = ""; o.textContent = none_;
  select.appendChild(o);
  items.forEach(v => {
    const e = document.createElement("option");
    e.value = v; e.textContent = v;
    select.appendChild(e);
  });
  // A saved value that is not on offer any more (a deleted sequence, a
  // robot that went away) stays VISIBLE as missing - silently resetting it
  // to none would quietly strip the answer's move on the next save.
  if (chosen && !items.includes(chosen)) {
    const m = document.createElement("option");
    m.value = chosen; m.textContent = "(missing) " + chosen;
    select.appendChild(m);
  }
  select.value = chosen || "";
}

  answerMoves(item){
  if (Array.isArray(item.moves) && item.moves.length) return item.moves;
  return (item.move || item.module) ? [{module: item.module || "", move: item.move || ""}] : [];
}

  markDirty(){
  const n = this.sheet.filter(r => r.dirty).length + (this.removedRows || 0);
  this.sheet.forEach(r => r.tr && r.tr.classList.toggle("dirty", r.dirty));
  const save = this.$("ansSave"), undo = this.$("ansUndo");
  save.disabled = undo.disabled = !n;
  save.textContent = n ? "Save answers (" + n + " changed)" : "Save answers";
  return n;
}

  findAnswers(){
  const want = (this.$("ansFind").value || "").trim().toLowerCase();
  this.sheet.forEach(row => {
    if (!row.tr) return;
    const text = [(row.item.questions || []).join(" ")]
      .concat(VoiceApp.ANSWER_KEYS.map(([, k]) => row.item[k] || "")).join(" ").toLowerCase();
    row.tr.hidden = !!want && !row.dirty && !text.includes(want);
  });
}

  // A new row goes on TOP, where it can be seen, with its first box ready.
  addAnswerRow(){
  this.$("ansFind").value = "";
  this.sheet.unshift({item: {questions: [], answer: ""}, dirty: true});
  this.drawSheet();
  const first = this.firstAsk(this.sheet[0]);
  if (first) { first.focus(); if (first.scrollIntoView) first.scrollIntoView({block: "center"}); }
}

  deleteRow(row){
  this.sheet = this.sheet.filter(r => r !== row);
  if (!row.fresh) this.removedRows = (this.removedRows || 0) + 1;
  this.drawSheet();
  this.$("ansStat").textContent = "Deleted — press Save answers to keep it that way, or Undo changes.";
}

  undoAnswers(){
  this.fillAnswers();
  this.$("ansStat").textContent = "Back to what is saved.";
}

  // Fills a row's empty languages from the first one written. With `questions`
  // (the row's 🌐 button) the ways of asking gain each language too.
  async translateRow(row, questions){
  const stat = this.$("ansStat");
  const src = VoiceApp.ANSWER_KEYS.map(([, k]) => (row.item[k] || "").trim()).find(Boolean);
  const qs = row.item.questions || [];
  if (!src && !qs.length) { stat.textContent = "Type a way of asking or a reply first."; return false; }
  if (questions) stat.textContent = "translating…";
  const post = body => fetch("/api/voice/translate", {method: "POST",
    headers: {"Content-Type": "application/json"}, body: JSON.stringify(body)})
    .then(r => r.json()).catch(() => null);
  let ok = false;
  if (src) {
    const res = await post({text: src, all: true});
    if (res && res.ok && res.translations) {
      ok = true;
      VoiceApp.ANSWER_KEYS.forEach(([lang, key]) => {
        const t = (res.translations[lang] || "").trim();
        if (t && !(row.item[key] || "").trim()) {
          row.item[key] = t;
          if (row.says && row.says[lang]) { row.says[lang].value = t; this.grow(row.says[lang]); }
        }
      });
    }
  }
  if (questions && qs.length) {
    const res = await post({texts: qs, all: true});
    if (res && res.ok && Array.isArray(res.results)) {
      ok = true;
      const all = new Set(qs);
      res.results.forEach(t => t && Object.values(t).forEach(q => { if (q && String(q).trim()) all.add(String(q).trim()); }));
      row.item.questions = [...all];
      if (row.asks) VoiceApp.ANSWER_KEYS.forEach(([l]) => {
        row.asks[l].value = this.asksIn(row.item.questions, l).join("\n");
        this.grow(row.asks[l]);
      });
    }
  }
  row.dirty = true;
  this.markDirty();
  if (questions) stat.textContent = ok ? "Translated — check it, then Save answers."
                                       : "Translation did not answer (this PC may be offline). Type them in, or save as is.";
  return ok;
}

  // What is saved: the moves as a list, and the first one also in the old
  // single move/module fields that older readers still use.
  cleanItem(item){
  const out = Object.assign({}, item);
  out.questions = (item.questions || []).map(s => String(s).trim()).filter(Boolean);
  VoiceApp.ANSWER_KEYS.forEach(([, k]) => {
    const v = String(item[k] || "").trim();
    if (v) out[k] = v; else delete out[k];
  });
  const moves = this.answerMoves(item).filter(m => m.module || m.move);
  delete out.moves; delete out.move; delete out.module;
  if (moves.length) {
    out.moves = moves;
    if (moves[0].move) out.move = moves[0].move;
    if (moves[0].module) out.module = moves[0].module;
  }
  return out;
}

  async saveAnswers(){
  const stat = this.$("ansStat");
  const blank = it => !(it.questions || []).length
                      && !VoiceApp.ANSWER_KEYS.some(([, k]) => (it[k] || "").trim());
  const before = this.sheet.length;
  this.sheet = this.sheet.filter(r => !blank(r.item));   // an untouched new row is no answer
  if (this.sheet.length !== before) this.drawSheet();
  const bad = this.sheet.filter(r => !(r.item.questions || []).length
                                     || !VoiceApp.ANSWER_KEYS.some(([, k]) => (r.item[k] || "").trim()));
  if (bad.length) {
    bad.forEach(r => { r.tr.classList.add("bad"); r.tr.hidden = false; });
    stat.textContent = "Row " + (this.sheet.indexOf(bad[0]) + 1)
                     + " needs a way of asking and a reply. Nothing was saved yet.";
    const ask = this.firstAsk(bad[0]);
    if (ask) ask.focus();
    return false;
  }
  const btn = this.$("ansSave");
  btn.disabled = true;
  // An empty language is translated before saving, so the rig has it ready
  // (the helper would translate it at the first question, and make someone wait).
  const todo = this.sheet.filter(r => r.dirty && VoiceApp.ANSWER_KEYS.some(([, k]) => !(r.item[k] || "").trim()));
  for (let i = 0; i < todo.length; i++) {
    stat.textContent = "translating " + (i + 1) + " of " + todo.length + "…";
    await this.translateRow(todo[i], false);
  }
  stat.textContent = "saving…";
  const faqs = this.sheet.map(r => this.cleanItem(r.item));
  if (!(await this.postFaqs(faqs))) { this.markDirty(); return false; }
  this.faqs = faqs;
  this.fillAnswers();
  stat.textContent = "Saved — " + faqs.length + " answers.";
  return true;
}

  async hear(text, lang = ""){
  if (text) await this.speak(text, lang);
}

  // The Language box above the question: any, or one every question is held to.
  fillAskLangs(){
  const sel = this.$("askLang");
  if (!sel || !this.cfg) return;
  sel.textContent = "";
  const add = (v, t) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = t;
    sel.appendChild(o);
  };
  add("", "any (it can tell)");
  const langs = this.langs();
  langs.forEach(l => add(l, "only " + VoiceApp.langName(l)));
  if (this.askLang && !langs.includes(this.askLang)) add(this.askLang, this.askLang);
  sel.value = this.askLang;
}

  pickAskLang(){
  this.askLang = this.$("askLang").value || "";
  try { localStorage.setItem("voice_ask_lang", this.askLang); } catch(e) {}
}

// ---- Voice: how it sounds -------------------------------------------
static SAMPLES = {
  th: "สวัสดีครับ ผมคือหุ่นยนต์น้อง Mice",
  en: "Hello, I am the Mice robot",
  ja: "こんにちは、マイスロボットです",
  zh: "你好，我是 Mice 机器人"
};

  fillVoice(){
  const t = this.cfg.tts || {}, s = this.cfg.stt || {};
  this.$("speakOn").checked = t.enabled !== false;
  this.$("listenOn").checked = s.enabled !== false;
  const ml = this.$("mainLang");
  ml.textContent = "";
  const langs = this.langs();
  langs.forEach(l => {
    const o = document.createElement("option");
    o.value = l; o.textContent = VoiceApp.langName(l);
    ml.appendChild(o);
  });
  ml.value = t.language || langs[0] || "";
  this.fillSteps(this.$("ttsRate"), "rate", t.rate);
  this.fillSteps(this.$("ttsPitch"), "pitch", t.pitch);
  this.fillOneVoice();
  const row = this.$("modelRow");
  row.textContent = "";
  let known = false;
  const radio = (id, word) => {
    const l = document.createElement("label");
    l.className = "mini pick";
    const r = document.createElement("input");
    r.type = "radio"; r.name = "sttModel"; r.value = id;
    r.checked = s.model === id;
    if (r.checked) known = true;
    l.appendChild(r);
    l.appendChild(document.createTextNode(word));
    row.appendChild(l);
  };
  VoiceApp.MODEL_WORDS.forEach(([id, word]) => radio(id, word));
  if (!known && s.model) radio(s.model, s.model);   // a model the words do not cover: say so
}

  // Speed and pitch as words with the step beside them, in the speech
  // service's own shapes ("+10%", "-5Hz"). A saved value off the list stays
  // visible rather than being quietly reset. `first` is the "same as" choice.
  fillSteps(sel, kind, chosen, first){
  if (!sel) return;
  sel.textContent = "";
  const add = (v, txt) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = txt;
    sel.appendChild(o);
    return o;
  };
  if (first) add("", first);
  const rate = kind === "rate";
  const unit = rate ? "%" : "Hz", step = rate ? 10 : 5, far = rate ? 40 : 20;
  const words = rate ? ["slower", "faster"] : ["lower", "higher"];
  const have = [];
  for (let v = -far; v <= far; v += step) {
    const val = (v < 0 ? "" : "+") + v + unit;
    have.push(val);
    add(val, v === 0 ? "normal" : (Math.abs(v) > far / 2 ? "much " : "a bit ")
             + words[v < 0 ? 0 : 1] + " (" + val + ")");
  }
  const want = String(chosen || "").trim();
  if (want && !have.includes(want)) add(want, want);
  sel.value = want || (first ? "" : "+0" + unit);
}

  // "th-TH-PremwadeeNeural" -> "Premwadee", for a voice the list does not hold.
  voiceShort(name){
  return String(name).replace(/^[a-z]{2,3}-[A-Z]{2,4}-/, "").replace(/Neural$/, "") || name;
}

  voiceWords(v){
  const g = {Female: "woman", Male: "man"}[v.gender] || v.gender || "";
  return (v.says || v.name) + (g ? " · " + g : "");
}

  // The voices come from the helper, which asks the speech service itself -
  // no list of names lives in this page.
  async fillOneVoice(){
  const sel = this.$("oneVoice");
  if (!sel) return;
  const want = ((this.cfg.tts || {}).oneVoice || "");
  if (!this.allVoices) {
    try {
      const r = await fetch("/api/voice/voices").then(res => res.json());
      this.allVoices = (r && r.ok && r.voices) ? r.voices : [];
      this.voicesByLang = (r && r.ok && r.byLang) || {};
    } catch(e) { this.allVoices = []; }
  }
  sel.textContent = "";
  const add = (value, text) => {
    const o = document.createElement("option");
    o.value = value; o.textContent = text;
    sel.appendChild(o);
    return o;
  };
  add("", "each language its own native voice (below) — recommended");
  this.allVoices.forEach(v => add(v.name, this.voiceWords(v) + " · one voice for every language (an accent in the others)"));
  if (want && !this.allVoices.some(v => v.name === want)) add(want, want);
  if (!this.allVoices.length) {
    // Offline, or the speech service refused: say so rather than showing
    // an empty box that looks broken.
    add("-", "(no voice list — this PC may be offline; the saved voices still speak)").disabled = true;
  }
  sel.value = want;
  this.fillLangVoices();
  this.voicesReady = true;                  // collectVoice may read the boxes now
  this.pickOneVoice();
  this.fillScenarioVoices();
}

  // One row per language: its own voice, used when no one voice is chosen.
  fillLangVoices(){
  const box = this.$("langVoices");
  if (!box) return;
  box.textContent = "";
  const V = (this.cfg.tts && this.cfg.tts.voices) || {};
  this.langVoice = {};
  this.langs().forEach(lang => {
    const f = document.createElement("div");
    f.className = "field";
    const lab = document.createElement("span");
    lab.textContent = VoiceApp.langName(lang);
    const sel = document.createElement("select");
    const list = this.voicesByLang[lang] || [];
    this.fillPick(sel, "(this PC's own voice)", list.map(v => v.name), V[lang] || "");
    [...(sel.options || [])].forEach(o => {
      const v = list.find(x => x.name === o.value);
      // No list (offline): the saved voice is not "missing", just unlisted.
      if (v || (!list.length && o.value)) o.textContent = v ? this.voiceWords(v) : this.voiceShort(o.value);
    });
    const b = document.createElement("button");
    b.type = "button"; b.textContent = "▶ Try";
    b.onclick = () => this.tryVoice(lang, sel.value || "");
    f.appendChild(lab); f.appendChild(sel); f.appendChild(b);
    box.appendChild(f);
    this.langVoice[lang] = {sel, f, b};
  });
}

  pickOneVoice(){
  const sel = this.$("oneVoice");
  const on = !!(sel && sel.value);
  Object.values(this.langVoice || {}).forEach(({sel: s, f, b}) => {
    s.disabled = b.disabled = on;
    f.classList.toggle("off", on);
  });
  // A scenario with a voice of its own wins over this tab: say so here, or
  // a change on this tab seems to do nothing.
  const note = this.$("voiceNote");
  const sc = this.scenarioList().find(x => (x.name || "") === (this.cfg.scenario || ""));
  if (note) {
    note.hidden = !(sc && sc.voice);
    note.textContent = sc && sc.voice
      ? "The scenario “" + sc.name + "” has a voice of its own, so that one speaks. Change it on Personality." : "";
  }
}

  // Try plays the voice AS CHOSEN on screen, before anything is saved: its
  // language's sample at this tab's speed and pitch.
  tryVoice(lang = "", voice = ""){
  lang = lang || (this.$("mainLang") && this.$("mainLang").value) || "th";
  const one = this.$("oneVoice") ? this.$("oneVoice").value : "";
  const own = ((this.langVoice || {})[lang] || {}).sel;
  voice = voice || one || (own ? own.value : "");
  const t = {speed: this.$("ttsRate").value || "+0%", pitch: this.$("ttsPitch").value || "+0Hz"};
  if (voice && voice !== "-") t.voice = voice;
  this.speak(VoiceApp.SAMPLES[lang] || VoiceApp.SAMPLES.en, lang, t);
}

  collectVoice(){
  const t = this.cfg.tts = this.cfg.tts || {};
  t.enabled = this.$("speakOn").checked;
  const ml = this.$("mainLang").value;
  if (ml) t.language = ml;
  t.rate = this.$("ttsRate").value || "+0%";
  t.pitch = this.$("ttsPitch").value || "+0Hz";
  // Only once the voice boxes are drawn: an empty box read before the list
  // arrived would wipe the saved voices.
  if (this.voicesReady) {
    t.voices = t.voices || {};
    Object.entries(this.langVoice || {}).forEach(([l, {sel}]) => { t.voices[l] = sel.value; });
    // Empty means the per-language voices. Anything else speaks everything.
    t.oneVoice = this.$("oneVoice").value === "-" ? "" : this.$("oneVoice").value;
  }
  this.cfg.stt = this.cfg.stt || {};
  this.cfg.stt.enabled = this.$("listenOn").checked;
  const pick = document.querySelector('input[name="sttModel"]:checked');
  if (pick) this.cfg.stt.model = pick.value;
}

// ---- Words it gets wrong ---------------------------------------------
  fillWords(){
  const box = this.$("biasRows");
  box.textContent = "";
  this.biasInputs = {};
  if (!this.cfg.stt) this.cfg.stt = {};
  if (!this.cfg.stt.languages) this.cfg.stt.languages = {};
  const langs = this.langs();
  Object.keys(this.cfg.stt.languages).forEach(l => { if (!langs.includes(l)) langs.push(l); });
  langs.forEach(lang => {
    if (!this.cfg.stt.languages[lang]) this.cfg.stt.languages[lang] = {bias: ""};
    const wrap = document.createElement("div");
    wrap.className = "field";
    const name = document.createElement("span");
    name.textContent = VoiceApp.langName(lang);
    const chips = document.createElement("div");
    chips.className = "row";
    const draw = () => {
      chips.textContent = "";
      const words = (this.cfg.stt.languages[lang].bias || "").split(/\s+/).filter(Boolean);
      if (!words.length) {
        const m = document.createElement("span");
        m.className = "mini";
        m.textContent = "none yet";
        chips.appendChild(m);
      }
      words.forEach(w => {
        const c = document.createElement("button");
        c.type = "button";
        c.className = "mini";
        c.title = "Take this word off";
        c.textContent = w + " ✕";
        c.onclick = () => {
          this.cfg.stt.languages[lang].bias = (this.cfg.stt.languages[lang].bias || "")
            .split(/\s+/).filter(x => x && x !== w).join(" ");
          draw();
        };
        chips.appendChild(c);
      });
    };
    draw();
    const input = document.createElement("input");
    this.biasInputs[lang] = input;
    input.placeholder = "add a word";
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "Add";
    add.onclick = () => {
      const w = String(input.value || "").trim();
      if (!w) return;
      const have = (this.cfg.stt.languages[lang].bias || "").split(/\s+/).filter(Boolean);
      w.split(/\s+/).forEach(part => { if (part && !have.includes(part)) have.push(part); });
      this.cfg.stt.languages[lang].bias = have.join(" ");
      input.value = "";
      draw();
    };
    input.addEventListener("keydown", e => { if (e.key === "Enter") { e.preventDefault(); add.click(); } });
    wrap.appendChild(name);
    wrap.appendChild(chips);
    wrap.appendChild(input);
    wrap.appendChild(add);
    box.appendChild(wrap);
  });
}

  // A word typed but not yet Added still counts when Save is pressed.
  collectWords(){
  if (!this.cfg.stt || !this.cfg.stt.languages || !this.biasInputs) return;
  let any = false;
  Object.keys(this.biasInputs).forEach(lang => {
    const val = String(this.biasInputs[lang].value || "").trim();
    if (!val) return;
    const have = (this.cfg.stt.languages[lang].bias || "").split(/\s+/).filter(Boolean);
    val.split(/\s+/).forEach(w => { if (w && !have.includes(w)) have.push(w); });
    this.cfg.stt.languages[lang].bias = have.join(" ");
    any = true;
  });
  if (any) this.fillWords();
}

// ---- Scenario ---------------------------------------------------------
// What the rig is being, and how it sounds while being it. A scenario is one
// entry in cfg.scenarios; cfg.scenario names the one in use. Plain text in
// cfg.scenario still works and is shown as "(just these words)", so a store
// written before scenarios existed opens unchanged.
  scenarioList(){
  return Array.isArray((this.cfg || {}).scenarios) ? this.cfg.scenarios : [];
}

  scenarioNow(){
  const want = (this.cfg.scenario || "").trim();
  return this.scenarioList().find(s => (s.name || "").trim() === want && want) || null;
}

  fillScenario(){
  const sel = this.$("scenPick");
  if (!sel) return;
  const named = this.scenarioNow();
  sel.textContent = "";
  const add = (v, txt) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = txt;
    sel.appendChild(o);
  };
  add("", "(just these words)");
  this.scenarioList().forEach(s => add(s.name || "", s.name || "(no name)"));
  sel.value = named ? named.name : "";
  this.showScenario(named || {prompt: (this.cfg.scenario || "").trim()});
}

  showScenario(s){
  this.$("scenPrompt").value = s.prompt || "";
  this.fillSteps(this.$("scenRate"), "rate", s.rate, "same as the Voice tab");
  this.fillSteps(this.$("scenPitch"), "pitch", s.pitch, "same as the Voice tab");
  this.scenVoiceWant = s.voice || "";
  this.fillScenarioVoices();
}

  // Every voice offered, one voice for every language first; "same as the
  // Voice tab" keeps that tab's choice.
  fillScenarioVoices(){
  const vs = this.$("scenVoice");
  if (!vs) return;
  const want = this.scenVoiceWant || "";
  vs.textContent = "";
  const add = (v, txt, into) => {
    const o = document.createElement("option");
    o.value = v; o.textContent = txt;
    (into || vs).appendChild(o);
  };
  add("", "same as the Voice tab");
  const names = [];
  (this.allVoices || []).forEach(v => { names.push(v.name); add(v.name, this.voiceWords(v) + " · speaks every language"); });
  Object.entries(this.voicesByLang || {}).forEach(([l, list]) => list.forEach(v => {
    if (!names.includes(v.name)) { names.push(v.name); add(v.name, this.voiceWords(v)); }
  }));
  if (want && !names.includes(want)) add(want, want);
  vs.value = want;
}

  pickScenario(){
  const name = this.$("scenPick").value;
  const s = this.scenarioList().find(x => (x.name || "") === name);
  this.showScenario(s || {prompt: ""});
}

  addScenario(){
  const name = (prompt("Name this scenario") || "").trim();
  if (!name) return;
  this.cfg.scenarios = this.scenarioList();
  if (!this.cfg.scenarios.some(s => (s.name || "") === name))
    this.cfg.scenarios.push({name, prompt: this.$("scenPrompt").value.trim(),
                             voice: this.$("scenVoice").value,
                             rate: this.$("scenRate").value,
                             pitch: this.$("scenPitch").value});
  this.cfg.scenario = name;
  this.fillScenario();
  this.$("sStat").textContent = "Added — press Save personality to keep it.";
}

  // Plays the scenario as it would sound: its own voice, speed and pitch, or
  // the Voice tab's where it says "same".
  tryScenario(){
  const lang = (this.$("mainLang") && this.$("mainLang").value) || "th";
  const own = ((this.langVoice || {})[lang] || {}).sel;
  const voice = this.$("scenVoice").value || this.$("oneVoice").value || (own ? own.value : "");
  const t = {speed: this.$("scenRate").value || this.$("ttsRate").value || "+0%",
             pitch: this.$("scenPitch").value || this.$("ttsPitch").value || "+0Hz"};
  if (voice && voice !== "-") t.voice = voice;
  this.speak(VoiceApp.SAMPLES[lang] || VoiceApp.SAMPLES.en, lang, t);
}

  collectScenario(){
  const sel = this.$("scenPick");
  if (!sel) return;
  const name = sel.value;
  const body = {prompt: this.$("scenPrompt").value.trim(),
                voice: this.$("scenVoice").value,
                rate: this.$("scenRate").value,
                pitch: this.$("scenPitch").value};
  if (!name) {                                // no scenario: the words alone
    this.cfg.scenario = body.prompt;
    return;
  }
  this.cfg.scenarios = this.scenarioList();
  const at = this.cfg.scenarios.findIndex(s => (s.name || "") === name);
  if (at < 0) this.cfg.scenarios.push(Object.assign({name}, body));
  else this.cfg.scenarios[at] = Object.assign({}, this.cfg.scenarios[at], body);
  this.cfg.scenario = name;
  this.pickOneVoice();                        // the Voice tab's note follows
}

// ---- How it speaks Thai ------------------------------------------------
// A26-69, user 2026-09-18: the local model *mixes ครับ and ค่ะ, cuts replies
// off, and sometimes answers in the wrong language*. The particle, the Thai
// room and the apology were all inside the code; they are settings now, and
// the LIST of particles comes from the store, so the next one costs no code.
  fillThai(){
  const a = this.cfg.answer || {};
  // Both lists come from the STORE, so a third particle or another pronoun is
  // an entry in config/voice.json and no page code.
  const pick = (id, list, chosen) => {
    const sel = this.$(id);
    if (!sel) return;
    sel.textContent = "";
    (list || []).forEach(p => {
      const o = document.createElement("option");
      o.value = o.textContent = p;
      sel.appendChild(o);
    });
    sel.value = chosen || (list || [])[0] || "";
  };
  pick("ansParticle", a.politeParticles || ["ครับ", "ค่ะ"], a.politeParticle);
  pick("ansPronoun", a.politePronouns || ["ผม", "ฉัน"], a.politePronoun);
  const flat = (this.cfg.llm || {}).maxTokens || 32;
  this.$("ansThai").value = (a.maxTokensByLang || {}).th ?? flat;
  this.$("ansSorry").value = (a.cannotAnswer || {}).th || "";
}
  collectThai(){
  const a = this.cfg.answer = this.cfg.answer || {};
  const sel = this.$("ansParticle");
  if (sel && sel.value) a.politeParticle = sel.value;
  const who = this.$("ansPronoun");
  if (who && who.value) a.politePronoun = who.value;
  const v = parseInt(this.$("ansThai").value, 10);
  if (Number.isFinite(v) && v > 0) {
    a.maxTokensByLang = a.maxTokensByLang || {};
    a.maxTokensByLang.th = v;
  }
  const sorry = (this.$("ansSorry").value || "").trim();
  // An empty box keeps the sentence it had: a blank apology would leave the
  // rig silent at the one moment it has to say something.
  if (sorry) {
    a.cannotAnswer = a.cannotAnswer || {};
    a.cannotAnswer.th = sorry;
  }
}

// ---- Faces ------------------------------------------------------------
// How long a name stays after the person is gone, and how often the camera
// looks. Both were numbers in the code until the user asked for them:
// *make can setting by my self in setting to setting the time out time*.
  fillFaces(){
  const f = this.cfg.face || {};
  this.showFaces(f.on !== false);
  this.$("faceForget").value = f.rememberSeconds ?? 120;
  this.$("faceEvery").value = f.autoSeconds ?? 5;
}
  collectFaces(){
  const num = (id, fallback) => {
    const v = parseFloat(this.$(id).value);
    return Number.isFinite(v) ? v : fallback;
  };
  const f = this.cfg.face = this.cfg.face || {};
  f.on = this.facesOn();
  f.rememberSeconds = num("faceForget", f.rememberSeconds ?? 120);
  f.autoSeconds = num("faceEvery", f.autoSeconds ?? 5);
  this.camSeconds = f.autoSeconds;
}

// ---- Advanced ---------------------------------------------------------
  fillAdvanced(){
  this.$("svcUrl").value = this.cfg.service || "";
  this.$("faqTh").value = this.cfg.faqThreshold ?? 0.75;
  this.$("askAgain").value = this.cfg.faqAskAgain ?? 0.65;
  const l = this.cfg.llm || {};
  this.$("llmModel").value = l.model || "";
  this.$("llmMax").value = l.maxTokens || 512;
}
  collectAdvanced(){
  // An empty box keeps the value it had - a NaN here would reach the
  // helper as null and stop the answering brain from reading its own
  // threshold.
  const num = (id, fallback) => {
    const v = parseFloat(this.$(id).value);
    return Number.isFinite(v) ? v : fallback;
  };
  this.cfg.service = this.$("svcUrl").value.trim() || this.cfg.service;
  this.cfg.faqThreshold = num("faqTh", this.cfg.faqThreshold ?? 0.75);
  this.cfg.faqAskAgain = num("askAgain", this.cfg.faqAskAgain ?? 0.65);
  this.cfg.llm = this.cfg.llm || {};
  this.cfg.llm.model = this.$("llmModel").value.trim() || this.cfg.llm.model || "Qwen/Qwen3.5-4B";
  this.cfg.llm.maxTokens = num("llmMax", this.cfg.llm.maxTokens || 512);
}

// The login is a shared component, mounted where the page can see it. One
// session across every page: log in here and the hub knows, and the other way
// round (A25-5).
  init(){
    if (this.initialized) return;
    this.initialized = true;
    const keep = (key, fallback) => {
      try { const v = localStorage.getItem(key); return v === null ? fallback : v; }
      catch(e) { return fallback; }
    };
    const save = (key, v) => { try { localStorage.setItem(key, v); } catch(e) {} };

    // Sound here is ON unless this browser switched it off: off by default,
    // a first visitor heard nothing and took the voice for broken.
    this.$("sound").checked = keep("sound", "true") === "true";
    this.$("sound").addEventListener("change", () => save("sound", String(this.$("sound").checked)));

    this.moveEnabled = keep("voice_move_enabled", "1") === "1";
    this.$("moveOn").checked = this.moveEnabled;
    this.$("moveOn").addEventListener("change", () => {
      this.moveEnabled = !!this.$("moveOn").checked;
      save("voice_move_enabled", this.moveEnabled ? "1" : "0");
    });

    this.globalRobot = keep("voice_global_robot", "");
    this.$("globalRobot").value = this.globalRobot;
    this.$("globalRobot").addEventListener("change", () => {
      this.globalRobot = this.$("globalRobot").value;
      save("voice_global_robot", this.globalRobot);
    });

    this.askLang = keep("voice_ask_lang", "");

    // The open tab is remembered; Advanced is not, since it hides with the
    // technical switch and would leave an empty settings area.
    const tab = keep("voice_tab", "answers");
    this.showTab(tab === "adv" ? "answers" : tab);

    // Unsaved answers are not lost to a closed tab.
    if (typeof window.addEventListener === "function")
      window.addEventListener("beforeunload", e => {
        if (this.sheet.some(r => r.dirty) || this.removedRows) { e.preventDefault(); e.returnValue = ""; }
      });

    // A shown camera stops with the tab hidden and comes back with it: a
    // board streaming to a tab nobody sees holds the hub's one relay open.
    document.addEventListener("visibilitychange", () => {
      if (!this.viewOn()) return;
      if (!document.hidden) return this.showView();
      this.stopImg();
      if (!this.autoFaceOn()) this.closeCam();
    });

    // Logged out, only the login box shows ("login first before do
    // everything" for the voice app).
    document.addEventListener("mice-auth", e => {
      const authed = e.detail && e.detail.authed;
      ["down", "ready", "answerCard", "settings"].forEach(id => {
        const el = this.$(id);
        if (el && el.classList) el.classList.toggle("mg-off", !authed);
      });
    });

    miceLogin.mount(this.$("loginHere"));
    this.load();
    this.pollFace();
    if (!this._faceInterval) {
      // Every second while the page is seen: with the watcher up an answer
      // is a local read, and a slower timer was half of the delay (A42-4).
      this._faceInterval = setInterval(() => { if (!document.hidden) this.pollFace(); }, 1000);
    }
    this.loadCamera();
  }

}
window.voiceApp = new VoiceApp();
// The page's buttons call these by name (onclick="...").
window.load = (...args) => window.voiceApp.load(...args);
window.talk = (...args) => window.voiceApp.talk(...args);
window.startConv = (...args) => window.voiceApp.startConv(...args);
window.stopConv = (...args) => window.voiceApp.stopConv(...args);
window.ask = (...args) => window.voiceApp.ask(...args);
window.speak = (...args) => window.voiceApp.speak(...args);
window.speakAndWait = (...args) => window.voiceApp.speakAndWait(...args);
window.doMove = (...args) => window.voiceApp.doMove(...args);
window.loadStores = (...args) => window.voiceApp.loadStores(...args);
window.postConfig = (...args) => window.voiceApp.postConfig(...args);
window.postFaqs = (...args) => window.voiceApp.postFaqs(...args);
window.fillAnswers = (...args) => window.voiceApp.fillAnswers(...args);
window.showTab = (...args) => window.voiceApp.showTab(...args);
window.findAnswers = (...args) => window.voiceApp.findAnswers(...args);
window.addAnswerRow = (...args) => window.voiceApp.addAnswerRow(...args);
window.saveAnswers = (...args) => window.voiceApp.saveAnswers(...args);
window.undoAnswers = (...args) => window.voiceApp.undoAnswers(...args);
window.pickAskLang = (...args) => window.voiceApp.pickAskLang(...args);
window.tryVoice = (...args) => window.voiceApp.tryVoice(...args);
window.pickOneVoice = (...args) => window.voiceApp.pickOneVoice(...args);
window.pickScenario = (...args) => window.voiceApp.pickScenario(...args);
window.addScenario = (...args) => window.voiceApp.addScenario(...args);
window.tryScenario = (...args) => window.voiceApp.tryScenario(...args);
window.loadModel = (...args) => window.voiceApp.loadModel(...args);
window.unloadModel = (...args) => window.voiceApp.unloadModel(...args);
window.startVoiceService = (...args) => window.voiceApp.startVoiceService(...args);
window.openReconize = (...args) => window.voiceApp.openReconize(...args);
window.whoAmI = (...args) => window.voiceApp.whoAmI(...args);
window.pickCamera = (...args) => window.voiceApp.pickCamera(...args);
window.toggleAutoFace = (...args) => window.voiceApp.toggleAutoFace(...args);
window.toggleView = (...args) => window.voiceApp.toggleView(...args);
window.toggleFaces = (...args) => window.voiceApp.toggleFaces(...args);
window.convRecord = (...args) => window.voiceApp.convRecord(...args);
window.convRms = (...args) => window.voiceApp.convRms(...args);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.voiceApp.init(), {once: true});
} else {
  window.voiceApp.init();
}
