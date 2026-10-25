/* Board motion completes through fresh status, not the command's acceptance. */
class GachaMotion {
  constructor({machine, refresh, post, tell, pollMs = 500, timeoutMs = 180000}) {
    Object.assign(this, {machine, refresh, post, tell, pollMs, timeoutMs});
    this.jobs = new Map();
  }

  async stop(i) {
    const m = this.machine(i);
    if (!m) return;
    const a = await this.post({machine: m.id, cmd: "STOP"});
    this.tell(a.ok ? "Stop requested; checking the board…" : this.error(a));
    await this.refresh();
  }

  error(a) { return a.says || (a.data && (a.data.reply || a.data.error)) || "The machine did not answer"; }

  async run(i, cmd, label, {test = false} = {}) {
    const m = this.machine(i);
    if (!m || this.jobs.has(m.id)) return;
    const id = m.id;
    this.jobs.set(id, cmd);
    try {
      const a = await this.post({machine: id, cmd});
      if (!a.ok) { this.tell(this.error(a)); return; }
      this.tell(label + ": accepted; waiting for the board…");
      const deadline = Date.now() + this.timeoutMs;
      while (Date.now() < deadline) {
        if (await this.refresh() === false) throw new Error("Status unavailable; completion is unknown");
        const current = this.machine(i);
        if (!current || current.id !== id) throw new Error("Machine selection changed; completion is unknown");
        const s = current.live || {};
        if (s.error) throw new Error(s.error);
        const result = s.motion_result;
        if (s.state === "idle") {
          const complete = result === "done" && (!test || (s.test_total > 0 && s.test_done === s.test_total));
          this.tell(complete ? label + ": board reports done" + (test ? " (" + s.test_done + "/" + s.test_total + " pockets)" : "")
            : label + ": " + (result || "completion unknown") + "; check the machine");
          return complete;
        }
        const progress = test ? " " + (s.test_done || 0) + "/" + (s.test_total || "?") + " pockets;" : "";
        this.tell(label + ":" + progress + " " + (s.phase || s.state || "waiting") +
          (s.phase_ms_left ? " (" + s.phase_ms_left + " ms left)" : ""));
        await new Promise(resolve => setTimeout(resolve, this.pollMs));
      }
      throw new Error("Still waiting for completion; check the machine or press Stop motion");
    } catch (e) {
      this.tell(label + ": " + e.message);
      return false;
    } finally {
      this.jobs.delete(id);
    }
  }
}
