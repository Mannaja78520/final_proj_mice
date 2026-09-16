"""Voice class parses and preserves startup, settings and request contracts without hardware."""
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
 style:{}, classList:{toggle(){}}, addEventListener(){}, focus(){}, remove(){},
 appendChild(v){this.children.push(v);}, prepend(){}, querySelector(){return node();}}; }
let mounts = 0;
const context = {console, Blob, AbortController, Uint8Array, setTimeout(){}, clearTimeout(){},
 setInterval(){return 1;}, clearInterval(){}, localStorage:{getItem(){return null;},setItem(){}},
 document:{readyState:'loading', body:node(), getElementById(id){if(!nodes.has(id))nodes.set(id,node());return nodes.get(id);},
 createElement:node, createTextNode:node, querySelector(){return null;},
 addEventListener(name,fn){events[name]=fn;}},
 miceLogin:{mount(){mounts++;},required(s){return s;}},
 fetch:async (url, options={}) => {calls.push([url, options]);return {ok:true,status:200,json:async()=>
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
 await context.loadStores();
 assert.equal(app.faqs[0].answer,'hi');
 context.openForm(0);
 assert.equal(nodes.get('aQ').value,'hello');
 await context.postFaqs();
 assert.equal(JSON.parse(calls.find(([u,o])=>u.endsWith('/faq')&&o.method==='POST')[1].body).faqs[0].answer,'hi');
 context.document.getElementById('q').value='hello'; await context.ask();
 const request=JSON.parse(calls.find(([u])=>u.endsWith('/ask'))[1].body);
 assert.deepEqual(request,{text:'hello',history:[]});
 assert.equal(app.convHistory.length,2);
 app.convActive=true; const session=app.convSession; context.stopConv();
 assert.equal(app.convActive,false); assert.equal(app.convSession,session+1);
 let recorder;
 context.MediaRecorder=class {constructor(){recorder=this;this.state='inactive';}start(){this.state='recording';}stop(){this.state='inactive';this.onstop();}};
 const pushRecorder={state:'untouched'}; app.rec=pushRecorder;
 await context.convRecord({}, {}, {}, 10);
 assert.equal(app.rec,pushRecorder); assert.equal(recorder.state,'inactive');
 assert.equal(context.convRms(),false);
 nodes.get('ttsLang').value='en'; let spoken;
 app.speak=(...args)=>{spoken=args;}; context.tryVoice();
 assert.deepEqual(spoken,['Hello, I am the Mice robot','en']);
 console.log('voice source regression passed');
})().catch(e=>{console.error(e);process.exitCode=1;});
"""

def check(source=None):
    source = source or Path(__file__).resolve().parents[2] / "apps/voice/app.js"
    return subprocess.run(["node", "-e", SCRIPT, str(source)], capture_output=True, text=True, timeout=20)

def run(t):
    result = check()
    t.ok(result.returncode == 0, TITLE, result.stdout + result.stderr)

if __name__ == "__main__":
    import sys
    result = check(Path(sys.argv[1]) if len(sys.argv) > 1 else None)
    print(result.stdout + result.stderr, end="")
    raise SystemExit(result.returncode)
