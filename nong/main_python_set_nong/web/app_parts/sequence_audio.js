// Browser preview music belongs to the editable project, never to robot SD cues.
class StudioSequenceAudio {
  constructor() {
    this.asset = null; this.media = null; this.preview = false;
    this.tail = null; this.loadSerial = 0;
  }
  signature() { const a = this.asset || this.pendingRef; return a ? [a.sha256, a.name, a.offsetMs || 0].join('|') : ''; }
  serializable() { if (!this.readyForSave()) throw new Error('เพลงที่กู้คืนยังไม่พร้อม เลือกไฟล์ .nong.json อีกครั้ง'); return this.asset ? { ...this.asset } : null; }
  readyForSave() { if (!this.pendingRef) return true; notice('เพลงที่กู้คืนยังไม่พร้อม รอให้โหลดเสร็จ หรือเปิดไฟล์ .nong.json อีกครั้ง'); return false; }
  draftRef() {
    if (this.pendingRef) return { ...this.pendingRef };
    if (!this.asset) return null;
    const { dataUrl, ...ref } = this.asset;
    return ref;  // Audio bytes are in IndexedDB, not the small synchronous draft quota.
  }
  async cache(asset, readOnly = false) {
    return new Promise(resolve => {
      if (!window.indexedDB) return resolve(null);
      const req = indexedDB.open('nong_project_audio', 1);
      req.onupgradeneeded = () => req.result.createObjectStore('tracks');
      req.onerror = () => resolve(null);
      req.onblocked = () => resolve(null);
      req.onsuccess = () => {
        const db = req.result, tx = db.transaction('tracks', readOnly ? 'readonly' : 'readwrite');
        const op = readOnly ? tx.objectStore('tracks').get(asset.sha256) : tx.objectStore('tracks').put(asset, asset.sha256);
        let value = null; op.onsuccess = () => { value = readOnly ? op.result : asset; };
        tx.oncomplete = () => { db.close(); resolve(value); };
        tx.onerror = () => { db.close(); resolve(null); };
        tx.onabort = () => { db.close(); resolve(null); };
      };
    });
  }
  async prepare(input) {
    if (!input) return null;
    let asset = { ...input };
    if (!asset.dataUrl) { const cached = await this.cache(asset, true); asset = cached ? { ...cached, ...asset, dataUrl: cached.dataUrl } : null; }
    if (!asset || typeof asset.dataUrl !== 'string' || !/^data:audio\/[a-z0-9.+-]+;base64,/i.test(asset.dataUrl))
      throw new Error('ไฟล์นี้ไม่มีเพลงที่เปิดได้ เลือกไฟล์ท่าและเพลง .nong.json อีกครั้ง');
    if (asset.dataUrl.length > 48 * 1024 * 1024) throw new Error('ไฟล์เพลงใหญ่เกิน 32 MB');
    const raw = atob(asset.dataUrl.slice(asset.dataUrl.indexOf(',') + 1));
    const bytes = Uint8Array.from(raw, c => c.charCodeAt(0));
    if (!bytes.length || bytes.length > 32 * 1024 * 1024) throw new Error('ขนาดไฟล์เพลงไม่ถูกต้อง');
    const hash = await StudioAudioDigest.sha256(bytes);
    if (asset.sha256 && asset.sha256 !== hash) throw new Error('เพลงไม่ตรงกับไฟล์ที่บันทึกไว้');
    const Context = window.AudioContext || window.webkitAudioContext;
    if (!Context) throw new Error('เบราว์เซอร์นี้ยังอ่านเพลงไม่ได้ ลองเปิดด้วย Edge หรือ Chrome');
    const decoder = new Context();
    try { const decoded = await decoder.decodeAudioData(bytes.buffer.slice(0)); if (!(decoded.duration > 0)) throw new Error('empty audio'); }
    catch (e) { throw new Error('อ่านเพลงไม่ได้ ไฟล์อาจไม่สมบูรณ์'); }
    finally { await decoder.close().catch(() => {}); }
    asset = { ...asset, name: String(asset.name || asset.file || 'เพลง'), sha256: hash,
      offsetMs: Number.isFinite(asset.offsetMs) ? asset.offsetMs : 0 };
    const media = new Audio(asset.dataUrl); media.preload = 'auto';
    await new Promise((resolve, reject) => {
      const timer = setTimeout(() => { clean(); reject(new Error('โหลดเพลงนานเกินไป ลองเลือกไฟล์อีกครั้ง')); }, 15000);
      const clean = () => { clearTimeout(timer); media.onloadedmetadata = media.onerror = null; };
      media.onloadedmetadata = () => { clean(); resolve(); };
      media.onerror = () => { clean(); reject(new Error('เปิดเพลงไม่ได้')); };
      media.load();
    });
    if (!Number.isFinite(media.duration) || media.duration <= 0) throw new Error('ความยาวเพลงไม่ถูกต้อง');
    await this.cache(asset);
    return { asset, media };
  }
  commit(prepared, ownerKeys = keys) {
    ++this.loadSerial;
    this.pendingRef = null; this.restoring = false;
    this.pause();
    if (this.media) { this.media.onerror = null; this.media.removeAttribute('src'); this.media.load(); }
    this.asset = prepared ? prepared.asset : null; this.media = prepared ? prepared.media : null;
    this.ownerKeys = ownerKeys;
    this.preview = !!prepared; this.tail = null; this.poseCache = null;
    const bar = $('sequenceAudioBar'); if (bar) bar.hidden = !prepared;
    if ($('sequenceAudioTitle')) $('sequenceAudioTitle').textContent = prepared ? 'เพลง: ' + this.asset.name : '';
    if (this.media) this.media.onerror = () => { this.pausePreview(); notice('เพลงหยุดเพราะอ่านไฟล์ไม่ได้ ท่ายังคงอยู่ เลือกเพลงใหม่แล้วลองอีกครั้ง'); };
    this.status('พร้อมทดลองในหน้าจอ');
  }
  keysChanged(current) {
    if (this.ownerKeys && this.ownerKeys !== current) {
      ++projectLoadGeneration; this.pausePreview(); this.commit(null, current);
    }
    this.ownerKeys = current;
  }
  restart() {
    this.seek(0);
    if (!this.head) this.media.play().catch(() => { this.pausePreview(); this.status('กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง'); });
  }
  status(text) { if ($('sequenceAudioStatus')) $('sequenceAudioStatus').textContent = text; }
  pause() { if (this.media) this.media.pause(); }
  pausePreview() {
    this.pause();
    if (this.preview) { playing = false; lastPlayMs = 0; keepAwake(false); if ($('playBtn')) $('playBtn').textContent = '▶ Play'; }
    if ($('sequenceAudioPlay')) $('sequenceAudioPlay').textContent = '▶ ทดลองพร้อมเพลง';
  }
  seek(ms) {
    if (!this.media) return;
    const time = Math.max(0, (ms - (this.asset.offsetMs || 0)) / 1000);
    this.media.currentTime = Math.min(time, this.media.duration);
    this.head = ms < (this.asset.offsetMs || 0) ? { at: performance.now(), ms } : null;
    if (this.head) this.media.pause();
    this.tail = time >= this.media.duration ? { at: performance.now(), ms } : null;
  }
  async toggle() {
    if (!this.media) return;
    this.preview = true;
    if (playing) { this.pausePreview(); return; }
    // This path never takes control of a real robot, even with Live checked.
    await togglePlay({ previewOnly: true, sequenceAudio: true });
    if (!playing) return;
    this.seek(playT);
    try {
      if (!this.head && playT < this.media.duration * 1000 + (this.asset.offsetMs || 0)) await this.media.play();
      if ($('sequenceAudioPlay')) $('sequenceAudioPlay').textContent = '❚❚ หยุดชั่วคราว';
      this.status('เล่นเพลงและท่าในหน้าจอ');
    } catch (e) { this.lastPlayError = String(e.name || '') + ': ' + e.message; this.pausePreview(); this.status('กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง'); }
  }
  downloadSong() {
    if (!this.asset) return;
    const link = document.createElement('a'); link.href = this.asset.dataUrl;
    link.download = this.asset.name; link.click();
  }
  clock(ms) {
    if (!this.preview || !this.media || !playing || !previewOnly || entryHold) return null;
    if (this.head) {
      const at = this.head.ms + performance.now() - this.head.at;
      if (at < this.asset.offsetMs) return at;
      this.head = null; this.media.currentTime = 0;
      this.media.play().catch(() => { this.pausePreview(); this.status('กดทดลองพร้อมเพลงอีกครั้งเพื่ออนุญาตเสียง'); });
      return this.asset.offsetMs;
    }
    if (this.media.ended || ms >= this.media.duration * 1000 + (this.asset.offsetMs || 0)) {
      if (!this.tail) this.tail = { at: performance.now(), ms: this.media.duration * 1000 + (this.asset.offsetMs || 0) };
      return this.tail.ms + performance.now() - this.tail.at;  // Explicit silent motion tail.
    }
    if (this.media.paused || this.media.seeking || this.media.readyState < 2) return ms;
    return Math.max(0, this.media.currentTime * 1000 + (this.asset.offsetMs || 0));
  }
  visualPose(ms) {
    if (!$('servoView') || !$('servoView').checked) return poseAt(ms);
    const signature = keysSignature() + '|' + $('loopChk').checked + '|' + JSON.stringify(RIG);
    if (!this.poseCache || this.poseCache.signature !== signature) {
      const start = playKeys().length ? playKeys()[0].pose : poseAt(0);
      this.poseCache = { signature, model: new ServoFollow(start), samples: [start.slice()] };
    }
    const cache = this.poseCache, index = Math.max(0, Math.floor(ms / 20));
    while (cache.samples.length <= index) {
      const at = cache.samples.length * 20;
      cache.samples.push(cache.model.step(poseAt(at), 20).slice());
    }
    return cache.samples[index].slice();
  }
  rewind(ms = 0) {
    this.pausePreview(); this.seek(ms); playT = ms; servoPlay = null;
    pose = poseAt(playT).map((v, i) => clampJ(i, v)); applyPose(); renderSliders(); renderTimeline();
    if ($('scrub')) $('scrub').value = totalMs() ? Math.round(ms / totalMs() * 1000) : 0;
  }
  async restore(ref) {
    if (!ref) { this.commit(null); return; }
    const serial = ++this.loadSerial;
    this.pendingRef = { ...ref }; this.restoring = true; this.preview = true;
    try { const prepared = await this.prepare(ref); if (serial === this.loadSerial) this.commit(prepared); }
    catch (e) { if (serial === this.loadSerial) { this.restoring = false; this.pausePreview(); notice('ท่ากู้คืนแล้ว แต่เพลงยังไม่พร้อม เปิดไฟล์ .nong.json อีกครั้ง: ' + e.message); } }
  }
}
const sequenceAudio = new StudioSequenceAudio();
window.StudioSequenceAudio = StudioSequenceAudio;
