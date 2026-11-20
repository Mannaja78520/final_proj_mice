"""A57-1: one portable project opens motion and music without losing work or driving hardware."""
import base64
import hashlib
import io
import json
import subprocess
import wave
import browser
import fake_serial
import qc as F

AREA='studio'
TITLE='latest results and portable motion/music project preserve work and one preview clock'
SLOW=True

DRIVER=r'''
function mark(s){ qcMark('LIBA~'+s); }
const nap=ms=>new Promise(r=>setTimeout(r,ms));
async function until(fn){for(let i=0;i<100;i++){if(fn())return;await nap(40);}throw Error('condition timeout');}
window.addEventListener('load',()=>qcStudioReady().then(async()=>{
 const nativeConfirm=window.confirm;window.confirm=()=>true;
 const originalFetch=window.fetch;
 const motionFunctions={sendPoseLive,liveSend,hubStop,safeDeviceCmd};const motionCalls=[];
 sendPoseLive=(...a)=>{motionCalls.push('pose');return Promise.resolve(false);};
 liveSend=(...a)=>{motionCalls.push('send');return Promise.resolve(false);};
 hubStop=(...a)=>{motionCalls.push('hubStop');return Promise.resolve(false);};
 safeDeviceCmd=(...a)=>{motionCalls.push('device');return Promise.resolve(false);};
 let oldGet,oldModels;
 try {
  const track=__TRACK__;
  const neutral=RIG.neutral.slice(),q=neutral.slice();q[0]+=3;
  const project={keys:[{pose:neutral,t:0,hold:0},{pose:q,t:600,hold:0},{pose:neutral,t:600,hold:0}],
    speedDps:120,maxDps:400,safeDps:400,loop:false,seqName:'qc_library_audio',sourceAudioAsset:track};
  window.fetch=(input,opts)=>{
    const url=String(input);
    if(url.includes('/app/latest-results/catalog.json'))return Promise.resolve(new Response(JSON.stringify({items:[{id:'sample',title:'ชุดทดสอบพร้อมเพลง',version:'test',projectUrl:'/app/latest-results/bundles/sample.nong.json'}]}),{status:200}));
    if(url.includes('/app/latest-results/bundles/sample.nong.json'))return Promise.resolve(new Response(JSON.stringify(project),{status:200}));
    return originalFetch(input,opts);
  };
  localStorage.setItem('nong_ask_unsaved','0');
  $('liveChk').checked=true;
  await projectLibrary.open();mark('catalog='+document.querySelectorAll('.library-item').length);
  const imported=await applyProjectData(project,'qc_library_audio.json',{imported:true});
  mark('import='+imported+'~keys='+keys.length+'~audio='+!!sequenceAudio.asset+'~dirty='+isDirty());
  mark('clocklength='+totalMs());
  const signature=workSig();
  for(const malformed of [{seqName:123},{keys:project.keys.map(k=>({...k,cues:123}))},{addons:{}}]){
    let rejected=false;try{await applyProjectData({...project,...malformed},'bad-schema.json');}catch(e){rejected=true;}
    mark('schema='+String(rejected&&workSig()===signature));
  }
  try {await applyProjectData({...project,keys:[{pose:[]}]},'broken.json');mark('invalid-missed');}catch(e){mark('invalid='+String(workSig()===signature));}
  try {await applyProjectData({...project,sourceAudioAsset:{...track,sha256:'0'.repeat(64)}},'bad-audio.json');mark('bad-audio-missed');}catch(e){mark('bad-audio='+String(workSig()===signature));}
  localStorage.setItem('nong_ask_unsaved','1');
  const pending=applyProjectData({...project,sourceAudioAsset:{...track,name:'another.wav'}},'cancel.json',{imported:true});
  await until(()=>document.getElementById('unsavedDlg')?.open);document.getElementById('unsavedCancel').click();
  mark('cancel='+String(!(await pending)&&workSig()===signature));
  localStorage.setItem('nong_ask_unsaved','0');
  const saved=await saveAll();mark('saved='+saved+'~clean='+!isDirty());
  const got=await Mice.Api.get('/api/load?name=qc_library_audio.json');
  mark('embedded='+String(got.ok&&got.data.sourceAudioAsset.dataUrl===track.dataUrl));
  sequenceAudio.commit(null);await loadProject('qc_library_audio.json');
  mark('reopen='+String(keys.length===3&&sequenceAudio.asset.sha256===track.sha256&&!isDirty()));
  const oldSig=workSig();await loadProject('qc_library_does_not_exist.json');mark('missing='+String(workSig()===oldSig));
  oldModels=refreshModels;refreshModels=()=>Promise.reject(new Error('model list unavailable'));
  try{await applyProjectData({...project,sourceAudioAsset:null},'models-fail.json');mark('models-missed');}catch(e){mark('models='+String(workSig()===oldSig));}
  refreshModels=oldModels;oldModels=null;
  oldGet=Mice.Api.get;let release;
  Mice.Api.get=path=>path.includes('slow.json')?new Promise(r=>release=r):oldGet.call(Mice.Api,path);
  const slow=loadProject('slow.json');
  await applyProjectData({...project,sourceAudioAsset:{...track,name:'newest.wav'}},'newest.json',{imported:true});
  release({ok:true,data:{...project,sourceAudioAsset:null}});await slow;Mice.Api.get=oldGet;oldGet=null;
  mark('stale='+String(sequenceAudio.asset.name==='newest.wav'));
  await sequenceAudio.cache(sequenceAudio.asset);const ref=sequenceAudio.draftRef();
  sequenceAudio.commit(null);
  const prepareAudio=sequenceAudio.prepare.bind(sequenceAudio);let releaseAudio;
  sequenceAudio.prepare=()=>new Promise(resolve=>releaseAudio=resolve);
  const restoring=sequenceAudio.restore(ref);const restoreSig=sequenceAudio.signature();
  await togglePlay();const saveBlocked=!(await saveAll());saveDraft();await nap(500);
  mark('restoreguard='+String(!playing&&saveBlocked&&sequenceAudio.draftRef().sha256===ref.sha256&&sequenceAudio.signature()===restoreSig&&JSON.parse(localStorage.getItem(DRAFT_KEY)).sourceAudioAsset.sha256===ref.sha256));
  releaseAudio(await prepareAudio(ref));await restoring;sequenceAudio.prepare=prepareAudio;
  mark('draftaudio='+String(sequenceAudio.asset?.sha256===track.sha256));
  const recoveredKeys=JSON.stringify(keys);sequenceAudio.commit(null);
  sequenceAudio.prepare=()=>Promise.reject(new Error('missing cached audio'));await sequenceAudio.restore(ref);
  await togglePlay();const blockedRecovery=!playing&&!(await saveAll())&&sequenceAudio.draftRef().sha256===ref.sha256;
  sequenceAudio.prepare=prepareAudio;
  await applyProjectData({...project,keys:project.keys.slice(0,2)},'recover-song.nong.json',{imported:true});
  mark('recoverymerge='+String(blockedRecovery&&JSON.stringify(keys)===recoveredKeys&&sequenceAudio.asset.sha256===ref.sha256&&!sequenceAudio.pendingRef));

  // Explicit preview remains isolated even when a user had Live checked.
  $('liveChk').checked=true;
  const playMedia=sequenceAudio.media.play.bind(sequenceAudio.media);
  sequenceAudio.media.play=()=>Promise.reject(new DOMException('blocked by browser','NotAllowedError'));
  await sequenceAudio.toggle();mark('policy='+String(!playing&&sequenceAudio.media.paused&&$('sequenceAudioStatus').textContent.includes('กด')));
  sequenceAudio.media.play=playMedia;
  await sequenceAudio.toggle();mark('startstate='+JSON.stringify({playing,paused:sequenceAudio.media.paused,previewOnly,entryHold,stat:$('tlStat').textContent,audio:$('sequenceAudioStatus').textContent,notice:$('noticeText').textContent}));await until(()=>playing&&!sequenceAudio.media.paused);
  sequenceAudio.media.currentTime=.65;await nap(120);
  mark('mediaclock='+String(Math.abs(playT-sequenceAudio.media.currentTime*1000)<100&&playT>600));
  sequenceAudio.pausePreview();const held=playT;await nap(100);mark('pause='+String(!playing&&sequenceAudio.media.paused&&playT===held));
  scrubTo(250);mark('seek='+String(!playing&&Math.abs(playT-totalMs()/4)<1&&Math.abs(sequenceAudio.media.currentTime*1000-playT)<2));
  selectKey(1);rewind();mark('rewind='+String(playT===0&&!playing));
  await sequenceAudio.toggle();await until(()=>playing&&!sequenceAudio.media.paused);keys[1].pose[0]+=.5;bumpKeys();
  mark('editpause='+String(!playing&&sequenceAudio.media.paused));
  timelinePreparing=true;await togglePlay({previewOnly:true,sequenceAudio:true});mark('cancelplan='+String(!timelinePreparing&&!playing));
  sequenceAudio.asset.offsetMs=250;sequenceAudio.restart();mark('offsetloop='+String(!!sequenceAudio.head&&sequenceAudio.media.paused));sequenceAudio.asset.offsetMs=0;sequenceAudio.rewind(0);
  const snapshot=projectSnapshot();mark('downloadpair='+String(snapshot.keys.length===3&&snapshot.sourceAudioAsset.dataUrl===track.dataUrl));
  mark('transportcalls='+motionCalls.length);
  $('liveChk').checked=false;
  loadParsedSeq({keys:project.keys,speed:120,loop:false,cues:0,skipped:0},'sequences/qc_other.yaml');
  mark('replaceclear='+String(!sequenceAudio.asset&&!projectSnapshot().sourceAudioAsset));
  await projectLibrary.open();const box=$('projectLibrary').getBoundingClientRect();
  mark('modalfit='+String(box.left>=0&&box.right<=innerWidth+1));$('projectLibrary').close();
 }catch(e){mark('ERR-'+(e.stack||e));}
 finally{
  if(oldGet)Mice.Api.get=oldGet;
  if(oldModels)refreshModels=oldModels;
  ({sendPoseLive,liveSend,hubStop,safeDeviceCmd}=motionFunctions);
  sequenceAudio.pausePreview();window.confirm=nativeConfirm;window.fetch=originalFetch;
  localStorage.removeItem('nong_ask_unsaved');mark('done');qcMark('done');
 }
}));
'''


def run(t):
    buf=io.BytesIO()
    with wave.open(buf,'wb') as w:w.setnchannels(1);w.setsampwidth(2);w.setframerate(8000);w.writeframes(b'\0\0'*9600)
    raw=buf.getvalue();track=dict(name='test song.wav',mediaType='audio/wav',sha256=hashlib.sha256(raw).hexdigest(),dataUrl='data:audio/wav;base64,'+base64.b64encode(raw).decode(),offsetMs=0)
    source=F.CODE/'nong/main_python_set_nong/web/app_parts/project_audio_digest.js'
    vectors=[b'',b'abc',bytes(range(256)),b'x'*55,b'x'*56,b'x'*63,b'x'*64,b'x'*65,raw]
    script=source.read_text(encoding='utf-8')+'\nconsole.log(JSON.stringify('+json.dumps([list(v) for v in vectors])+'.map(x=>StudioAudioDigest.portable(Uint8Array.from(x)))));'
    result=subprocess.run(['node','-'],input=script,capture_output=True,text=True,encoding='utf-8')
    t.ok(result.returncode==0,'portable SHA-256 fallback executes',result.stderr[-500:])
    if result.returncode==0:t.eq(json.loads(result.stdout),[hashlib.sha256(v).hexdigest() for v in vectors],'LAN fallback matches independent SHA-256 vectors and actual WAV')
    paths=[F.STUDIO/'projects/qc_library_audio.json',F.STUDIO/'sequences/qc_library_audio.yaml']
    backups={p:p.read_bytes() if p.exists() else None for p in paths}
    fake_serial.reset();base,_main=F.start_hub()
    try:
        browser.page(DRIVER.replace('__TRACK__',json.dumps(track)),query=base+'/studio/_qcdriver.html',seconds=35,flags=('--autoplay-policy=no-user-gesture-required',))
        marks=[m[5:] for m in fake_serial.qc_marks if m.startswith('LIBA~')]
        t.ok(bool(marks) and not any(m.startswith('ERR-') for m in marks),'driver completes without thrown errors',marks[-5:])
        t.eq(marks.count('schema=true'),3,'all three malformed supported-field fixtures preserve accepted state')
        for expected,label in [
            ('catalog=1','library is visible and offers a ready item'),
            ('import=true~keys=3~audio=true~dirty=true','import has editable keys plus song and remains unsaved until Save'),
            ('clocklength=1200','import preserves fixed original timeline'),
            ('schema=true','malformed names, cues and addons are rejected before any project state changes'),
            ('restoreguard=true','pending draft audio preserves its reference and blocks Play and Save'),
            ('invalid=true','invalid keys do not replace accepted motion or audio'),
            ('bad-audio=true','mismatched/corrupt audio is rejected before mutation'),
            ('cancel=true','unsaved-work Cancel preserves both timeline and song'),
            ('saved=true~clean=true','Save retains the complete pair and marks clean'),
            ('embedded=true','saved project contains portable song bytes'),
            ('reopen=true','normal saved-project reopen restores song and motion'),
            ('missing=true','missing project retains existing pair'),
            ('models=true','fallible model preflight cannot replace accepted project/audio on failure'),
            ('stale=true','late old response cannot overwrite a newer import'),
            ('recoverymerge=true','matching song recovery preserves restored edited keys after a missing-cache failure'),
            ('draftaudio=true','draft audio identity restores from persistent browser cache'),
            ('policy=true','blocked autoplay stops preview and explains the required user gesture'),
            ('mediaclock=true','preview follows media time after a seek, not an independent clamped timer'),
            ('pause=true','pause stops music and motion together'),
            ('seek=true','scrub uses the same audio/time position'),
            ('rewind=true','key selection and rewind remain preview-only'),
            ('editpause=true','editing audio preview pauses both clocks without stopping hardware'),
            ('cancelplan=true','cancelling preview preparation stays draw-only'),
            ('offsetloop=true','loop restart honors leading audio offset silence'),
            ('downloadpair=true','download serialization includes the complete editable pair'),
            ('transportcalls=0','Live import/draw/seek/edit/cancel preview invokes no transport helpers'),
            ('replaceclear=true','loading another sequence cannot inherit the previous song'),
            ('modalfit=true','library dialog stays within viewport')]:t.ok(expected in marks,label,marks[-6:])
        motion=[line for line in fake_serial.wire if str(line).startswith(('POSE ','JOINT ','MOVE ')) and 'QCMARK' not in str(line)]
        t.ok(not motion,'opening, seeking and playing audio preview sends no motion commands',motion[-5:])
    finally:
        browser.kill()
        for p,content in backups.items():
            if content is None:p.unlink(missing_ok=True)
            else:p.write_bytes(content)
