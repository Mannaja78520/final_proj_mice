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
