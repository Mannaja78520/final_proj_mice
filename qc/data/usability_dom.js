const fs=require('fs'),vm=require('vm'),path=require('path');
const root=path.resolve(__dirname,'../..'),read=p=>fs.readFileSync(path.join(root,p),'utf8');
class Element {
 constructor(){this.children=[];this._html='';this.style={};this.value='';this.hidden=false;this.disabled=false;this.classList={toggle(){},add(){},remove(){}};this.tBodies=[{innerHTML:''}];}
 get innerHTML(){return this._html;} set innerHTML(v){this._html=String(v);this.children=[];}
 get textContent(){return this._html;}set textContent(v){this._html=String(v);}
 appendChild(n){this.children.push(n);return n;} append(...ns){this.children.push(...ns);}
 getAttribute(k){return this[k]??null;}setAttribute(k,v){this[k]=v;}removeAttribute(k){delete this[k];}
 replaceChildren(...ns){this.children=ns;this._html="";}
 insertAdjacentHTML(_where,s){this._html+=s;}
 querySelectorAll(){return [];}querySelector(){return null;}
}
function context(){
 const elements=new Map(),timers=new Map();let timer=0;
 const el=id=>{if(!elements.has(id))elements.set(id,new Element());return elements.get(id);};
 const c={console,URL,URLSearchParams,AbortController,Date,Map,Set,Promise,setTimeout,clearTimeout,
 setInterval:fn=>{timers.set(++timer,fn);return timer;},clearInterval:id=>timers.delete(id),
 location:{href:'http://fixture.invalid/',origin:'http://fixture.invalid'},
 localStorage:{getItem(){return null;},setItem(){}},onTab(){},addEventListener(){},
 document:{getElementById:el,querySelectorAll(){return[];},querySelector(){return null;},createElement(){return new Element();},addEventListener(){},hidden:false,readyState:"loading",documentElement:new Element(),body:new Element()},
 fetch:async()=>{throw Error('offline fixture');}};
 c.window=c;c.esc=String;c.$=el;c.el=el;c.timers=timers;c.Mice={App:class{},Api:{}};vm.createContext(c);vm.runInContext(read('shared/web/mice-ui.js'),c);return c;
}
function loadClass(c,file,name,end){const s=read(file),a=s.indexOf('class '+name),b=s.indexOf(end,a);if(a<0||b<0)throw Error('class boundary missing '+name);vm.runInContext(s.slice(a,b)+'\nthis.TestClass='+name,c);const obj=Object.create(c.TestClass.prototype);obj.$=c.el;obj.esc=s=>String(s??'');return obj;}
const response=(data,ok=true)=>({ok,status:ok?200:503,json:async()=>data,text:async()=>typeof data==='string'?data:JSON.stringify(data)});
let failures=0;function check(ok,name){console.log((ok?'PASS ':'FAIL ')+name);if(!ok)failures++;}
async function test(name,fn){try{await fn();}catch(e){check(false,name+': '+e.message);}}
module.exports={read,vm,Element,context,loadClass,response,check,test,finish(){process.exitCode=failures?1:0;}};
