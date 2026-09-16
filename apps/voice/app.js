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
    this.initialized = false;
  }


  say(msg){ this.$("stat").textContent = msg; }

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
  const p = r.parts || {};
  window._parts = p;
  this.$("parts").textContent = (p.faq || "?") + " · speech " + (p.stt || "?")
                         + " · voice " + (p.tts || "?")
                         + " · model " + (p.llm || "?");
  // Conversation mode needs STT; show it when speech-in is loaded or loading.
  const sttOk = p.stt && p.stt !== "off in config/voice.json"
                && !p.stt.startsWith("could not");
  this.$("convStart").hidden = !sttOk;
  this.say("ready");
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

  async startService(){
    const btn = this.$("startVoiceBtn");
    const stat = this.$("startVoiceStat");
    if (btn) btn.disabled = true;
    if (stat) stat.textContent = "Starting voice service…";
    try {
      const res = await fetch("/api/voice/start", { method: "POST" });
      const j = await res.json();
      if (!j.ok) {
        if (btn) btn.disabled = false;
        if (j.need_login && window.miceLogin) {
          if (stat) stat.textContent = "Please log in first to start services.";
          return window.miceLogin.required("log in to start the voice service");
        }
        if (stat) stat.textContent = j.error || "Could not start service.";
        return;
      }
      if (stat) stat.textContent = "Launched! Waiting for model to be ready…";
      for (let i = 0; i < 25; i++) {
        await new Promise(r => setTimeout(r, 1000));
        try {
          const hr = await fetch("/api/voice/health").then(r => r.json());
          if (hr.ok) {
            if (btn) btn.disabled = false;
            if (stat) stat.textContent = "";
            return this.load();
          }
        } catch (e) {}
      }
      if (btn) btn.disabled = false;
      if (stat) stat.textContent = "Still loading in background. Press 'Try again' when ready.";
    } catch(err) {
      if (btn) btn.disabled = false;
      if (stat) stat.textContent = "Failed to send start request.";
    }
  }

  async stopService(){
    const btn = this.$("stopVoiceBtn");
    if (btn) btn.disabled = true;
    this.say("unloading voice models…");
    try {
      const res = await fetch("/api/voice/stop", { method: "POST" });
      const j = await res.json();
      if (!j.ok) {
        if (btn) btn.disabled = false;
        if (j.need_login && window.miceLogin) {
          return window.miceLogin.required("log in to stop the voice service");
        }
        return this.say(j.error || "Could not stop voice service.");
      }
      this.say("voice helper stopped");
      await new Promise(r => setTimeout(r, 600));
      return this.load();
    } catch(err) {
      if (btn) btn.disabled = false;
      this.say("Failed to send stop command.");
    }
  }

// The helper's errors arrive in plain words already — show them as they are,
// only falling back when something answered without one.
  human(err){
  if (!err) return "";
  if (/not running|helper/.test(err)) return "";   // the down-card says it better
  return err;
}

  async talk(){
  if(this.rec && this.rec.state==="recording") return this.rec.stop();
  try {
    const s = await navigator.mediaDevices.getUserMedia({audio:true});
    this.rec = new MediaRecorder(s);
    this.ch = [];
    this.rec.ondataavailable = e => this.ch.push(e.data);
    this.rec.onstop = async () => {
      this.$("talk").textContent = "🎤 Press to talk";
      this.$("wait").textContent = "sending…";
      s.getTracks().forEach(t => t.stop());
      try {
        const r = await fetch("/api/voice/transcribe", {method:"POST", body:new Blob(this.ch)}).then(r=>r.json());
        if(r.ok) { 
          this.$("q").value = r.text; 
          this.$("wait").textContent = "";
          this.ask();
        }
        else this.$("wait").textContent = r.error || "That did not work.";
      } catch(e) { this.$("wait").textContent = "The voice helper stopped answering."; }
    };
    this.rec.start();
    this.$("talk").textContent = "🛑 Stop recording";
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
    stream = await navigator.mediaDevices.getUserMedia({audio:true});
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
      r = await fetch("/api/voice/transcribe", {method:"POST", body:blob,
              signal}).then(r=>r.json());
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

    // 2. Show the question
    this.$("q").value = text;
    
    this.$("answerCard").hidden = false;
    const logDiv = this.$("convLog");
    const userBubble = document.createElement("div");
    userBubble.style.cssText = "align-self:flex-end;background:var(--acc);color:#fff;padding:8px 12px;border-radius:16px;max-width:85%";
    userBubble.textContent = text;
    logDiv.appendChild(userBubble);
    logDiv.scrollTop = logDiv.scrollHeight;

    // 3. Ask
    this.$("wait").textContent = "thinking…";
    let a;
    try {
      a = await fetch("/api/voice/ask", {
        method:"POST",
        headers:{"Content-Type":"application/json"},
        body: JSON.stringify({text: text, history: this.convHistory}),
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

    // 4. Show answer
    this.$("answerCard").hidden = false;
    this.$("answer").textContent = a.answer;
    this.$("source").textContent = a.source === "faq"
      ? "from the saved answers · instant"
      : "from the local model";

    // 5. Speak (if sound on) — wait for playback to finish before cooldown
    if (this.$("sound").checked) {
      await this.speakAndWait(a.answer, signal);
      if (!this.convActive || this.convSession !== mySession + 1) break;
    }

    if (a.move && a.module) {
      const bot = await this.findRobot(a.module);
      if (bot && bot.dev) {
        fetch("/api/stream/voice", {
          method: "POST",
          headers: {"Content-Type": "application/json"},
          body: JSON.stringify({text: a.answer, dev: bot.dev})
        }).catch(e => console.log(e));
        await this.doMove(a);
      }
    }

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
    const aiBubble = document.createElement("div");
    aiBubble.style.cssText = "align-self:flex-start;background:var(--sunk);padding:8px 12px;border-radius:16px;max-width:85%;white-space:pre-wrap";
    aiBubble.textContent = a.answer;
    logDiv.appendChild(aiBubble);
    logDiv.scrollTop = logDiv.scrollHeight;

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

  async ask(){
  const text = this.$("q").value.trim();
  if (!text) { this.$("q").focus(); return; }
  this.$("answerCard").hidden = true;
  this.$("wait").textContent = "thinking — the first question can take a minute "
                        + "while the model loads…";
  try {
    const r = await fetch("/api/voice/ask", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text, history: this.convHistory}),
    }).then(r => r.json());
    if (!r.ok) {
      this.$("answerCard").hidden = false;
      this.$("answer").textContent = r.error || "That did not work — try again.";
      this.$("source").textContent = "";
    } else {
      this.$("answerCard").hidden = false;
      this.$("answer").textContent = r.answer;
      this.$("source").textContent = r.source === "faq"
        ? "from the saved answers · instant"
        : "from the local model";

      // Update conversation history
      this.convHistory.push({role:"user", content:text});
      this.convHistory.push({role:"assistant", content:r.answer});
      if (this.convHistory.length > 16) this.convHistory = this.convHistory.slice(-16);

      const logDiv = this.$("convLog");
      const userBubble = document.createElement("div");
      userBubble.style.cssText = "align-self:flex-end;background:var(--acc);color:#fff;padding:8px 12px;border-radius:16px;max-width:85%";
      userBubble.textContent = text;
      const aiBubble = document.createElement("div");
      aiBubble.style.cssText = "align-self:flex-start;background:var(--sunk);padding:8px 12px;border-radius:16px;max-width:85%;white-space:pre-wrap";
      aiBubble.textContent = r.answer;
      logDiv.appendChild(userBubble);
      logDiv.appendChild(aiBubble);
      logDiv.scrollTop = logDiv.scrollHeight;
      
      this.$("q").value = "";

      if (this.$("sound").checked) await this.speak(r.answer);
      if (r.move && r.module) {
        const bot = await this.findRobot(r.module);
        if (bot && bot.dev) {
          fetch("/api/stream/voice", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({text: r.answer, dev: bot.dev})
          }).catch(e => console.log(e));
        }
        await this.doMove(r);
      }
    }
  } catch(e) {
    this.$("answerCard").hidden = false;
    this.$("answer").textContent = "The voice helper stopped answering. "
                            + "Is it still running?";
    this.$("source").textContent = "";
  }
  this.$("wait").textContent = "";
}

// The rig speaks the answer out loud with this PC's own voice (A20-9) -
// no internet. The helper returns sound bytes; the checkbox remembers
// itself, because a visitor who muted it once should not have to again.
  async speak(text, lang, voice){
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  try {
    const payload = {text: text, lang: lang || ""};
    if (voice) payload.voice = voice;
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify(payload),
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
  async speakAndWait(text, signal){
  this.$("wait").textContent = "saying…";
  this.$("speakingText").textContent = text;
  this.$("speakingNow").hidden = false;
  try {
    const r = await fetch("/api/voice/say", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({text: text, lang: ""}),
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
  this.mvClear();
  this.$("wait").textContent = "looking for " + r.module + "…";
  try {
    const bot = await this.findRobot(r.module);
    if (!bot || !bot.dev) {
      const all = await fetch("/api/modules/all").then(x => x.json()).catch(() => null);
      const here = (((all && all.modules) || [])
                    .map(m => m.name).filter(Boolean).join(", ")) || "none";
      this.$("wait").textContent = "No robot named " + r.module
                            + " answered just now. Here now: " + here + ".";
      return;
    }
    // One show per robot: a second request while it moves is answered in
    // words - never queued, never silently taking the running one over.
    const st = await fetch("/api/play").then(x => x.json()).catch(() => null);
    if (st && st.running && st.dev === bot.dev) {
      this.$("wait").textContent = bot.name + " is already moving "
                            + "- ask again once it stops.";
      return;
    }
    this.$("wait").textContent = "getting the moves…";
    const s = await fetch("/api/seqsteps?name=" + encodeURIComponent(r.move))
                .then(x => x.json());
    if (!s.ok) { this.$("wait").textContent = s.error || "cannot read that move."; return; }
    const p = await fetch("/api/play", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({dev: bot.dev, steps: s.steps,
                            loop: s.loop, name: r.move}),
    }).then(x => x.json());
    if (p.error) { this.$("wait").textContent = p.error; return; }
    this.mvBtn = document.createElement("button");
    this.mvBtn.textContent = "■ Stop the move";
    this.mvBtn.onclick = () => { this.mvClear();
                            fetch("/api/play/stop", {method:"POST"}); };
    this.$("wait").textContent = "";
    this.$("wait").appendChild(this.mvBtn);
    this.mvTimer = setInterval(async () => {
      const st = await fetch("/api/play").then(x => x.json()).catch(() => null);
      if (!st || !st.running) this.mvClear();
    }, 700);
  } catch(e) {
    this.$("wait").textContent = "The robot did not take that move — log in first?";
  }
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
  this.fillAnswers(); this.fillVoice(); this.fillWords(); this.fillAdvanced();
}

  async postConfig(statId){
  this.$(statId).textContent = "";
  this.collectVoice(); this.collectAdvanced();       // every save writes the whole store
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
    row.style.cssText = "justify-content:space-between;"
                      + "border-top:1px solid var(--line);padding-top:var(--sp-2)";
    const label = document.createElement("span");
    label.style.cssText = "flex:1;min-width:0";
    const q0 = (item.questions || [])[0] || "(no question)";
    label.innerHTML = "<b></b><br><span class='mini'></span>";
    label.querySelector("b").textContent = q0
        + (item.questions && item.questions.length > 1
           ? "  +" + (item.questions.length - 1) : "");
    label.querySelector(".mini").textContent =
        (item.answer || "") + (item.move ? "  · 🤖 " + item.module + ": "
                                          + item.move : "");
    const btns = document.createElement("span");
    btns.className = "row";
    [["▶", () => this.hear(item.answer)],
     ["Edit", () => this.openForm(i)],
     ["✕", () => this.delAnswer(i)]].forEach(([t, fn]) => {
      const b = document.createElement("button");
      b.textContent = t;
      b.onclick = fn;
      btns.appendChild(b);
    });
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

  openForm(i){
  this.editAt = i;
  this.fillPick(this.$("aMove"), "(no move)", this.seqs,
           i < 0 ? "" : this.faqs[i].move);
  this.fillPick(this.$("aRobot"), "(no robot)", this.robots,
           i < 0 ? "" : this.faqs[i].module);
  this.$("aQ").value = i < 0 ? "" : (this.faqs[i].questions || []).join("\n");
  this.$("aA").value = i < 0 ? "" : (this.faqs[i].answer || "");
  this.$("aForm").hidden = false;
}

  closeForm(){ this.$("aForm").hidden = true; }

  async saveAnswer(){
  const qs = this.$("aQ").value.split("\n").map(s => s.trim()).filter(Boolean);
  const answer = this.$("aA").value.trim();
  if (!qs.length || !answer) {
    this.$("wait").textContent = "An answer needs at least one way of asking, "
                          + "and what to reply."; return;
  }
  const entry = {questions: qs, answer: answer};
  if (this.$("aMove").value) entry.move = this.$("aMove").value;
  if (this.$("aRobot").value) entry.module = this.$("aRobot").value;
  if (this.editAt < 0) this.faqs.push(entry); else this.faqs[this.editAt] = entry;
  if (await this.postFaqs()) { this.closeForm(); this.fillAnswers();
                          this.$("wait").textContent = "Answer saved."; }
  else this.fillAnswers();               // redraw what really saved
}

  async delAnswer(i){
  this.faqs.splice(i, 1);
  if (await this.postFaqs()) this.fillAnswers();
}

  async hear(text){
  if (text) await this.speak(text);
}

// ---- Voice and language ----------------------------------------------
static SAMPLES = {th: "สวัสดีครับ ผมคือหุ่นยนต์น้อง Mice",
                 en: "Hello, I am the Mice robot",
                 ja: "こんにちは、マイスロボットです",
                 zh: "你好，我是 Mice 机器人"};

static VOICE_PRESETS = {
  th: [
    { id: "th-TH-PremwadeeNeural", name: "Premwadee (Neural หญิง ธรรมชาติ/ลื่นไหล) ⭐" },
    { id: "th-TH-NiwatNeural", name: "Niwat (Neural ชาย ธรรมชาติ/ลื่นไหล) ⭐" },
    { id: "Microsoft Pattara", name: "Microsoft Pattara (Windows ในเครื่อง ชาย)" },
  ],
  en: [
    { id: "en-US-JennyNeural", name: "Jenny (Neural Female Smooth) ⭐" },
    { id: "en-US-GuyNeural", name: "Guy (Neural Male Smooth) ⭐" },
    { id: "Microsoft David", name: "Microsoft David (Windows Local Male)" },
    { id: "Microsoft Zira", name: "Microsoft Zira (Windows Local Female)" },
    { id: "Microsoft Mark", name: "Microsoft Mark (Windows Local Male)" },
  ],
  ja: [
    { id: "ja-JP-NanamiNeural", name: "Nanami (Neural 女性) ⭐" },
    { id: "ja-JP-KeitaNeural", name: "Keita (Neural 男性) ⭐" },
  ],
  zh: [
    { id: "zh-CN-XiaoxiaoNeural", name: "Xiaoxiao (Neural 女性) ⭐" },
    { id: "zh-CN-YunxiNeural", name: "Yunxi (Neural 男性) ⭐" },
  ],
};

  fillVoice(){
  const t = this.cfg.tts || {}, s = this.cfg.stt || {};
  this.$("speakOn").checked = !!t.enabled;
  this.$("listenOn").checked = !!s.enabled;
  const defaultLangs = [
    { id: "th", name: "ไทย (Thai)" },
    { id: "en", name: "English (US)" },
    { id: "ja", name: "日本語 (Japanese)" },
    { id: "zh", name: "中文 (Chinese)" },
  ];
  const langMap = new Map();
  defaultLangs.forEach(d => langMap.set(d.id, d.name));
  const configuredLangs = Object.keys(t.voices || {});
  configuredLangs.forEach(l => {
    if (!langMap.has(l)) langMap.set(l, l);
  });
  this.$("ttsLang").textContent = "";
  langMap.forEach((label, id) => {
    const o = document.createElement("option");
    o.value = id; o.textContent = label;
    this.$("ttsLang").appendChild(o);
  });
  this.$("ttsLang").value = t.language || "th";
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
  const V = (this.cfg.tts && this.cfg.tts.voices) || {};
  const select = this.$("ttsVoice");
  select.textContent = "";

  const defOpt = document.createElement("option");
  defOpt.value = "";
  defOpt.textContent = "(Windows chooses default)";
  select.appendChild(defOpt);

  const presets = VoiceApp.VOICE_PRESETS[lang] || [];
  const current = V[lang] || "";
  let matched = false;

  presets.forEach(p => {
    const o = document.createElement("option");
    o.value = p.id;
    o.textContent = p.name;
    if (p.id === current) {
      o.selected = true;
      matched = true;
    }
    select.appendChild(o);
  });

  if (current && !matched) {
    const o = document.createElement("option");
    o.value = current;
    o.textContent = current;
    o.selected = true;
    select.appendChild(o);
  }
}

  tryVoice(){
  const lang = this.$("ttsLang").value;
  const voice = this.$("ttsVoice").value;
  const sample = VoiceApp.SAMPLES[lang] || "Hello";
  if (voice) {
    this.speak(sample, lang, voice);
  } else {
    this.speak(sample, lang);
  }
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
  const langs = Object.keys((this.cfg.stt || {}).languages || {});
  langs.forEach(lang => {
    const wrap = document.createElement("div");
    wrap.className = "row";
    wrap.style.cssText = "align-items:flex-start;margin-bottom:var(--sp-2)";
    const name = document.createElement("span");
    name.className = "mini";
    name.style.cssText = "flex:0 0 34px;padding-top:6px";
    name.textContent = lang === "th" ? "ไทย" : lang;
    const chips = document.createElement("div");
    chips.style.cssText = "flex:1;display:flex;gap:4px;flex-wrap:wrap";
    const draw = () => {
      chips.textContent = "";
      const words = (this.cfg.stt.languages[lang].bias || "").split(/\s+/)
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
        c.textContent = w + " ✕";
        c.onclick = () => {
          const left = (this.cfg.stt.languages[lang].bias || "").split(/\s+/)
                         .filter(x => x && x !== w);
          this.cfg.stt.languages[lang].bias = left.join(" ");
          draw();
        };
        chips.appendChild(c);
      });
    };
    draw();
    const input = document.createElement("input");
    input.placeholder = lang === "th" ? "คำที่ฟังผิดบ่อย" : "word misheard";
    input.style.cssText = "flex:1 1 110px;min-width:100px;border:1px solid var(--line);border-radius:var(--r-md);background:var(--sunk);color:var(--txt);padding:6px;font:inherit";
    const add = document.createElement("button");
    add.textContent = "Add";
    add.onclick = () => {
      const w = input.value.trim();
      if (!w) return;
      const have = (this.cfg.stt.languages[lang].bias || "").split(/\s+/)
                     .filter(Boolean);
      if (!have.includes(w)) have.push(w);
      this.cfg.stt.languages[lang].bias = have.join(" ");
      input.value = "";
      draw();
    };
    input.addEventListener("keydown", e => { if (e.key === "Enter") add.click(); });
    wrap.appendChild(name);
    wrap.appendChild(chips);
    wrap.appendChild(input);
    wrap.appendChild(add);
    box.appendChild(wrap);
  });
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
  this.cfg.llm.model = this.$("llmModel").value.trim();
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
  }

}
window.voiceApp = new VoiceApp();
window.say = (...args) => window.voiceApp.say(...args);
window.load = (...args) => window.voiceApp.load(...args);
window.down = (...args) => window.voiceApp.down(...args);
window.human = (...args) => window.voiceApp.human(...args);
window.startVoiceService = (...args) => window.voiceApp.startService(...args);
window.stopVoiceService = (...args) => window.voiceApp.stopService(...args);
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
window.openForm = (...args) => window.voiceApp.openForm(...args);
window.closeForm = (...args) => window.voiceApp.closeForm(...args);
window.saveAnswer = (...args) => window.voiceApp.saveAnswer(...args);
window.delAnswer = (...args) => window.voiceApp.delAnswer(...args);
window.hear = (...args) => window.voiceApp.hear(...args);
window.fillVoice = (...args) => window.voiceApp.fillVoice(...args);
window.fillVoices = (...args) => window.voiceApp.fillVoices(...args);
window.tryVoice = (...args) => window.voiceApp.tryVoice(...args);
window.collectVoice = (...args) => window.voiceApp.collectVoice(...args);
window.fillWords = (...args) => window.voiceApp.fillWords(...args);
window.fillAdvanced = (...args) => window.voiceApp.fillAdvanced(...args);
window.collectAdvanced = (...args) => window.voiceApp.collectAdvanced(...args);
if (document.readyState === "loading") {
  document.addEventListener("DOMContentLoaded", () => window.voiceApp.init(), {once: true});
} else {
  window.voiceApp.init();
}