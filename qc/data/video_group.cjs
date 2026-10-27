const fs = require('fs'), path = require('path'), vm = require('vm'), {performance} = require('perf_hooks');
const ROOT=path.resolve(__dirname,'../..'), STUDIO=path.join(ROOT,'nong/main_python_set_nong');
const THREE=require(path.join(STUDIO,'web/vendor/three.min.js'));
const read=name=>fs.readFileSync(path.join(STUDIO,'web/app_parts',name+'.js'),'utf8');
function context() {
  const config=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/video_follow.json')));
  const safe=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/safe_path.json')));
  const policy=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/video_motion_policy.json')));
  const elements=new Map();
  const c=vm.createContext({THREE,console,performance,setTimeout,clearTimeout,notice:()=>{},
    window:{NONG_RIG_DEFAULT:JSON.parse(fs.readFileSync(path.join(STUDIO,'rig_default.json')))},
    localStorage:{getItem:()=>null,setItem:()=>{}},document:{getElementById:id=>{
      if(!elements.has(id))elements.set(id,{value:id==='speedDps'?38:id==='maxDps'?400:'',checked:false,options:[],add(o){this.options.push(o);}});
      return elements.get(id);
    }},fetch:async file=>({json:async()=>file==='safe_path.json'?safe:file==='video_follow.json'?config:policy}),
    Option:function(label,value){this.label=label;this.value=value;}});
  const run=s=>vm.runInContext(s,c);
  run('const $=id=>document.getElementById(id);');
  for(const name of ['rig_data','build_rig','ik_4_dof_arm','collision_shapes','collisions','safe_path','timing','yaml_export','video_body_motion','video_tracking','video_motion_smooth','video_appearance','video_routine_assignment','video_routine_sections','video_routines','video_rig_fit','video_checked_playback'])run(read(name));
  const timeline=read('timeline');run(timeline.slice(timeline.indexOf('function easeKeys('),timeline.indexOf('\nfunction poseAt(')));
  const videoSource=read('pose_from_video');run(videoSource.slice(0,videoSource.lastIndexOf('\nvidFill();')));
  c.config=config;c.safe=safe;c.policy=policy;
  run(`VIDEO_FOLLOW=config;VIDEO_POLICY=policy;
    let pose=RIG.neutral.map((v,i)=>clampJ(i,v)),keys=[],SAFE_DPS=60;const MIN_MOVE_MS=80;
    const scene=new THREE.Scene(),matJoint=new THREE.MeshBasicMaterial();
    function partMat(){return new THREE.MeshBasicMaterial();}
    robot=new THREE.Group();scene.add(robot);buildRigShapes();applyPose();loadSafeSettings(safe);
  `);
  return {c,run};
}
module.exports={context,ROOT,STUDIO};
if(require.main===module){
  const {c,run}=context();let passed=0,failed=0;
  function check(name,code){try{if(!run(code))throw Error('assertion false');passed++;console.log('PASS '+name);}catch(e){failed++;console.log('FAIL '+name+': '+e.message);}}
  run(`function person(twist=0,roll=0,camera=[0,0,0],raised=false){
    const q=[];for(let i=0;i<33;i++)q.push(new THREE.Vector3());
    q[23].set(.17,0,0);q[24].set(-.17,0,0);
    const rot=new THREE.Euler(0,twist,roll,'XYZ');
    for(const [a,s,e,w,side] of [[0,11,13,15,1],[1,12,14,16,-1]]){
      const offset=new THREE.Vector3(side*.2,0,0).applyEuler(rot);
      q[s].copy(offset).add(new THREE.Vector3(0,.45,0));
      const upper=new THREE.Vector3(raised?side*.6:0,raised?.7:-1,.1).normalize().applyEuler(rot);
      q[e].copy(q[s]).addScaledVector(upper,.28);q[w].copy(q[e]).addScaledVector(upper,.25);
    }
    const view=new THREE.Euler(...camera,'XYZ');
    return q.map(p=>{const v=p.clone().applyEuler(view);return{x:v.x,y:-v.y,z:-v.z,v:1};});
  }
  function result(items){return{worldLandmarks:items.map(i=>i.w.map(p=>({...p,visibility:p.v}))),
    landmarks:items.map(i=>i.w.map(p=>({x:i.x+p.x*.15,y:.65+p.y*.4,visibility:1})))};}
  `);
  check('initial torso twist preserved independently of shoulder roll',`(()=>{const b=VideoBodyMotion.measure(person(.3,.05));return Math.abs(b.twist-.3)<.02&&Math.abs(b.roll-.05)<.02;})()`);
  check('front side high camera transforms preserve anatomical pose',`(()=>{const a=VideoBodyMotion.measure(person(.3,.08));return [[0,1.2,0],[.8,.9,.2],[-.5,-1.4,-.15]].every(v=>{const b=VideoBodyMotion.measure(person(.3,.08,v));return VideoBodyMotion.difference(a,b)<1e-4&&Math.abs(a.twist-b.twist)<1e-6&&Math.abs(a.roll-b.roll)<1e-6;});})()`);
  check('tracking identity survives detector order swaps',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'fixed',dancer:'auto'});const a={x:.5,w:person(.2,0)},b={x:.8,w:person(-.2,0,[],true)};const x=tr.step(result([a,b]),0,null,0),y=tr.step(result([b,a]),.1,null,0);return x.track===y.track;})()`);
  check('different group routines remain separate',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'fixed',dancer:'auto'});const f=tr.step(result([{x:.5,w:person(0,0)},{x:.8,w:person(0,0,[0,0,0],true)}]),0,null,0);return f.styles.length===2&&f.supporters===1;})()`);
  check('same arms but different waist or shrug are separate routines',`(()=>{
    const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'fixed',dancer:'auto'});
    const f=tr.step(result([{x:.5,w:person(.4,0)},{x:.8,w:person(-.4,0)},{x:.15,w:person(.4,.5)}]),0,null,0);
    return f.styles.length===3&&f.supporters===1;
  })()`);
  check('repeat annotation includes shoulder roll and torso twist',`(()=>{
    const tr=new VideoSubjectTracker({subjectMode:'single',cameraMode:'fixed',dancer:'auto'});
    tr.step(result([{x:.5,w:person(0,0)}]),0,null,0);
    const f=tr.step(result([{x:.5,w:person(0,.2)}]),2,null,0);
    return f.repeatAt===null;
  })()`);
  check('automatic routines use the whole new clip, not initial identical stance',`(()=>{
    const options={subjectMode:'group',cameraMode:'fixed',dancer:'auto'},tr=new VideoSubjectTracker(options),discovery=new VideoRoutineDiscovery(options);
    for(let i=0;i<24;i++)discovery.add(tr.step(result([{x:.3,w:person(0,0)},{x:.7,w:person(0,0,[0,0,0],i>=5)}]),i/10,null,0));
    const groups=discovery.finish();
    return groups.length===2&&groups.every(g=>g.coverage===1&&g.people===1)&&VideoBodyMotion.styleDifference(groups[0].frames[20].body,groups[1].frames[20].body)>24;
  })()`);
  check('new clip with matching dancers produces one routine without positional labels',`(()=>{
    const options={subjectMode:'group',cameraMode:'cuts',dancer:'auto'},tr=new VideoSubjectTracker(options),discovery=new VideoRoutineDiscovery(options);
    for(let i=0;i<15;i++)discovery.add(tr.step(result([{x:.2,w:person(.1,.02,[.3,.5,0],i>5)},{x:.8,w:person(.1,.02,[.3,.5,0],i>5)}]),i/10,null,0));
    const groups=discovery.finish();return groups.length===1&&groups[0].people===2;
  })()`);
  check('smoothing removes noisy short reversals and preserves the opening pose',`(()=>{
    const poses=Array.from({length:80},(_,i)=>RIG.home.map((v,j)=>j===0?v+(i?((i%2)?4:-4):0):v)),times=poses.map((_,i)=>i*100),frames=poses.map(()=>({trusted:true,action:'accept',shot:0}));
    const smoothed=new VideoMotionSmoother().apply(poses,times,frames);
    return smoothed.after.reversals<smoothed.before.reversals*.25&&smoothed.after.largestStep<smoothed.before.largestStep&&JSON.stringify(smoothed.poses[0])===JSON.stringify(poses[0]);
  })()`);
  check('smoothing retains real movement and never fills an unknown interval from the future',`(()=>{
    const poses=Array.from({length:40},(_,i)=>RIG.home.map((v,j)=>j===0?v+Math.min(20,Math.max(0,i-8)*2):v)),times=poses.map((_,i)=>i*100),frames=poses.map((_,i)=>({trusted:i>3,action:i>3?'accept':'uncertain',shot:0}));
    const smoothed=new VideoMotionSmoother().apply(poses,times,frames);
    return smoothed.poses.slice(0,4).every(p=>p[0]===poses[0][0])&&Math.abs(smoothed.poses.at(-1)[0]-poses.at(-1)[0])<2;
  })()`);
  check('manual checked clock advances robot through a flat source-time detour',`(()=>{
    let now=0;const video={paused:false,seeking:false,currentTime:0,playbackRate:1,pause(){this.paused=true;},play(){this.paused=false;return Promise.resolve();}};
    const playback=new VideoCheckedPlayback(()=>now),made={keepMusic:false,keys:[{sourceMs:0,t:1000},{sourceMs:0,t:6000},{sourceMs:1000,t:1000}]};
    playback.update(video,made,0,0,1000);now=3000;const source=playback.update(video,made,0,0,1000);
    return source===0&&playback.robotMs===3000&&playback.manual&&video.paused&&VideoRigFitter.sourceForClock(made.keys,3000).rate===0;
  })()`);
  check('camera scene change from arm movement alone does not reset the shot',`(()=>{
    const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'cuts',dancer:'auto'});
    tr.step(result([{x:.5,w:person(0,0)}]),0,null,0);
    const f=tr.step(result([{x:.5,w:person(0,0,[0,0,0],true)}]),.2,null,.3);
    return !f.cut&&f.shot===0;
  })()`);
  check('global routine assignment avoids a greedy cross-role match',`(()=>{
    const d=new VideoRoutineDiscovery({}),roles=[{id:0,last:{t:0}},{id:1,last:{t:0}}];
    d.joinCost=(rows,role)=>rows[0].actor.costs[role.id];
    const groups=[[[{t:1,index:1,actor:{costs:[3,4]}}]],[[{t:1,index:1,actor:{costs:[2,40]}}]]];
    const found=d.assign(groups,roles);return found[0].routine===roles[1]&&found[1].routine===roles[0]&&found.every(c=>!c.ambiguous);
  })()`);
  check('appearance descriptor is anonymous normalized and bounded',`(()=>{
    const p=Array.from({length:33},()=>({x:.5,y:.2}));p[11]={x:.3,y:.35};p[12]={x:.7,y:.35};p[23]={x:.3,y:.8};p[24]={x:.7,y:.8};
    const red=new Uint8Array(64*64*4),blue=new Uint8Array(red.length);for(let i=0;i<red.length;i+=4){red[i]=255;blue[i+2]=255;red[i+3]=blue[i+3]=255;}
    const a=VideoAppearanceDescriptor.measure(p,red,64,64),b=VideoAppearanceDescriptor.measure(p,blue,64,64),distance=VideoAppearanceDescriptor.distance(a,b);
    return a.length===96&&VideoAppearanceDescriptor.distance(a,a)===0&&distance>0&&distance<=1;
  })()`);
  check('smoothing retains continuous slow intentional motion without deadband jumps',`(()=>{
    const poses=Array.from({length:30},(_,i)=>RIG.home.map((v,j)=>j===0?v+i*.2:v)),times=poses.map((_,i)=>i*100),frames=poses.map(()=>({trusted:true,action:'accept',shot:0}));
    const out=new VideoMotionSmoother().apply(poses,times,frames).poses;
    return out.slice(10).every((p,k)=>p[0]>out[k+9][0])&&out.at(-1)[0]>poses[0][0]+4;
  })()`);
  check('automatic routine qualification rejects isolated noise as a new dance',`(()=>{
    const a=VideoBodyMotion.measure(person(0,0)),b=VideoBodyMotion.measure(person(0,0,[0,0,0],true));
    const make=(id,raised)=>({id,coverage:1,trustedCoverage:1,frames:Array.from({length:80},(_,i)=>({t:i/10,w:[1],trusted:true,body:raised(i)?b:a}))});
    const discovery=new VideoRoutineDiscovery({}),roles=discovery.classify([make(1,()=>false),make(2,i=>i===20),make(3,i=>i>=20&&i<=60)]);
    return roles.find(r=>r.id===2).kind==='fragment'&&roles.find(r=>r.id===3).kind==='routine';
  })()`);
  check('ambiguous camera association remains uncertain beyond a fixed timeout',`(()=>{
    const d=new VideoRoutineDiscovery({learned:false,cameraMode:'cuts'}),a=VideoBodyMotion.measure(person()),b=VideoBodyMotion.measure(person(0,0,[0,0,0],true));
    d.joinCost=()=>5;
    for(let i=0;i<16;i++)d.add({t:i*.2,shot:i<8?0:1,cut:i===8,scene:i===8?.8:0,actors:[
      {id:i<8?1:3,confidence:1,cx:.3,w:person(),body:a},{id:i<8?2:4,confidence:1,cx:.7,w:person(0,0,[0,0,0],true),body:b}]});
    const roles=d.finish().filter(r=>typeof r.id==='number');return roles.length===2&&roles.every(r=>r.frames.slice(8).every(f=>!f.trusted&&f.action==='uncertain'));
  })()`);
  check('trusted still observations let the smoothed rig finish reaching the accepted target',`(()=>{
    const start=RIG.home.slice(),target=start.slice();target[0]+=20;
    const poses=Array.from({length:15},(_,i)=>(i?target:start).slice()),times=poses.map((_,i)=>i*100),frames=poses.map((_,i)=>({trusted:true,shot:0,action:i===0?'initial':i===1?'accept':'hold'}));
    const output=new VideoMotionSmoother().apply(poses,times,frames).poses;
    return Math.abs(output.at(-1)[0]-target[0])<.5&&output[1][0]<target[0];
  })()`);
  check('many similar performers use bounded exact global assignment',`(()=>{
    const matrix=Array.from({length:30},(_,i)=>Array.from({length:60},(_,j)=>j===i?10:j===i+30?11:Infinity));
    const best=VideoRoutineAssignment.solve(matrix),alternate=VideoRoutineAssignment.solve(matrix,0,0);
    return best.cost===300&&best.columns.every((column,row)=>column===row)&&alternate.cost===301;
  })()`);
  check('unresolved cuts automatically yield usable local scene sections with rebased time',`(()=>{
    const d=new VideoRoutineDiscovery({learned:false,cameraMode:'cuts'}),a=VideoBodyMotion.measure(person()),b=VideoBodyMotion.measure(person(0,0,[0,0,0],true));d.joinCost=()=>5;
    for(let i=0;i<16;i++)d.add({t:i*.2,shot:i<8?0:1,cut:i===8,scene:i===8?.8:0,actors:[{id:i<8?1:3,confidence:1,cx:.3,w:person(),body:a},{id:i<8?2:4,confidence:1,cx:.7,w:person(0,0,[0,0,0],true),body:b}]});
    const sections=d.finish().filter(r=>r.kind==='segment'&&r.sourceStart>1);
    return sections.length===2&&sections.every(r=>Math.abs(r.sourceStart-1.6)<1e-6&&Math.abs(r.sourceEnd-3)<1e-6&&r.frames[0].t===0&&r.trustedCoverage===1&&r.frames.every(f=>f.w));
  })()`);
  check('group representation keeps one stable leader rather than confidence flicker',`(()=>{
    const group=[1,2].map(id=>Array.from({length:12},(_,index)=>({index,t:index/10,actor:{id,confidence:(index%2===id%2)?1:.6}})));
    const selected=VideoRoutineSections.observations(group);return selected.size===12&&new Set([...selected.values()].map(a=>a.id)).size===1;
  })()`);
  check('explicit performer overrides auto subject',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'fixed',dancer:'2'});const f=tr.step(result([{x:.5,w:person(0,0)},{x:.8,w:person(0,0,[0,0,0],true)}]),0,null,0);return f.track===2;})()`);
  check('camera cut does not create waist jump',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'cuts',dancer:'auto'});const a=tr.step(result([{x:.5,w:person(.3,.05)}]),0,null,0),b=tr.step(result([{x:.4,w:person(.3,.05,[.7,1.2,.2])}]),.1,null,.8);return Math.abs(a.waist-b.waist)<.02;})()`);
  check('hand boxes collide despite old clear wrist spacing',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return 40>2*R_WRIST+CLEAR&&G.boxesHit(G.box(new THREE.Vector3(),A,[17,23,2.5]),G.box(new THREE.Vector3(0,40,0),A,[17,23,2.5]),CLEAR);})()`);
  check('depth separated crossed hands remain clear',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return !G.boxesHit(G.box(new THREE.Vector3(),A,[17,23,2.5]),G.box(new THREE.Vector3(0,0,16),A,[17,23,2.5]),CLEAR);})()`);
  check('segment box distance detects crossing between endpoints',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return G.segmentBox(new THREE.Vector3(-50,0,0),new THREE.Vector3(50,0,0),G.box(new THREE.Vector3(),A,[10,10,10]))===0;})()`);
  check('physical collision snapshot restores pose and transforms',`(()=>{const p=pose.slice(),q=RIG.home.slice();q[9]=RIG.max[9];StudioCollisionGeometry.snapshot(q);return pose===p?false:JSON.stringify(pose)===JSON.stringify(p);})()`);
  check('waist rotation preserves clearance but shrug moves shoulders',`(()=>{const a=RIG.home.slice(),b=a.slice(),d=a.slice();b[8]=RIG.max[8];d[9]=RIG.max[9];const A=StudioCollisionGeometry.snapshot(a),B=StudioCollisionGeometry.snapshot(b),D=StudioCollisionGeometry.snapshot(d);return A.arms[0].e.distanceTo(B.arms[0].e)<1e-5&&A.arms[0].s.distanceTo(D.arms[0].s)>.1;})()`);
  check('factory HOME clear with physical hand and joint envelopes',`!collisionAt(RIG.home)`);
  check('actual FK hand penetrates body despite clear wrist spacing',`(()=>{const p=[93.4,111.5,41.5,89.3,105.5,83.1,47.2,84.1,101.4,98.3],g=StudioCollisionGeometry.snapshot(p);return g.arms[0].w.distanceTo(g.arms[1].w)>2*R_WRIST+CLEAR&&(collisionAt(p)||'').includes('hand');})()`);
  check('actual folded forearm hits its own shoulder in alternate joint travel',`(collisionAt([90,140,-100,80,90,40,90,90,90,90.5])||'').includes('its shoulder joint')`);
  check('snapshot restores exact pose identity and matrices after exception',`(()=>{
    const original=pose,matrix=bodyGroup.matrixWorld.toArray().join(','),g=palmMarks[0].children.find(o=>o.geometry?.type==='BoxGeometry').geometry,originalCompute=g.computeBoundingBox;
    try{g.computeBoundingBox=()=>{throw Error('fixture geometry failure');};const p=RIG.home.slice();p[9]=RIG.max[9];try{StudioCollisionGeometry.snapshot(p);}catch(_){} }
    finally{g.computeBoundingBox=originalCompute;}
    return pose===original&&bodyGroup.matrixWorld.toArray().join(',')===matrix;
  })()`);
  check('selected performer loss cannot silently choose another routine',`(()=>{
    const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'cuts',dancer:'1'});
    tr.step(result([{x:.3,w:person(0,0)},{x:.7,w:person(0,0,[0,0,0],true)}]),0,null,0);
    const f=tr.step(result([{x:.7,w:person(0,0,[0,0,0],true)}]),1,null,.8);
    return f.w===null&&f.action==='uncertain';
  })()`);
  check('gradual genuine turns accumulate across held frames',`(()=>{
    const gate=new VideoTemporalPolicy(null,'fixed');let f;for(let i=0;i<15;i++)f=gate.step(VideoBodyMotion.measure(person(0,0,[0,i*.025,0])),0,false);
    return Math.abs(f.waist)>.2;
  })()`);
  check('moving-view heading-only observations do not rotate waist without evidence',`(()=>{
    const gate=new VideoTemporalPolicy(null,'cuts');let f;for(let i=0;i<15;i++)f=gate.step(VideoBodyMotion.measure(person(0,0,[0,i*.025,0])),.03,false);
    return Math.abs(f.waist)<.03;
  })()`);
  run(`function fromRig(p){
    const saved=pose;pose=p.slice();applyPose();robot.updateMatrixWorld(true);
    const w=person(0,0);const put=(i,o)=>{const v=o.getWorldPosition(new THREE.Vector3()).multiplyScalar(.001);w[i]={x:v.x,y:-v.y,z:-v.z,v:1};};
    [[11,jointGroups[0]],[13,elbowBalls[0]],[15,wristBalls[0]],[12,jointGroups[4]],[14,elbowBalls[1]],[16,wristBalls[1]]].forEach(([i,o])=>put(i,o));
    w[23]={x:.1,y:.2,z:0,v:1};w[24]={x:-.1,y:.2,z:0,v:1};pose=saved;applyPose();return w;
  }`);
  check('actual fitter emits waist and shrug, not only arm targets',`(()=>{
    const p=RIG.home.slice();p[8]+=15;p[9]=Math.min(RIG.max[9],p[9]+5);
    const w=fromRig(p),body=VideoBodyMotion.measure(w);
    const fitter=new VideoRigFitter({waist:true,shrug:true,subjectMode:'group',mirror:false});
    const f=fitter.frames([{t:0,w,body,waist:body.twist,action:'initial',trusted:true,shot:0}]);
    return f&&Math.abs(f.poses[0][8]-RIG.neutral[8])>5&&Math.abs(f.poses[0][9]-RIG.neutral[9])>1;
  })()`);
  check('static accepted stance never accumulates solver drift',`(()=>{
    const w=fromRig(RIG.home),body=VideoBodyMotion.measure(w);
    const f=new VideoRigFitter({waist:true,shrug:true,subjectMode:'group',mirror:false}).frames(Array.from({length:8},(_,i)=>({t:i/10,w,body,waist:0,action:i?'hold':'initial',trusted:true,shot:0})));
    return f&&f.poses.every(p=>p.every((v,j)=>v===f.poses[0][j]));
  })()`);
  check('missing opening never borrows a raised future pose',`(()=>{
    const w=person(0,0,[0,0,0],true),body=VideoBodyMotion.measure(w);
    const f=new VideoRigFitter({waist:true,shrug:true,subjectMode:'group',mirror:false}).frames([{t:0,w:null,body:null,shot:0,trusted:false},{t:.5,w,body,action:'accept',trusted:true,shot:0}]);
    return f&&f.poses[0].every((v,j)=>v===clampJ(j,RIG.neutral[j]));
  })()`);
  check('unknown learned states use conservative geometric fallback',`(()=>{const p=new VideoTemporalPolicy({enabled:true,schema:'mice-video-q-v1',features:policy.features,bins:policy.bins,q:{},actions:policy.actions});p.step(VideoBodyMotion.measure(person(.2,0)),0,false);return p.step(null,.8,true).action==='uncertain';})()`);
  check('sequential learning model has held-out acceptance and real stateful actions',`VIDEO_POLICY.algorithm==='episodic-tabular-q-learning'&&VIDEO_POLICY.training.actionChangesAcceptedState&&VIDEO_POLICY.validation.syntheticOnly&&VIDEO_POLICY.validation.acceptancePassed`);
  check('pose-preserving source clock follows actual slowed motion and holds',`(()=>{
    const K=[{sourceMs:0,sourceHoldEnd:1000,hold:1000,t:1000},{sourceMs:2000,sourceHoldEnd:2000,hold:0,t:4000}];
    const a=VideoRigFitter.clockForSource(K,500),b=VideoRigFitter.clockForSource(K,1500),c=VideoRigFitter.clockForSource(K,2000);
    return a.ms===500&&b.ms===3000&&b.rate===.25&&c.ms===5000;
  })()`);
  check('RRT via source slots remain in chronological order',`(()=>{
    const K=[{sourceMs:0,sourceHoldEnd:0,hold:0,t:1000},{sourceMs:1000,sourceHoldEnd:1000,hold:0,t:3000,via:true},{sourceMs:2000,sourceHoldEnd:2000,hold:0,t:1000}];
    return VideoRigFitter.clockForSource(K,500).ms===1500&&VideoRigFitter.clockForSource(K,1500).ms===3500;
  })()`);
  check('very slow video steps the checked robot clock rather than clamping speed',`(()=>{
    let now=0;const player={paused:false,seeking:false,currentTime:0,playbackRate:1,pause(){this.paused=true;},play(){this.paused=false;return Promise.resolve();}};
    const playback=new VideoCheckedPlayback(()=>now),made={keepMusic:false,keys:[{sourceMs:0,sourceHoldEnd:0,hold:0,t:1000},{sourceMs:100,sourceHoldEnd:100,hold:0,t:6000}]};
    playback.update(player,made,0,0,100);now=1000;const source=playback.update(player,made,0,0,100);
    return !!playback.manual&&player.paused&&Math.abs(source-100/6)<1e-6&&Math.abs(VideoRigFitter.clockForSource(made.keys,source).ms-1000)<1e-6;
  })()`);
  check('acknowledged slow seek resumes normal playback with real seeking setter',`(()=>{
    let now=0,played=0,time=0;
    const video={paused:false,seeking:false,playbackRate:1,pause(){this.paused=true;},play(){played++;this.paused=false;return Promise.resolve();}};
    Object.defineProperty(video,'currentTime',{get(){return time;},set(v){time=v;this.seeking=true;}});
    const playback=new VideoCheckedPlayback(()=>now),made={keepMusic:false,keys:[{sourceMs:0,t:1000},{sourceMs:100,t:6000},{sourceMs:1100,t:1000}]};
    playback.update(video,made,0,0,1100);now=1000;playback.update(video,made,0,0,1100);
    if(!video.seeking||!playback.manual)return false;
    video.seeking=false;now=6200;const source=playback.update(video,made,0,0,1100);
    return playback.manual===null&&played===1&&!video.paused&&source>100&&video.playbackRate===1;
  })()`);
  check('pausing a flat-source detour resumes its checked clock rather than restarting',`(()=>{
    let now=0;const video={currentTime:0,paused:true,seeking:false,playbackRate:1,pause(){this.paused=true;},play(){this.paused=false;return Promise.resolve();}};
    const player=new VideoCheckedPlayback(()=>now),made={keepMusic:false,keys:[{sourceMs:0,t:1000},{sourceMs:0,t:6000},{sourceMs:1000,t:1000}]};
    player.start(video,0);now=3000;player.update(video,made,0,0,1000);player.pause(video);
    now=6000;player.start(video,0);now=6500;player.update(video,made,0,0,1000);
    return player.robotMs===3500&&!!player.manual;
  })()`);
  check('clearing analysis resets any inherited video slowdown',`(()=>{const p={playbackRate:.1};vidCheckedPlayback.reset(p);return p.playbackRate===1;})()`);
  async function checkAsync(name,code){try{if(!(await run(code)))throw Error('assertion false');passed++;console.log('PASS '+name);}catch(e){failed++;console.log('FAIL '+name+': '+e.message);}}
  (async()=>{
    run(read('video_page'));
    await checkAsync('pending seek resolves on mode cancellation without a media event',`(async()=>{
      const listeners=new Map(),video={currentTime:0,readyState:2,seeking:false,addEventListener(k,v){listeners.set(k,v);},removeEventListener(k){listeners.delete(k);}};
      vidStop=false;const pending=vidSeek(video,1,vidGeneration);vidModeChanged();
      return (await pending)===false&&vidSeekCancel===null&&listeners.size===0;
    })()`);
    await checkAsync('routine batch cancels before saving a stale analysis',`(async()=>{
      const oldUse=vidUse,oldRemake=vidRemake,oldSave=globalThis.saveAll,oldAsk=globalThis.askUnsaved,oldName=globalThis.setWorkName;
      let saves=0,asks=0;
      try{
        vidBusy=false;vidStop=false;vidRoutines=[{id:1,kind:'routine',trustedCoverage:1,frames:[]},{id:2,kind:'routine',trustedCoverage:1,frames:[]}];
        globalThis.askUnsaved=async()=>{asks++;return true;};globalThis.setWorkName=()=>{};globalThis.saveAll=async()=>{saves++;return true;};
        vidRemake=()=>{vidMade={keys:[{pose:RIG.home,t:1000}]};};vidUse=async()=>{vidGeneration++;return true;};
        await vidSaveRoutines();return saves===0&&asks===1&&!vidBusy;
      }finally{vidUse=oldUse;vidRemake=oldRemake;globalThis.saveAll=oldSave;globalThis.askUnsaved=oldAsk;globalThis.setWorkName=oldName;vidRoutines=[];}
    })()`);
    await checkAsync('delayed unsaved prompt cannot replace timeline after modes change',`(async()=>{
      const oldAsk=globalThis.askUnsaved;vidMade={keys:[{pose:RIG.home,t:1000}]};keys=[];vidStop=false;
      try{globalThis.askUnsaved=async()=>{vidGeneration++;return true;};const used=await vidUse('replace');return used===false&&keys.length===0;}
      finally{globalThis.askUnsaved=oldAsk;}
    })()`);
    await checkAsync('each saved routine serializes its own choice and restores the batch selection',`(async()=>{
      const oldUse=vidUse,oldRemake=vidRemake,oldSave=globalThis.saveAll,oldAsk=globalThis.askUnsaved,oldName=globalThis.setWorkName,oldSrc=vidSrc;
      const selected=[];
      try{
        vidBusy=false;vidStop=false;vidSrc={kind:'file',name:'new_clip.mp4'};$('vidRoutine').value='auto';
        vidRoutines=[{id:1,kind:'routine',trustedCoverage:1,frames:[]},{id:2,kind:'routine',trustedCoverage:1,frames:[]}];
        globalThis.askUnsaved=async()=>true;globalThis.setWorkName=()=>{};
        globalThis.saveAll=async()=>{selected.push(vidSettings().routine);return true;};
        vidRemake=()=>{vidMade={keys:[{pose:RIG.home,t:1000}],videoMs:1000,handMiss:[0,0],kept:1};};vidUse=async()=>true;
        await vidSaveRoutines();return selected.join(',')==='1,2'&&$('vidRoutine').value==='auto';
      }finally{vidUse=oldUse;vidRemake=oldRemake;globalThis.saveAll=oldSave;globalThis.askUnsaved=oldAsk;globalThis.setWorkName=oldName;vidSrc=oldSrc;vidRoutines=[];}
    })()`);
    await checkAsync('scene batch saves the matching original video windows without double offsets',`(async()=>{
      const oldUse=vidUse,oldRemake=vidRemake,oldSave=globalThis.saveAll,oldAsk=globalThis.askUnsaved,oldName=globalThis.setWorkName,oldSrc=vidSrc,oldRange=vidRoutineRange;
      const selected=[];
      try{
        vidBusy=false;vidStop=false;vidSrc={kind:'file',name:'new_clip.mp4'};$('vidRoutine').value='auto';vidRoutineRange={from:5,to:60};
        vidRoutines=[{id:'scene_1_1',kind:'segment',trustedCoverage:1,sourceStart:10,sourceEnd:20,frames:[]},{id:'scene_2_1',kind:'segment',trustedCoverage:1,sourceStart:30,sourceEnd:40,frames:[]}];
        globalThis.askUnsaved=async()=>true;globalThis.setWorkName=()=>{};globalThis.saveAll=async()=>{const x=vidSettings();selected.push([x.routine,x.from,x.to]);return true;};
        vidRemake=()=>{vidMade={keys:[{pose:RIG.home,t:1000}],videoMs:1000,handMiss:[0,0],kept:1};};vidUse=async()=>true;
        await vidSaveRoutines();return JSON.stringify(selected)===JSON.stringify([['scene_1_1',15,25],['scene_2_1',35,45]])&&vidRoutineRange.from===5;
      }finally{vidUse=oldUse;vidRemake=oldRemake;globalThis.saveAll=oldSave;globalThis.askUnsaved=oldAsk;globalThis.setWorkName=oldName;vidSrc=oldSrc;vidRoutines=[];vidRoutineRange=oldRange;}
    })()`);
    await checkAsync('a different clip resets old performer and scene identities to automatic',`(async()=>{
      const oldList=vidList,oldDraw=vidDraw,oldSaved=vidSaved;
      try{
        vidList=()=>{};vidDraw=()=>{};vidSaved={src:{url:'https://old.example/clip'},anchorX:.13};vidBusy=false;
        $('vidPlayer').src='old.mp4';$('vidRoutine').value='scene_8_3';$('vidDancer').value='99';
        vidSetSrc('/new.mp4',{kind:'link',url:'https://new.example/clip',name:'new'});
        return vidSaved===null&&vidRoutines.length===0&&vidRoutineRange===null&&$('vidRoutine').value==='auto'&&$('vidDancer').value==='auto';
      }finally{vidList=oldList;vidDraw=oldDraw;vidSaved=oldSaved;}
    })()`);
    await checkAsync('cancelled read cannot repopulate observations or fit new modes',`(async()=>{
      vidFrames=vidFit=vidMade=null;vidRead=async()=>{vidModeChanged();return[{t:0,w:person()}];};
      const result=await vidMake();return result===false&&vidFrames===null&&vidFit===null;
    })()`);
    await checkAsync('Make-and-save cannot save after analysis mode changed',`(async()=>{
      vidBusy=false;var saves=0;saveAll=async()=>{saves++;return true;};vidMake=async()=>{vidGeneration++;return true;};
      await vidMakeAndSave();return saves===0;
    })()`);
    await checkAsync('video tick displays a moving checked rig while source time remains flat',`(async()=>{
      const oldNow=vidCheckedPlayback.now,oldRaf=globalThis.requestAnimationFrame;
      const player=$('vidPlayer'),start=RIG.home.slice(),target=RIG.home.slice();target[0]+=10;
      try{
        globalThis.requestAnimationFrame=()=>{};vidOn=true;vidBusy=false;playing=false;vidFrames=null;
        Object.assign(player,{src:'test.mp4',duration:20,currentTime:0,paused:true,seeking:false,pause(){this.paused=true;},play(){this.paused=false;return Promise.resolve();}});
        $('vidFrom').value='0';$('vidTo').value='20';vidLastMs=0;
        vidMade={keepMusic:false,keys:[{sourceMs:0,pose:start,t:1000},{sourceMs:0,pose:target,t:6000},{sourceMs:1000,pose:target,t:1000}]};
        let now=0;vidCheckedPlayback.now=()=>now;vidCheckedPlayback.start(player,0);now=3000;vidTick();
        return Math.abs(pose[0]-start[0]-5)<1e-5;
      }finally{vidOn=false;vidCheckedPlayback.reset(player);vidCheckedPlayback.now=oldNow;globalThis.requestAnimationFrame=oldRaf;pose=RIG.home.slice();applyPose();}
    })()`);
    await checkAsync('retimed show cannot attach original unwarped audio',`(async()=>{
      vidMade={keepMusic:false,keys:[{sourceMs:0,sourceHoldEnd:0,hold:0,t:1000},{sourceMs:1000,sourceHoldEnd:1000,hold:0,t:4000}]};
      let calls=0;fetch=async()=>{calls++;throw Error('must not upload');};
      await vidSound();return calls===0&&$('vidStat').textContent.includes('retimed music');
    })()`);
    await checkAsync('configuration and policy share one complete readiness promise',`(async()=>{
      VIDEO_FOLLOW=null;VIDEO_POLICY=null;VIDEO_READY=null;
      fetch=async file=>({json:async()=>file==='video_follow.json'?config:policy});
      const a=videoFollowReady(),b=videoFollowReady();const same=a===b;await a;
      return same&&VIDEO_FOLLOW===config&&VIDEO_POLICY===policy;
    })()`);
    await checkAsync('saved group/camera/performer choices survive late option population',`(async()=>{
      $('vidSubject').options=[];$('vidCamera').options=[];VIDEO_FOLLOW=null;
      const saved={subjectMode:'group',cameraMode:'cuts',dancer:'2',waist:true,shrug:true,learned:true};
      vidApplySettings(saved);VIDEO_FOLLOW=config;vidFill();vidApplySettings(vidSaved);
      return $('vidSubject').value==='group'&&$('vidCamera').value==='cuts'&&$('vidDancer').value==='2'&&$('vidShrug').checked;
    })()`);
    console.log('RESULT '+JSON.stringify({passed,failed}));process.exitCode=failed?1:0;
  })().catch(e=>{console.error(e);process.exitCode=1;});
}
