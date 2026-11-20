// Local installed results catalog. The same .nong.json also opens from disk.
class StudioProjectLibrary {
  constructor() { this.items = []; this.serial = 0; }
  async open(selectedId = '') {
    const dialog = $('projectLibrary'); if (!dialog.open) dialog.showModal();
    const status = $('projectLibraryStatus'); status.textContent = 'กำลังโหลดผลงานล่าสุด…';
    try {
      const response = await fetch('/app/latest-results/catalog.json', { cache: 'no-store', signal: AbortSignal.timeout(10000) });
      if (!response.ok) throw new Error('ยังไม่พบรายการผลงานบน Hub เครื่องนี้');
      const catalog = await response.json();
      if (!Array.isArray(catalog.items)) throw new Error('รายการผลงานไม่สมบูรณ์');
      this.items = catalog.items; const list = $('projectLibraryList'); list.replaceChildren();
      for (const item of this.items) {
        if (!item || typeof item.id !== 'string' || typeof item.title !== 'string') continue;
        const url = new URL(item.projectUrl, location.origin);
        if (url.origin !== location.origin || !url.pathname.startsWith('/app/latest-results/bundles/')) continue;
        const row = document.createElement('div'); row.className = 'library-item';
        const label = document.createElement('strong'); label.textContent = item.title;
        const info = document.createElement('span'); info.className = 'hint'; info.textContent = [item.version, item.status].filter(Boolean).join(' · ');
        const button = document.createElement('button'); button.textContent = 'เปิดพร้อมเพลง'; button.className = 'primary';
        button.onclick = () => this.load(item);
        row.append(label, info, button); list.append(row);
        if (item.id === selectedId) { row.classList.add('library-selected'); button.focus(); }
      }
      status.textContent = this.items.length ? 'เลือกชุดงาน หรือเลือกไฟล์ .nong.json ที่ดาวน์โหลดไว้' : 'ยังไม่มีชุดงาน เลือกไฟล์ที่บันทึกไว้ได้';
    } catch (e) { status.textContent = e.message + ' — ยังนำเข้าไฟล์ท่าและเพลงที่ดาวน์โหลดไว้ได้'; }
  }
  async load(item) {
    const generation = ++projectLoadGeneration; const status = $('projectLibraryStatus');
    status.textContent = 'กำลังอ่านท่าและเพลงของ ' + item.title + '…';
    try {
      const response = await fetch(item.projectUrl, { cache: 'no-store', signal: AbortSignal.timeout(15000) });
      if (!response.ok) throw new Error('ไม่พบไฟล์ชุดงาน');
      const project = await response.json();
      if (generation !== projectLoadGeneration) return;
      const opened = await applyProjectData(project, item.id + '.json', { generation, imported: true });
      if (opened) { $('projectLibrary').close(); showTab('sequence'); }
    } catch (e) { if (generation === projectLoadGeneration) status.textContent = e.message + ' — งานเดิมยังอยู่'; }
  }
  async importFile(file) {
    if (!file) return;
    const generation = ++projectLoadGeneration;
    try {
      if (file.size > 48 * 1024 * 1024) throw new Error('ไฟล์ใหญ่เกิน 48 MB');
      const project = JSON.parse(await file.text());
      if (generation !== projectLoadGeneration) return;
      const opened = await applyProjectData(project, file.name.replace(/\.nong\.json$/i, '.json'), { generation, imported: true });
      if (opened) { if ($('projectLibrary').open) $('projectLibrary').close(); showTab('sequence'); }
    } catch (e) { if (generation === projectLoadGeneration) notice('เปิดไฟล์ไม่ได้: ' + e.message + ' งานเดิมยังอยู่'); }
  }
  downloadProject() {
    const blob = new Blob([JSON.stringify(projectSnapshot(), null, 1)], { type: 'application/json' });
    const url = URL.createObjectURL(blob), link = document.createElement('a');
    link.href = url; link.download = cleanName($('projName').value || 'my_move') + '.nong.json'; link.click();
    setTimeout(() => URL.revokeObjectURL(url), 1000);
  }
}
const projectLibrary = new StudioProjectLibrary();
window.StudioProjectLibrary = StudioProjectLibrary;
