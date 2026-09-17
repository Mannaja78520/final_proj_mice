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
    this.autoDetect = true;
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
  }


  say(msg){ this.$("stat").textContent = msg; }

  async pollFace(){
    try {
      // With a station picked, ask who THAT camera sees - the face app is
      // already watching it, so Voice reads the result instead of opening
      // a second camera on the same lens.
      const q = this.camStation ? "?camera=" + encodeURIComponent(this.camStation) : "";
      const r = await fetch("/api/voice/face" + q).then(res => res.json()).catch(() => null);
      if (r && r.ok) {
        this.updateFace(r.person || "");
      }
    } catch(e) {}
  }

  updateFace(person){
    this.currentPerson = (person || "").trim();
    const badge = this.$("faceBadge");
    const nameEl = this.$("faceName");
    if (!badge || !nameEl) return;
    if (this.currentPerson) {
      nameEl.textContent = this.currentPerson;
      badge.style.borderColor = "var(--ok, #10b981)";
      badge.style.color = "var(--ok, #10b981)";
      badge.title = "Recognized person: " + this.currentPerson;
    } else {
      nameEl.textContent = "No face";
      badge.style.borderColor = "var(--line, #ddd)";
      badge.style.color = "var(--dim, #888)";
      badge.title = "No recent face recognized (within 120s)";
    }
  }

  // ---- the camera on THIS device -----------------------------------------
  // One frame at a time, sent to /api/voice/identify, which asks the face app
  // with persist=false: no picture is kept anywhere (user 2026-09-18: *do not
  // save the picture of it because it took my rom*). The camera is let go in
  // every exit - a page that leaves the light on looks like it is recording.
  //
  // Which camera is NOT a new setting: the face app already stores an
  // app-wide default as the device LABEL, and this page asks the helper for
  // it (/api/voice/camera). A choice made here is this browser's own
  // override, kept in localStorage, which is how their kiosk does it too.
  camPicked(){
    try { return localStorage.getItem(this.CAM_KEY) || ""; } catch(e) { return ""; }
  }

  async fillCameras(){
    const sel = this.$("camPick");
    // globalThis, not a bare navigator: this class is also loaded outside a
    // browser by a check, where a bare navigator throws on sight.
    const media = globalThis.navigator && globalThis.navigator.mediaDevices;
    if (!sel || !media) return;
    const cams = (await navigator.mediaDevices.enumerateDevices())
                   .filter(d => d.kind === "videoinput");
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
    }
    sel.hidden = false;
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
      return;
    }
    if (auto) auto.disabled = false;
    if (this.camStream) {                      // swap the camera under a watch
      this.closeCam();
      if (auto && auto.checked) this.openCam().catch(() => {});
    }
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
    this.$("camBox").hidden = false;
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
    if (r.ok && r.person) {
      this.updateFace(r.person);
      if (line) line.textContent = "";
    } else if (line) {
      line.textContent = r.error || "nobody I know is in front of the camera";
    }
    return r;
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
      if (!this.autoFaceOn()) this.closeCam();
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
    if (!on) return this.closeCam();
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
      this.camDefaultLabel = r.label || "";
      this.camSeconds = r.seconds || 5;
      this.camStations = r.stations || [];
      const picked = this.camPicked();
      this.camStation = picked.startsWith("station:") ? picked.slice(8) : "";
      const box = this.$("autoFace");
      if (this.camStation && box) box.disabled = true;
      let want = "";
      try { want = localStorage.getItem(this.CAM_KEY + "_auto") || ""; } catch(e) {}
      if (box && want && !box.checked) { box.checked = true; this.toggleAutoFace(); }
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

  syncLanguageUI(lang){
    if (!lang || !this.autoDetect) return;
    const ttsLang = this.$("ttsLang");
    if (ttsLang && ttsLang.value !== lang) {
      ttsLang.value = lang;
      if (typeof this.fillVoices === "function") this.fillVoices();
    }
  }

  async load(){
  this.$("retry").hidden = true;
  this.$("down").hidden = true;
  this.$("ready").hidden = true;
  this.say("checking the voice helper…");
  let r;
  try {
    r = await fetch("/api/voice/health").then(r => r.json());
  } catch(e) { return this.down("The hub did not answer."); }
  if (!r.ok) return this.down(this.human(r.error));
  this.$("down").hidden = true;
  this.$("ready").hidden = false;
  this.$("setRow").hidden = false;          // settings exist only while helper runs
  if (this.cfg === null) this.loadStores();
  const p = r.parts || {};
  this.updateParts(p);

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
  this.say("ready");
}

  updateParts(p){
  window._parts = p;
  const partsEl = this.$("parts");
  if (partsEl) {
    partsEl.textContent = (p.faq || "?") + " · speech " + (p.stt || "?")
                       + " · voice " + (p.tts || "?")
                       + " · model " + (p.llm || "?");
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
      btnUnload.textContent = "Unload Model";
    } else if (isLoaded) {
      btnLoad.disabled = false;
      btnLoad.textContent = "Load Model";
      btnUnload.disabled = false;
      btnUnload.textContent = "Unload Model";
    } else {
      btnLoad.disabled = false;
      btnLoad.textContent = "Load Model";
      btnUnload.disabled = true;
      btnUnload.textContent = "Unload Model";
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
  this.say("the voice helper is off");
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
      this.$("talk").textContent = "Press to talk";
      this.$("wait").textContent = "sending…";
      s.getTracks().forEach(t => t.stop());
      try {
        const langParam = this.autoDetect ? "auto" : (this.$("ttsLang")?.value || "th");
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
    this.$("talk").textContent = "Stop recording";
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
    const blob = await this.convListenOnce();
    if (!blob || !this.convActive || this.convSession !== mySession + 1) break;

    // 1. Transcribe
    this.$("wait").textContent = "listening…";
    let r;
    try {
      const langParam = this.autoDetect ? "auto" : (this.$("ttsLang")?.value || "th");
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
    if (this.autoDetect) this.syncLanguageUI(detectedLang);

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
        payload.lang = this.$("ttsLang")?.value || this.cfg?.tts?.language || "th";
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
    if (this.autoDetect && a.lang) this.syncLanguageUI(a.lang);
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
      const convSpeakLang = this.autoDetect ? (a.lang || detectedLang) : (this.$("ttsLang")?.value || "th");
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
  if (this.autoDetect) this.syncLanguageUI(detectedLang);
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
      payload.lang = this.$("ttsLang")?.value || this.cfg?.tts?.language || "th";
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
      if (this.autoDetect && r.lang) this.syncLanguageUI(r.lang);
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
        const speakLang = this.autoDetect ? (r.lang || explicitLang || detectedLang) : (this.$("ttsLang")?.value || "th");
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

// The rig speaks the answer out loud with this PC's own voice (A20-9) -
// no internet. The helper returns sound bytes; the checkbox remembers
// itself, because a visitor who muted it once should not have to again.
  async speak(text, lang, voice = ""){
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  if (!voice && lang && this.cfg && this.cfg.tts && this.cfg.tts.voices) {
    voice = this.cfg.tts.voices[lang] || "";
  }
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text, lang: lang || "", voice: voice || ""}),
    });
    if (!r.ok) { this.$("wait").textContent = (await r.json()).error; this.$("speakingNow").hidden = true; return; }
    const player = new Audio(URL.createObjectURL(await r.blob()));
    player.onended = () => { this.$("wait").textContent = ""; this.$("speakingNow").hidden = true; };
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
  if (!voice && lang && this.cfg && this.cfg.tts && this.cfg.tts.voices) {
    voice = this.cfg.tts.voices[lang] || "";
  }
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text, lang: lang || "", voice: voice || ""}),
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

// ---- Settings (A20-12). The stores live on the brain PC; this page reads
// them through the hub and saves through the same gated doors as everything
// else that can change the rig. The helper picks edits up with no restart.

static MODEL_WORDS = [["base", "Fast"], ["small", "Balanced"],
                     ["medium", "Most accurate"]];

  setAdvanced(on){
  document.body.classList.toggle("adv", !!on);
  try { localStorage.setItem("hub_adv", on ? "1" : "0"); } catch(e) {}
  this.$("advOn").checked = !!on;
}
  toggleSet(){
  const s = this.$("settings");
  s.hidden = !s.hidden;
  if (!s.hidden && this.cfg === null) this.loadStores();
}

  async loadStores(){
  const [c, f] = await Promise.all([
    fetch("/api/voice/config").then(x => x.json()).catch(() => null),
    fetch("/api/voice/faq").then(x => x.json()).catch(() => null),
  ]);
  if (!c || !c.ok) return;                 // the down-card already explains
  this.cfg = c.config;
  this.faqs = (f && f.ok && Array.isArray(f.faqs)) ? f.faqs : [];
  const [ls, ms] = await Promise.all([
    fetch("/api/list?kind=sequences").then(x => x.json()).catch(() => null),
    fetch("/api/modules/all").then(x => x.json()).catch(() => null),
  ]);
  this.seqs = (ls && ls.files) || [];
  this.robots = (((ms || {}).modules) || []).map(m => m.name).filter(Boolean);
  const grSel = this.$("globalRobot");
  if (grSel) {
    const cur = this.globalRobot || grSel.value || "";
    grSel.textContent = "";
    const optPer = document.createElement("option");
    optPer.value = "";
    optPer.textContent = "(Per-answer)";
    grSel.appendChild(optPer);
    const optAll = document.createElement("option");
    optAll.value = "__all__";
    optAll.textContent = "All robots";
    grSel.appendChild(optAll);
    this.robots.forEach(name => {
      const opt = document.createElement("option");
      opt.value = name;
      opt.textContent = name;
      grSel.appendChild(opt);
    });
    if (cur && cur !== "__all__" && !this.robots.includes(cur)) {
      const opt = document.createElement("option");
      opt.value = cur;
      opt.textContent = "(missing) " + cur;
      grSel.appendChild(opt);
    }
    grSel.value = cur;
  }
  this.fillAnswers(); this.fillVoice(); this.fillWords(); this.fillAdvanced();
}

  async postConfig(statId){
  this.$(statId).textContent = "";
  this.collectWords(); this.collectVoice(); this.collectAdvanced();       // every save writes the whole store
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
      "Saving needs a login — the box at the top of this page. Log in there, "
      + "then press Save again.");
    return false;
  }
  if (!r.ok) {
    this.$(statId).textContent = ((await r.json().catch(() => ({}))).error)
                          || "That did not save — try again.";
    return false;
  }
  this.$(statId).textContent = "Saved.";
  return true;
}

  async postFaqs(){
  this.$("wait").textContent = "";
  let r;
  try {
    r = await fetch("/api/voice/faq", {method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({faqs: this.faqs})});
  } catch(e) {
    this.$("wait").textContent = "The voice helper is not answering."; return false;
  }
  if (r.status === 401) {
    this.$("wait").textContent = miceLogin.required(
      "Saving needs a login — the box at the top of this page. Log in there, "
      + "then press Save again.");
    return false;
  }
  if (!r.ok) {
    this.$("wait").textContent = ((await r.json().catch(() => ({}))).error)
                          || "That did not save — try again.";
    return false;
  }
  return true;
}

// ---- Answers ----------------------------------------------------------
  fillAnswers(){
  const box = this.$("ansList");
  box.textContent = "";
  this.$("ansEmpty").hidden = this.faqs.length > 0;
  this.faqs.forEach((item, i) => {
    const row = document.createElement("div");
    row.className = "row";
    row.style.cssText = "justify-content:space-between;align-items:flex-start;"
                      + "border-top:1px solid var(--line);padding:var(--sp-2) 0;gap:8px";
    const label = document.createElement("span");
    label.style.cssText = "flex:1;min-width:0";
    const q0 = (item.questions || [])[0] || "(no question)";
    label.innerHTML = "<b></b><div class='mini multilang-answers' style='margin-top:4px;display:flex;flex-direction:column;gap:2px'></div>";
    label.querySelector("b").textContent = q0
        + (item.questions && item.questions.length > 1
           ? "  +" + (item.questions.length - 1) : "");
    const sub = label.querySelector(".multilang-answers");
    
    // Show answer for each language
    const aTh = item.answer || "";
    const aEn = item.answer_en || "";
    const aJa = item.answer_ja || "";
    const aZh = item.answer_zh || "";
    
    if (aTh) {
      const d = document.createElement("div");
      d.textContent = "TH: " + aTh;
      sub.appendChild(d);
    }
    if (aEn) {
      const d = document.createElement("div");
      d.textContent = "EN: " + aEn;
      sub.appendChild(d);
    }
    if (aJa) {
      const d = document.createElement("div");
      d.textContent = "JA: " + aJa;
      sub.appendChild(d);
    }
    if (aZh) {
      const d = document.createElement("div");
      d.textContent = "ZH: " + aZh;
      sub.appendChild(d);
    }
    const movesToShow = (Array.isArray(item.moves) && item.moves.length > 0)
      ? item.moves
      : (item.move ? [{module: item.module, move: item.move}] : []);

    if (movesToShow.length > 0) {
      const d = document.createElement("div");
      d.style.cssText = "display:flex;gap:4px;flex-wrap:wrap;margin-top:4px;align-items:center";
      movesToShow.forEach(m => {
        if (m.move || m.module) {
          const badge = document.createElement("span");
          badge.className = "badge";
          badge.style.cssText = "font-size:11px;padding:2px 6px;border-radius:4px;background:var(--dim-bg,#eee);color:var(--text);border:1px solid var(--line,#ddd)";
          badge.textContent = "🤖 " + (m.module || "any robot") + ": " + (m.move || "(no move)");
          d.appendChild(badge);
        }
      });
      sub.appendChild(d);
    }

    const btns = document.createElement("span");
    btns.className = "row";
    btns.style.cssText = "gap:4px;flex-wrap:wrap;justify-content:flex-end;flex:0 0 auto";
    
    // Per-language preview buttons
    const playLang = (text, lang) => {
      this.hear(text, lang);
    };
    [
      ["Play TH", () => playLang(item.answer, "th")],
      ["Play EN", () => playLang(item.answer_en || item.answer, "en")],
      ["Play JA", () => playLang(item.answer_ja || item.answer, "ja")],
      ["Play ZH", () => playLang(item.answer_zh || item.answer, "zh")],
    ].forEach(([t, fn]) => {
      const b = document.createElement("button");
      b.textContent = t;
      b.style.cssText = "padding:2px 6px;font-size:11px";
      b.onclick = fn;
      btns.appendChild(b);
    });
    
    const editBtn = document.createElement("button");
    editBtn.textContent = "Edit";
    editBtn.style.cssText = "padding:2px 8px;font-size:12px";
    editBtn.onclick = () => this.openForm(i);
    btns.appendChild(editBtn);

    const delBtn = document.createElement("button");
    delBtn.textContent = "✕";
    delBtn.style.cssText = "padding:2px 8px;font-size:12px";
    delBtn.onclick = () => this.delAnswer(i);
    btns.appendChild(delBtn);

    row.appendChild(label);
    row.appendChild(btns);
    box.appendChild(row);
  });
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

  addMoveRow(module = "", move = "") {
    const container = this.$("extraMoves");
    if (!container) return;
    const row = document.createElement("div");
    row.className = "row move-row";
    row.style.cssText = "gap:6px;align-items:center;margin-top:4px";

    const rSel = document.createElement("select");
    rSel.className = "move-robot-sel";
    rSel.style.cssText = "flex:1 1 130px";
    this.fillPick(rSel, "(no robot)", this.robots, module);

    const mSel = document.createElement("select");
    mSel.className = "move-seq-sel";
    mSel.style.cssText = "flex:1 1 150px";
    this.fillPick(mSel, "(no move)", this.seqs, move);

    const delBtn = document.createElement("button");
    delBtn.type = "button";
    delBtn.className = "mini";
    delBtn.textContent = "✕";
    delBtn.style.cssText = "padding:2px 8px;font-size:12px";
    delBtn.onclick = () => row.remove();

    row.appendChild(rSel);
    row.appendChild(mSel);
    row.appendChild(delBtn);
    container.appendChild(row);
  }

  openForm(i){
  this.editAt = i;
  const item = (i >= 0 && this.faqs[i]) ? this.faqs[i] : null;
  const moves = (item && Array.isArray(item.moves) && item.moves.length > 0)
    ? item.moves
    : (item && (item.move || item.module) ? [{module: item.module, move: item.move}] : []);

  const firstMove = moves[0] || {module: "", move: ""};
  this.fillPick(this.$("aMove"), "(no move)", this.seqs, firstMove.move || "");
  this.fillPick(this.$("aRobot"), "(no robot)", this.robots, firstMove.module || "");

  const extraContainer = this.$("extraMoves");
  if (extraContainer) {
    extraContainer.textContent = "";
    for (let k = 1; k < moves.length; k++) {
      this.addMoveRow(moves[k].module, moves[k].move);
    }
  }

  this.$("aQ").value = !item ? "" : (item.questions || []).join("\n");
  this.$("aA").value = !item ? "" : (item.answer || "");
  if (this.$("aAEn")) this.$("aAEn").value = !item ? "" : (item.answer_en || "");
  if (this.$("aAJa")) this.$("aAJa").value = !item ? "" : (item.answer_ja || "");
  if (this.$("aAZh")) this.$("aAZh").value = !item ? "" : (item.answer_zh || "");
  if (this.$("transStat")) this.$("transStat").textContent = "";
  this.$("aForm").hidden = false;
}

  closeForm(){ this.$("aForm").hidden = true; }

  async autoTranslateAnswers(){
    const stat = this.$("transStat");
    if (stat) stat.textContent = "translating…";
    const aTh = this.$("aA") ? this.$("aA").value.trim() : "";
    const aEn = this.$("aAEn") ? this.$("aAEn").value.trim() : "";
    const aJa = this.$("aAJa") ? this.$("aAJa").value.trim() : "";
    const aZh = this.$("aAZh") ? this.$("aAZh").value.trim() : "";
    const srcText = aTh || aEn || aJa || aZh;
    const qLines = (this.$("aQ").value || "").split("\n").map(s => s.trim()).filter(Boolean);

    if (!srcText && qLines.length === 0) {
      if (stat) stat.textContent = "Type an answer or question first.";
      return;
    }

    try {
      let anyOk = false;
      const ctrl = new AbortController();
      const timer = setTimeout(() => ctrl.abort(), 15000);

      if (srcText) {
        try {
          const res = await fetch("/api/voice/translate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text: srcText, all: true}),
            signal: ctrl.signal
          }).then(r => r.json());
          if (res && res.ok && res.translations) {
            anyOk = true;
            const t = res.translations;
            if (this.$("aA") && (!this.$("aA").value.trim() || srcText === aTh)) this.$("aA").value = t.th || aTh;
            if (this.$("aAEn") && (!this.$("aAEn").value.trim() || srcText === aEn)) this.$("aAEn").value = t.en || aEn;
            if (this.$("aAJa") && (!this.$("aAJa").value.trim() || srcText === aJa)) this.$("aAJa").value = t.ja || aJa;
            if (this.$("aAZh") && (!this.$("aAZh").value.trim() || srcText === aZh)) this.$("aAZh").value = t.zh || aZh;
          }
        } catch(e) {}
      }

      // Translate all question lines in one batch
      if (qLines.length > 0) {
        try {
          const res = await fetch("/api/voice/translate", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({texts: qLines, all: true}),
            signal: ctrl.signal
          }).then(r => r.json());
          if (res && res.ok && Array.isArray(res.results)) {
            anyOk = true;
            const allQ = new Set(qLines);
            res.results.forEach(qt => {
              if (qt) {
                [qt.th, qt.en, qt.ja, qt.zh].forEach(q => {
                  if (q && q.trim()) allQ.add(q.trim());
                });
              }
            });
            this.$("aQ").value = [...allQ].join("\n");
          } else {
            const allQ = new Set(qLines);
            await Promise.all(qLines.map(async line => {
              try {
                const qRes = await fetch("/api/voice/translate", {
                  method: "POST",
                  headers: {"Content-Type": "application/json"},
                  body: JSON.stringify({text: line, all: true}),
                  signal: ctrl.signal
                }).then(r => r.json());
                if (qRes && qRes.ok && qRes.translations) {
                  anyOk = true;
                  const qt = qRes.translations;
                  [qt.th, qt.en, qt.ja, qt.zh].forEach(q => {
                    if (q && q.trim()) allQ.add(q.trim());
                  });
                }
              } catch(e) {}
            }));
            this.$("aQ").value = [...allQ].join("\n");
          }
        } catch(e) {}
      }
      clearTimeout(timer);

      if (stat) {
        stat.textContent = anyOk ? "Translated to 4 languages!" : "Translation completed.";
      }
    } catch(e) {
      if (stat) stat.textContent = "Translation finished.";
    }
  }

  async saveAnswer(){
  const qs = this.$("aQ").value.split("\n").map(s => s.trim()).filter(Boolean);
  let aTh = this.$("aA") ? this.$("aA").value.trim() : "";
  let aEn = this.$("aAEn") ? this.$("aAEn").value.trim() : "";
  let aJa = this.$("aAJa") ? this.$("aAJa").value.trim() : "";
  let aZh = this.$("aAZh") ? this.$("aAZh").value.trim() : "";
  const primary = aTh || aEn || aJa || aZh;
  if (!qs.length || !primary) {
    this.$("wait").textContent = "An answer needs at least one way of asking, "
                          + "and what to reply."; return;
  }
  // Auto-translate any missing language fields before saving
  if (!aTh || !aEn || !aJa || !aZh) {
    this.$("wait").textContent = "translating answers to other languages…";
    try {
      const res = await fetch("/api/voice/translate", {
        method: "POST",
        headers: {"Content-Type": "application/json"},
        body: JSON.stringify({text: primary, all: true})
      }).then(r => r.json());
      if (res.ok && res.translations) {
        const t = res.translations;
        if (!aTh) aTh = t.th || primary;
        if (!aEn) aEn = t.en || primary;
        if (!aJa) aJa = t.ja || primary;
        if (!aZh) aZh = t.zh || primary;
      }
    } catch(e) {}
  }
  const moves = [];
  const r0 = this.$("aRobot") ? this.$("aRobot").value : "";
  const m0 = this.$("aMove") ? this.$("aMove").value : "";
  if (r0 || m0) {
    moves.push({module: r0, move: m0});
  }
  const extraRows = this.$("extraMoves") ? this.$("extraMoves").querySelectorAll(".move-row") : [];
  extraRows.forEach(row => {
    const r = row.querySelector(".move-robot-sel")?.value || "";
    const m = row.querySelector(".move-seq-sel")?.value || "";
    if (r || m) {
      moves.push({module: r, move: m});
    }
  });

  const entry = {
    questions: qs,
    answer: aTh || primary,
    answer_en: aEn || primary,
    answer_ja: aJa || primary,
    answer_zh: aZh || primary,
  };
  if (moves.length > 0) {
    entry.moves = moves;
    if (moves[0].move) entry.move = moves[0].move;
    if (moves[0].module) entry.module = moves[0].module;
  }
  if (this.editAt < 0) this.faqs.push(entry); else this.faqs[this.editAt] = entry;
  if (await this.postFaqs()) {
    this.closeForm();
    this.fillAnswers();
    this.$("wait").textContent = "Answer saved across all languages.";
  } else {
    this.fillAnswers(); // redraw what really saved
  }
}

  async delAnswer(i){
  this.faqs.splice(i, 1);
  if (await this.postFaqs()) this.fillAnswers();
}

  async hear(text, lang = ""){
  if (text) await this.speak(text, lang);
}

  toggleAutoDetect(on){
    this.autoDetect = !!on;
    const b = this.$("autoDetectBeta");
    if (b) b.checked = this.autoDetect;
    const l = this.$("autoDetectLang");
    if (l) l.checked = this.autoDetect;
    try { localStorage.setItem("voice_auto_detect", this.autoDetect ? "1" : "0"); } catch(e) {}
  }

  toggleTestMode(on){
    this.toggleAutoDetect(on);
  }

  runTestPrompt(text, lang){
    this.$("q").value = text;
    this.ask(lang);
  }

// ---- Voice and language ----------------------------------------------
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
  const langs = Object.keys(t.voices || {});
  ["th", "en", "ja", "zh"].forEach(l => { if (!langs.includes(l)) langs.push(l); });
  this.$("ttsLang").textContent = "";
  const langLabels = {th: "ไทย (th)", en: "English (en)", ja: "日本語 (ja)", zh: "中文 (zh)"};
  langs.forEach(l => {
    const o = document.createElement("option");
    o.value = l; o.textContent = langLabels[l] || l;
    this.$("ttsLang").appendChild(o);
  });
  this.$("ttsLang").value = t.language || langs[0] || "th";
  this.fillVoices();
  const row = this.$("modelRow");
  row.textContent = "";
  let known = false;
  VoiceApp.MODEL_WORDS.forEach(([id, word]) => {
    const l = document.createElement("label");
    l.className = "mini";
    l.style.cssText = "display:flex;gap:6px;align-items:center";
    const r = document.createElement("input");
    r.type = "radio"; r.name = "sttModel"; r.value = id;
    r.checked = s.model === id;
    if (r.checked) known = true;
    l.appendChild(r);
    l.appendChild(document.createTextNode(word));
    row.appendChild(l);
  });
  if (!known && s.model) {          // a model the words do not cover: say so
    const l = document.createElement("label");
    l.className = "mini"; l.style.cssText = "display:flex;gap:6px;align-items:center";
    const r = document.createElement("input");
    r.type = "radio"; r.name = "sttModel"; r.value = s.model; r.checked = true;
    l.appendChild(r);
    l.appendChild(document.createTextNode(s.model));
    row.appendChild(l);
  }
}

  fillVoices(){
  const lang = this.$("ttsLang").value;
  const V = (this.cfg.tts && this.cfg.tts.voices) || {};   // a store may not name tts yet
  const names = new Set();
  if (V[lang]) names.add(V[lang]);
  const presets = {
    th: ["th-TH-PremwadeeNeural", "th-TH-NiwatNeural"],
    en: ["en-US-JennyNeural", "en-US-GuyNeural"],
    ja: ["ja-JP-NanamiNeural", "ja-JP-KeitaNeural"],
    zh: ["zh-CN-XiaoxiaoNeural", "zh-CN-YunxiNeural"]
  };
  (presets[lang] || []).forEach(v => names.add(v));
  for (const l of Object.keys(V)) {
    if (V[l]) names.add(V[l]);
  }
  this.fillPick(this.$("ttsVoice"), "(Windows chooses)", [...names].filter(Boolean),
           V[lang] || (presets[lang] && presets[lang][0]) || "");
}

  tryVoice(){
  // The point is to hear the voice AS PICKED, so the picked language rides
  // along; an answer's own this.speak() stays on the venue's default language.
  this.speak(VoiceApp.SAMPLES[this.$("ttsLang").value] || "Hello", this.$("ttsLang").value);
}

  collectVoice(){
  this.cfg.tts = this.cfg.tts || {};
  this.cfg.tts.enabled = this.$("speakOn").checked;
  this.cfg.tts.language = this.$("ttsLang").value;
  this.cfg.tts.voices = this.cfg.tts.voices || {};
  this.cfg.tts.voices[this.cfg.tts.language] = this.$("ttsVoice").value;
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
  ["th", "en", "ja", "zh"].forEach(lang => {
    if (!this.cfg.stt.languages[lang]) this.cfg.stt.languages[lang] = {bias: ""};
  });
  const langs = ["th", "en", "ja", "zh"];
  Object.keys(this.cfg.stt.languages).forEach(l => { if (!langs.includes(l)) langs.push(l); });
  const langLabels = {th: "ไทย", en: "EN", ja: "JA", zh: "ZH"};
  langs.forEach(lang => {
    const wrap = document.createElement("div");
    wrap.className = "row";
    wrap.style.cssText = "align-items:flex-start;margin-bottom:var(--sp-2)";
    const name = document.createElement("span");
    name.className = "mini";
    name.style.cssText = "flex:0 0 44px;padding-top:6px;font-weight:600";
    name.textContent = langLabels[lang] || lang;
    const chips = document.createElement("div");
    chips.style.cssText = "flex:1;display:flex;gap:4px;flex-wrap:wrap";
    const draw = () => {
      chips.textContent = "";
      const words = ((this.cfg.stt.languages[lang] && this.cfg.stt.languages[lang].bias) || "").split(/\s+/)
                      .filter(Boolean);
      if (!words.length) {
        const m = document.createElement("span");
        m.className = "mini";
        m.textContent = lang === "th"
          ? "ยังไม่มีคำที่ต้องช่วย" : "no corrections yet";
        chips.appendChild(m);
      }
      words.forEach(w => {
        const c = document.createElement("button");
        c.type = "button";
        c.textContent = w + " ✕";
        c.onclick = () => {
          const left = ((this.cfg.stt.languages[lang] && this.cfg.stt.languages[lang].bias) || "").split(/\s+/)
                         .filter(x => x && x !== w);
          this.cfg.stt.languages[lang].bias = left.join(" ");
          draw();
        };
        chips.appendChild(c);
      });
    };
    draw();
    const input = document.createElement("input");
    this.biasInputs[lang] = input;
    input.placeholder = lang === "th" ? "คำที่ฟังผิดบ่อย" : "word misheard";
    input.style.cssText = "flex:1 1 110px;min-width:100px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--sunk);color:var(--txt);padding:6px;font:inherit";
    const add = document.createElement("button");
    add.type = "button";
    add.textContent = "Add";
    add.onclick = () => {
      const w = String(input.value || "").trim();
      if (!w) return;
      if (!this.cfg.stt.languages[lang]) this.cfg.stt.languages[lang] = {bias: ""};
      const have = (this.cfg.stt.languages[lang].bias || "").split(/\s+/)
                     .filter(Boolean);
      w.split(/\s+/).forEach(part => {
        if (part && !have.includes(part)) have.push(part);
      });
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

  collectWords(){
    if (!this.cfg.stt || !this.cfg.stt.languages || !this.biasInputs) return;
    Object.keys(this.biasInputs).forEach(lang => {
      const inp = this.biasInputs[lang];
      if (inp && inp.value) {
        const val = String(inp.value).trim();
        if (val) {
          if (!this.cfg.stt.languages[lang]) this.cfg.stt.languages[lang] = {bias: ""};
          const have = (this.cfg.stt.languages[lang].bias || "").split(/\s+/).filter(Boolean);
          val.split(/\s+/).forEach(w => {
            if (w && !have.includes(w)) have.push(w);
          });
          this.cfg.stt.languages[lang].bias = have.join(" ");
          inp.value = "";
        }
      }
    });
    if (typeof this.fillWords === "function") this.fillWords();
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
  this.cfg.llm.enabled = true;
  this.cfg.llm.model = this.$("llmModel").value.trim() || this.cfg.llm.model || "Qwen/Qwen3.5-4B";
  this.cfg.llm.maxTokens = num("llmMax", this.cfg.llm.maxTokens || 512);
}

// The login is a shared component, mounted where the page can see it. One
// session across every page: log in here and the hub knows, and the other way
// round (A25-5).
  init(){
    if (this.initialized) return;
    this.initialized = true;
try { this.$("sound").checked = localStorage.sound === "true"; } catch(e) {}
this.$("sound").addEventListener("change",
                            () => { try { localStorage.sound = this.$("sound").checked; } catch(e) {} });

try { this.setAdvanced(localStorage.getItem("hub_adv") === "1"); }
catch(e) { this.setAdvanced(false); }

try {
  const me = localStorage.getItem("voice_move_enabled");
  this.moveEnabled = (me !== null) ? (me === "1") : true;
  if (this.$("moveOn")) this.$("moveOn").checked = this.moveEnabled;
} catch(e) {}
this.$("moveOn")?.addEventListener("change", () => {
  this.moveEnabled = !!(this.$("moveOn") && this.$("moveOn").checked);
  try { localStorage.setItem("voice_move_enabled", this.moveEnabled ? "1" : "0"); } catch(e) {}
});

try {
  this.globalRobot = localStorage.getItem("voice_global_robot") || "";
  if (this.$("globalRobot")) this.$("globalRobot").value = this.globalRobot;
} catch(e) {}
this.$("globalRobot")?.addEventListener("change", () => {
  this.globalRobot = this.$("globalRobot") ? this.$("globalRobot").value : "";
  try { localStorage.setItem("voice_global_robot", this.globalRobot); } catch(e) {}
});

try {
  const ad = localStorage.getItem("voice_auto_detect");
  this.autoDetect = (ad !== null) ? (ad === "1") : true;
  if (this.$("autoDetectBeta")) this.$("autoDetectBeta").checked = this.autoDetect;
  if (this.$("autoDetectLang")) this.$("autoDetectLang").checked = this.autoDetect;
} catch(e) {}

// Hides everything except the login box when not logged in, enforcing
// the "login first before do everything" rule for the voice app.
document.addEventListener("mice-auth", e => {
  const authed = e.detail && e.detail.authed;
  ["down", "ready", "answerCard", "setRow", "settings"].forEach(id => {
    const el = this.$(id);
    if (el && el.classList) el.classList.toggle("mg-off", !authed);
  });
});

miceLogin.mount(this.$("loginHere"));
this.load();
this.pollFace();
if (!this._faceInterval) {
  this._faceInterval = setInterval(() => this.pollFace(), 2500);
}
this.loadCamera();
  }

}
window.voiceApp = new VoiceApp();
window.say = (...args) => window.voiceApp.say(...args);
window.load = (...args) => window.voiceApp.load(...args);
window.down = (...args) => window.voiceApp.down(...args);
window.human = (...args) => window.voiceApp.human(...args);
window.talk = (...args) => window.voiceApp.talk(...args);
window.convRms = (...args) => window.voiceApp.convRms(...args);
window.convRecord = (...args) => window.voiceApp.convRecord(...args);
window.convListenOnce = (...args) => window.voiceApp.convListenOnce(...args);
window.startConv = (...args) => window.voiceApp.startConv(...args);
window.stopConv = (...args) => window.voiceApp.stopConv(...args);
window.ask = (...args) => window.voiceApp.ask(...args);
window.speak = (...args) => window.voiceApp.speak(...args);
window.speakAndWait = (...args) => window.voiceApp.speakAndWait(...args);
window.mvClear = (...args) => window.voiceApp.mvClear(...args);
window.findRobot = (...args) => window.voiceApp.findRobot(...args);
window.doMove = (...args) => window.voiceApp.doMove(...args);
window.setAdvanced = (...args) => window.voiceApp.setAdvanced(...args);
window.toggleSet = (...args) => window.voiceApp.toggleSet(...args);
window.loadStores = (...args) => window.voiceApp.loadStores(...args);
window.postConfig = (...args) => window.voiceApp.postConfig(...args);
window.postFaqs = (...args) => window.voiceApp.postFaqs(...args);
window.fillAnswers = (...args) => window.voiceApp.fillAnswers(...args);
window.fillPick = (...args) => window.voiceApp.fillPick(...args);
window.addMoveRow = (...args) => window.voiceApp.addMoveRow(...args);
window.openForm = (...args) => window.voiceApp.openForm(...args);
window.closeForm = (...args) => window.voiceApp.closeForm(...args);
window.autoTranslateAnswers = (...args) => window.voiceApp.autoTranslateAnswers(...args);
window.saveAnswer = (...args) => window.voiceApp.saveAnswer(...args);
window.delAnswer = (...args) => window.voiceApp.delAnswer(...args);
window.hear = (...args) => window.voiceApp.hear(...args);
window.toggleAutoDetect = (...args) => window.voiceApp.toggleAutoDetect(...args);
window.toggleTestMode = (...args) => window.voiceApp.toggleTestMode(...args);
window.runTestPrompt = (...args) => window.voiceApp.runTestPrompt(...args);
window.fillVoice = (...args) => window.voiceApp.fillVoice(...args);
window.fillVoices = (...args) => window.voiceApp.fillVoices(...args);
window.tryVoice = (...args) => window.voiceApp.tryVoice(...args);
window.collectVoice = (...args) => window.voiceApp.collectVoice(...args);
window.fillWords = (...args) => window.voiceApp.fillWords(...args);
window.collectWords = (...args) => window.voiceApp.collectWords(...args);
window.fillAdvanced = (...args) => window.voiceApp.fillAdvanced(...args);
window.collectAdvanced = (...args) => window.voiceApp.collectAdvanced(...args);
window.loadModel = (...args) => window.voiceApp.loadModel(...args);
window.unloadModel = (...args) => window.voiceApp.unloadModel(...args);
window.startVoiceService = (...args) => window.voiceApp.startVoiceService(...args);
window.openReconize = (...args) => window.voiceApp.openReconize(...args);
window.whoAmI = (...args) => window.voiceApp.whoAmI(...args);
window.pickCamera = (...args) => window.voiceApp.pickCamera(...args);
window.toggleAutoFace = (...args) => window.voiceApp.toggleAutoFace(...args);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.voiceApp.init(), {once: true});
} else {
  window.voiceApp.init();
}