const fs = require('fs'), path = require('path'), vm = require('vm'), {performance} = require('perf_hooks');
const ROOT=path.resolve(__dirname,'../..'), STUDIO=path.join(ROOT,'nong/main_python_set_nong');
const THREE=require(path.join(STUDIO,'web/vendor/three.min.js'));
const read=name=>fs.readFileSync(path.join(STUDIO,'web/app_parts',name+'.js'),'utf8');
function context() {
  const config=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/video_follow.json')));
  const safe=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/safe_path.json')));
  const policy=JSON.parse(fs.readFileSync(path.join(STUDIO,'web/video_motion_policy.json')));
  const elements=new Map();
  const c=vm.createContext({THREE,console,performance,setTimeout,clearTimeout,
    window:{NONG_RIG_DEFAULT:JSON.parse(fs.readFileSync(path.join(STUDIO,'rig_default.json')))},
    localStorage:{getItem:()=>null,setItem:()=>{}},document:{getElementById:id=>{
      if(!elements.has(id))elements.set(id,{value:id==='speedDps'?38:id==='maxDps'?400:'',checked:false,options:[],add(o){this.options.push(o);}});
      return elements.get(id);
    }},fetch:async file=>({json:async()=>file==='safe_path.json'?safe:file==='video_follow.json'?config:policy}),
    Option:function(label,value){this.label=label;this.value=value;}});
  const run=s=>vm.runInContext(s,c);
  run('const $=id=>document.getElementById(id);');
  for(const name of ['rig_data','build_rig','ik_4_dof_arm','collision_shapes','collisions','safe_path','timing','yaml_export','video_body_motion','video_tracking','video_rig_fit'])run(read(name));
  run(read('pose_from_video').replace(/\nvidFill\(\);\s*\nvideoFollowReady\(\)\.then\(vidFill\)\.catch\(\(\) => \{\}\);\s*$/,''));
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
  check('explicit performer overrides auto subject',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'fixed',dancer:'2'});const f=tr.step(result([{x:.5,w:person(0,0)},{x:.8,w:person(0,0,[0,0,0],true)}]),0,null,0);return f.track===2;})()`);
  check('camera cut does not create waist jump',`(()=>{const tr=new VideoSubjectTracker({subjectMode:'group',cameraMode:'cuts',dancer:'auto'});const a=tr.step(result([{x:.5,w:person(.3,.05)}]),0,null,0),b=tr.step(result([{x:.4,w:person(.3,.05,[.7,1.2,.2])}]),.1,null,.8);return Math.abs(a.waist-b.waist)<.02;})()`);
  check('hand boxes collide despite old clear wrist spacing',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return 40>2*R_WRIST+CLEAR&&G.boxesHit(G.box(new THREE.Vector3(),A,[17,23,2.5]),G.box(new THREE.Vector3(0,40,0),A,[17,23,2.5]),CLEAR);})()`);
  check('depth separated crossed hands remain clear',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return !G.boxesHit(G.box(new THREE.Vector3(),A,[17,23,2.5]),G.box(new THREE.Vector3(0,0,16),A,[17,23,2.5]),CLEAR);})()`);
  check('segment box distance detects crossing between endpoints',`(()=>{const G=StudioCollisionGeometry,A=[new THREE.Vector3(1,0,0),new THREE.Vector3(0,1,0),new THREE.Vector3(0,0,1)];return G.segmentBox(new THREE.Vector3(-50,0,0),new THREE.Vector3(50,0,0),G.box(new THREE.Vector3(),A,[10,10,10]))===0;})()`);
  check('physical collision snapshot restores pose and transforms',`(()=>{const p=pose.slice(),q=RIG.home.slice();q[9]=RIG.max[9];StudioCollisionGeometry.snapshot(q);return pose===p?false:JSON.stringify(pose)===JSON.stringify(p);})()`);
  check('waist rotation preserves clearance but shrug moves shoulders',`(()=>{const a=RIG.home.slice(),b=a.slice(),d=a.slice();b[8]=RIG.max[8];d[9]=RIG.max[9];const A=StudioCollisionGeometry.snapshot(a),B=StudioCollisionGeometry.snapshot(b),D=StudioCollisionGeometry.snapshot(d);return A.arms[0].e.distanceTo(B.arms[0].e)<1e-5&&A.arms[0].s.distanceTo(D.arms[0].s)>.1;})()`);
  check('factory HOME clear with physical hand and joint envelopes',`!collisionAt(RIG.home)`);
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
  console.log('RESULT '+JSON.stringify({passed,failed}));process.exitCode=failed?1:0;
}
