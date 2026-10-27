// Discover motion groups from the whole clip, rather than a single still or
// apparent gender. Uncertain cross-shot associations form separate fragments.
class VideoRoutineDiscovery {
  constructor(options, config = VIDEO_FOLLOW.routines) { this.options = options; this.config = config; this.frames = []; this.histories = new Map(); }
  static distance(a, b) {
    let sum = 0, count = 0;
    for (let arm = 0; arm < 2; arm++) if (a.arms[arm].ok && b.arms[arm].ok) for (const bone of ['upper', 'fore']) {
      sum += THREE.MathUtils.radToDeg(a.arms[arm][bone].angleTo(b.arms[arm][bone])); count++;
    }
    if (!count) return 180;
    return Math.max(sum / count, THREE.MathUtils.radToDeg(Math.abs(VideoBodyMotion.wrap(a.twist - b.twist))), THREE.MathUtils.radToDeg(Math.abs(a.roll - b.roll)));
  }
  add(frame) {
    if (frame.cut) this.histories.clear();
    const actors = (frame.actors || []).map(actor => {
      const history = this.histories.get(actor.id) || [];
      history.push(actor.body); if (history.length > 3) history.shift(); this.histories.set(actor.id, history);
      if (history.length < 3) return actor;
      const median = values => values.sort((a, b) => a - b)[1], body = { ...actor.body, arms: actor.body.arms.map(a => ({ ...a })) };
      for (const arm of [0, 1]) for (const bone of ['upper', 'fore']) body.arms[arm][bone] = new THREE.Vector3(...['x', 'y', 'z'].map(axis => median(history.map(b => b.arms[arm][bone][axis])))).normalize();
      body.twist += median(history.map(b => VideoBodyMotion.wrap(b.twist - actor.body.twist)));
      body.roll = median(history.map(b => b.roll)); return { ...actor, body };
    });
    this.frames.push({ ...frame, actors });
  }
  compatible(a, b) {
    const other = new Map(b.map(r => [r.index, r])); let count = 0, sum = 0, different = 0;
    for (const row of a) {
      const match = other.get(row.index); if (!match) continue;
      const error = VideoRoutineDiscovery.distance(row.actor.body, match.actor.body);
      count++; sum += error; if (error > this.config.styleDegrees) different++;
    }
    if (!count) {
      const first = a[0].t > b[0].t ? a[0] : b[0], last = a[0].t > b[0].t ? b.at(-1) : a.at(-1);
      return first.t >= last.t && first.t - last.t <= this.config.joinGapSeconds && Math.abs(first.actor.cx - last.actor.cx) < .12 && VideoRoutineDiscovery.distance(first.actor.body, last.actor.body) < this.config.styleDegrees;
    }
    return count >= this.config.minimumOverlap && sum / count <= this.config.styleDegrees && different / count <= this.config.divergentFraction;
  }
  joinCost(rows, routine) {
    const boundary = VideoRoutineDiscovery.distance(rows[0].actor.body, routine.last.actor.body);
    const past = [...routine.observations].map(([index, actor]) => ({ t: this.frames[index].t, actor }));
    const sample = rows.filter((r, i) => i % 2 === 0 && r.t - rows[0].t <= this.config.signatureSeconds);
    const near = rows[0].t - routine.last.t <= this.config.joinGapSeconds;
    if (sample.length < this.config.minimumSignatureSamples) return near ? boundary : Infinity;
    let repeated = Infinity;
    for (let k = 0; k < past.length; k += 3) {
      if (past[k].t < rows[0].t - VIDEO_FOLLOW.tracking.repeatSeconds) continue;
      let sum = 0, count = 0, cursor = k;
      for (const row of sample) {
        const target = past[k].t + row.t - rows[0].t;
        while (cursor + 1 < past.length && Math.abs(past[cursor + 1].t - target) < Math.abs(past[cursor].t - target)) cursor++;
        if (Math.abs(past[cursor].t - target) > .2) continue;
        sum += VideoRoutineDiscovery.distance(row.actor.body, past[cursor].actor.body); count++;
      }
      if (count >= Math.max(this.config.minimumSignatureSamples, sample.length * .8)) repeated = Math.min(repeated, sum / count);
    }
    return Number.isFinite(repeated) ? (near ? boundary * .25 + repeated * .75 : repeated) : (near ? boundary : Infinity);
  }
  assign(groups, routines) {
    const choices = groups.map(group => {
      const rows = group.flat().sort((a, b) => a.index - b.index);
      const appearance = VideoAppearanceDescriptor.average(rows.map(row => row.actor.appearance));
      return routines.filter(r => rows[0].t >= r.last.t).map(r => {
        const motion = this.joinCost(rows, r), look = VideoAppearanceDescriptor.distance(appearance, r.appearance);
        const cost = Number.isFinite(look) ? Math.min(Number.isFinite(motion) ? motion : this.config.newRoutineCost, this.config.newRoutineCost) * this.config.motionWeight + look * this.config.appearanceWeight : motion;
        return { routine: r, cost };
      }).filter(c => c.cost < this.config.newRoutineCost).sort((a, b) => a.cost - b.cost).slice(0, 4)
        .concat({ routine: null, cost: this.config.newRoutineCost });
    });
    let best = Infinity, picked = [];
    const search = (i, cost, used, path) => {
      if (cost >= best) return;
      if (i === groups.length) { best = cost; picked = path.slice(); return; }
      for (const choice of choices[i]) if (!choice.routine || !used.has(choice.routine)) {
        const next = new Set(used); if (choice.routine) next.add(choice.routine);
        search(i + 1, cost + choice.cost, next, [...path, choice]);
      }
    };
    search(0, 0, new Set(), []);
    return picked.map((choice, i) => ({ ...choice, ambiguous: !!choice.routine && choices[i].some(c => c.routine !== choice.routine && c.cost - choice.cost < this.config.joinMarginDegrees) }));
  }
  finish() {
    const shots = new Map(), common = new Map();
    this.frames.forEach((frame, index) => {
      const visible = (frame.actors || []).filter(a => a.confidence >= VIDEO_FOLLOW.tracking.confidence);
      if (visible.length > 1 && visible.every(a => visible.every(b => VideoRoutineDiscovery.distance(a.body, b.body) <= this.config.styleDegrees)))
        common.set(index, visible.slice().sort((a, b) => b.confidence - a.confidence)[0]);
      if (!shots.has(frame.shot)) shots.set(frame.shot, new Map());
      const tracks = shots.get(frame.shot);
      for (const actor of frame.actors || []) {
        if (!tracks.has(actor.id)) tracks.set(actor.id, []);
        tracks.get(actor.id).push({ index, t: frame.t, actor });
      }
    });
    const routines = [];
    for (const tracks of shots.values()) {
      const groups = [];
      for (const track of tracks.values()) {
        if (track.length < this.config.minimumOverlap) continue;
        const group = groups.find(g => g.every(member => this.compatible(track, member)));
        if (group) group.push(track); else groups.push([track]);
      }
      const assignments = this.assign(groups, routines);
      for (const [groupIndex, group] of groups.entries()) {
        const rows = group.flat().sort((a, b) => a.index - b.index), first = rows[0];
        const assignment = assignments[groupIndex];
        let routine = assignment?.routine;
        if (!routine) { routine = { id: routines.length + 1, observations: new Map(), people: new Set(), ambiguous: false }; routines.push(routine); }
        routine.ambiguous ||= !!assignment?.ambiguous;
        for (const row of rows) {
          const old = routine.observations.get(row.index);
          // Select a real observation, never average different people.
          if (!old || row.actor.confidence > old.confidence) routine.observations.set(row.index, { ...row.actor,
            associationUncertain: !!assignment?.ambiguous && row.t - first.t < this.config.cutHoldSeconds });
          routine.people.add(row.actor.id);
        }
        routine.last = rows.at(-1);
        routine.appearance = VideoAppearanceDescriptor.average([...routine.observations.values()].map(a => a.appearance));
      }
    }
    return routines.map(r => {
      const policy = new VideoTemporalPolicy(this.options.learned === false ? null : VIDEO_POLICY, this.options.cameraMode);
      const frames = this.frames.map((f, i) => {
        // Shared motion is supported by multiple people in THIS frame, not
        // backfilled from a later pose or averaged over incompatible dancers.
        const actor = r.observations.get(i) || common.get(i);
        const state = policy.step(actor?.associationUncertain ? null : actor?.body || null, f.cut ? Math.max(.25, f.scene) : f.scene, f.cut, actor && actor.confidence >= VIDEO_FOLLOW.tracking.confidence ? 1 : 0);
        return { ...f, ...state, w: actor?.w || null, p: actor?.p || null, track: actor?.id || null };
      });
      return { id: r.id, frames, coverage: frames.filter(f => f.w).length / Math.max(1, this.frames.length),
        trustedCoverage: frames.filter(f => f.w && f.trusted).length / Math.max(1, this.frames.length), people: r.people.size, ambiguous: r.ambiguous };
    }).sort((a, b) => b.coverage - a.coverage);
  }
}
