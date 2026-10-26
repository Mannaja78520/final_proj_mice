const {read,vm,context,loadClass,response,check,test,finish}=require('./usability_dom');
(async()=>{
 await test('camera scan failures',async()=>{
  const c=context(),a=loadClass(c,'apps/camera/app.js','CameraApp','window.cameraApp =');a.foundCams=new Map();
  await a.load(false);check(c.el('none').hidden&&!c.el('stat').textContent.includes('found'),'camera complete failure does not say no cameras');
  c.fetch=async()=>response({modules:[]});await a.load(false);check(!c.el('none').hidden,'camera genuine empty state stays available');
 });
 await test('TV acknowledgements',async()=>{
  const c=context(),a=loadClass(c,'apps/tv/index.html','TVRemoteApp','const app =');a.activeDev='usb:COM99';a.modules=[{dev:a.activeDev}];a.poll=()=>{};
  c.fetch=async()=>response({error:'refused'},false);await a.playSequence('demo');
  check(!c.el('nowSeq').textContent.startsWith('Starting'),'TV failed sequence load ends pending state');
  let home=0;c.fetch=async u=>{if(u.includes('c=HOME'))home++;return response({error:'refused'},false);};await a.goHome();
  check(home===0,'TV refused Stop prevents subsequent HOME');
  home=0;c.fetch=async u=>{if(u.includes('c=HOME'))home++;return response({running:true});};await a.goHome();check(home===0,'TV waits for stopped status before HOME');
  c.fetch=async()=>response({error:'refused'},false);
  c.el('customSpeak').value='keep draft';await a.speakCustom();check(c.el('customSpeak').value==='keep draft','TV failed speech retains draft');
  c.fetch=async()=>{throw Error('offline');};await a.stop();check(c.el('nowSeq').textContent.length>0,'TV Stop network failure is handled visibly');
  home=0;c.fetch=async u=>{if(u.includes('c=HOME'))home++;return response({running:false,error:'serial port disconnected'});};await a.goHome();
  check(home===0,'TV Stop transport error blocks HOME even when clock stopped');
  let resolveSeq,plays=0;c.fetch=async u=>u.startsWith('/api/seqsteps')?new Promise(r=>resolveSeq=r):(u==='/api/play'?(plays++,response({ok:true})):response({running:false,error:'',stop_ok:true,stop_reply:'OK stopped',dev:'usb:COM99',epoch:0}));
  const delayed=a.playSequence('delayed');await a.stop();resolveSeq(response({steps:[{pose:[90],t:1000}]}));await delayed;
  check(plays===0,'TV Stop cancels a delayed sequence-load continuation');

 });
 await test('TV epoch and selected-board barrier',async()=>{
  const c=context(),a=loadClass(c,'apps/tv/index.html','TVRemoteApp','const app =');a.activeDev='usb:COM99';a.modules=[{dev:a.activeDev}];a.poll=()=>{};
  let home=0;const commands=[];
  c.fetch=async url=>url==='/api/play/stop'?response({running:false,stop_ok:true,stop_reply:'OK stopped',dev:'usb:OTHER',error:''}):url.includes('c=STOP')?(commands.push('STOP'),response('ERR locked')):(home++,response('OK home'));
  await a.goHome();check(home===0&&commands.join()==='STOP','TV confirms selected robot STOP separately from another show target');
  commands.length=0;c.fetch=async url=>url==='/api/play/stop'?response({running:false,stop_ok:true,stop_reply:'OK stopped',dev:'usb:OTHER',error:''}):(url.includes('c=STOP')?(commands.push('STOP'),response('OK stopped')):(commands.push('HOME'),response('OK home')));
  await a.goHome();check(commands.join()==='STOP,HOME','TV selected STOP acknowledgement precedes HOME');
  let epochReady,releaseEpoch,posts=0;const fetchingEpoch=new Promise(r=>epochReady=r);
  c.fetch=async(url,opts)=>{
   if(url.startsWith('/api/seqsteps'))return response({steps:[{pose:[90],t:1000}]});
   if(url==='/api/play'&&opts.method==='GET'){epochReady();return new Promise(r=>releaseEpoch=r);}
   if(url==='/api/play'){posts++;return response({ok:true});}
   return response({running:false,stop_ok:true,stop_reply:'OK stopped',dev:a.activeDev,error:'',epoch:8});
  };
  const epochPending=a.playSequence('epoch-read');await fetchingEpoch;await a.stop();releaseEpoch(response({epoch:8}));await epochPending;
  check(posts===0,'TV Stop cancels intent even when late epoch read returns the new revision');

  let sendStart,resolveStart;const dispatched=new Promise(r=>sendStart=r);let stamped;
  c.fetch=async(url,opts)=>{
   if(url.startsWith('/api/seqsteps'))return response({steps:[{pose:[90],t:1000}]});
   if(url==='/api/play'&&opts.method==='GET')return response({epoch:7});
   if(url==='/api/play'){stamped=JSON.parse(opts.body);sendStart();return new Promise(r=>resolveStart=r);}
   return response({running:false,stop_ok:true,stop_reply:'OK stopped',dev:a.activeDev,error:'',epoch:8});
  };
  const pending=a.playSequence('already-dispatched');await dispatched;const stopped=await a.stop();
  check(stopped&&stamped.expected_epoch===7,'TV dispatches Stop immediately while stamped Play response is outstanding');
  resolveStart(response({ok:false,error:'stale epoch'}));await pending;
  let stopRelease,playCount=0;const waiting=a.stop();
  // The prior fetch resolved synchronously; create a deliberately pending STOP next.
  await waiting;
  c.fetch=async(url,opts)=>{
   if(url==='/api/play/stop')return new Promise(r=>stopRelease=r);
   if(url.startsWith('/api/seqsteps'))return response({steps:[{pose:[90],t:1000}]});
   if(url==='/api/play'&&opts.method==='GET')return response({epoch:9});
   if(url==='/api/play'){playCount++;return response({ok:true});}
   return response('OK stopped');
  };
  const barrier=a.stop(),later=a.playSequence('later');
  await new Promise(r=>setTimeout(r,0));check(playCount===0,'TV later Play waits for full Stop confirmation barrier');
  stopRelease(response({running:false,stop_ok:true,stop_reply:'OK stopped',dev:a.activeDev,error:'',epoch:9}));await barrier;await later;
  check(playCount===1,'TV new explicit Play can start after confirmed Stop');
 });
 await test('Voice model controls',async()=>{
  const c=context(),a=loadClass(c,'apps/voice/app.js','VoiceApp','window.voiceApp =');a.say=()=>{};a.pollTimer=null;
  for(const method of ['loadModel','unloadModel']){
   const id=method==='loadModel'?'btnLoadModel':'btnUnloadModel';c.el(id).disabled=false;
   await a[method]();check(!c.el(id).disabled&&!c.el(id).textContent.includes('Ã¢â‚¬Â¦'),'Voice '+method+' failure restores retry control');
  }
 });
 await test('Gacha logs',async()=>{
  const c=context(),a=loadClass(c,'apps/gacha/index.html','GachaApp','window.GachaApp =');c.Mice.Api.get=async()=>({ok:false,says:'offline'});
  c.el('logT').tBodies[0].innerHTML='cached record';await a.loadLog();
  check(c.el('logT').tBodies[0].innerHTML==='cached record'&&c.el('logStat').textContent.length>0,'Gacha failed log refresh keeps records and marks stale');
  c.Mice.Api.get=async u=>({ok:true,data:u.includes('/stats')?{stats:{}}:{rows:[]}});await a.loadLog();
  check(c.el('logT').tBodies[0].innerHTML.includes("\u0e22\u0e31\u0e07\u0e44\u0e21\u0e48\u0e21\u0e35"),'Gacha successful empty log says no records');
 });
 await test('AllJao popup activation',async()=>{
  const c=context(),a=loadClass(c,'apps/all-jao/index.html','AllJaoApp','const allJaoApp =');let resolve,opened=0;
  c.open=()=>{opened++;return {location:{},close(){}};};a.playPath='/play';a.playHere=()=>new Promise(r=>resolve=r);a.partner={open(){},ensure:async()=>'/play'};a.status={error(){},ready(){}};
  const pending=a.openGames();check(opened===1,'AllJao reserves tab before awaiting network');resolve(true);await pending;
 });
 await test('Studio project-list failure',async()=>{
  const c=context();c.syncAskUnsavedBox=()=>{};c.askUnsavedOn=()=>false;c.Mice.Api.get=async()=>({ok:false,says:'offline'});
  const s=read('nong/main_python_set_nong/web/app_parts/project_save_load.js');vm.runInContext(s.slice(s.indexOf('async function refreshProjects')),c);
  c.el('projList').innerHTML='cached project';await c.refreshProjects();
  check(c.el('projList').innerHTML==='cached project'&&c.el('tlStat').textContent.length>0,'Studio project list failure preserves choices and explains retry');
 });
 await test('module Run refusal',async()=>{
  const c=context();let explained=false;c.el('moveSel').value='/moves/demo.yaml';
  c.cmd=async()=> 'ERR login required';c.sayRefusal=()=>{explained=true;};
  const s=read('firmware/src/web/WebUI.h');const a=s.indexOf('async function runSel()'),b=s.indexOf('\nasync function loadFiles',a);
  vm.runInContext(s.slice(a,b),c);await c.runSel();check(explained,'saved-show Run surfaces command refusal');
 });
 finish();
})();
