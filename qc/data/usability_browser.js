const mark=(key,value)=>qcMark('USABLE~'+key+'='+Boolean(value));
async function frame(path,ready){
 const old=document.querySelector('iframe');if(old)old.remove();
 const f=document.createElement('iframe');f.width=1280;f.height=900;document.body.appendChild(f);f.src=path;
 if(!await qcWaitFor(()=>{try{return f.contentDocument?.readyState==='complete'&&ready(f.contentWindow);}catch(_){return false;}},18000))throw Error('page not ready: '+path);
 return {f,w:f.contentWindow,d:f.contentDocument};
}
window.addEventListener('load',async()=>{
 try{
  {
   const {w,d}=await frame('/',w=>w.MODS?.length&&w.scan);
   w.showTab('modules');const native=w.fetch;
   w.fetch=(url,opts)=>url.startsWith('/api/modules')?Promise.reject(Error('offline fixture')):native.call(w,url,opts);
   await w.scan(true);const button=d.querySelector('#mods .mod button');
   await mark('cached_controls_live',button&&typeof button.onclick==='function');
   await mark('cached_warning_visible',d.querySelector('#mods .banner.err')&&d.querySelector('#mods .stale'));
  }
  {
   const {w,d}=await frame('/app/camera/',w=>w.cameraApp);
   w.fetch=()=>Promise.reject(Error('offline fixture'));await w.cameraApp.load(false);
   await mark('camera_error_not_empty',d.getElementById('none').hidden&&d.getElementById('stat').textContent.length>0);
   w.fetch=()=>Promise.resolve(new w.Response(JSON.stringify({modules:[]})));await w.cameraApp.load(false);
   await mark('camera_empty_after_success',!d.getElementById('none').hidden);
  }
  {
   const {w,d}=await frame('/app/tv/',w=>w.app);
   const a=w.app;clearInterval(a.pollTimer);a.poll=()=>{};a.activeDev='usb:COM99';a.modules=[{dev:a.activeDev}];
   let homes=0;w.fetch=async url=>{if(url.includes('c=HOME'))homes++;return new w.Response(JSON.stringify({running:false,error:'serial port disconnected'}));};
   await a.goHome();await mark('tv_stop_error_blocks_home',homes===0&&d.getElementById('actionStat').textContent.length>0);
   let resolveSeq,plays=0;w.fetch=async url=>url.includes('c=STOP')?new w.Response('OK stopped'):url.startsWith('/api/seqsteps')?new Promise(r=>resolveSeq=r):(url==='/api/play'?(plays++,new w.Response('{"ok":true}')):new w.Response('{"running":false,"error":"","stop_ok":true,"stop_reply":"OK stopped","dev":"usb:COM99","epoch":0}'));
   const pending=a.playSequence('slow');await a.stop();resolveSeq(new w.Response('{"steps":[{"pose":[90],"t":1000}]}'));await pending;
   await mark('tv_stop_cancels_delayed_play',plays===0);
   w.fetch=async()=>new w.Response('{"ok":false,"error":"refused"}',{status:403});d.getElementById('customSpeak').value='keep this';await a.speakCustom();
   await mark('tv_speech_keeps_draft',d.getElementById('customSpeak').value==='keep this');
   d.getElementById('nowSeq').textContent='idle';await mark('tv_action_error_survives_status',d.getElementById('actionStat').textContent.length>0);
  }
  {
   const {w,d}=await frame('/app/voice/',w=>w.voiceApp);
   w.fetch=async()=>new w.Response('{"ok":false,"error":"test helper unavailable"}',{status:503});
   await w.voiceApp.loadModel();await mark('voice_load_retry_enabled',!d.getElementById('btnLoadModel').disabled);
   await w.voiceApp.unloadModel();await mark('voice_unload_retry_enabled',!d.getElementById('btnUnloadModel').disabled);
  }
  {
   const {w,d}=await frame('/app/gacha/',w=>w.gachaApp);
   const body=d.getElementById('logT').tBodies[0];body.innerHTML='<tr><td>cached</td></tr>';
   w.Mice.Api.get=async()=>({ok:false,data:{},says:'offline'});await w.gachaApp.loadLog();
   await mark('log_cache_marked_stale',body.textContent==='cached'&&d.getElementById('logStat').textContent.length>0);
   w.Mice.Api.get=async url=>({ok:true,data:url.includes('/stats')?{stats:{}}:{rows:[]}});await w.gachaApp.loadLog();
   await mark('log_empty_after_success',body.textContent.includes('ยังไม่มี'));
  }
  {
   const {w,d}=await frame('/mod?dev=usb%3ACOM99',w=>typeof w.liftStatus==='function'&&typeof w.runSel==='function');
   const fault={state:'fault',fault:'home_timeout',stage:-1,stages:4,enc:false,homed:false};w.liftStatus(fault);
   await mark('lift_fault_visible',!d.getElementById('liftFault').hidden&&d.getElementById('stg').textContent==='?');
   const moves=[...d.querySelectorAll('#liftCard [data-lift-motion],#gotoBtns button')];
   await mark('lift_fault_disables_motion',moves.length>=5&&moves.every(b=>b.disabled));
   await mark('lift_stop_remains_enabled',!d.querySelector('#liftCard button.danger').disabled);
   const sent=[];w.cmd=async command=>{sent.push(command);return 'OK fault cleared';};
   d.querySelector('#liftFault button').click();await new Promise(r=>setTimeout(r,50));
   await mark('lift_clear_never_moves',sent.length===1&&sent[0]==='FAULT CLEAR');
   w.liftStatus({...fault,state:'idle',fault:''});await mark('lift_clear_status_restores_controls',d.getElementById('liftFault').hidden&&moves.every(b=>!b.disabled));
   d.getElementById('moveSel').innerHTML='<option value="/moves/demo.yaml">demo</option>';w.cmd=async()=> 'ERR log in first';await w.runSel();
   d.getElementById('seqStat').textContent='idle';await mark('saved_run_refusal_persists',d.getElementById('moveRunStat').textContent.includes('locked'));
  }
 }catch(error){await qcMark('USABLE~error='+String(error));}
 await qcMark('done');
});
