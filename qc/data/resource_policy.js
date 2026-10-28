"use strict";
const fs = require('fs'), vm = require('vm');
let failed = 0;
const ok = (value, message) => { console.log((value ? 'PASS ' : 'FAIL ') + message); if (!value) failed++; };
const registry = JSON.parse(fs.readFileSync('config/resource_policy.json', 'utf8')).browser;
function context(hints, denied) {
  const events = {}, c = {console, navigator:hints, CustomEvent:class {constructor(type){this.type=type;}},
    addEventListener:(name,fn)=>{events[name]=fn;}, dispatchEvent(event){if(events[event.type])events[event.type](event);}};
  Object.defineProperty(c,'localStorage',{get(){if(denied)throw Error('denied');return {getItem(){return null;},setItem(){}};}});
  c.window=c;c.MiceResourceRegistry=registry;vm.createContext(c);
  vm.runInContext(fs.readFileSync('shared/web/resources.js','utf8'),c);c.events=events;return c;
}
(async()=>{
  const weak=context({hardwareConcurrency:2,deviceMemory:2},true), strong=context({hardwareConcurrency:16,deviceMemory:16});
  ok(weak.MiceResources.display().id==='light','weak browser remains light independently of the Hub');
  ok(strong.MiceResources.display().id==='fast','capable browser selects the higher display preset');
  ok(context({},true).MiceResources.display().id==='light','missing browser hints and denied storage have a usable fallback');
  weak.MiceResources.setMode('fast');ok(weak.MiceResources.display().id==='fast','explicit display override works even when storage is denied');
  weak.events.storage({key:'mice_display_mode',newValue:null});ok(weak.MiceResources.mode==='auto','clearing browser preferences restores automatic display');
  const renderer={setPixelRatio(v){this.ratio=v;}};weak.MiceResources.applyRenderer(renderer,3);
  ok(renderer.ratio===1,'high screen density is capped on weaker clients');
  const absent=context({},true);delete absent.MiceResourceRegistry;
  const fallback=new absent.MiceResourceClient(null,{},null);
  ok(fallback.display().fps>0 && fallback.display().pixelRatio===1,'missing bootstrap retains a conservative render budget');
  const controlsById={resourceDisplay:{value:'auto'},resourceMode:{value:'fast'}};
  weak.document={addEventListener(){},getElementById:id=>controlsById[id]};weak.onTab=()=>{};
  vm.runInContext(fs.readFileSync('main_python/web/home/parts/settings.js','utf8'),weak);
  weak.MiceResources.setMode('fast');
  ok(controlsById.resourceDisplay.value==='fast','actual settings selector follows policy changes');
  weak.events.storage({key:'mice_display_mode',newValue:null});
  ok(controlsById.resourceDisplay.value==='auto'&&controlsById.resourceMode.value==='fast',
    'cross-tab reset updates only the actual display selector and preserves unsaved Hub edits');
  // Execute actual Studio tick: render throttling cannot throttle playback/control.
  let draws=0,moves=0;const c=weak;
  Object.assign(c,{requestAnimationFrame(){},freezeCheck(){},playTick(){moves++;},distDraw(){},controls:{update(){return false;}},
    playing:false,distShown(){return false;},renderer:{render(){draws++;}},scene:{},activeCam(){return {};}});
  const source=fs.readFileSync('nong/main_python_set_nong/web/app_parts/main_loop.js','utf8');
  const tick=source.slice(source.indexOf('function tick(now) {'),source.indexOf('// Per-joint servo self-test'));
  vm.runInContext('let _dirty3d=2;'+tick,c);
  c.tick(0);c.tick(10);ok(vm.runInContext('_dirty3d',c)===1,'a skipped visual frame does not consume the pending redraw');
  c.tick(50);ok(moves===3 && draws===2,'playback/control ticks continue while only visual frames are limited');
  // A 40 fps profile on a 60 Hz screen paints ~40 times a second, not every
  // second vsync (30): the next frame is due from the last DUE time.
  const pace=new strong.MiceResourceClient({profiles:[{id:'p',fps:40,pixelRatio:1,minCpus:0,minMemoryGiB:0}]},{},null);
  let painted=0;for(let i=0;i<600;i++){const now=i*1000/60;if(pace.frameDue(now)){pace.rendered(now);painted++;}}
  ok(painted>=390&&painted<=401,'a 40 fps profile paints 40 frames a second on a 60 Hz screen ('+painted+' in 10 s)');
  let after=0;for(let i=0;i<60;i++){const now=60000+i*1000/60;if(pace.frameDue(now)){pace.rendered(now);after++;}}
  ok(after<=41,'a long pause does not cause a burst of catch-up frames ('+after+' in 1 s)');
  // Execute actual Hub boot with storage denied: initial scans still start.
  const boot=vm.createContext({console,Promise,document:{hidden:false,getElementById(){return {checked:false};}},
    setInterval(){return 1;},clearInterval(){},showTab(){},scan(){return Promise.resolve();},scanUsb(){return Promise.resolve();},loadShared(){return Promise.resolve();}});
  boot.window=boot;Object.defineProperty(boot,'localStorage',{get(){throw Error('denied');}});
  vm.runInContext(fs.readFileSync('main_python/web/home/parts/boot_scans.js','utf8'),boot);
  await Promise.resolve();await Promise.resolve();
  ok(boot.HOME_SCANNED===true,'denied storage cannot abort Hub initial scans');
  process.exitCode=failed?1:0;
})().catch(error=>{console.error(error);process.exitCode=1;});
