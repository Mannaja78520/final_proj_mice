"""Checked Studio commands wait for arrival and cannot start after cancellation."""
import browser
import fake_serial
import qc as F

AREA = "studio"
TITLE = "checked motion uses reported arrival and cancels stale starts"
SLOW = True

DRIVER = r"""
(async()=>{
  const mark=async(name,ok)=>qcMark('DISPATCH~'+name+'='+!!ok);
  const wait=ms=>new Promise(r=>setTimeout(r,ms));
  let original;
  try {
    await qcStudioReady();await qcWaitFor(()=>!!boardSafeIdentity);
    original={rawCmd,getStatus,sdUpload,fetch,hubStop,safeDeviceCmd,ensureSafeTimeline,startCheckedSequence,hubDriven,serialChain};
    const rng=safeRng(67),clear=[];let pair;
    for(let n=0;n<800 && !pair;n++) {
      const q=RIG.min.map((lo,j)=>+(lo+rng()*(RIG.max[j]-lo)).toFixed(1));
      if(safePoseError(q))continue;
      for(const a of clear)if(pathHit(a,q)){pair=[a,q];break;}
      if(clear.length<40)clear.push(q);
    }
    if(!pair)throw Error('no blocked transition');
    let actual=pair[0].slice(),target=null,polls=0,moving=false;
    let sent=[],overlap=false,dirty=false,missing=false;
    hubStop=async()=>{};
    getStatus=async()=>{
      await wait(10);
      if(moving && ++polls>=3){actual=target.slice();moving=false;}
      return {chip:boardSafeIdentity,seq:{running:false},module:{joints:actual.slice(),
        moving:missing ? undefined : moving,min:RIG.min.slice(),max:RIG.max.slice(),speed_dps:120}};
    };
    rawCmd=async c=>{
      if(c==='STOP'){moving=false;target=null;return original.rawCmd(c);}
      if(c.startsWith('POSE ')) {
        const q=c.split(/\s+/).slice(1,NJ+1).map(Number);
        overlap=overlap || moving;dirty=dirty || !!pathHit(actual,q);
        sent.push(q);target=q;moving=true;polls=0;
        // Real wire remains the assertion boundary; only arrival timing is controlled.
        return original.rawCmd(c);
      }
      return original.rawCmd(c);
    };
    safeDeviceCmd=async(device,c)=>rawCmd(c);
    await original.rawCmd('POSE '+actual.join(' '));
    const ok=await liveSend('POSE '+pair[1].join(' ')+' T 800');
    await mark('arrival',ok && sent.length>=2 && !overlap && !dirty && safeGap(actual,pair[1])<0.11);
    sent=[];missing=true;
    await mark('missingState',!(await liveSend('POSE '+pair[0].join(' '))) && !sent.length);
    missing=false;
    // A queued target belongs to the robot selected when it was requested.
    let release;const blocked=withSafeMotion(()=>new Promise(r=>release=r));
    await qcWaitFor(()=>!!release);
    const queued=liveSend('POSE '+pair[0].join(' '));
    const identity=boardSafeIdentity;boardSafeIdentity+='-changed';release();await blocked;
    await mark('target',!(await queued) && !sent.length);boardSafeIdentity=identity;
    // Native SD startup must not MOVE after Stop arrives during upload.
    keys=[{pose:pair[0].slice(),t:800,hold:0},{pose:pair[1].slice(),t:800,hold:0}];
    bumpKeys();$('loopChk').checked=false;
    let uploaded,uploadRelease,moves=0;
    sdUpload=async()=>{uploaded=true;await new Promise(r=>uploadRelease=r);};
    const guardedRaw=rawCmd;
    rawCmd=async c=>{if(/^MOVE\s/.test(c))moves++;return guardedRaw(c);};
    const start=startCheckedSequence(0,false);
    await qcWaitFor(()=>uploaded,10000);
    await cancelSafeMotion('QC stop during upload');uploadRelease();
    await mark('uploadCancel',!(await start) && moves===0);
    // Config changes during planning similarly leave no POSE to dispatch.
    actual=pair[0].slice();sent=[];
    const motion=liveSend('POSE '+pair[1].join(' '));
    RIG.extraClearanceMm+=1;await cancelSafeMotion('QC gap change');
    await mark('gapCancel',!(await motion) && !sent.length);RIG.extraClearanceMm-=1;
    // Snapshot a hub entry, then edit the timeline while a checked leg starts.
    keys=[{pose:pair[1].slice(),t:800,hold:0},{pose:pair[0].slice(),t:800,hold:0}];bumpKeys();
    actual=pair[0].slice();sent=[];let posts=0,edited=false;
    fetch=async(url,options)=>{
      if(url==='/api/play' && options && options.method==='POST'){posts++;return {json:async()=>({})};}
      return original.fetch(url,options);
    };
    rawCmd=async c=>{const reply=await guardedRaw(c);if(c.startsWith('POSE ') && !edited){edited=true;keys[1].hold=123;bumpKeys();}return reply;};
    const hubResult=await hubPlay(0);
    await mark('editDuringEntry',edited && !hubResult && posts===0);
    rawCmd=guardedRaw;sent=[];moving=false;actual=pair[0].slice();
    // An earlier delayed Stop is a barrier, never a late interruption of the next move.
    let stopRelease,stopCalls=0;
    hubStop=async()=>{if(++stopCalls===1)await new Promise(r=>stopRelease=r);};
    const stopping=cancelSafeMotion('QC delayed stop');
    await qcWaitFor(()=>!!stopRelease);
    const next=liveSend('POSE '+pair[0].join(' '));
    await wait(60);const beforeStop=!sent.length;
    hubStop=async()=>{};stopRelease();await stopping;
    await mark('stopBarrier',beforeStop && await next);
    // Direct playback owns its clock through entry; Live-off releases both.
    keys=[{pose:pair[0].slice(),t:800,hold:0},{pose:pair[1].slice(),t:800,hold:0}];bumpKeys();
    await ensureSafeTimeline();sent=[];moving=false;
    await mark('detourClock',safeGap(poseAt(keyStartMs(1)+keyTravelMs(1)),keys[1].pose)<0.15);
    keys=[keys[0],{...keys[1],off:true}, {...keys[1],hold:400}];bumpKeys();
    $('loopChk').checked=true;await ensureSafeTimeline();
    const selectedEnd=keyStartMs(2)+keyTravelMs(2);
    await mark('detourClockExtras',keyTravelMs(0)===0 &&
      safeGap(poseAt(selectedEnd+200),keys[2].pose)<0.15 && segmentAt(selectedEnd+1)===-1);
    playing=true;
    const direct=directSafePlay(0);
    await qcWaitFor(()=>sent.length>0);
    $('liveChk').checked=false;liveChanged();
    await direct;await safeCancelTail;
    await mark('directCancel',!playing && !entryHold);
    // A truncated native file must not loop across the omitted checked prefix.
    $('loopChk').checked=true;await ensureSafeTimeline();
    let saved='';sdUpload=async(file,text)=>{saved=text;};
    rawCmd=async c=>/^MOVE\s/.test(c) ? 'OK MOVE' : guardedRaw(c);
    const partial=await startCheckedSequence(1,false);
    await mark('partialLoop',partial && /^loop: false$/m.test(saved) && !/^loop: true$/m.test(saved));
    // A POSE accepted after prompt STOP must be followed by a terminal STOP.
    moving=false;actual=pair[0].slice();sent=[];let ackRelease;const delivery=[];
    rawCmd=async c=>{
      if(c.startsWith('POSE ')){await new Promise(r=>ackRelease=r);delivery.push('POSE');}
      if(c==='STOP')delivery.push('STOP');
      return guardedRaw(c);
    };
    const delayed=liveSend('POSE '+pair[1].join(' '));
    await qcWaitFor(()=>!!ackRelease);
    delivery.length=0; // discard takeover STOP; require a new prompt STOP before late delivery
    const cancelled=cancelSafeMotion('QC HTTP stop race');
    await qcWaitFor(()=>delivery.includes('STOP'));
    ackRelease();await delayed;await cancelled;
    await mark('terminalStop',delivery.includes('POSE') && delivery[delivery.length-1]==='STOP' && !moving && sent.length===1);
    rawCmd=guardedRaw;
    // Stop during Run's initial planner must not establish a new generation.
    let planRelease,starts=0;
    ensureSafeTimeline=async()=>new Promise(r=>planRelease=r);
    startCheckedSequence=async()=>{starts++;return null;};
    const run=robotRun();await qcWaitFor(()=>!!planRelease);
    await cancelSafeMotion('QC initial planning stop');planRelease(true);await run;
    await mark('runPlanningStop',starts===0);
    ensureSafeTimeline=original.ensureSafeTimeline;
    // A second Stop takes precedence while handoff awaits its own Stop.
    let handRelease,handStops=0;
    hubStop=async()=>{if(++handStops===1)await new Promise(r=>handRelease=r);};
    hubDriven=()=>false;playing=true;previewOnly=false;handedOff=false;$('liveChk').checked=true;
    const hand=handOffToRobot();await qcWaitFor(()=>!!handRelease);
    const newerStop=cancelSafeMotion('QC stop during handoff');
    handRelease();await hand;await newerStop;
    await mark('handoffStop',starts===0);
    hubStop=async()=>{};hubDriven=original.hubDriven;startCheckedSequence=original.startCheckedSequence;
    // A queued native MOVE is cancelled before touching the serial writer.
    let serialRelease;const writes=[];
    const port={writable:{getWriter:()=>({write:async bytes=>{
      writes.push(new TextDecoder().decode(bytes));
      setTimeout(()=>{for(const w of serialWaiters.splice(0)){const v=w.filter('@7 OK stopped');if(v!==null)w.res(v);}},0);
    },releaseLock(){}})}};
    const previousPort=serialPort;serialPort=port;
    const captured=safeDevice();serialPort=previousPort;
    await mark('directCapture',captured.dev==='' && captured.port===port && captured.target.startsWith('serial:'));
    serialChain=new Promise(r=>serialRelease=r);
    const native=serialCmd('MOVE queued.yaml',{port,id:7});
    await cancelSafeMotion('QC queued native stop');serialRelease();
    const result=await native;
    await serialCmd('MOVE STOP',{port,id:7});
    await mark('serialQueuedStop',result.startsWith('ERR') && writes.length===1 && writes[0]==='#7 MOVE STOP\n');
    rawCmd=async c=>c==='STOP' ? 'ERR unavailable' : guardedRaw(c);
    await mark('stopAcknowledged',(await robotCmd('STOP'))==='' && $('robotStat').textContent.includes('Could not confirm Stop'));
  }catch(e){await qcMark('DISPATCH~error='+String(e).replace(/[^a-z0-9]/gi,'_').slice(0,100));}
  finally {
    liveAbort();
    if(original){rawCmd=original.rawCmd;getStatus=original.getStatus;sdUpload=original.sdUpload;fetch=original.fetch;hubStop=original.hubStop;safeDeviceCmd=original.safeDeviceCmd;ensureSafeTimeline=original.ensureSafeTimeline;startCheckedSequence=original.startCheckedSequence;hubDriven=original.hubDriven;serialChain=original.serialChain;}
    await qcMark('done');
  }
})();
"""


def run(t):
    if not browser.available():
        t.give_up("browser needed")
    fake_serial.reset()
    base, _ = F.start_hub()
    browser.page(DRIVER, query="%s/studio/_qcdriver.html?dev=usb%%3A%s" %
                 (base, fake_serial.PORT), seconds=60)
    results = dict(m[9:].split("=", 1) for m in fake_serial.qc_marks
                   if m.startswith("DISPATCH~") and "=" in m)
    t.ok("error" not in results, "checked-dispatch driver completed", results)
    for key, label in [
        ("arrival", "detour wire commands wait for physical arrival and every actual leg is clear"),
        ("missingState", "missing movement state refuses all poses"),
        ("target", "queued motion cannot adopt a new robot"),
        ("uploadCancel", "Stop during upload prevents native MOVE"),
        ("gapCancel", "changed clearance cancels pending poses"),
        ("editDuringEntry", "editing a show during entry prevents unchecked hub startup"),
        ("stopBarrier", "a delayed old Stop completes before a new checked move starts"),
        ("directCancel", "Live off cancels direct playback and releases its preview clock"),
        ("partialLoop", "a partial native run cannot loop over an omitted checked prefix"),
        ("detourClock", "selecting a detoured keyframe parks after all of its checked legs"),
        ("detourClockExtras", "detour selection excludes destination hold and loop return after a suspended key"),
        ("terminalStop", "a late HTTP POSE is followed by a final Stop before new movement"),
        ("runPlanningStop", "Stop during Run planning prevents a fresh startup generation"),
        ("handoffStop", "Stop while handoff waits prevents native startup"),
        ("serialQueuedStop", "queued native serial MOVE is cancelled while addressed Stop still writes"),
        ("directCapture", "direct serial keeps its actual port even when hub or WiFi fields remain set"),
        ("stopAcknowledged", "an unacknowledged Stop is reported as failure"),
    ]:
        t.ok(results.get(key) == "true", label, results)
