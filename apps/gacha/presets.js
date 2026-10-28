"use strict";

// One owner for saving a preset. An event opens only after every save and
// every board acknowledgement succeeds; HTTP 200 alone is not acceptance.
class GachaPreset {
  constructor(ops) {
    this.ops = ops;
    this.busy = false;
  }

  async checked(path, body, stage, ids) {
    const reply = await this.ops.post(path, body);
    if (!reply || !reply.ok || (reply.data && reply.data.ok === false)) {
      throw Error(stage + ": " + ((reply && (reply.says || (reply.data && reply.data.error))) || "No acknowledgement"));
    }
    if (stage === "close" || stage === "name" || stage === "open") {
      const key = stage === "name" ? "name" : "open";
      const sent = reply.data && reply.data.sent && reply.data.sent[key];
      if (!sent || typeof sent !== "object") throw Error(stage + ": Missing board acknowledgements");
      for (const id of ids || Object.keys(sent)) {
        if (!/^OK(?:\b|$)/.test(String(sent[id] || "").trim())) {
          throw Error(stage + " / " + id + ": " + (sent[id] || "Board did not acknowledge"));
        }
      }
    }
    return reply;
  }

  async run() {
    if (this.busy) return {ok: false, busy: true};
    this.busy = true;
    this.ops.setBusy(true);
    let opening = false;
    try {
      const data = this.ops.read();
      const ids = data.machines.map(m => m.id);
      if (!ids.length || ids.some(id => !id) || new Set(ids).size !== ids.length) {
        throw Error("Add machines with unique IDs before starting the event");
      }
      this.ops.tell("loading", "กำลังบันทึกข้อมูล งานจะเปิดหลังบันทึกครบและเครื่องตอบรับ");
      await this.checked("/api/gacha/event", {open: false}, "close");
      await this.checked("/api/gacha/config", {machines: data.machines, items: data.items}, "configuration");
      await this.checked("/api/gacha/rules", data.rules, "rules");
      await this.checked("/api/gacha/event", {name: data.name}, "name", ids);
      opening = true;
      await this.checked("/api/gacha/event", {open: true}, "open", ids);
      opening = false;
      let refreshed = false;
      try { refreshed = await this.ops.refresh(); } catch (e) {}
      this.ops.tell(refreshed ? "ready" : "warn", refreshed
        ? "บันทึกครบและเครื่องตอบรับการเปิดงานแล้ว"
        : "บันทึกและเปิดงานแล้ว แต่โหลดสถานะล่าสุดไม่สำเร็จ กดตรวจสถานะอีกครั้ง");
      return {ok: true, refreshed};
    } catch (error) {
      let message = error.message || String(error);
      if (opening) {
        try { await this.checked("/api/gacha/event", {open: false}, "close"); }
        catch (closeError) { message += "; ยืนยันการปิดงานไม่ได้: " + closeError.message; }
      }
      this.ops.tell("error", "บันทึกหรือเปิดงานไม่สำเร็จ: " + message);
      return {ok: false, error: message};
    } finally {
      this.busy = false;
      this.ops.setBusy(false);
    }
  }
}
window.GachaPreset = GachaPreset;
