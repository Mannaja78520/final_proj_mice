"""Voice class parses and preserves startup, settings and request contracts without hardware.

A42-1: the answers sheet saves what is typed in a cell; an answer never names
its voice (the helper picks it); Try plays the speed on screen.
"""
from pathlib import Path
import subprocess

AREA = "tools"
TITLE = "voice class initializes once and keeps settings and conversation state"

SCRIPT = r"""
const assert = require('node:assert/strict');
const vm = require('node:vm');
const fs = require('node:fs');
const nodes = new Map(), events = {}, calls = [];
function node() { return {value:'', checked:false, hidden:true, textContent:'', children:[],
 style:{}, dataset:{}, classList:{toggle(){},remove(){},add(){}}, focus(){}, remove(){},
 addEventListener(n,f){(this.on=this.on||{})[n]=f;},
 appendChild(v){this.children.push(v);}, prepend(){}, querySelector(){return node();}}; }
let mounts = 0;
const context = {console, Blob, AbortController, Uint8Array, setTimeout(){}, clearTimeout(){},
 setInterval(){return 1;}, clearInterval(){}, localStorage:{getItem(){return null;},setItem(){}},
 document:{readyState:'loading', body:node(), getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},
 createElement:node, createTextNode:node, querySelector(){return null;},
 addEventListener(name,fn){events[name]=fn;}},
 miceLogin:{mount(){mounts++;},required(s){return s;}},
 fetch:async (url, options={}) => {calls.push([url, options]);
 // Finding every robot took 10 s (2026-10-15) and the settings stayed empty
 // until it came back: here it never comes back, and the settings must fill.
 if(url.endsWith('/modules/all')) return new Promise(()=>{});
 return {ok:true,status:200,json:async()=>
 url.endsWith('/health')?{ok:true,parts:{stt:'ready'}}:
 url.endsWith('/config')?{ok:true,config:{tts:{},stt:{}}}:
 url.endsWith('/faq')?{ok:true,faqs:[{questions:['hello'],answer:'hi'}]}:
 url.includes('/api/list')?{files:['wave']}:
 url.endsWith('/modules/all')?{modules:[{name:'Nong'}]}:
 {ok:true,answer:'hi',source:'faq'}};}};
context.window=context;
vm.createContext(context);
vm.runInContext(fs.readFileSync(process.argv[1],'utf8'),context);
(async()=>{
 const app=context.voiceApp;
 assert.equal(app.cfg,null);
 events.DOMContentLoaded(); app.init();
 await new Promise(resolve=>setImmediate(resolve));
 assert.equal(mounts,1);
 assert.equal(calls.filter(([u])=>u.endsWith('/health')).length,1);
 // The camera picker is there even with no camera in this browser (A42-1).
 assert.ok(nodes.get('camPick').children.length>=1);
 await context.loadStores();
 assert.equal(app.faqs[0].answer,'hi');
 // A42-1: the answers are a sheet - each cell is typed into where it stands.
 assert.equal(app.sheet.length,1);
 assert.equal(app.sheet[0].ask.value,'hello');
 const en=app.sheet[0].says.en; en.value='hi there'; en.on.input();
 assert.equal(nodes.get('ansSave').disabled,false);
 await context.saveAnswers();
 const saved=JSON.parse(calls.filter(([u,o])=>u.endsWith('/faq')&&o.method==='POST').pop()[1].body).faqs[0];
 assert.equal(saved.answer,'hi'); assert.equal(saved.answer_en,'hi there');
 assert.equal(JSON.stringify(saved.questions),'["hello"]');
 context.document.getElementById('q').value='hello'; await context.ask();
 const request=JSON.parse(calls.find(([u])=>u.endsWith('/ask'))[1].body);
 assert.deepEqual(request,{text:'hello',history:[]});
 // The helper picks the voice: an answer never names one (A42-1), or the
 // scenario's and the one-for-every-language voice are skipped.
 await new Promise(resolve=>setImmediate(resolve));
 const said=calls.filter(([u])=>u.endsWith('/say')).map(([,o])=>JSON.parse(o.body));
 assert.ok(said.length>=1); assert.ok(said.every(b=>!('voice' in b)), JSON.stringify(said));
 assert.equal(app.convHistory.length,2);
 app.convActive=true; const session=app.convSession; context.stopConv();
 assert.equal(app.convActive,false); assert.equal(app.convSession,session+1);
 let recorder;
 context.MediaRecorder=class {constructor(){recorder=this;this.state='inactive';}start(){this.state='recording';}stop(){this.state='inactive';this.onstop();}};
 const pushRecorder={state:'untouched'}; app.rec=pushRecorder;
 await context.convRecord({}, {}, {}, 10);
 assert.equal(app.rec,pushRecorder); assert.equal(recorder.state,'inactive');
 assert.equal(context.convRms(),false);
 // Try plays what is ON SCREEN, before saving: its speed rides along.
 nodes.get('mainLang').value='en'; nodes.get('ttsRate').value='-10%'; let spoken;
 app.speak=(...args)=>{spoken=args;}; context.tryVoice();
 assert.equal(JSON.stringify(spoken),JSON.stringify(['Hello, I am the Mice robot','en',{speed:'-10%',pitch:'+0Hz'}]));
 console.log('voice source regression passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""

def check(source=None):
    source = source or Path(__file__).resolve().parents[2] / "apps/voice/app.js"
    return subprocess.run(["node", "-e", SCRIPT, str(source)], capture_output=True, text=True, timeout=20)

def run(t):
    result = check()
    # The pass line too: a script stuck on a promise that never settles ends
    # with exit 0 and nothing said.
    t.ok(result.returncode == 0 and "regression passed" in result.stdout, TITLE,
         result.stdout + result.stderr or "the script stopped before its last line")

if __name__ == "__main__":
    import sys
    result = check(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(result.stdout + result.stderr, end="")
    raise SystemExit(result.returncode)
