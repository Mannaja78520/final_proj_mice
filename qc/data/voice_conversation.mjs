import fs from 'fs';
const js = fs.readFileSync(process.argv[2], 'utf8');
const el = id => ({id, style:{}, hidden:true, textContent:'', checked:false, value:'',
  dataset:{}, children:[], options:[], classList:{toggle(){},add(){},remove(){},contains(){return false;}},
  appendChild(){}, prepend(){}, remove(){}, focus(){}, blur(){}, setAttribute(){}, removeAttribute(){},
  scrollIntoView(){}, querySelector(){return null;}, querySelectorAll(){return [];}, addEventListener(){}});
const els = {}, store = {};
globalThis.localStorage = {getItem:k=>store[k]??null,setItem:(k,v)=>{store[k]=String(v);},removeItem:k=>delete store[k]};
globalThis.document = {hidden:false,body:el('body'),querySelector:()=>null,querySelectorAll:()=>[],
  getElementById:id=>els[id]??(els[id]=el(id)),createElement:el,createTextNode:el,addEventListener(){}};
Object.defineProperty(globalThis,'navigator',{configurable:true,value:{mediaDevices:{enumerateDevices:async()=>[]}}});
globalThis.window=globalThis;
globalThis.miceLogin={mount(){}};
globalThis.fetch=async()=>({ok:true,json:async()=>({ok:true,config:{tts:{},stt:{},llm:{}},faqs:[],parts:{},modules:[],sequences:[]})});
eval(js);
const app=globalThis.voiceApp;
async function flush(){for(let i=0;i<45;i++)await Promise.resolve();}
await flush();
const clock={now:0,next:0,jobs:new Map()};
globalThis.setTimeout=(fn,ms=0)=>{const id=++clock.next;clock.jobs.set(id,{at:clock.now+ms,fn});return id;};
globalThis.clearTimeout=id=>clock.jobs.delete(id);
const repeaters=new Set();
globalThis.setInterval=(fn,ms)=>{
  const id=++clock.next;repeaters.add(id);
  const next=()=>{if(!repeaters.has(id))return;fn();if(repeaters.has(id))clock.jobs.set(id,{at:clock.now+ms,fn:next});};
  clock.jobs.set(id,{at:clock.now+ms,fn:next});return id;
};
globalThis.clearInterval=id=>{repeaters.delete(id);clock.jobs.delete(id);};
Date.now=()=>clock.now;
Object.defineProperty(performance,'now',{value:()=>clock.now,configurable:true});
const delay=ms=>new Promise(resolve=>setTimeout(resolve,ms));
async function drain(p,limit=90000){
  let done=false,error,value;p.then(v=>{done=true;value=v;},e=>{done=true;error=e;});
  for(let i=0;i<15000&&!done;i++){
    await flush();if(done)break;
    const first=[...clock.jobs].sort((a,b)=>a[1].at-b[1].at)[0];
    if(!first)throw Error('no scheduled completion');
    const [id,j]=first;if(j.at>limit)throw Error('virtual deadline');
    clock.jobs.delete(id);clock.now=j.at;j.fn();
  }
  await flush();if(error)throw error;if(!done)throw Error('promise did not settle');return value;
}
let intervals=[],tracks=[],denied=false,recorderError=false;
class Track extends EventTarget {stop(){this.stopped=true;}}
function stream(){const track=new Track();tracks.push(track);return {getTracks:()=>[track]};}
class Recorder {
  constructor(){this.state='inactive';}
  start(){this.state='recording';this.startTime=clock.now;
    if(recorderError)setTimeout(()=>this.onerror?.({error:new Error('lost device')}),500);}
  stop(){if(this.state!=='recording')return;this.state='inactive';intervals.push([this.startTime,clock.now]);
    setTimeout(()=>{this.ondataavailable?.({data:new Blob(['recording'])});this.onstop?.();},20);}
}
globalThis.MediaRecorder=Recorder;
class Context {
  createAnalyser(){return {frequencyBinCount:256,getByteTimeDomainData(){}};}
  createMediaStreamSource(){return {connect(){},disconnect(){}};}
  async close(){this.closed=true;}
}
globalThis.AudioContext=Context;
navigator.mediaDevices.getUserMedia=async()=>{if(denied)throw Error('permission denied');return stream();};
const record=app.convRecord.bind(app),listen=app.convListenOnce.bind(app);
const start=app.startConv.bind(app),speak=app.speakAndWait.bind(app),quiet=app.rigQuiet.bind(app);
const move=app.doMove.bind(app);
Object.defineProperty(app,'autoDetect',{value:false,configurable:true});
Object.defineProperty(app,'askLang',{value:'en',configurable:true});
const results=[];
function ok(pass,label,detail){results.push({pass:!!pass,label,detail});}
function reset(speech=[]){
  clock.now=0;clock.jobs.clear();repeaters.clear();intervals=[];tracks=[];denied=false;recorderError=false;
  app.convActive=true;app.convSession+=10;app.convCapture=null;app.convAnalyser=null;
  app.convRms=()=>!speech.some(([a,b])=>a<=clock.now&&clock.now<b);
  app.cfg={tts:{enabled:true},stt:{},use:{speak:['edge','local']}};
  app.svc={use:{speak:['edge','local']}};app.scenarioList=()=>[];
  app.replyOwner=null;app.nativeReply=null;
}
for(const [label,speech,stop] of [
  ['continuous 30 seconds',[[0,30000]],30000],
  ['a 1.2 second thinking pause',[[0,2000],[3200,6000]],7400],
  ['a brief pause',[[0,2000],[2600,5000]],6400],
  ['waiting seven seconds before speaking',[[7000,12000]],13400],
  ['no speech',[],10000]
]){
  reset(speech);const blob=await drain(record(stream(),null,null));
  ok(intervals[0]?.[1]===stop,label+' ends at the correct boundary',intervals);
  ok(blob.size>0===!!speech.length,label+' keeps speech and discards empty microphone noise',blob.size);
  ok(!app.convCapture,label+' releases its recorder owner');
}
reset([[0,30000]]);setTimeout(()=>app.stopConv(),2500);await drain(record(stream(),null,null));
ok(intervals[0][1]===2500,'Stop cancels capture immediately, including deferred recorder stop',intervals);
reset([[0,30000]]);setTimeout(()=>tracks[0].dispatchEvent(new Event('ended')),2000);
const ended=await drain(listen());
ok(ended.size===0&&tracks.every(t=>t.stopped),'an unplugged microphone cancels and releases its track');
app.rigQuiet=async()=>{};app.rigSpokeWithin=async()=>false;
app.addMessageToLog=()=>el('bubble');app.scrollConv=()=>{};
els.sound.checked=false;els.moveOn=el('moveOn');els.moveOn.checked=false;
for(const error of ['denied','recorder']){
  reset([[0,30000]]);app.convActive=false;denied=error==='denied';recorderError=error==='recorder';
  app.convListenOnce=listen;await drain(start());
  ok(!app.convActive&&els.convStop.hidden&&!els.talk.hidden,error+' restores conversation controls');
  ok(tracks.every(t=>t.stopped),error+' releases every microphone track');
}
reset([]);app.convActive=false;let uploads=0;
app.convListenOnce=listen;
globalThis.fetch=async()=>{uploads++;return {ok:true,json:async()=>({ok:false})};};
setTimeout(()=>app.stopConv(),20500);await drain(start());
ok(uploads===0,'idle listening never uploads silence',uploads);

reset([[0,30000]]);let second;
const old=listen();await flush();
setTimeout(()=>{app.stopConv();app.convActive=true;app.convSession++;second=listen();},100);
setTimeout(()=>app.stopConv(),500);
await drain(old);await drain(second);
ok(tracks.length===2&&tracks.every(t=>t.stopped),'rapid Stop/Start releases both independent captures');
ok(!app.convAnalyser&&!app.convCapture,'old capture cleanup cannot retain or erase a new capture');

reset([]);globalThis.fetch=(_u,opts)=>new Promise((_resolve,reject)=>opts.signal.addEventListener('abort',()=>reject(new Error('aborted'))));
await drain(quiet(new AbortController().signal));
ok(clock.now===1200,'a hung rig status request has a bounded wait',clock.now);

reset([]);app.convActive=false;let turns=0;const late=[];
app.convListenOnce=async()=>{if(!turns++)return new Blob(['audio']);await delay(1000);return null;};
app.findRobot=async()=>{await delay(200);return {dev:'fake-nong'};};app.doMove=async()=>{};
els.moveOn.checked=true;
globalThis.fetch=async u=>{
  if(u.includes('/transcribe'))return {json:async()=>({ok:true,text:'hello',language:'en'})};
  if(u.includes('/ask'))return {json:async()=>({ok:true,answer:'hello',lang:'en',move:'hello.yaml',module:'nong'})};
  if(u.includes('/stream/voice'))late.push(u);
  return {json:async()=>({ok:true})};
};
setTimeout(()=>app.stopConv(),100);await drain(start());await drain(delay(300));
ok(!late.length,'a delayed robot lookup cannot start speech after Stop',late);

reset([]);let moves=0;
app.findRobot=async()=>{await delay(200);return {dev:'fake-nong'};};
globalThis.fetch=async(u,opts)=>{if(u==='/api/play'&&opts?.method==='POST')moves++;return {json:async()=>({ok:true})};};
const moveAbort=new AbortController();setTimeout(()=>moveAbort.abort(),100);
await drain(move({move:'hello.yaml',module:'nong'},moveAbort.signal));
ok(!moves,'a delayed lookup cannot start movement after conversation Stop');

reset([]);const motionEvents=[];let posted=0,newMove;
app.findRobot=async()=>({dev:'fake-nong'});
globalThis.fetch=async(u,opts)=>{
  if(u==='/api/play'&&opts?.method==='POST'){
    const n=++posted;motionEvents.push({kind:'play'+n,at:clock.now});
    if(n===1)await delay(500);
  }
  if(u==='/api/play/stop')motionEvents.push({kind:'stop',at:clock.now});
  return {json:async()=>({ok:true,running:false,steps:[]})};
};
const firstMoveAbort=new AbortController();
const firstMove=move({move:'hello.yaml',module:'nong'},firstMoveAbort.signal);
setTimeout(()=>firstMoveAbort.abort(),100);
setTimeout(()=>{newMove=move({move:'hello.yaml',module:'nong'});},200);
await drain(firstMove);await drain(newMove);
const bAt=motionEvents.findIndex(e=>e.kind==='play2');
ok(bAt>0&&!motionEvents.slice(bAt+1).some(e=>e.kind==='stop'),
   'retiring an old pending move cannot stop a newer move',motionEvents);

let speechLog=[],audioLog=[],voiceList=[],nativeError=false,nativeHang=false,nativeEndHang=false;
globalThis.SpeechSynthesisUtterance=class {constructor(text){this.text=text;}};
globalThis.speechSynthesis={speaking:false,pending:false,getVoices:()=>voiceList,
  speak(u){this.pending=true;speechLog.push({at:clock.now,u});this.current=u;
    if(nativeHang)return;
    setTimeout(()=>{if(this.current!==u)return;this.pending=false;
      if(nativeError){u.onerror?.();return;}this.speaking=true;u.onstart?.();
      if(nativeEndHang)return;
      setTimeout(()=>{if(this.current!==u)return;this.speaking=false;this.current=null;u.onend?.();},1000);
    },10);},
  cancel(){this.current=null;this.speaking=false;this.pending=false;}
};
globalThis.Audio=class {
  async play(){audioLog.push({at:clock.now});setTimeout(()=>{if(!this.paused)this.onended?.();},1000);}
  pause(){this.paused=true;}
};
URL.createObjectURL=()=> 'blob:answer';URL.revokeObjectURL=()=>{};
function soundSetup(ms=4000){
  reset([]);speechLog=[];audioLog=[];nativeError=false;nativeHang=false;nativeEndHang=false;
  speechSynthesis.cancel();voiceList=[{name:'Local English',lang:'en-US',localService:true}];
  globalThis.fetch=async(_u,opts)=>{await delay(ms);if(opts.signal.aborted)throw Error('aborted');
    return {ok:true,headers:{get:()=> 'audio/mpeg'},blob:async()=>new Blob(['sound'])};};
}
soundSetup(50);await drain(speak('Hello','en'));
ok(audioLog.length===1&&!speechLog.length,'cached server sound wins without a second voice',{audioLog,speechLog});
soundSetup();await drain(speak('Hello','en'));
ok(speechLog.length===1&&!audioLog.length&&clock.now===1660,'slow server uses one installed voice and waits until it finishes',{audioLog,at:clock.now});
for(const mode of ['disabled','wrong language','remote voice','one voice','mixed voice','scenario','explicit','pitch','scenario rate','scenario pitch','unselected provider']){
  soundSetup();let explicit;
  if(mode==='disabled')app.cfg.tts.fastDeviceVoice=false;
  if(mode==='wrong language')voiceList[0].lang='ja-JP';
  if(mode==='remote voice')voiceList[0].localService=false;
  if(mode==='one voice')app.cfg.tts.oneVoice='chosen';
  if(mode==='mixed voice')app.cfg.tts.mixedVoice='chosen';
  if(mode==='scenario'){app.cfg.scenario='event';app.scenarioList=()=>[{name:'event',voice:'chosen'}];}
  if(mode==='explicit')explicit='chosen';
  if(mode==='pitch')app.cfg.tts.pitch='+5Hz';
  if(mode==='scenario rate'||mode==='scenario pitch'){app.cfg.scenario='event';app.scenarioList=()=>[{name:'event',[mode.split(' ')[1]]:'+10%'}];}
  if(mode==='unselected provider'){app.cfg.use.speak=['edge'];app.svc.use.speak=['edge'];}
  await drain(speak('Hello','en',null,explicit));
  ok(!speechLog.length&&audioLog.length===1,mode+' preserves the selected voice');
}
soundSetup();await drain(speak('Hello คุณทดสอบ','en'));
ok(!speechLog.length&&audioLog.length===1,'a mixed-script name keeps the multilingual server voice');
for(const text of ['Hello Привет','Hello مرحبا','Hello 안녕하세요']){
 soundSetup();await drain(speak(text,'en'));ok(!speechLog.length&&audioLog.length===1,'a foreign-script name preserves the server voice: '+text);
}
soundSetup();voiceList=[];setTimeout(()=>{voiceList=[{lang:'en-US',localService:true}];},300);
await drain(speak('Hello','en'));
ok(speechLog.length===1,'a delayed browser voice list is checked again before speaking');
soundSetup();nativeError=true;await drain(speak('Hello','en'));
ok(audioLog.length===1,'a native start error falls back to server sound');
soundSetup();nativeHang=true;await drain(speak('Hello','en'));
ok(audioLog.length===1&&!speechSynthesis.pending,'a native voice that never starts is canceled before server playback');
for(const stop of [300,800]){
  soundSetup();const ctrl=new AbortController();setTimeout(()=>ctrl.abort(),stop);
  await drain(speak('Hello','en',ctrl.signal));await drain(delay(5000));
  ok(!audioLog.length&&!speechSynthesis.speaking&&!speechSynthesis.pending,'Stop at '+stop+'ms prevents late playback');
}
soundSetup();const oldCtrl=new AbortController();const oldSpeech=speak('Old','en',oldCtrl.signal);
let nextSpeech;setTimeout(()=>{oldCtrl.abort();nextSpeech=speak('New','en');},800);
await drain(oldSpeech);await drain(nextSpeech);
ok(speechLog.length===2&&!audioLog.length&&!speechSynthesis.speaking,'old speech cleanup cannot cancel the new session');
soundSetup();globalThis.fetch=async()=>({ok:true,headers:{get:()=> 'application/json'},json:async()=>({error:'no sound'})});
await drain(speak('Hello','en'));
ok(!audioLog.length&&speechLog.length===1,'a JSON error with HTTP 200 uses an eligible local voice, never an error as audio');
for(const mode of ['offline','http500']){
 soundSetup();globalThis.fetch=async()=>{if(mode==='offline')throw Error('offline');return {ok:false,headers:{get:()=> 'application/json'}};};
 await drain(speak('Hello','en'));ok(speechLog.length===1&&!audioLog.length,mode+' does not outrun a working local voice');
}
soundSetup();nativeEndHang=true;await drain(speak('Hello','en'));
ok(clock.now<=16000&&!speechSynthesis.speaking,'a native voice that starts but never finishes releases conversation');
console.log(JSON.stringify(results));
process.exit(results.every(r=>r.pass)?0:1);
