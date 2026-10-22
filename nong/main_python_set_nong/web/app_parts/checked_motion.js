// One owner for Studio motion setup and individual checked waypoints.
let safeMotionEpoch = 0, safeGoalRevision = 0;
let safeMotionTail = Promise.resolve(), lastSafeMove = Promise.resolve(true);
let safeTimelineCache = null, timelinePreparing = false;
let safeActiveDevice = null;
function safeDevice() { return {dev:moduleDev(), port:serialPort, bus:busId(), target:safeTarget()}; }
async function safeDeviceCmd(device,c) {
  if (device.dev) {
    const q=new URLSearchParams({dev:device.dev,c});
    const r=await fetch('/api/dev/cmd?'+q);
    if(!r.ok)throw new Error(await r.text());
    return (await r.text()).trim();
  }
  if(device.port!==serialPort || device.bus!==busId())throw new Error('the original cable is no longer selected');
  return serialCmd(c);
}
function withSafeMotion(work) {
  const result = safeMotionTail.catch(() => {}).then(work);
  safeMotionTail = result.catch(() => {});
  return result;
}
function safeTarget() { return moduleDev() + "|" + (boardSafeIdentity || ""); }
function safeMotionNote(text, warning = false) {
  if ($("robotStat")) $("robotStat").textContent = text;
  if ($("tlStat")) $("tlStat").textContent = text;
  if (warning) notice(text);
}
function cancelSafeMotion(reason) {
  const device=safeActiveDevice || (haveRobot() ? safeDevice() : null);
  liveAbort();
  if (!currentUser || !device) return Promise.resolve(false);
  return (async () => {
    await hubStop();
    try { await safeDeviceCmd(device,"STOP"); } catch (e) { safeMotionNote("Could not confirm Stop: " + e.message, true); }
    return false;
  })();
}
function safeStale(epoch, device, revision) {
  return !currentUser || !haveRobot() || epoch !== safeMotionEpoch || device !== safeTarget() || revision !== safeRevision();
}
async function safeIdle(stale, expected) {
  const deadline = performance.now() + 90000;
  while (!stale()) {
    const status = await getStatus();
    if (stale()) return null;
    const q = status.module && status.module.joints;
    if (!Array.isArray(q) || q.length !== NJ || q.some(v => !Number.isFinite(v)))
      throw new Error("the robot did not report its current pose");
    if(typeof status.module.moving!=='boolean' || !status.seq || typeof status.seq.running!=='boolean')
      throw new Error('the robot did not report whether it is moving');
    if (!status.module.moving && !status.seq.running) {
      if (expected && safeGap(q, expected) > 0.15)
        throw new Error("the robot stopped away from the checked waypoint; reconnect before retrying");
      return status;
    }
    if (performance.now() >= deadline) throw new Error("the robot did not confirm that movement finished");
    await new Promise(resolve => setTimeout(resolve, 60));
  }
  return null;
}
async function safeTakeover(stale) {
  if (stale()) return null;
  safeActiveDevice=safeDevice();
  await hubStop();
  if (stale()) return null;
  const reply = await rawCmd("STOP");
  if (!/^OK\b/.test(reply)) throw new Error(reply || "Stop was not acknowledged");
  const status = await safeIdle(stale);
  if (!status) return null;
  const m = status.module;
  if (boardSafeIdentity && String(status.chip || status.id || "") !== boardSafeIdentity)
    throw new Error("a different robot answered; reconnect first");
  for (let j = 0; j < NJ; j++) {
    if (!Array.isArray(m.min) || !Array.isArray(m.max) || !Number.isFinite(m.min[j]) || !Number.isFinite(m.max[j]) ||
        RIG.min[j] < m.min[j] - 0.01 || RIG.max[j] > m.max[j] + 0.01)
      throw new Error("Studio limits exceed the robot limits; match them in Setup before moving");
  }
  return status;
}
// Keep endpoint cues and holds on their original destination; onset cues start
// with the first detour leg. Each eased leg gets the physical minimum time.
function safeLegKeys(path, key) {
  const lengths = path.slice(1).map((q,i) => safeGap(path[i],q));
  const need = path.slice(1).map((q,i) => Math.ceil(Math.max(MIN_MOVE_MS,minTime(path[i],q))));
  const total = lengths.reduce((a,b)=>a+b,0) || 1;
  const spare = Math.max(0,(key.t || 0)-need.reduce((a,b)=>a+b,0));
  return path.slice(1).map((q,i) => ({...key,pose:q.slice(),
    t:Math.ceil(need[i]+spare*lengths[i]/total), hold:i===need.length-1 ? key.hold || 0 : 0,
    cues:i===0 ? (key.cues || []).slice() : [],
    cuesAfter:i===need.length-1 ? (key.cuesAfter || []).slice() : [],
    name:i===need.length-1 ? key.name || "" : "checked detour",via:i!==need.length-1}));
}
async function checkedPoseUnlocked(goal, requestedMs, epoch, goalRevision, initial) {
  const device = safeTarget(), revision = safeRevision();
  const hardStale = () => safeStale(epoch,device,revision);
  const replaced = () => goalRevision !== null && goalRevision !== safeGoalRevision;
  const stale = () => hardStale() || replaced();
  const status = initial || await safeTakeover(stale);
  if (!status || stale()) return false;
  const source = status.module.joints.slice();
  const plan = await planSafeAsync(source,goal,SAFE.budgetMs,SAFE.seed,stale);
  if (stale()) return false;
  if (plan.fail) { safeMotionNote("Not moved: " + plan.fail,true); return false; }
  const duration = requestedMs || autoTime(source,goal,status.module.speed_dps || speedDps());
  const legs = safeLegKeys(plan.path,{t:duration,hold:0});
  if (plan.how === "around") safeMotionNote("RRT*: going around the body in " + legs.length +
    " checked moves; keeping an extra " + (RIG.extraClearanceMm || 0) + " mm gap.",true);
  let actual = source;
  for (const leg of legs) {
    if (stale()) return false;
    // Validate from the reported endpoint of the previous leg, not its target.
    if (safePoseError(actual) || pathHit(actual,leg.pose))
      throw new Error("the reported pose does not have a clear route to the next waypoint");
    const started = performance.now();
    const reply = await rawCmd("POSE " + leg.pose.map(fmtA).join(" ") + " T " + leg.t);
    liveRtt += ((performance.now()-started)-liveRtt)*0.25;
    if (!/^OK\b/.test(reply)) throw new Error(reply || "the robot refused the move");
    if (hardStale()) return false;
    // A newer drag finishes this checked leg, then replaces the remaining
    // route. Stop/Live-off/settings changes cancel immediately after an await.
    const arrived = await safeIdle(hardStale,leg.pose);
    if (!arrived) return false;
    actual = arrived.module.joints.slice();
    if (entryHold) { pose=actual.slice();applyPose();renderSliders(); }
  }
  return !stale();
}
async function checkedPose(goal,ms,epoch,goalRevision,target) {
  return withSafeMotion(async () => {
    if(target!==safeTarget() || epoch!==safeMotionEpoch)return false;
    try { return await checkedPoseUnlocked(goal,ms,epoch,goalRevision); }
    catch (e) {
      liveAbort();
      try { await rawCmd("STOP"); } catch (_) {}
      safeMotionNote("Movement stopped: " + e.message,true);
      return false;
    }
  });
}
function safeTimelineSignature() { return keysSignature()+"|"+!!$("loopChk").checked+"|"+safeRevision(); }
function checkedTimeline() {
  return safeTimelineCache && safeTimelineCache.sig===safeTimelineSignature() ? safeTimelineCache.keys : null;
}
async function ensureSafeTimeline(cancelled = () => false) {
  const sig = safeTimelineSignature();
  if (checkedTimeline()) return true;
  const source = buildPlayKeys().map(k=>({...k,pose:k.pose.slice()}));
  if (!source.length) return false;
  const stale=()=>cancelled() || sig!==safeTimelineSignature();
  const error=safePoseError(source[0].pose);
  if (error) {safeMotionNote("Cannot play: starting pose "+error,true);return false;}
  const out=[source[0]], loop=!!$("loopChk").checked;
  const remaining=source.slice(1);
  if(loop && source.length>1) remaining.push({...source[0],hold:0,cues:[],cuesAfter:[],
    t:autoTime(source[source.length-1].pose,source[0].pose,speedDps()),loopReturn:true});
  let around=0;
  for(const key of remaining) {
    const plan=await planSafeAsync(out[out.length-1].pose,key.pose,SAFE.budgetMs,SAFE.seed,stale);
    if(stale())return false;
    if(plan.fail) {safeMotionNote("Cannot play: "+plan.fail+". Fix the highlighted pose or reduce the extra gap.",true);return false;}
    if(plan.how==='around')around++;
    out.push(...safeLegKeys(plan.path,key));
  }
  if(stale())return false;
  safeTimelineCache={sig,keys:out,loop};
  _pkCache=null;
  if(around) safeMotionNote("RRT*: "+around+" move(s) rerouted around the body. The preview and robot use these checked waypoints.",true);
  return true;
}
