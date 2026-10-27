const {read,vm,Element,context,response,check,test,finish}=require('./usability_dom');
(async()=>{
 await test('modules stale controls',async()=>{
  const c=context();vm.runInContext(read('main_python/web/home/parts/modules.js'),c);
  c.MODS=[{name:'cached'}];c.modsHtml='<div>cached</div>';c.modsAt=Date.now();
  c.filterMods=()=>{};c.repaintMods=()=>{c.el('mods').innerHTML='';const b=new Element();b.onclick=()=>{};c.el('mods').appendChild(b);};
  await c.scan(true);check(c.el('mods').children.some(n=>typeof n.onclick==='function'),'failed refresh keeps cached row handlers');
  let reject;c.fetch=()=>new Promise((_,no)=>reject=no);const older=c.scan(false);
  c.fetch=async()=>response({modules:[{name:'new'}]});c.mergeFar=()=>{};
  await c.scan(false);const html=c.el('mods').innerHTML;reject(Error('old failure'));await older;
  check(c.el('mods').innerHTML===html,'old scan rejection cannot replace newer rows');
 });
 await test('Home failed discovery',async()=>{
  const c=context();c.paintLastOpened=()=>{};c.MODS=[];c.HOME_SCANNED=true;c.MODS_ERROR=true;
  vm.runInContext(read('main_python/web/home/parts/home.js'),c);c.paintHome();
  check(!c.el('homeSum').textContent.includes('No modules found'),'Home distinguishes failed discovery from empty');
 });
 await test('network identity and partial failure',async()=>{
  const c=context();c.esc=String;vm.runInContext(read('main_python/web/home/parts/network.js'),c);c.netPick=()=>{c.el('netact').innerHTML='selection changed';};
  c.fetch=async url=>response(url==='/api/scan'?{modules:[{id:1,chip:'aaaa',name:'same',type:'nong',ip:'fake.invalid'}]}:url==='/api/ports'?{ports:[{port:'COM99'}]}:{usb:[{port:'COM99',module:{id:2,chip:'bbbb',name:'same',type:'nong'}}]});
  await c.loadNet();check(c.netMods.length===2,'same-name modules retain distinct chip identities');
  c.fetch=async url=>{if(url.startsWith('/api/scanusb'))throw Error('probe refused');return response(url==='/api/scan'?{modules:[]}:{ports:[{port:'COM99'}]});};
  await c.loadNet();check(!c.el('netlist').textContent.includes("haven't found any"),'failed USB probe does not become empty advice');
  const html=read('main_python/web/home/parts/network.html');check(html.includes('id="grpout"'),'group result exists outside refreshed selection controls');
 });
 await test('remote bus firmware target',async()=>{
  const c=context();vm.runInContext(read('main_python/web/home/parts/firmware.js'),c);
  c.whoAmI=async()=>'local';c.fetch=async url=>response(url==='/api/allmods'?{host:'local',modules:[{id:3,name:'bus-child',type:'nong',host:'far',hostIp:'192.0.2.1',dev:'hub:192.0.2.1/usb:COM7:3'}]}:url==='/api/ports'?{ports:[]}:{modules:[]});
  const boards=await c.fwBoards();check(!boards.some(b=>b.farPort==='COM7'),'remote bus child never offers gateway cable flashing');
 });
 finish();
})();
