"""RRT* and clothing clearance use the real Studio geometry and settings."""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "RRT star rechecks rounded paths and keeps the clothing gap"
SLOW = True

DRIVER = r"""
(async function(){
  const mark = async (name, yes) => {
    await rawCmd('MOVE QCMARK STAR~' + name + '=' + !!yes);
  };
  let rig, settings;
  try {
    if (!(await qcWaitFor(() => currentUser && typeof planSafeAsync === 'function' && RIG)))
      throw new Error('Studio not ready');
    rig = JSON.parse(JSON.stringify(RIG)); settings = {...SAFE};
    RIG.extraClearanceMm = 0;
    const rnd = safeRng(67), samples = [];
    let pair, hit;
    for (let n = 0; n < 600 && (!pair || !hit); n++) {
      const q = RIG.min.map((lo, j) => lo + rnd()*(RIG.max[j]-lo));
      if (collisionAt(q)) { hit = hit || q; continue; }
      for (const a of samples) if (pathHit(a,q)) {pair = pair || [a,q]; break;}
      if (samples.length < 35) samples.push(q);
    }
    await mark('scene', pair && hit);
    if (!pair || !hit) throw new Error('No actual blocked move found');
    await mark('sourceRejected', !!planSafe(hit,pair[1],100).fail);
    await mark('nanPoseRejected', !!planSafe(pair[0],Array(NJ).fill(NaN),100).fail);
    await mark('nanSettingRejected', !loadSafeSettings({checkDeg:'oops'}) && !!planSafe(...pair,100).fail);
    loadSafeSettings(settings);
    await mark('unknownPlannerRejected', !loadSafeSettings({planner:'typo'}) && !!planSafe(...pair,100).fail);
    loadSafeSettings(settings);
    const plan = planSafe(...pair,3000,11);
    const clean = !plan.fail && plan.path[0].every((v,j)=>v===pair[0][j]) &&
      plan.path.every((q,i)=>!safePoseError(q) && (!i || !pathHit(plan.path[i-1],q)));
    await mark('wirePath', clean && plan.planner==='rrt-star');
    // Exercise the same RRT* search long enough for real parent choice/rewiring.
    const stats = {rewires:0,parentChoices:0,improvements:0};
    const originalOptimize = SAFE.optimizeMs; SAFE.optimizeMs=400;
    const search = rrtStar(...pair,1200,safeRng(17),performance.now(),stats);
    let value; do {value=search.next();} while(!value.done);
    SAFE.optimizeMs=originalOptimize;
    await mark('rewiring', value.value && stats.rewires>0 && stats.parentChoices>0);
    let cancelled=false;
    const pending = planSafeAsync(...pair,2500,41,()=>cancelled);
    cancelled=true;
    await mark('cancel', (await pending).cancelled);
    const a=pair[0].slice(), b=pair[1].slice();
    const pendingRevision=planSafeAsync(a,b,2500,42);
    RIG.extraClearanceMm=1;
    await mark('revision', (await pendingRevision).cancelled);
    RIG.extraClearanceMm=0;
    const q=pair[0];
    const clearBefore=!collisionAt(q);
    RIG.extraClearanceMm=1000;
    await mark('clothesBlock', clearBefore && !!collisionAt(q) && !!planSafe(q,pair[1],100).fail);
    RIG.extraClearanceMm=-1;
    await mark('negativeGapRejected', !!collisionAt(q));
    RIG.extraClearanceMm=0;
    const accepted=setSafetyClearance('14');
    const bundle=JSON.parse(JSON.stringify(collectSettings()));
    RIG.extraClearanceMm=0;
    applySettings(JSON.parse(JSON.stringify(bundle)),'QC');
    await mark('gapRoundtrip', accepted && RIG.extraClearanceMm===14 &&
      JSON.parse(localStorage.getItem('nong_rig')).extraClearanceMm===14 &&
      document.getElementById('clearanceStat').textContent.includes((CLEAR+14)+' mm'));
    await mark('invalidInput', !setSafetyClearance('-5') && RIG.extraClearanceMm===14);
    await mark('emptyInput', !setSafetyClearance('') && RIG.extraClearanceMm===14);
  } catch(error) {
    await rawCmd('MOVE QCMARK STAR~error='+String(error).replace(/[^a-z0-9]/gi,'_').slice(0,100));
  } finally {
    if(rig) {RIG=rig;saveRig();renderRigUI();}
    if(settings) loadSafeSettings(settings);
    await qcMark('done');
  }
})();
"""


def run(t):
    if not browser.available():
        t.give_up("a browser is needed")
    fake_serial.reset()
    base, _ = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" %
                 (base, fake_serial.PORT), seconds=45)
    marks = [m[5:] for m in fake_serial.qc_marks if m.startswith("STAR~")]
    results = dict(m.split("=", 1) for m in marks if "=" in m)
    t.ok("error" not in results, "the checked-motion driver finished", results.get("error"))
    for name, label in [
        ("scene", "actual rig supplies clear endpoints with a blocked transition"),
        ("sourceRejected", "colliding source is refused"),
        ("nanPoseRejected", "invalid angles are refused"),
        ("nanSettingRejected", "bad sampling settings cannot disable collision checking"),
        ("unknownPlannerRejected", "unknown planners fail closed"),
        ("wirePath", "rounded transmitted waypoints are checked from the exact source"),
        ("rewiring", "RRT star performs lower-cost parent selection and neighbor rewiring"),
        ("cancel", "cancelled async planning returns no dispatchable path"),
        ("revision", "changed rig settings cancel an in-progress path"),
        ("clothesBlock", "extra clothing gap changes actual planning decisions"),
        ("negativeGapRejected", "invalid stored gaps fail closed"),
        ("gapRoundtrip", "gap survives actual settings export/import and browser persistence"),
        ("invalidInput", "negative UI gaps preserve the last valid value"),
        ("emptyInput", "empty UI gaps preserve the last valid value"),
    ]:
        t.ok(results.get(name) == "true", label, results)
