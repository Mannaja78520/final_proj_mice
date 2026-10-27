// Runs Nong Studio's own video planner headless and times it (A50-1).
// The planner is NOT copied: qc/data/video_group.cjs loads the real Studio
// parts (vidPicksFor -> vidBuild -> safeKeys/RRT) into a vm context, so what
// is timed and compared is exactly what Studio would make from the same fit.
// Usage: node planner.cjs <analysis.json> <project.json> <out.json> <safeDps> <music 0|1> [repeats]
const fs = require('fs'), path = require('path'), {performance} = require('perf_hooks');
const {context} = require(path.resolve(__dirname, '../../qc/data/video_group.cjs'));

const [analysisPath, projectPath, outPath, safeDps, music, repeats = '3'] = process.argv.slice(2);
const analysis = JSON.parse(fs.readFileSync(analysisPath, 'utf8'));
const project = JSON.parse(fs.readFileSync(projectPath, 'utf8'));
const {c, run} = context();
c.fit = analysis.fit;
c.opts = {...project.video, music: music === '1'};
// JSON has plain {x,y,z}; Studio's assess() needs THREE vectors.
run(`fit.targets = fit.targets.map(b => b && {...b, arms: b.arms.map(a => ({...a,
  upper: new THREE.Vector3(a.upper.x, a.upper.y, a.upper.z), fore: new THREE.Vector3(a.fore.x, a.fore.y, a.fore.z)}))});
  SAFE_DPS = ${Number(safeDps)};`);
const times = [];
let made = null;
for (let k = 0; k < Math.max(1, +repeats); k++) {
  const t0 = performance.now();
  made = run('vidBuild(fit, vidPicksFor(fit, opts.tol), opts)');
  times.push(performance.now() - t0);
}
times.sort((a, b) => a - b);
fs.writeFileSync(outPath, JSON.stringify({
  keys: made.keys, safeDps: Number(safeDps), music: c.opts.music, partial: made.partial,
  safe: made.safe, computeMs: times[times.length >> 1], computeRunsMs: times,
  studioScore: made.achieved && {meanBoneDegrees: made.achieved.meanBoneDegrees, worstBoneDegrees: made.achieved.worstBoneDegrees},
}));
console.log(`planner safeDps=${safeDps} music=${c.opts.music} keys=${made.keys.length} median ${times[times.length >> 1].toFixed(0)} ms`);
