// Studio's own collision verdict on a whole trajectory (A50-1).
// StudioCollisionGeometry.hit() is the check Studio applies before a move may
// be saved (CLEAR mm + rig extra gap, hand paddles as boxes). Every contender's
// servo motion is judged by it, so "near touch" means the same for all.
// extraMm: RIG.extraClearanceMm for this run, added by Studio to its own base gap
// (the caller works it out from the scenario's total gap; user 2026-10-27: backlash).
// Usage: node studio_eval.cjs <poses.json: [[10 deg]...]> <out.json> [extraMm]
const fs = require('fs'), path = require('path');
const {context} = require(path.resolve(__dirname, '../../qc/data/video_group.cjs'));

const [inPath, outPath, extraMm] = process.argv.slice(2);
const {c, run} = context();
c.P = JSON.parse(fs.readFileSync(inPath, 'utf8'));
if (extraMm !== undefined) run(`RIG.extraClearanceMm = ${Number(extraMm)};`);
const hits = run('P.map(p => StudioCollisionGeometry.hit(p.map((v, j) => clampJ(j, v))))');
const reasons = {};
hits.forEach(h => { if (h) reasons[h] = (reasons[h] || 0) + 1; });
fs.writeFileSync(outPath, JSON.stringify({extraMm: run('RIG.extraClearanceMm'), frames: hits.length, flagged: hits.filter(Boolean).length,
  flags: hits.map(h => (h ? 1 : 0)), reasons}));
