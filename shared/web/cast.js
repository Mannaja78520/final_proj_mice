// Sound to the robot: song, PC sound and microphone, mixed (2026-09-28).
//
// ONE engine, three pages: the board's own page (WebUI.h), the same page
// opened through the hub, and the board's secure talk page (/talk on https,
// SecureTalk.cpp) - the only page a phone browser will give its microphone
// to. The board serves this file from flash, the hub from shared/web, exactly
// like mice.js. So it brings its own helpers instead of leaning on the page.
//
// Up to three sources play through the robot AT THE SAME TIME, each with its
// own switch: a song file from this phone or PC, the sound the PC is playing,
// and the microphone. The browser mixes them (Web Audio), squeezes the peaks
// with a limiter - two loud sources summed past full scale used to wrap round
// and crack - and sends one 16-bit mono stream at the rate the board plays at.
//
// TWO ROADS, picked by how this page was opened:
//   through the hub (?dev=) -> POST to the hub, which paces it out as UDP;
//   the board's own address -> a WebSocket straight to the board (/ws/audio),
//     because a browser cannot send UDP. This is what a phone joined to the
//     robot's own WiFi uses: no hub, no PC.
// The hub routes are called on location.origin on purpose: the shim that makes
// the module page work through the hub rewrites every '/api/' string into
// '/api/dev/', which is right for board commands and wrong for these.
var castOn=false,castCtx=null,castNode=null,castMix=null,castRate=22050,castMisses=0;
var castStream=null,castMicStream=null,castSong=null,castWs=null,castSrc={};
var castResamp={pos:0,last:0};
function castEl(id){ return document.getElementById(id); }
function castSay1(t){ const e=castEl('castStat'); if(e) e.textContent=t; }
function castLog(m){ if(typeof log==='function') log(m); else console.log(m); }
function castRefusal(t){ return typeof refusal==='function' ? refusal(t) : ''; }
function castDev(){ return new URLSearchParams(location.search).get('dev')||''; }
function castWant(k){ const e=castEl('cast_'+k); return !!(e&&e.checked); }
// The PC-sound source only exists where the browser can share a screen or a
// tab with its sound - a desktop Chrome or Edge. A phone has no such picker,
// so the switch is not shown there rather than shown and failing.
function castSetup(){
  const pc=castEl('castPcRow');
  if(pc) pc.style.display=(navigator.mediaDevices&&navigator.mediaDevices.getDisplayMedia
                            &&!/Android|iPhone|iPad/i.test(navigator.userAgent))?'':'none';
}
async function castToggle(){
  if(castOn){ castStop('stopped - the robot is quiet again'); return; }
  return castStart();
}
async function castStart(){
  if(!castWant('song')&&!castWant('pc')&&!castWant('mic')){
    castSay1('switch on at least one: a song, this PC sound or the microphone');
    return;
  }
  // The graph first, so every source has somewhere to go. The browser does
  // the rate change when it can (a proper filter); where it cannot, the
  // low-pass below keeps the JS fallback from folding treble into hiss.
  try{ castCtx=new AudioContext({sampleRate:castRate}); }
  catch(e){ castCtx=new AudioContext(); }
  castMix=castCtx.createGain();
  const lp=castCtx.createBiquadFilter();
  lp.type='lowpass'; lp.frequency.value=castRate*0.45;
  const lim=castCtx.createDynamicsCompressor();
  lim.threshold.value=-6; lim.knee.value=6; lim.ratio.value=20;
  lim.attack.value=0.003; lim.release.value=0.15;
  castNode=castCtx.createScriptProcessor(2048,1,1);
  castMix.connect(lp); lp.connect(lim); lim.connect(castNode);
  castNode.connect(castCtx.destination);   // silent: onaudioprocess writes nothing
  castResamp={pos:0,last:0};
  castOn=true;
  // Sources BEFORE the road: a phone only lets a page start sound or ask for
  // the microphone straight after a tap, and waiting for the robot to answer
  // first uses that moment up (iPhone Safari then refuses play()).
  castCtx.resume();
  for(const k of ['song','pc','mic']) if(castWant(k)) await castSource(k,true);
  if(!castOn) return;
  if(!Object.keys(castSrc).length){ castStop('nothing to send - every source was refused'); return; }
  try{ await castOpen(); }
  catch(e){ castStop(e.message||String(e)); return; }
  if(castSong) castSong.currentTime=0;   // it played while the road opened
  castNode.onaudioprocess=e=>castSend(e.inputBuffer.getChannelData(0));
  castEl('castBtn').textContent='Stop';
  castSay();
}
// Open the road to the board. Either way the board is told the rate first.
async function castOpen(){
  if(castDev()){
    var said={};
    const r=await fetch(location.origin+'/api/stream/start',{method:'POST',
      body:JSON.stringify({dev:castDev(),rate:castRate,name:'live sound'})});
    said=await r.json().catch(()=>({}));
    if(!r.ok||!said.ok) throw new Error(castRefusal(JSON.stringify(said))||
      ('could not start it: '+(said.error||('the hub answered '+r.status))));
    return;
  }
  await new Promise((ok,fail)=>{
    const w=new WebSocket((location.protocol==='https:'?'wss://':'ws://')+location.host+'/ws/audio');
    w.binaryType='arraybuffer';
    const t=setTimeout(()=>{ try{w.close();}catch(e){castLog('! cast: '+e);} fail(new Error(
      'the robot did not answer. Log in on this page first, then press it again.')); },4000);
    w.onopen=()=>{
      clearTimeout(t);
      // The secure talk page has no cookie session: it signs in on the
      // socket itself, over the encrypted link, before anything else.
      if(typeof castAuth==='function'){ const a=castAuth(); w.send('LOGIN '+a.user+' '+a.pass); }
      w.send('START '+castRate); castWs=w; ok();
    };
    w.onmessage=m=>{
      if(typeof m.data==='string'&&m.data.startsWith('ERR')&&castWs===w)
        castStop('the robot said: '+m.data.slice(4));
    };
    w.onerror=()=>{ clearTimeout(t); fail(new Error(
      'the robot refused the sound. Log in on this page first, then press it again.')); };
    w.onclose=()=>{ if(castWs===w&&castOn) castStop('the connection to the robot closed'); };
  });
}
// Switch one source on or off - also while sending, so the song can keep
// playing while the microphone comes and goes.
async function castSource(k,on){
  if(!castOn) return;
  if(!on){
    const s=castSrc[k]; delete castSrc[k];
    if(s){ try{ s.node.disconnect(); if(s.stop) s.stop(); }catch(e){ castLog('! cast: '+e); } }
    if(!Object.keys(castSrc).length) castSay1('every source is off - the robot is quiet, still connected');
    else castSay();
    return;
  }
  if(castSrc[k]) return;
  try{
    if(k==='song'){
      const f=castEl('castFile').files[0];
      if(!f){ castSay1('choose a song file first'); castEl('cast_song').checked=false; return; }
      // createMediaElementSource takes an element over for good, and only
      // once - so each send gets a fresh element (castStop drops it).
      if(!castSong){
        castSong=new Audio(); castSong.loop=true;
        castSong.src=URL.createObjectURL(f); castSong.dataset.name=f.name;
        castSong._node=castCtx.createMediaElementSource(castSong);
      }else if(castSong.dataset.name!==f.name){
        URL.revokeObjectURL(castSong.src);
        castSong.src=URL.createObjectURL(f); castSong.dataset.name=f.name;
      }
      castSong._node.connect(castMix);
      await castSong.play();
      castSrc.song={node:castSong._node,stop:()=>castSong.pause()};
    }else if(k==='mic'){
      if(!window.isSecureContext||!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){
        castEl('cast_mic').checked=false;
        // The board's plain page cannot have the microphone; its secure one
        // can. The button is only on the board's own page (not the hub's).
        const b=castDev() ? null : castEl('castSecure');
        if(b) b.style.display='';
        castSay1('a phone only gives the microphone to a secure page. '
          +(b ? 'Press "Microphone page" below.' : 'Use the song switch, or open the robot through the hub on a PC.'));
        return;
      }
      castMicStream=await navigator.mediaDevices.getUserMedia({audio:{echoCancellation:true,
                                                           noiseSuppression:true,autoGainControl:true}});
      const n=castCtx.createMediaStreamSource(castMicStream);
      n.connect(castMix);
      castSrc.mic={node:n,stop:()=>castMicStream.getTracks().forEach(t=>t.stop())};
    }else if(k==='pc'){
      // THE PICKER CANNOT BE AVOIDED for the PC's own sound: Chrome and Edge
      // on Windows only hand over system audio together with a screen or a
      // tab, and getDisplayMedia with audio alone is refused (user, 2026-09-07).
      castStream=await navigator.mediaDevices.getDisplayMedia({video:true,audio:true});
      // The picture is not wanted and never was: stop the video track at once,
      // so nothing is captured beyond the sound and the sharing bar goes.
      castStream.getVideoTracks().forEach(t=>t.stop());
      if(!castStream.getAudioTracks().length){
        castStream=null; castEl('cast_pc').checked=false;
        castSay1('no sound in what was shared - tick SHARE AUDIO in the picker');
        return;
      }
      const n=castCtx.createMediaStreamSource(castStream);
      n.connect(castMix);
      const s=castStream;
      castSrc.pc={node:n,stop:()=>s.getTracks().forEach(t=>t.stop())};
      // the browser's own stop-sharing button ends this source, not the others
      s.getAudioTracks()[0].onended=()=>{ if(castEl('cast_pc'))castEl('cast_pc').checked=false; castSource('pc',false); };
    }
  }catch(e){
    const box=castEl('cast_'+k); if(box) box.checked=false;
    castSay1(k==='mic'
      ? 'the browser did not give the microphone. Press it again and choose Allow.'
      : k==='pc' ? 'the browser did not share the sound. Pick a screen or a tab and tick SHARE AUDIO.'
      : 'this song would not play here: '+(e.message||e));
  }
}
function castSay(){
  const on=Object.keys(castSrc).map(k=>({song:'the song',pc:'this PC sound',mic:'your microphone'})[k]);
  castSay1('the robot is playing '+on.join(' and '));
}
// One chunk of the mix -> 16-bit PCM -> the road. A dropped chunk is not worth
// a message - the next one is 93 ms away (2048 samples at castRate 22050) -
// but a road that has stopped taking anything IS, or the page sits there
// showing a moving level bar while the robot is silent.
function castSend(f){
  if(!castOn) return;
  const x=castCtx.sampleRate===castRate ? f : castResample(f,castCtx.sampleRate);
  const pcm=new Int16Array(x.length);
  let peak=0;
  for(let i=0;i<x.length;i++){
    const v=Math.max(-1,Math.min(1,x[i]));
    const a=v<0?-v:v; if(a>peak)peak=a;
    pcm[i]=v<0 ? v*32768 : v*32767;
  }
  const lv=castEl('castLevel'); if(lv) lv.textContent='|'.repeat(Math.round(peak*8));
  if(castWs){
    // Half a second already waiting in the socket means the WiFi is behind:
    // skip this chunk rather than let the delay grow for the rest of the song.
    if(castWs.readyState!==1) return;
    if(castWs.bufferedAmount>castRate){ if(++castMisses===20) castSay1(
      'the WiFi to the robot is too slow - move closer, or switch a source off'); return; }
    castMisses=0; castWs.send(pcm.buffer); return;
  }
  fetch(location.origin+'/api/stream/feed',{method:'POST',body:pcm.buffer})
    .then(r=>{ castMisses = r.ok ? 0 : castMisses+1;
               if(castMisses===10) castSay1(
                 'the hub stopped taking the sound - press Stop and start it again'); })
    .catch(()=>{ if(++castMisses===10) castSay1(
                 'the hub is not answering - press Stop and start it again'); });
}
// Only when the browser would not run at castRate (older Safari): linear
// interpolation, carrying the position across chunks so there is no click at
// every seam. The low-pass in the graph has already removed what would alias.
function castResample(f,from){
  const step=from/castRate, out=[];
  let p=castResamp.pos;
  while(p<f.length){
    const i=Math.floor(p), fr=p-i;
    const a=i<0?castResamp.last:f[i], b=f[Math.min(f.length-1,i+1)];
    out.push(a+(b-a)*fr); p+=step;
  }
  castResamp.pos=p-f.length; castResamp.last=f[f.length-1];
  return out;
}
function castStop(why){
  castOn=false;
  // Teardown: an already-closed piece is not worth a line on screen, but it
  // goes in the technical log rather than nowhere - an empty catch is how the
  // four bugs check_modsite_errors was written for got in.
  for(const k of Object.keys(castSrc)){
    try{ castSrc[k].node.disconnect(); if(castSrc[k].stop) castSrc[k].stop(); }catch(e){ castLog('! cast: '+e); }
  }
  castSrc={};
  try{ if(castNode)castNode.disconnect(); }catch(e){ castLog('! cast: '+e); }
  try{ if(castCtx)castCtx.close(); }catch(e){ castLog('! cast: '+e); }
  if(castSong){ castSong.pause(); URL.revokeObjectURL(castSong.src); castSong=null; }
  castNode=castCtx=castStream=castMicStream=castMix=null;
  if(castWs){
    const w=castWs; castWs=null;
    try{ w.send('STOP'); w.close(); }catch(e){ castLog('! cast: '+e); }
  }else if(castDev()){
    fetch(location.origin+'/api/stream/stop',{method:'POST'})
      .catch(()=>{ castSay1('stopped here, but the hub did not '
        +'confirm it. If the robot is still playing, press Stop again.'); });
  }
  const b=castEl('castBtn'); if(b) b.innerHTML='&#127911; Send sound to the robot';
  const lv=castEl('castLevel'); if(lv) lv.textContent='';
  if(why) castSay1(why);
}
if(document.readyState==='loading') document.addEventListener('DOMContentLoaded',castSetup);
else castSetup();
