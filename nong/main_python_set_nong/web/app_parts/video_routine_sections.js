// When a camera cut cannot be linked reliably, keep the observed local dance
// as a separate, source-windowed project instead of inventing a person match.
class VideoRoutineSections {
  static observations(group) {
    const leader = group.slice().sort((a, b) => b.reduce((sum, row) => sum + row.actor.confidence, 0) - a.reduce((sum, row) => sum + row.actor.confidence, 0))[0]?.[0]?.actor.id;
    const selected = new Map();
    for (const row of group.flat()) {
      const old = selected.get(row.index);
      if (!old || row.actor.id === leader || (old.id !== leader && row.actor.confidence > old.confidence)) selected.set(row.index, row.actor);
    }
    return selected;
  }
  static build(units, frames, options, config, qualified) {
    const sections = [];
    for (const unit of units) {
      if (qualified.has(unit.parentId) && !unit.ambiguous) continue;
      const indexes = [...unit.observations.keys()].sort((a, b) => a - b), first = indexes[0], last = indexes.at(-1);
      const from = frames[first].t, to = frames[last].t;
      if (to - from < config.minimumSegmentSeconds) continue;
      const policy = new VideoTemporalPolicy(options.learned === false ? null : VIDEO_POLICY, options.cameraMode);
      const local = frames.slice(first, last + 1).map((frame, offset) => {
        const actor = unit.observations.get(first + offset);
        const state = policy.step(actor?.body || null, frame.scene, offset === 0, actor && actor.confidence >= VIDEO_FOLLOW.tracking.confidence ? 1 : 0);
        return { ...frame, ...state, t: frame.t - from, w: actor?.w || null, p: actor?.p || null, track: actor?.id || null };
      });
      sections.push({ id: 'scene_' + unit.shot + '_' + unit.ordinal, kind: 'segment', parentId: unit.parentId,
        sourceStart: from, sourceEnd: to, frames: local, crossShotUncertain: unit.ambiguous,
        ambiguous: false, people: unit.people,
        coverage: local.filter(f => f.w).length / local.length,
        trustedCoverage: local.filter(f => f.w && f.trusted).length / local.length });
    }
    return sections.sort((a, b) => a.sourceStart - b.sourceStart || b.trustedCoverage - a.trustedCoverage);
  }
}
