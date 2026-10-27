// Studio's own collision verdict on a whole trajectory (A50-1).
// StudioCollisionGeometry.hit() is the check Studio applies before a move may
// be saved (CLEAR mm + rig extra gap, hand paddles as boxes). Every contender's
// servo motion is judged by it, so "near touch" means the same for all.
// gapMm: the total gap that counts (user 2026-10-27: 5 mm for servo backlash);
// Studio adds RIG.extraClearanceMm to its CLEAR, so extra = gapMm - CLEAR.
// Usage: node studio_eval.cjs <poses.json: [[10 deg]...]> <out.json> [gapMm]
const fs = require('fs'), path = require('path');
const {context} = require(path.resolve(__dirname, '../../qc/data/video_group.cjs'));

const [inPath, outPath, gapMm] = process.argv.slice(2);
const {c, run} = context();
c.P = JSON.parse(fs.readFileSync(inPath, 'utf8'));
if (gapMm) run(`RIG.extraClearanceMm = Math.max(RIG.extraClearanceMm || 0, ${Number(gapMm)} - CLEAR);`);
const hits = run('P.map(p => StudioCollisionGeometry.hit(p.map((v, j) => clampJ(j, v))))');
const reasons = {};
hits.forEach(h => { if (h) reasons[h] = (reasons[h] || 0) + 1; });
fs.writeFileSync(outPath, JSON.stringify({gapMm: run('CLEAR + RIG.extraClearanceMm'), frames: hits.length, flagged: hits.filter(Boolean).length,
  flags: hits.map(h => (h ? 1 : 0)), reasons}));
