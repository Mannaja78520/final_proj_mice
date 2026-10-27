// One owner for Studio motion setup and individual checked waypoints.
let safeMotionEpoch = 0, safeGoalRevision = 0;
let safeMotionTail = Promise.resolve(), safeCancelTail = Promise.resolve(), lastSafeMove = Promise.resolve(true);
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
  return serialCmd(c,{port:device.port,id:device.bus});
}
function withSafeMotion(work) {
  const result = safeMotionTail.catch(() => {}).then(async()=>{await safeCancelTail;return work();});
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
  if(reason!=='sequence takeover') {
    playing=false;entryHold=false;seekToken++;
    if($('playBtn'))$('playBtn').textContent='▶ Play';keepAwake(false);
  }
  if (!currentUser || !device) return Promise.resolve(false);
  const stop=safeCancelTail.catch(()=>{}).then(async () => {
    await hubStop();
    try { await safeDeviceCmd(device,"STOP"); } catch (e) { safeMotionNote("Could not confirm Stop: " + e.message, true); }
    return false;
  });
  safeCancelTail=stop;return stop;
}
function safeStale(epoch, device, revision) {
  return !currentUser || !haveRobot() || epoch !== safeMotionEpoch || device !== safeTarget() || revision !== safeRevision();
}
async function safeIdle(stale, expected, progress) {
  const deadline = performance.now() + 90000;
  while (!stale()) {
    const status = await getStatus();
    if (stale()) return null;
    const q = status.module && status.module.joints;
    if (!Array.isArray(q) || q.length !== NJ || q.some(v => !Number.isFinite(v)))
      throw new Error("the robot did not report its current pose");
    if(progress)progress(status);
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
async function checkedPoseUnlocked(goal, requestedMs, epoch, goalRevision, initial, progress) {
  const device = safeTarget(), revision = safeRevision();
  const hardStale = () => safeStale(epoch,device,revision);
  const replaced = () => goalRevision !== null && goalRevision !== safeGoalRevision;
  const stale = () => hardStale() || replaced();
  const status = initial || await safeTakeover(hardStale);
  if (!status || hardStale()) return false;
  const source = status.module.joints.slice();
  const plan = await planSafeAsync(source,goal,SAFE.budgetMs,SAFE.seed,hardStale);
  if (hardStale()) return false;
  if (plan.fail) { safeMotionNote("Not moved: " + plan.fail,true); return false; }
  const duration = requestedMs || autoTime(source,goal,status.module.speed_dps || speedDps());
  const legs = safeLegKeys(plan.path,{t:duration,hold:0});
  if (plan.how === "around") safeMotionNote("RRT*: going around the body in " + legs.length +
    " checked moves; keeping an extra " + (RIG.extraClearanceMm || 0) + " mm gap.",true);
  let actual = source;
  for (let index=0;index<legs.length;index++) {
    const leg=legs[index];
    if (hardStale() || (index>0 && replaced())) return false;
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
    const arrived = await safeIdle(hardStale,leg.pose,progress);
    if (!arrived) return false;
    actual = arrived.module.joints.slice();
    if (entryHold) { pose=actual.slice();applyPose();renderSliders(); }
  }
  return !stale();
}
async function checkedPose(goal,ms,epoch,goalRevision,target) {
  return withSafeMotion(async () => {
    if(target!==safeTarget() || epoch!==safeMotionEpoch)return false;
    const device=safeDevice();
    try { return await checkedPoseUnlocked(goal,ms,epoch,goalRevision); }
    catch (e) {
      liveAbort();
      try { await safeDeviceCmd(device,"STOP"); } catch (_) {}
      safeMotionNote("Movement stopped: " + e.message,true);
      return false;
    }
  });
}
function safeTimelineSignature() { return keysSignature()+"|"+!!$("loopChk").checked+"|"+safeRevision(); }
function checkedTimeline() {
  return safeTimelineCache && safeTimelineCache.sig===safeTimelineSignature() ? safeTimelineCache.keys : null;
}
// A clock parked on the unchecked timeline (a keyframe click before Run) lands
// on a different move once times are raised or detours added: the same 80 ms
// park became "mid move 1" and Run replayed it. Re-find the same keyframe and
// the same share of its move or hold in the checked list.
function safeClockGroups(K) {
  const groups=[];let at=K.length ? K[0].hold || 0 : 0;
  for(let j=1;j<K.length;j++) {
    const id=K[j].loopReturn ? 'loop' : K[j].src;
    let g=groups[groups.length-1];
    if(!g || g.id!==id) {g={id,start:at,move:0,hold:0};groups.push(g);}
    g.move+=K[j].t || 0;g.hold+=K[j].hold || 0;at+=(K[j].t || 0)+(K[j].hold || 0);
  }
  return {first:K.length ? K[0].hold || 0 : 0,groups,total:at};
}
function safeRemapClock(ms, before, after) {
  const a=safeClockGroups(before), b=safeClockGroups(after);
  if(!(ms>0))return 0;
  if(ms<a.first)return a.first ? b.first*ms/a.first : 0;
  const g=a.groups.find(x=>ms<x.start+x.move+x.hold);
  const n=g && b.groups.find(x=>x.id===g.id);
  if(!n)return g ? Math.min(ms,b.total) : b.total;
  const offset=ms-g.start;
  if(offset<g.move)return n.start+(g.move ? n.move*offset/g.move : 0);
  return n.start+n.move+Math.min(n.hold,offset-g.move);
}
async function ensureSafeTimeline(cancelled = () => false) {
  const sig = safeTimelineSignature();
  if (checkedTimeline()) return true;
  const before = playKeys();
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
  playT=safeRemapClock(playT,before,out);
  safeTimelineCache={sig,keys:out,loop};
  _pkCache=null;
  if(around) safeMotionNote("RRT*: "+around+" move(s) rerouted around the body. The preview and robot use these checked waypoints.",true);
  return true;
}
// Snapshot the validated show. Stop, target changes and edits during upload
// invalidate startup before any native MOVE can reach the board.
async function startCheckedSequence(fromMs, keepCopy = true) {
  const epoch=safeMotionEpoch, device=safeTarget(), revision=safeRevision();
  const sig=safeTimelineSignature();
  const stale=()=>safeStale(epoch,device,revision) || sig!==safeTimelineSignature();
  if(!(await ensureSafeTimeline(stale)) || stale())return null;
  const destination=poseAt(fromMs).slice();
  const {name,yaml}=buildYaml(fromMs);
  const part=fromMs>0 && keyIndexAtMs(fromMs)>0;
  const file=(part ? name+'.part' : name)+'.yaml';
  return withSafeMotion(async()=>{
    if(stale())return null;
    safeActiveDevice=safeDevice();
    // A partial file starts at its retained keyframe. Its original loop
    // closure belongs to the complete show, so a partial run plays once.
    const nativeYaml=part ? yaml.replace(/^loop:\s*true\s*$/m,'loop: false') : yaml;
    await sdUpload(file,nativeYaml);
    if(stale())return null;
    const kept=keepCopy ? await keepLastRun(nativeYaml,file) : '';
    if(stale())return null;
    const initial=await safeTakeover(stale);
    if(!initial || stale())return null;
    if(!(await checkedPoseUnlocked(destination,0,epoch,null,initial)) || stale())return null;
    const reply=await rawCmd('MOVE '+file);
    if(stale()) {await safeDeviceCmd(safeActiveDevice,'STOP');return null;}
    if(!/^OK\b/.test(reply))throw new Error(reply || 'the robot did not start the sequence');
    return {file,name,part,kept};
  });
}
// Direct Web Serial has no native hub clock. Advance one checked move at a
// time, including entry and holds, and draw the board's reported position.
async function directSafePlay(fromMs) {
  const epoch=safeMotionEpoch, device=safeTarget(), revision=safeRevision(),sig=safeTimelineSignature();
  const stale=()=>!playing || safeStale(epoch,device,revision) || sig!==safeTimelineSignature();
  const K=checkedTimeline().map(k=>({...k,pose:k.pose.slice()}));
  const phases=[];let at=0;
  const add=(key,ms,move)=>{if(ms>0)phases.push({key,start:at,end:at+ms,move});at+=ms;};
  add(K[0],K[0].hold || 0,false);
  K.slice(1).forEach(k=>{add(k,k.t,true);add(k,k.hold || 0,false);});
  const draw=(q,time)=>{
    pose=q.slice();playT=time;applyPose();renderSliders();
    $('scrub').value=at ? Math.round(time/at*1000) : 0;
    $('tlTime').textContent=(time/1000).toFixed(1)+'s / '+(at/1000).toFixed(1)+'s';
  };
  const hold=async(ms,update)=>{
    const start=performance.now();
    while(!stale() && performance.now()-start<ms) {
      if(update)update(performance.now()-start);
      await new Promise(r=>setTimeout(r,40));
    }
  };
  entryHold=true;
  // no board show here, so the music pace is asked for by hand and handed back
  const music=planPace(K)==='music';
  return withSafeMotion(async()=>{try {
    let status=await safeTakeover(stale);
    if(!status || stale())return false;
    if(music) await rawCmd('PACE MUSIC').catch(()=>'');   // an older board: moves just run slower
    if(!(await checkedPoseUnlocked(poseAt(fromMs),0,epoch,null,status,s=>draw(s.module.joints,fromMs))) || stale())return false;
    let cursor=fromMs;
    do {
      for(const phase of phases) {
        if(phase.end<=cursor)continue;
        if(stale())return false;
        const start=Math.max(cursor,phase.start),duration=phase.end-start,clock=performance.now();
        if(phase.move) {
          status=await safeIdle(stale);
          if(!status || stale())return false;
          if(!(await checkedPoseUnlocked(phase.key.pose,duration,epoch,null,status,s=>
            draw(s.module.joints,Math.min(phase.end,start+performance.now()-clock)))) || stale())return false;
          await hold(Math.max(0,duration-(performance.now()-clock)));
        } else await hold(duration,elapsed=>draw(phase.key.pose,start+elapsed));
        if(stale())return false;
        draw(phase.key.pose,phase.end);cursor=phase.end;
      }
      cursor=0;
    }while($('loopChk').checked && !stale());
    return !stale();
  }catch(e){await cancelSafeMotion('direct playback failed');safeMotionNote('Playback stopped: '+e.message,true);return false;}
  finally {
    if(music) await rawCmd('PACE NORMAL').catch(()=>'');
    if(epoch===safeMotionEpoch) {playing=false;entryHold=false;$('playBtn').textContent='▶ Play';keepAwake(false);}
  }});
}
